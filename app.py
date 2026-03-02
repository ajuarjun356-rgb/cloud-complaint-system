from flask import Flask, render_template, request, redirect, session
import sqlite3

app = Flask(__name__)
app.secret_key = "secret123"

@app.route("/")
def home():
    return render_template("home.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]

        try:
            conn = sqlite3.connect("database.db")
            cur = conn.cursor()
            cur.execute("INSERT INTO users (name, email, password) VALUES (?, ?, ?)",
                        (name, email, password))
            conn.commit()
        except sqlite3.IntegrityError:
            conn.close()
            return "This email is already registered! Please use a different email."
        conn.close()
        return redirect("/login")

    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        conn = sqlite3.connect("database.db")
        cur = conn.cursor()

        cur.execute(
            "SELECT * FROM users WHERE email=? AND password=?",
            (email, password)
        )
        user = cur.fetchone()
        conn.close()

        if user:
            session["user_email"] = email
            return redirect("/dashboard")
        else:
            return "Invalid login"

    return render_template("login.html")

from flask import session

@app.route("/dashboard")
def dashboard():
    if "user_email" not in session:
        return redirect("/login")

    email = session["user_email"]

    conn = sqlite3.connect("database.db")
    cur = conn.cursor()

    cur.execute(
        "SELECT id, complaint, status FROM complaints WHERE user_email=?",
        (email,)
    )

    complaints = cur.fetchall()
    conn.close()

    return render_template("dashboard.html", complaints=complaints, email=email)


@app.route("/add_complaint", methods=["GET", "POST"])
def add_complaint():
    if "user_email" not in session:
        return redirect("/login")

    if request.method == "POST":
        complaint = request.form["complaint"]
        email = session["user_email"]

        conn = sqlite3.connect("database.db")
        cur = conn.cursor()

        cur.execute(
            "INSERT INTO complaints (user_email, complaint, status) VALUES (?, ?, ?)",
            (email, complaint, "Pending")
        )

        conn.commit()
        conn.close()

        return redirect("/dashboard")

    return render_template("add_complaint.html")



@app.route("/complaint", methods=["GET", "POST"])
def complaint():
    message = None

    if request.method == "POST":
        email = request.form["email"]
        complaint_text = request.form["complaint"]

        conn = sqlite3.connect("database.db")
        cur = conn.cursor()

        cur.execute("INSERT INTO complaints (user_email, complaint) VALUES (?, ?)",
                    (email, complaint_text))

        conn.commit()
        conn.close()

        message = "Complaint submitted successfully!"

    return render_template("complaint.html", message=message)

@app.route("/admin")
def admin():
    conn = sqlite3.connect("database.db")
    cur = conn.cursor()
    

    cur.execute("SELECT * FROM complaints")
    complaints = cur.fetchall()

    conn.close()
    return render_template("admin.html", complaints=complaints)

@app.route("/resolve/<int:id>")
def resolve(id):
    conn = sqlite3.connect("database.db")
    cur = conn.cursor()

    cur.execute("UPDATE complaints SET status='Resolved' WHERE id=?", (id,))
    conn.commit()
    conn.close()

    return redirect("/admin")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")

