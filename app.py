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

# تحميل البيانات من Excel
participants_df = pd.read_excel("نموذج_المشاركين.xlsx")
questions_df = pd.read_excel("نموذج_الأسئلة.xlsx")

# تحويل المشاركين إلى dict
participants = {str(row["رقم الهوية"]): row["الاسم"] for _, row in participants_df.iterrows()}

# تحويل الأسئلة إلى قائمة
questions = []
for _, row in questions_df.iterrows():
    q = {"question": row["السؤال"], "type": row["النوع"]}
    if row["النوع"] == "mcq":
        q["options"] = [row["خيار1"], row["خيار2"], row["خيار3"], row["خيار4"]]
    questions.append(q)

@app.route('/')
def wait_page():
    now = datetime.now(ksa_tz)
    if now >= OFFICIAL_START_TIME:
        return redirect(url_for('login'))
    return render_template('waiting.html', start_time=OFFICIAL_START_TIME.isoformat())

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        user_id = request.form['user_id'].strip()
        user_name = request.form['user_name'].strip()
        if not user_id.isdigit() or len(user_id) != 10:
            error = "رقم الهوية يجب أن يكون 10 أرقام"
        elif user_id in participants:
            session['user_id'] = user_id
            session['user_name'] = user_name
            return redirect(url_for('start'))
        else:
            error = "رقم الهوية غير موجود أو غير مطابق"
    return render_template('login.html', error=error)

@app.route('/start', methods=['GET', 'POST'])
def start():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        session['start_time'] = datetime.now(ksa_tz).isoformat()
        return redirect(url_for('exam'))

    return render_template('start.html', user_name=session['user_name'])

@app.route('/exam', methods=['GET', 'POST'])
def exam():
    if 'user_id' not in session or 'start_time' not in session:
        return redirect(url_for('login'))

    start_time = datetime.fromisoformat(session['start_time'])
    now = datetime.now(ksa_tz)
    elapsed = (now - start_time).total_seconds()
    remaining = TEST_DURATION_MINUTES * 60 - elapsed

    if remaining <= 0:
        return redirect(url_for('submitted'))

    minutes = int(remaining // 60)
    seconds = int(remaining % 60)

    if request.method == 'POST':
        answers = {}
        for i in range(len(questions)):
            answers[f"Q{i+1}"] = request.form.get(f"q{i}", "")
        session['answers'] = answers
        return redirect(url_for('submitted'))

    return render_template('exam.html', questions=questions, minutes=minutes, seconds=seconds)

@app.route('/submitted')
def submitted():
    if 'answers' not in session:
        return redirect(url_for('login'))

    # هنا يمكن لاحقًا ربط الإرسال إلى Google Sheets
    return render_template('submitted.html', user_name=session.get('user_name'))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
