"""オークションシート画像をClaude APIのVision機能で解析するモジュール。

成長の仕組み:
  1. app/knowledge/auction_sheet_knowledge.md ... ベースとなる評価基準の知識(ユーザーが設定画面から編集可能)
  2. app/knowledge/learned_rules.md ... フィードバック/購入後結果/AIの自己振り返りから蓄積されたルール
  両方をシステムプロンプトに組み込むことで、使えば使うほど判定の説明・精度が育っていく設計。
"""
import base64
import json
import os
import re

import requests

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

KNOWLEDGE_DIR = os.path.join(os.path.dirname(__file__), "knowledge")
BASE_KNOWLEDGE_PATH = os.path.join(KNOWLEDGE_DIR, "auction_sheet_knowledge.md")
LEARNED_RULES_PATH = os.path.join(KNOWLEDGE_DIR, "learned_rules.md")

DEFAULT_MODEL = "claude-sonnet-4-5"

RESPONSE_SCHEMA_HINT = """
必ず次のJSON形式のみで回答してください（前後に説明文やコードブロック記号は付けないこと）。

{
  "auction_house": "会場名（読み取れなければ null）",
  "overall_grade": "総合評価点（例: 4.5, R, 3.5 など。読み取れなければ null）",
  "exterior_grade": "外装個別評価（例: C。読み取れなければ null）",
  "interior_grade": "内装評価（例: B。読み取れなければ null）",
  "mileage_km": "走行距離（数値のみ。読み取れなければ null）",
  "grade_explanation": "総合評価点・内外装評価が何を意味するか、日本語の平易な説明",
  "damage_points": [
    {"location": "傷/凹みなどがある部位（日本語、例: 右フロントフェンダー）", "symbol": "シート記号（例: A2）", "meaning": "記号の意味の説明", "severity": "low | medium | high"}
  ],
  "equipment_and_remarks": ["特記事項欄・装備欄の内容を平易な日本語にしたリスト"],
  "risk_flags": ["修復歴・メーター不明・臭い・冠水など、購入前に必ず確認すべき懸念点のリスト（無ければ空配列）"],
  "user_criteria_check": [
    {"criterion": "ユーザー独自の仕入れ基準の項目名（例: 評価点3.5超, 走行5万km以下, 色, ルーフU3以上, 元レンタカー, 半事故車, トヨタ/ホンダA1A2板金なし基準 等）", "status": "pass | fail | unknown", "note": "判断根拠の短い説明"}
  ],
  "export_notes": "オーストラリア輸出前提での注意点（ADRコンプライアンス、RAWS/SEVSの輸入方式確認、冠水歴、RHDは問題なし等）があれば記載。特筆事項がなければ null",
  "cost_reference_note": "知識ベースのコスト参考情報（手数料・陸送費・部品交換費用の目安）に照らして、参考になる一言があれば記載。断定的な総額は出さず目安として。特になければ null",
  "verdict": "buy | conditional | avoid",
  "verdict_label": "買い | 条件付き買い | 見送り推奨",
  "verdict_reason": "上記の根拠を踏まえた総合判断の理由（3〜6文程度、具体的に）",
  "confidence": "high | medium | low",
  "checklist_before_bid": ["入札前に確認・現車チェックすべき項目のリスト"],
  "disclaimer": "AI解析はシート記載内容に基づく推定であり現車確認に代わるものではない旨の一言"
}
"""


def _read_file(path):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    return ""


def _learned_rules_text():
    text = _read_file(LEARNED_RULES_PATH).strip()
    if not text:
        return "（まだ蓄積された学習ルールはありません。基本ルールのみで判定します。）"
    return text


def build_system_prompt():
    base_knowledge = _read_file(BASE_KNOWLEDGE_PATH)
    learned = _learned_rules_text()
    return f"""あなたは日本の中古車オークションシート（USS・TAA・JUなど）を読み解くベテラン査定アドバイザーです。
アップロードされた画像から、車両評価点・内外装評価・車両図の傷/凹み記号・特記事項を正確に読み取り、
車に詳しくない人にも分かるように徹底的に解説し、「買いかどうか」を根拠とともに判定してください。

# 基礎知識（オークションシートの読み方）
{base_knowledge}

# これまでのフィードバック・実績から蓄積された学習ルール（基礎知識より優先して適用すること）
{learned}

# 出力形式
{RESPONSE_SCHEMA_HINT}

画像が不鮮明、または一部の項目が読み取れない場合は、無理に断定せず null にするか
grade_explanation や risk_flags の中でその旨を明記してください。誠実さを最優先してください。
"""


def _extract_json(text):
    text = text.strip()
    # コードブロックで囲まれていた場合に備えて除去
    text = re.sub(r"^```(json)?", "", text.strip())
    text = re.sub(r"```$", "", text.strip())
    # 最初の { から最後の } までを抜き出す(念のため)
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1:
        text = text[start : end + 1]
    return json.loads(text)


def _call_claude(api_key, model, max_tokens, messages, system=None):
    headers = {
        "x-api-key": api_key,
        "anthropic-version": ANTHROPIC_VERSION,
        "content-type": "application/json",
    }
    body = {"model": model, "max_tokens": max_tokens, "messages": messages}
    if system:
        body["system"] = system

    resp = requests.post(ANTHROPIC_API_URL, headers=headers, json=body, timeout=120)
    if resp.status_code != 200:
        try:
            detail = resp.json().get("error", {}).get("message", resp.text)
        except Exception:  # noqa: BLE001
            detail = resp.text
        raise RuntimeError(f"Anthropic API エラー ({resp.status_code}): {detail}")

    data = resp.json()
    return "".join(
        block.get("text", "") for block in data.get("content", []) if block.get("type") == "text"
    )


def _call_gemini(api_key, model, max_tokens, user_parts, system=None):
    """Gemini API (generateContent) を呼び出してテキストを返す。
    user_parts: [{"text": ...}] や [{"inline_data": {...}}, {"text": ...}] の形式。"""
    url = GEMINI_API_URL.format(model=model)
    body = {
        "contents": [{"role": "user", "parts": user_parts}],
        "generationConfig": {"maxOutputTokens": max_tokens},
    }
    if system:
        body["systemInstruction"] = {"parts": [{"text": system}]}

    resp = requests.post(
        url,
        params={"key": api_key},
        json=body,
        timeout=120,
    )
    if resp.status_code != 200:
        try:
            detail = resp.json().get("error", {}).get("message", resp.text)
        except Exception:  # noqa: BLE001
            detail = resp.text
        raise RuntimeError(f"Gemini API エラー ({resp.status_code}): {detail}")

    data = resp.json()
    try:
        parts = data["candidates"][0]["content"]["parts"]
    except (KeyError, IndexError):
        raise RuntimeError(f"Gemini APIから想定外の応答: {str(data)[:300]}")
    return "".join(p.get("text", "") for p in parts)


def analyze_image(image_path, api_key, model=DEFAULT_MODEL, provider="anthropic"):
    """画像を解析してdictを返す。失敗時は例外を投げる。"""
    with open(image_path, "rb") as f:
        image_bytes = f.read()
    b64 = base64.standard_b64encode(image_bytes).decode("utf-8")

    ext = os.path.splitext(image_path)[1].lower()
    media_type = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
        ".gif": "image/gif",
    }.get(ext, "image/jpeg")

    system_prompt = build_system_prompt()
    instruction = "この中古車オークションシートを解析し、指定されたJSON形式のみで回答してください。"

    if provider == "gemini":
        user_parts = [
            {"inline_data": {"mime_type": media_type, "data": b64}},
            {"text": instruction},
        ]
        raw_text = _call_gemini(api_key, model, 4000, user_parts, system=system_prompt)
    else:
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": b64,
                        },
                    },
                    {"type": "text", "text": instruction},
                ],
            }
        ]
        raw_text = _call_claude(api_key, model, 4000, messages, system=system_prompt)

    parsed = _extract_json(raw_text)
    parsed["_raw_text"] = raw_text
    parsed["_model"] = f"{provider}:{model}"
    return parsed


def synthesize_growth_rules(api_key, feedback_rows, outcome_rows, model=DEFAULT_MODEL, provider="anthropic"):
    """蓄積されたフィードバックと購入後結果をAIに振り返らせ、
    今後の判定に反映すべきルール文を提案させる（成長トリガー）。"""
    feedback_text = "\n".join(
        f"- 判定「{r['analysis_verdict']}」に対する評価: {r['rating']} / コメント: {r['comment'] or '(なし)'}"
        for r in feedback_rows
    ) or "(フィードバックはまだありません)"

    outcome_text = "\n".join(
        f"- 判定「{r['analysis_verdict']}」/ 購入: {r['purchased']} / 実際の状態: {r['actual_condition'] or '-'} "
        f"/ 修理費用: {r['repair_cost'] if r['repair_cost'] is not None else '-'}円 "
        f"/ シートになかった問題: {r['hidden_issues'] or '-'} / 満足度: {r['satisfaction'] or '-'}"
        for r in outcome_rows
    ) or "(購入後の結果報告はまだありません)"

    current_rules = _learned_rules_text()

    prompt = f"""あなたは中古車オークションシート解析AIの「振り返り」を行うアシスタントです。
以下は、これまでの解析結果に対するユーザーからのフィードバックと、実際に購入した後の結果報告です。

# これまでの学習ルール（現状）
{current_rules}

# ユーザーからのフィードバック一覧
{feedback_text}

# 購入後の結果報告一覧
{outcome_text}

これらを踏まえて、今後の解析・判定精度を上げるために追加/修正すべき具体的なルールを
簡潔な箇条書き（Markdown）で提案してください。既存ルールと重複する内容は書かないでください。
データが少なく有効な傾向が見えない場合は、その旨を正直に一文で述べてください。
"""

    if provider == "gemini":
        raw_text = _call_gemini(api_key, model, 1500, [{"text": prompt}])
    else:
        raw_text = _call_claude(api_key, model, 1500, [{"role": "user", "content": prompt}])
    return raw_text.strip()


def append_learned_rule_text(text):
    os.makedirs(KNOWLEDGE_DIR, exist_ok=True)
    existing = _read_file(LEARNED_RULES_PATH)
    from datetime import datetime

    stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    addition = f"\n\n## {stamp} 追加\n{text}\n"
    with open(LEARNED_RULES_PATH, "w", encoding="utf-8") as f:
        f.write((existing + addition).strip() + "\n")
