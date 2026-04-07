import sqlite3
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
            subject TEXT,
            duration INTEGER
        )
    ''')
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
    return render_template("index.html", quote=quote)

@app.route("/add", methods=["GET", "POST"])
@login_required
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

@app.route("/sessions")
@login_required
def sessions():
    conn = sqlite3.connect(db)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM sessions")
    sessions_data = cursor.fetchall()
    conn.close()
    return render_template("sessions.html", sessions=sessions_data)

@app.route("/sessions/<int:id>")
@login_required
def delete(id):
    conn = sqlite3.connect(db)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM sessions WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return redirect(url_for("sessions"))

if __name__ == '__main__':
    app.run(debug=True)
