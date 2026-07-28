"""日英UI翻訳。session['lang'] が 'en' のとき英語表示。"""

STRINGS = {
    # ナビゲーション
    "nav_diagnose": {"ja": "診断する", "en": "Diagnose"},
    "nav_cases": {"ja": "案件管理", "en": "Deals"},
    "nav_estimate": {"ja": "金額査定", "en": "Cost Estimate"},
    "nav_stats": {"ja": "統計", "en": "Stats"},
    "nav_grow": {"ja": "AIを育てる", "en": "Train AI"},
    "nav_settings": {"ja": "設定", "en": "Settings"},
    "nav_logout": {"ja": "ログアウト", "en": "Logout"},
    "app_title": {"ja": "オークションシートAI診断", "en": "Auction Sheet AI Checker"},

    # トップページ
    "index_h1": {"ja": "オークションシートを診断する", "en": "Diagnose an Auction Sheet"},
    "index_desc": {
        "ja": "車のオークションシートの写真をアップロードすると、AIが評価点・傷/凹み記号・特記事項を徹底解説し、「買い / 条件付き買い / 見送り推奨」を根拠つきで判定します。",
        "en": "Upload a photo of a Japanese car auction sheet. The AI explains the grade, damage symbols and remarks, then gives a Buy / Conditional / Avoid verdict with reasons.",
    },
    "sheet_image": {"ja": "オークションシート画像", "en": "Auction sheet image"},
    "drop_hint": {"ja": "ここに画像をドラッグ＆ドロップ（またはクリックして選択）", "en": "Drag & drop the image here (or click to select)"},
    "link_to_case": {"ja": "案件に紐付ける（任意）", "en": "Link to a deal (optional)"},
    "no_link": {"ja": "（紐付けない）", "en": "(no link)"},
    "diagnose_btn": {"ja": "AIに診断させる", "en": "Run AI Diagnosis"},
    "stats_h2": {"ja": "これまでの診断傾向", "en": "Diagnosis Overview"},
    "stat_total": {"ja": "診断件数", "en": "Diagnoses"},
    "stat_feedback": {"ja": "フィードバック数", "en": "Feedback"},
    "stat_accuracy": {"ja": "判定正解率(自己申告)", "en": "Accuracy (self-reported)"},
    "stat_outcomes": {"ja": "購入後結果報告", "en": "Purchase outcomes"},
    "recent_h2": {"ja": "最近の診断結果", "en": "Recent Diagnoses"},
    "no_history": {"ja": "まだ診断履歴がありません。", "en": "No diagnoses yet."},
    "grade_label": {"ja": "総合評価", "en": "Grade"},

    # 判定
    "verdict_buy": {"ja": "買い", "en": "Buy"},
    "verdict_conditional": {"ja": "条件付き買い", "en": "Conditional"},
    "verdict_avoid": {"ja": "見送り推奨", "en": "Avoid"},

    # 結果ページ
    "result_title": {"ja": "診断結果", "en": "Diagnosis Result"},
    "overall_verdict": {"ja": "総合判定", "en": "Verdict"},
    "confidence": {"ja": "AIの確信度", "en": "AI confidence"},
    "grade_section": {"ja": "評価点の解説", "en": "Grade Explanation"},
    "auction_house": {"ja": "会場", "en": "Auction house"},
    "exterior": {"ja": "外装評価", "en": "Exterior"},
    "interior": {"ja": "内装評価", "en": "Interior"},
    "mileage": {"ja": "走行距離", "en": "Mileage"},
    "criteria_section": {"ja": "あなたの仕入れ基準との照合", "en": "Check Against Your Buying Criteria"},
    "criteria": {"ja": "基準", "en": "Criterion"},
    "judgement": {"ja": "判定", "en": "Result"},
    "note": {"ja": "備考", "en": "Note"},
    "pass": {"ja": "✅ 合格", "en": "✅ Pass"},
    "fail": {"ja": "❌ 不合格", "en": "❌ Fail"},
    "unknown": {"ja": "❔ 不明", "en": "❔ Unknown"},
    "export_section": {"ja": "オーストラリア輸出における注意点", "en": "Notes for Export to Australia"},
    "cost_section": {"ja": "コスト参考情報", "en": "Cost Reference"},
    "damage_section": {"ja": "車両図の傷・凹みなどの記号", "en": "Damage Symbols on Vehicle Diagram"},
    "location": {"ja": "部位", "en": "Location"},
    "symbol": {"ja": "記号", "en": "Symbol"},
    "meaning": {"ja": "意味", "en": "Meaning"},
    "severity": {"ja": "重大度", "en": "Severity"},
    "no_damage": {"ja": "目立った傷・凹みの記載は確認できませんでした。", "en": "No notable damage marks found."},
    "equipment_section": {"ja": "装備・特記事項", "en": "Equipment & Remarks"},
    "no_remarks": {"ja": "特記事項は読み取れませんでした。", "en": "No remarks could be read."},
    "risk_section": {"ja": "購入前に必ず確認すべき懸念点", "en": "Concerns to Check Before Buying"},
    "no_risk": {"ja": "シート上、特筆すべき懸念点はありませんでした。", "en": "No major concerns found on the sheet."},
    "checklist_section": {"ja": "入札前チェックリスト", "en": "Pre-bid Checklist"},
    "another_btn": {"ja": "別のシートを診断する", "en": "Diagnose Another Sheet"},

    # フィードバック
    "feedback_h2": {"ja": "この判定は合っていましたか？（AIを育てる フィードバック①）", "en": "Was this verdict right? (Train the AI #1)"},
    "feedback_desc": {"ja": "正誤やコメントを送ると、次回以降の判定ルールに自動で反映されます。", "en": "Your corrections are added to the AI's rules for future diagnoses."},
    "rating": {"ja": "評価", "en": "Rating"},
    "rating_correct": {"ja": "妥当だった", "en": "Correct"},
    "rating_partial": {"ja": "一部違った", "en": "Partially wrong"},
    "rating_incorrect": {"ja": "大きく違った", "en": "Wrong"},
    "fb_category": {"ja": "指摘の種類（診断のどこを改善すべきか）", "en": "Type of issue (what to improve)"},
    "fb_memo": {"ja": "メモ（具体的にどう違ったか・どう直すべきか）", "en": "Memo (what was wrong / how to fix)"},
    "send_feedback": {"ja": "フィードバックを送る", "en": "Send Feedback"},
    "past_feedback": {"ja": "これまでのフィードバック", "en": "Past Feedback"},
    "outcome_h2": {"ja": "購入後の結果を記録する（AIを育てる フィードバック②）", "en": "Record Purchase Outcome (Train the AI #2)"},
    "record_btn": {"ja": "結果を記録する", "en": "Record Outcome"},
    "date": {"ja": "日時", "en": "Date"},
    "staff": {"ja": "担当", "en": "Staff"},
    "type": {"ja": "種別", "en": "Type"},
    "content": {"ja": "内容", "en": "Content"},

    # 案件
    "cases_h1": {"ja": "案件管理（豪州輸出パイプライン）", "en": "Deal Management (Australia Export Pipeline)"},
    "cases_desc": {"ja": "問い合わせから豪州到着・コンプライアンスまでの流れを案件ごとに追跡します。", "en": "Track each deal from enquiry to arrival and compliance in Australia."},
    "new_case": {"ja": "新規案件", "en": "New Deal"},
    "customer_name": {"ja": "お客様名", "en": "Customer name"},
    "car_info": {"ja": "希望車種・条件", "en": "Requested car / conditions"},
    "memo": {"ja": "メモ", "en": "Memo"},
    "create_case_btn": {"ja": "案件を作成", "en": "Create Deal"},
    "case_list": {"ja": "案件一覧", "en": "Deal List"},
    "no_cases": {"ja": "まだ案件がありません。上のフォームから作成してください。", "en": "No deals yet. Create one above."},
    "customer": {"ja": "お客様", "en": "Customer"},
    "stage": {"ja": "ステージ", "en": "Stage"},
    "updated": {"ja": "更新日", "en": "Updated"},
    "case_title": {"ja": "案件", "en": "Deal"},
    "created": {"ja": "作成", "en": "Created"},
    "pipeline_h3": {"ja": "進行ステージ", "en": "Pipeline Stage"},
    "change_stage": {"ja": "ステージを変更", "en": "Change stage"},
    "update_btn": {"ja": "更新", "en": "Update"},
    "final_price_h3": {"ja": "成約金額", "en": "Contracted Price"},
    "final_price_desc": {"ja": "お客様と成約した金額を記録します（例: AUD 22,500 / ¥1,850,000）。", "en": "Record the price agreed with the customer (e.g. AUD 22,500)."},
    "final_price_unset": {"ja": "未設定", "en": "Not set"},
    "save_btn": {"ja": "保存", "en": "Save"},
    "case_analyses_h2": {"ja": "この案件の診断結果", "en": "Diagnoses for This Deal"},
    "case_analyses_empty": {"ja": "まだ診断がありません。トップページでシートを診断する際に、この案件を選択すると紐付きます。", "en": "No diagnoses yet. Select this deal when running a diagnosis to link it."},
    "docs_h2": {"ja": "書類の保存（Invoice・Import Approval など）", "en": "Documents (Invoice, Import Approval, etc.)"},
    "docs_desc": {"ja": "案件に関する書類を保存します。Google連携を設定している場合は、スプレッドシートへの記録とGoogle Driveへの保存も自動で行われます。", "en": "Store deal documents. If Google sync is configured, they are also logged to your spreadsheet and saved to Google Drive automatically."},
    "doc_type": {"ja": "書類の種類", "en": "Document type"},
    "doc_file": {"ja": "ファイル（PDF・画像など）", "en": "File (PDF, image, etc.)"},
    "upload_doc_btn": {"ja": "書類を保存", "en": "Save Document"},
    "doc_list": {"ja": "保存済み書類", "en": "Saved Documents"},
    "download": {"ja": "ダウンロード", "en": "Download"},
    "notes_h2": {"ja": "経過メモ・履歴", "en": "Notes & History"},
    "add_note": {"ja": "メモを追加（商談内容、船便情報、コンプライアンス状況など）", "en": "Add a note (negotiation, shipping, compliance, etc.)"},
    "record_note_btn": {"ja": "記録する", "en": "Add Note"},
    "back_to_cases": {"ja": "案件一覧へ戻る", "en": "Back to Deal List"},
    "stage_change": {"ja": "ステージ変更", "en": "Stage change"},
    "note_type": {"ja": "メモ", "en": "Note"},

    # ステージ名
    "stage_問い合わせ": {"ja": "問い合わせ", "en": "Enquiry"},
    "stage_候補提案": {"ja": "候補提案", "en": "Proposal"},
    "stage_契約": {"ja": "契約", "en": "Contract"},
    "stage_落札・購入": {"ja": "落札・購入", "en": "Purchased"},
    "stage_港手配": {"ja": "港手配", "en": "Port/Shipping"},
    "stage_豪州到着": {"ja": "豪州到着", "en": "Arrived AU"},
    "stage_コンプライアンス": {"ja": "コンプライアンス", "en": "Compliance"},
    "stage_完了": {"ja": "完了", "en": "Done"},

    # ログイン
    "login_h1": {"ja": "ログイン", "en": "Login"},
    "login_desc": {"ja": "社内共有の合言葉と、あなたの名前を入力してください。名前は診断履歴・フィードバックの記録に使われます。", "en": "Enter the shared passphrase and your name. Your name is recorded with diagnoses and feedback."},
    "your_name": {"ja": "名前（ニックネーム可）", "en": "Your name"},
    "passphrase": {"ja": "合言葉", "en": "Passphrase"},
    "enter_btn": {"ja": "入る", "en": "Enter"},

    # 金額査定
    "estimate_h1": {"ja": "金額査定（豪州輸入 総額計算）", "en": "Cost Estimate (Total Landed Cost, Australia)"},
    "save_estimate_h2": {"ja": "この査定を案件に保存", "en": "Save This Estimate to a Deal"},
    "save_to_case_btn": {"ja": "案件のメモに保存", "en": "Save to Deal Notes"},
}


def make_t(lang):
    def t(key):
        entry = STRINGS.get(key)
        if not entry:
            return key
        return entry.get(lang) or entry.get("ja") or key

    return t


def translate_stage(stage, lang):
    entry = STRINGS.get(f"stage_{stage}")
    if entry:
        return entry.get(lang) or stage
    return stage
