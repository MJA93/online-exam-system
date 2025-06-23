import os
import pandas as pd
from flask import Flask, request, session, redirect, url_for, render_template
from datetime import datetime, timedelta
import pytz

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# إعدادات الوقت
ksa_tz = pytz.timezone("Asia/Riyadh")
OFFICIAL_START_TIME = ksa_tz.localize(datetime(2025, 6, 22, 7, 30, 0))
TEST_DURATION_MINUTES = 20

# تحميل ملفات Excel
participants_df = pd.read_excel("نموذج_المشاركين.xlsx")
questions_df = pd.read_excel("نموذج_الأسئلة.xlsx")

# تحويل المشاركين إلى dict
participants = {
    str(row["رقم الهوية"]).strip(): row["الاسم"]
    for _, row in participants_df.iterrows()
}

# تجهيز الأسئلة
questions = []
for _, row in questions_df.iterrows():
    q_type = row["النوع"].strip().lower()
    question_entry = {
        "question": str(row["السؤال"]).strip(),
        "type": q_type
    }
    if q_type == "mcq":
        # تفصيل الخيارات بفواصل
        options = [opt.strip() for opt in str(row["الخيارات"]).split(",")]
        question_entry["options"] = options
    elif q_type == "true_false":
        question_entry["options"] = ["صح", "خطأ"]
    questions.append(question_entry)


@app.route("/", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        name = request.form["name"].strip()
        id_number = request.form["id"].strip()

        if not id_number.isdigit() or len(id_number) > 10:
            error = "رقم الهوية يجب ألا يتجاوز 10 أرقام."
        elif id_number not in participants:
            error = "رقم الهوية غير مسجل."
        elif participants[id_number] != name:
            error = "الاسم لا يطابق رقم الهوية."
        else:
            session["id"] = id_number
            session["name"] = name
            return redirect(url_for("waiting"))

    return render_template("login.html", error=error)


@app.route("/waiting")
def waiting():
    if "id" not in session:
        return redirect(url_for("login"))

    now = datetime.now(ksa_tz)
    remaining = (OFFICIAL_START_TIME - now).total_seconds()
    if remaining <= 0:
        return redirect(url_for("start_exam"))
    return render_template("waiting.html", remaining=int(remaining), name=session["name"])


@app.route("/start")
def start_exam():
    if "id" not in session:
        return redirect(url_for("login"))

    session["start_time"] = datetime.now(ksa_tz).isoformat()
    return render_template("start_exam.html", name=session["name"])


@app.route("/exam", methods=["GET", "POST"])
def exam():
    if "id" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":
        answers = request.form.to_dict()
        session["answers"] = answers
        return redirect(url_for("submitted"))

    start_time = datetime.fromisoformat(session["start_time"])
    elapsed = (datetime.now(ksa_tz) - start_time).total_seconds()
    remaining = TEST_DURATION_MINUTES * 60 - elapsed
    if remaining <= 0:
        return redirect(url_for("submitted"))

    return render_template("exam.html", questions=questions, remaining=int(remaining))


@app.route("/submitted")
def submitted():
    if "id" not in session:
        return redirect(url_for("login"))

    # حفظ الأجوبة في ملف نصي أو أي معالجة لاحقة
    id_ = session["id"]
    name = session["name"]
    answers = session.get("answers", {})

    filename = f"answers_{id_}.txt"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(f"الاسم: {name}\nرقم الهوية: {id_}\n\n")
        for i, q in enumerate(questions):
            f.write(f"س{ i+1 }: {q['question']}\n")
            f.write(f"الإجابة: {answers.get(f'q{i+1}', '')}\n\n")

    return render_template("submitted.html", name=name)


if __name__ == "__main__":
    app.run(debug=True)
