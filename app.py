import sqlite3
from flask import Flask, render_template, request, redirect, url_for
import requests


app = Flask(__name__)
db = "database.db"  # Path to SQLite database

def init_db():
    conn = sqlite3.connect(db)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject TEXT,
            duration INTEGER
        )
    ''')
    conn.commit()
    conn.close()

init_db()

def get_quote():
    fallback_quote = "Keep going — small progress every day adds up."
    try:
        response = requests.get("https://api.quotable.io/random", timeout=3)
        response.raise_for_status()
        data = response.json()
        return data.get("content", fallback_quote)
    except (requests.RequestException, ValueError, KeyError):
        return fallback_quote

# Route 1: Home page with random quote
@app.route('/')
def index():
    quote = get_quote()
    return render_template("index.html", quote=quote)

# Route 2: Add a new study session
@app.route("/add", methods=["GET", "POST"])

def add():
    if request.method == "POST":
        subject = request.form["subject"]
        duration = request.form["duration"]

        conn = sqlite3.connect(db)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO sessions (subject, duration) VALUES (?, ?)", (subject, duration))
        conn.commit()
        conn.close()

        return redirect(url_for("sessions"))

    return render_template("add.html")

# Route 3: View all study sessions
@app.route("/sessions")

def sessions():
    conn = sqlite3.connect(db)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM sessions")
    sessions = cursor.fetchall()
    conn.close()
    return render_template("sessions.html", sessions=sessions)

# Route 4: Delete a study session
@app.route("/sessions/<int:id>")
def delete(id):
    conn = sqlite3.connect(db)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM sessions WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return redirect(url_for("sessions"))

if __name__ == '__main__':
    app.run(debug=True)