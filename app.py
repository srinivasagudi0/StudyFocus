import sqlite3
from flask import Flask, render_template, request, redirect, url_for

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

# Route 1: Home page with random quote
@app.route('/')
def index():
    quote = requests.get("https://api.quotable.io/random").json()
    return render_template("index.html", quote=quote["content"])

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