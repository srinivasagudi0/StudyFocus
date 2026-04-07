import sqlite3
import os
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session
import requests
from authentication import create_user_table, check_user, add_user
import random

app = Flask(__name__)
app.secret_key = "your_secret_key_here"
db = "database.db"

def init_db():
    conn = sqlite3.connect(db)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            subject TEXT,
            duration INTEGER
        )
    ''')
    cursor.execute("PRAGMA table_info(sessions)")
    columns = [column[1] for column in cursor.fetchall()]
    if "username" not in columns:
        cursor.execute("ALTER TABLE sessions ADD COLUMN username TEXT")
    conn.commit()
    conn.close()

init_db()
create_user_table()


def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if not session.get("username"):
            return redirect(url_for("login"))
        return view(*args, **kwargs)

    return wrapped_view
def get_quote():
    with open("quotes.txt", "r") as f:
        quotes = f.read().splitlines()
        fallback_quote = random.choice(quotes)

    try:
        response = requests.get("https://api.quotable.io/random", timeout=3)
        response.raise_for_status()
        data = response.json()
        return data.get("content", fallback_quote)
    except (requests.RequestException, ValueError, KeyError):
        return fallback_quote


def fetch_user_sessions(username):
    conn = sqlite3.connect(db)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, subject, duration FROM sessions WHERE username = ? ORDER BY id DESC",
        (username,),
    )
    sessions_data = cursor.fetchall()
    conn.close()
    return sessions_data


def build_session_summary(sessions_data):
    subject_totals = {}
    total_minutes = 0

    for _, subject, duration in sessions_data:
        minutes = int(duration)
        total_minutes += minutes
        subject_totals[subject] = subject_totals.get(subject, 0) + minutes

    sorted_subjects = sorted(
        subject_totals.items(),
        key=lambda item: item[1],
        reverse=True,
    )

    return {
        "session_count": len(sessions_data),
        "total_minutes": total_minutes,
        "average_minutes": round(total_minutes / len(sessions_data), 1) if sessions_data else 0,
        "subjects": [
            {"subject": subject, "minutes": minutes}
            for subject, minutes in sorted_subjects
        ],
        "recent_sessions": [
            {"subject": subject, "duration": int(duration)}
            for _, subject, duration in sessions_data[:10]
        ],
    }


def get_study_insights(username):
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None, "Set OPENAI_API_KEY to generate insights."

    sessions_data = fetch_user_sessions(username)
    if not sessions_data:
        return None, "Add a few study sessions first."

    session_summary = build_session_summary(sessions_data)
    model = os.getenv("OPENAI_INSIGHTS_MODEL", "gpt-3.5-turbo")

    prompt = f"""
You are analyzing a student's study log.
Return exactly 3 short bullet points.
Each bullet must be one sentence.
Focus on patterns, consistency, and one practical suggestion.

Study summary:
{session_summary}
""".strip()

    try:
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": [
                    {
                        "role": "system",
                        "content": "You produce concise study insights from session logs.",
                    },
                    {
                        "role": "user",
                        "content": prompt,
                    },
                ],
                "temperature": 0.4,
                "max_completion_tokens": 180,
            },
            timeout=20,
        )
        response.raise_for_status()
        data = response.json()
        content = data["choices"][0]["message"]["content"].strip()
        return content, None
    except (requests.RequestException, KeyError, IndexError, ValueError):
        return None, "Could not generate insights right now."

@app.route('/login', methods=["GET", "POST"])
def login():
    created = request.args.get("created") == "1"
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        if check_user(username, password):
            session['username'] = username
            return redirect(url_for("index"))
        else:
            return render_template("login.html", error="Invalid username or password", created=created)
    return render_template("login.html", created=created)

@app.route('/signup', methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        try:
            add_user(username, password)
            return redirect(url_for("login", created=1))
        except Exception as e:
            return render_template("signup.html", error="Username already exists or error occurred")
    return render_template("signup.html")

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for("login"))

@app.route('/')
@login_required
def index():
    quote = get_quote()
    sessions_data = fetch_user_sessions(session["username"])
    session_summary = build_session_summary(sessions_data)
    return render_template("index.html", quote=quote, session_summary=session_summary)


@app.route("/insights", methods=["POST"])
@login_required
def insights():
    quote = get_quote()
    sessions_data = fetch_user_sessions(session["username"])
    session_summary = build_session_summary(sessions_data)
    insights_text, insights_error = get_study_insights(session["username"])
    return render_template(
        "index.html",
        quote=quote,
        insights=insights_text,
        insights_error=insights_error,
        session_summary=session_summary,
    )

@app.route("/add", methods=["GET", "POST"])
@login_required
def add():
    if request.method == "POST":
        subject = request.form["subject"]
        duration = request.form["duration"]
        conn = sqlite3.connect(db)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO sessions (username, subject, duration) VALUES (?, ?, ?)",
            (session["username"], subject, duration),
        )
        conn.commit()
        conn.close()
        return redirect(url_for("sessions"))
    return render_template("add.html")

@app.route("/sessions")
@login_required
def sessions():
    sessions_data = fetch_user_sessions(session["username"])
    return render_template("sessions.html", sessions=sessions_data)

@app.route("/sessions/<int:id>")
@login_required
def delete(id):
    conn = sqlite3.connect(db)
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM sessions WHERE id = ? AND username = ?",
        (id, session["username"]),
    )
    conn.commit()
    conn.close()
    return redirect(url_for("sessions"))

if __name__ == '__main__':
    app.run(debug=True)
