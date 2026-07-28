import os
import uuid

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session,
)

import db
import config
import analyzer

BASE_DIR = os.path.dirname(__file__)
UPLOAD_DIR = os.path.join(BASE_DIR, "data", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

app = Flask(__name__)
app.secret_key = config.get_secret_key()
app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024  # 20MB

db.init_db()

ALLOWED_EXT = {".png", ".jpg", ".jpeg", ".webp", ".gif"}


@app.before_request
def require_login():
    """ACCESS_PASSWORD が設定されている場合のみ、合言葉ログインを要求する。"""
    if not config.get_access_password():
        return None  # 1人利用モード（従来通り）
    if request.endpoint in ("login", "static"):
        return None
    if not session.get("logged_in"):
        return redirect(url_for("login"))
    return None


@app.route("/login", methods=["GET", "POST"])
def login():
    if not config.get_access_password():
        return redirect(url_for("index"))
    if request.method == "POST":
        password = request.form.get("password", "")
        name = request.form.get("user_name", "").strip()
        if password == config.get_access_password() and name:
            session["logged_in"] = True
            session["user_name"] = name
            return redirect(url_for("index"))
        flash("合言葉が違うか、名前が未入力です。", "error")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


def current_user():
    return session.get("user_name")


@app.context_processor
def inject_globals():
    return {
        "has_api_key": bool(config.active_api_key()),
        "current_user": session.get("user_name"),
        "login_enabled": bool(config.get_access_password()),
    }


@app.route("/")
def index():
    analyses = db.list_analyses(limit=12)
    stats = db.stats_summary()
    cases = db.list_cases(active_only=True)
    return render_template("index.html", analyses=analyses, stats=stats, cases=cases)


# ---- 金額査定（豪州輸入総額計算） ----


@app.route("/estimate")
def estimate():
    active_cases = db.list_cases(active_only=True)
    return render_template("estimate.html", cases=active_cases)


@app.route("/estimate/save", methods=["POST"])
def estimate_save():
    case_id_raw = request.form.get("case_id", "")
    summary = request.form.get("summary", "").strip()
    if case_id_raw.isdigit() and summary:
        db.add_case_note(int(case_id_raw), summary, user_name=current_user())
        flash("査定結果を案件に保存しました。", "success")
        return redirect(url_for("case_detail", case_id=int(case_id_raw)))
    flash("保存に失敗しました。案件と査定内容を確認してください。", "error")
    return redirect(url_for("estimate"))


# ---- 案件管理（豪州輸出パイプライン） ----


@app.route("/cases")
def cases():
    all_cases = db.list_cases()
    return render_template("cases.html", cases=all_cases, stages=db.CASE_STAGES)


@app.route("/cases/new", methods=["POST"])
def case_new():
    customer_name = request.form.get("customer_name", "").strip()
    if not customer_name:
        flash("お客様名を入力してください。", "error")
        return redirect(url_for("cases"))
    car_info = request.form.get("car_info", "").strip()
    notes = request.form.get("notes", "").strip()
    case_id = db.create_case(customer_name, car_info, current_user(), notes)
    flash("案件を作成しました。", "success")
    return redirect(url_for("case_detail", case_id=case_id))


@app.route("/case/<int:case_id>")
def case_detail(case_id):
    case = db.get_case(case_id)
    if not case:
        flash("案件が見つかりませんでした。", "error")
        return redirect(url_for("cases"))
    events = db.case_events(case_id)
    linked_analyses = db.analyses_for_case(case_id)
    return render_template(
        "case_detail.html",
        case=case,
        events=events,
        linked_analyses=linked_analyses,
        stages=db.CASE_STAGES,
    )


@app.route("/case/<int:case_id>/stage", methods=["POST"])
def case_stage(case_id):
    stage = request.form.get("stage", "")
    db.update_case_stage(case_id, stage, user_name=current_user())
    flash(f"ステージを「{stage}」に更新しました。", "success")
    return redirect(url_for("case_detail", case_id=case_id))


@app.route("/case/<int:case_id>/note", methods=["POST"])
def case_note(case_id):
    content = request.form.get("content", "").strip()
    if content:
        db.add_case_note(case_id, content, user_name=current_user())
        flash("メモを記録しました。", "success")
    return redirect(url_for("case_detail", case_id=case_id))


@app.route("/analyze", methods=["POST"])
def analyze():
    if not config.active_api_key():
        flash("先に「設定」画面でAPIキーを登録してください。", "error")
        return redirect(url_for("settings"))

    file = request.files.get("sheet_image")
    if not file or file.filename == "":
        flash("画像ファイルを選択してください。", "error")
        return redirect(url_for("index"))

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXT:
        flash("対応していないファイル形式です（png/jpg/jpeg/webp/gif）。", "error")
        return redirect(url_for("index"))

    filename = f"{uuid.uuid4().hex}{ext}"
    save_path = os.path.join(UPLOAD_DIR, filename)
    file.save(save_path)

    try:
        result = analyzer.analyze_image(
            save_path, config.active_api_key(), config.active_model(), provider=config.get_provider()
        )
    except Exception as e:  # noqa: BLE001
        flash(f"解析中にエラーが発生しました: {e}", "error")
        return redirect(url_for("index"))

    case_id_raw = request.form.get("case_id", "").strip()
    case_id = int(case_id_raw) if case_id_raw.isdigit() and int(case_id_raw) > 0 else None

    analysis_id = db.save_analysis(
        image_filename=filename,
        model=result.get("_model"),
        grade=result.get("overall_grade"),
        interior_grade=result.get("interior_grade"),
        verdict=result.get("verdict"),
        summary=result.get("verdict_reason", "")[:500],
        full_response=result,
        user_name=current_user(),
        case_id=case_id,
    )
    return redirect(url_for("result", analysis_id=analysis_id))


@app.route("/result/<int:analysis_id>")
def result(analysis_id):
    row = db.get_analysis(analysis_id)
    if not row:
        flash("解析結果が見つかりませんでした。", "error")
        return redirect(url_for("index"))
    import json

    data = json.loads(row["full_response"])
    feedback_list = db.get_feedback_for_analysis(analysis_id)
    outcome_list = db.get_outcomes_for_analysis(analysis_id)
    return render_template(
        "result.html",
        row=row,
        data=data,
        feedback_list=feedback_list,
        outcome_list=outcome_list,
    )


@app.route("/result/<int:analysis_id>/feedback", methods=["POST"])
def submit_feedback(analysis_id):
    rating = request.form.get("rating")
    comment = request.form.get("comment", "").strip()
    category = request.form.get("category", "").strip() or None
    db.add_feedback(analysis_id, rating, comment, user_name=current_user(), category=category)

    # 成長の仕組み(1): 訂正コメントがあれば即座に学習ルールへ反映
    if rating in ("incorrect", "partial") and comment:
        row = db.get_analysis(analysis_id)
        who = f"（{current_user()}）" if current_user() else ""
        cat = f"［{category}］" if category else ""
        rule_text = (
            f"- 過去の解析（判定: {row['verdict']} / 概要: {row['summary']}）についてユーザー{who}から"
            f"「{rating}」の評価{cat}。指摘内容: {comment}"
        )
        db.add_learned_rule("feedback", rule_text)
        analyzer.append_learned_rule_text(rule_text)
        flash("フィードバックを記録し、今後の判定ルールに反映しました。", "success")
    else:
        flash("フィードバックを記録しました。", "success")

    return redirect(url_for("result", analysis_id=analysis_id))


@app.route("/result/<int:analysis_id>/outcome", methods=["POST"])
def submit_outcome(analysis_id):
    purchased = request.form.get("purchased")
    actual_condition = request.form.get("actual_condition", "").strip()
    repair_cost_raw = request.form.get("repair_cost", "").strip()
    repair_cost = int(repair_cost_raw) if repair_cost_raw.isdigit() else None
    hidden_issues = request.form.get("hidden_issues", "").strip()
    satisfaction = request.form.get("satisfaction")
    notes = request.form.get("notes", "").strip()

    db.add_outcome(
        analysis_id, purchased, actual_condition, repair_cost, hidden_issues, satisfaction, notes,
        user_name=current_user(),
    )
    flash("購入後の結果を記録しました。今後の判定精度向上に活用されます。", "success")
    return redirect(url_for("result", analysis_id=analysis_id))


@app.route("/settings")
def settings():
    base_knowledge = analyzer._read_file(analyzer.BASE_KNOWLEDGE_PATH)
    learned_rules = analyzer._read_file(analyzer.LEARNED_RULES_PATH)
    rules_rows = db.list_learned_rules()
    return render_template(
        "settings.html",
        base_knowledge=base_knowledge,
        learned_rules=learned_rules,
        rules_rows=rules_rows,
        api_key_set=bool(config.get_api_key()),
        model=config.get_model(),
        provider=config.get_provider(),
        gemini_key_set=bool(config.get_gemini_key()),
        gemini_model=config.get_gemini_model(),
    )


@app.route("/settings/knowledge", methods=["POST"])
def save_knowledge():
    text = request.form.get("base_knowledge", "")
    with open(analyzer.BASE_KNOWLEDGE_PATH, "w", encoding="utf-8") as f:
        f.write(text)
    flash("評価基準ナレッジを更新しました。", "success")
    return redirect(url_for("settings"))


@app.route("/settings/api_key", methods=["POST"])
def save_api_key():
    key = request.form.get("api_key", "").strip()
    if key:
        config.save_api_key(key)
        flash("APIキーを保存しました。", "success")
    model_name = request.form.get("model", "").strip()
    if model_name:
        config.save_model(model_name)
    return redirect(url_for("settings"))


@app.route("/settings/provider", methods=["POST"])
def save_provider():
    provider = request.form.get("provider", "anthropic")
    config.save_provider(provider)
    gemini_key = request.form.get("gemini_api_key", "").strip()
    if gemini_key:
        config.save_gemini_key(gemini_key)
    gemini_model = request.form.get("gemini_model", "").strip()
    if gemini_model:
        config.save_gemini_model(gemini_model)
    label = "Gemini（無料枠あり）" if provider == "gemini" else "Claude（高精度・有料）"
    flash(f"AIエンジンを {label} に設定しました。", "success")
    return redirect(url_for("settings"))


@app.route("/settings/access_password", methods=["POST"])
def save_access_password():
    pw = request.form.get("access_password", "").strip()
    config.save_access_password(pw)
    if pw:
        session["logged_in"] = True
        if not session.get("user_name"):
            session["user_name"] = "管理者"
        flash("合言葉を設定しました。以降、全員がログインを求められます。", "success")
    else:
        flash("合言葉を解除しました（1人利用モード）。", "success")
    return redirect(url_for("settings"))


@app.route("/grow", methods=["GET"])
def grow():
    feedback_rows = db.all_feedback_with_analysis()
    outcome_rows = db.all_outcomes_with_analysis()
    proposal = session.get("growth_proposal")
    return render_template(
        "grow.html",
        feedback_rows=feedback_rows,
        outcome_rows=outcome_rows,
        proposal=proposal,
    )


@app.route("/grow/run", methods=["POST"])
def grow_run():
    if not config.active_api_key():
        flash("先に「設定」画面でAPIキーを登録してください。", "error")
        return redirect(url_for("settings"))

    feedback_rows = db.all_feedback_with_analysis()
    outcome_rows = db.all_outcomes_with_analysis()

    if not feedback_rows and not outcome_rows:
        flash("まだフィードバックや購入後結果のデータがありません。まずは解析→評価を行ってください。", "error")
        return redirect(url_for("grow"))

    try:
        proposal = analyzer.synthesize_growth_rules(
            config.active_api_key(), feedback_rows, outcome_rows, config.active_model(), provider=config.get_provider()
        )
    except Exception as e:  # noqa: BLE001
        flash(f"振り返り生成中にエラーが発生しました: {e}", "error")
        return redirect(url_for("grow"))

    session["growth_proposal"] = proposal
    return redirect(url_for("grow"))


@app.route("/grow/approve", methods=["POST"])
def grow_approve():
    proposal = session.get("growth_proposal")
    if proposal:
        db.add_learned_rule("growth", proposal)
        analyzer.append_learned_rule_text(proposal)
        flash("提案されたルールを学習ルールに追加しました。次回以降の解析に反映されます。", "success")
        session.pop("growth_proposal", None)
    return redirect(url_for("grow"))


@app.route("/grow/discard", methods=["POST"])
def grow_discard():
    session.pop("growth_proposal", None)
    flash("提案を破棄しました。", "success")
    return redirect(url_for("grow"))


@app.route("/stats")
def stats():
    s = db.stats_summary()
    outcomes = db.all_outcomes_with_analysis()
    return render_template("stats.html", stats=s, outcomes=outcomes)


@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    from flask import send_from_directory

    return send_from_directory(UPLOAD_DIR, filename)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5050))
    app.run(host="127.0.0.1", port=port, debug=True)
