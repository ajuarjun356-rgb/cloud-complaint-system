import sqlite3
import os
from flask import Flask, render_template, request, redirect, session, url_for

app = Flask(__name__)
app.secret_key = "secret123"  # Required for sessions

# --- DATABASE INITIALIZATION ---
def init_db():
    conn = sqlite3.connect("database.db")
    cur = conn.cursor()
    # Create users table
    cur.execute('''CREATE TABLE IF NOT EXISTS users 
                   (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                    name TEXT, email TEXT UNIQUE, password TEXT)''')
    # Create complaints table
    cur.execute('''CREATE TABLE IF NOT EXISTS complaints 
                   (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                    user_id INTEGER, subject TEXT, description TEXT, status TEXT DEFAULT 'Pending')''')
    conn.commit()
    conn.close()

# Initialize the database immediately when the app starts
init_db()

# --- ROUTES ---

@app.route("/")
def home():
    return render_template("home.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        password = request.form.get("password")
        
        try:
            conn = sqlite3.connect("database.db")
            cur = conn.cursor()
            cur.execute("INSERT INTO users (name, email, password) VALUES (?, ?, ?)", (name, email, password))
            conn.commit()
            conn.close()
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            return "Email already exists! Please go back and try a different one."
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        
        conn = sqlite3.connect("database.db")
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE email = ? AND password = ?", (email, password))
        user = cur.fetchone()
        conn.close()
        
        if user:
            session["user_id"] = user[0]
            session["user_name"] = user[1]
            return redirect(url_for("dashboard"))
        else:
            return "Invalid Login Credentials. Please try again."
    return render_template("login.html")

@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))
    
    conn = sqlite3.connect("database.db")
    cur = conn.cursor()
    cur.execute("SELECT * FROM complaints WHERE user_id = ?", (session["user_id"],))
    user_complaints = cur.fetchall()
    conn.close()
    
    return render_template("dashboard.html", complaints=user_complaints, name=session["user_name"])

@app.route("/add_complaint", methods=["GET", "POST"])
def add_complaint():
    if "user_id" not in session:
        return redirect(url_for("login"))
        
    if request.method == "POST":
        subject = request.form.get("subject")
        description = request.form.get("description")
        
        conn = sqlite3.connect("database.db")
        cur = conn.cursor()
        cur.execute("INSERT INTO complaints (user_id, subject, description) VALUES (?, ?, ?)", 
                    (session["user_id"], subject, description))
        conn.commit()
        conn.close()
        return redirect(url_for("dashboard"))
    return render_template("add_complaint.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))

# --- RENDER/CLOUD CONFIGURATION ---
if __name__ == "__main__":
    # Get port from environment or default to 5000
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)