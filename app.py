import sqlite3
import os
import smtplib
from datetime import date
from email.mime.text import MIMEText
from flask import Flask, render_template, request, redirect, session, url_for
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-in-production")

# ---------------- FILE UPLOAD ---------------- #

UPLOAD_FOLDER = "static/uploads"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "pdf", "doc", "docx"}
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# ---------------- EMAIL CONFIG ---------------- #

EMAIL_ADDRESS = os.environ.get("EMAIL_ADDRESS", "ajuarjun356@gmail.com")
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD", "bxpz kpkr lceb zpod")
ADMIN_EMAIL    = os.environ.get("ADMIN_EMAIL",   "admin@cms.com")


def send_email(to_email, subject, message, html_message=None):
    try:
        msg = MIMEText(
            html_message if html_message else message,
            "html" if html_message else "plain"
        )
        msg["Subject"] = subject
        msg["From"]    = EMAIL_ADDRESS
        msg["To"]      = to_email

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.send_message(msg)

        print("Email sent to:", to_email)

    except Exception as e:
        print("Email error:", e)


# ---------------- DATABASE ---------------- #

def init_db():
    conn = sqlite3.connect("database.db")
    cur  = conn.cursor()

    # Users table — now includes 'role' column
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id       INTEGER PRIMARY KEY AUTOINCREMENT,
        name     TEXT,
        email    TEXT UNIQUE,
        password TEXT,
        role     TEXT DEFAULT 'user'
    )
    """)

    # Complaints table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS complaints (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id      INTEGER,
        subject      TEXT,
        description  TEXT,
        category     TEXT,
        priority     TEXT,
        status       TEXT DEFAULT 'Pending',
        created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        file_path    TEXT,
        admin_remark TEXT,
        assigned_to  INTEGER DEFAULT NULL
    )
    """)

    # Complaint logs
    cur.execute("""
    CREATE TABLE IF NOT EXISTS complaint_logs (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        complaint_id INTEGER,
        status       TEXT,
        remark       TEXT,
        updated_by   TEXT DEFAULT 'Admin',
        updated_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Add columns if upgrading from old DB
cur.execute("PRAGMA table_info(complaints)")
complaint_cols = [c[1] for c in cur.fetchall()]

if "category" not in complaint_cols:
    cur.execute("ALTER TABLE complaints ADD COLUMN category TEXT")

if "priority" not in complaint_cols:
    cur.execute("ALTER TABLE complaints ADD COLUMN priority TEXT")

if "created_at" not in complaint_cols:
    cur.execute("ALTER TABLE complaints ADD COLUMN created_at TEXT")

if "file_path" not in complaint_cols:
    cur.execute("ALTER TABLE complaints ADD COLUMN file_path TEXT")

if "admin_remark" not in complaint_cols:
    cur.execute("ALTER TABLE complaints ADD COLUMN admin_remark TEXT")

if "assigned_to" not in complaint_cols:
    cur.execute("ALTER TABLE complaints ADD COLUMN assigned_to INTEGER DEFAULT NULL")

    cur.execute("PRAGMA table_info(users)")
    user_cols = [c[1] for c in cur.fetchall()]
    if "role" not in user_cols:
        cur.execute("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'user'")

    cur.execute("PRAGMA table_info(complaint_logs)")
    log_cols = [c[1] for c in cur.fetchall()]
    if "updated_by" not in log_cols:
        cur.execute("ALTER TABLE complaint_logs ADD COLUMN updated_by TEXT DEFAULT 'Admin'")

    conn.commit()
    conn.close()


init_db()


# ================================================================
#  HELPER — shared DB query
# ================================================================

def get_db():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn


# ================================================================
#  HOME
# ================================================================

@app.route("/")
def home():
    return render_template("home.html")


# ================================================================
#  REGISTER
# ================================================================

@app.route("/register", methods=["GET", "POST"])
def register():
    error = None

    if request.method == "POST":
        name     = (request.form.get("name")     or "").strip()
        email    = (request.form.get("email")    or "").strip()
        password = (request.form.get("password") or "").strip()

        if not name or not email or not password:
            error = "All fields are required."
        elif len(password) < 6:
            error = "Password must be at least 6 characters."
        else:
            # ✅ Hash password before storing
            hashed = generate_password_hash(password)

            try:
                conn = get_db()
                conn.execute(
                    "INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, 'user')",
                    (name, email, hashed)
                )
                conn.commit()
                conn.close()
                return redirect(url_for("login"))

            except sqlite3.IntegrityError:
                error = "Email already exists!"

    return render_template("register.html", error=error)


# ================================================================
#  LOGIN  (User + Admin + Agent)
# ================================================================

@app.route("/login", methods=["GET", "POST"])
def login():
    error = None

    if request.method == "POST":
        role     = request.form.get("role")
        email    = (request.form.get("email")    or "").strip()
        password = (request.form.get("password") or "").strip()

        if role == "admin":
            # Admin uses hardcoded credentials (no DB)
            if email == "admin@cms.com" and password == "admin123":
                session.clear()
                session["admin"] = True
                return redirect(url_for("admin"))
            else:
                error = "Invalid admin credentials"

        elif role == "agent":
            conn = get_db()
            user = conn.execute(
                "SELECT * FROM users WHERE email = ? AND role = 'agent'", (email,)
            ).fetchone()
            conn.close()

            if user and check_password_hash(user["password"], password):
                session.clear()
                session["agent_id"]    = user["id"]
                session["agent_name"]  = user["name"]
                session["agent_email"] = user["email"]
                return redirect(url_for("agent_dashboard"))
            else:
                error = "Invalid agent credentials"

        else:
            conn = get_db()
            user = conn.execute(
                "SELECT * FROM users WHERE email = ? AND role = 'user'", (email,)
            ).fetchone()
            conn.close()

            if user and check_password_hash(user["password"], password):
                session.clear()
                session["user_id"]    = user["id"]
                session["user_name"]  = user["name"]
                session["user_email"] = user["email"]
                return redirect(url_for("dashboard"))
            else:
                error = "Incorrect email or password"

    return render_template("login.html", error=error)


# ================================================================
#  ADMIN LOGIN (separate route)
# ================================================================

@app.route("/admin_login", methods=["GET", "POST"])
def admin_login():
    error = None

    if request.method == "POST":
        email    = (request.form.get("email")    or "").strip()
        password = (request.form.get("password") or "").strip()

        if email == "admin@cms.com" and password == "admin123":
            session["admin"] = True
            return redirect(url_for("admin"))
        else:
            error = "Invalid admin credentials"

    return render_template("admin_login.html", error=error)


# ================================================================
#  USER DASHBOARD
# ================================================================

@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))

    search = (request.args.get("search") or "").strip()
    conn   = get_db()

    if search:
        complaints = conn.execute("""
            SELECT * FROM complaints
            WHERE user_id = ?
            AND (subject LIKE ? OR category LIKE ? OR priority LIKE ? OR status LIKE ? OR admin_remark LIKE ?)
            ORDER BY id DESC
        """, (
            session["user_id"],
            f"%{search}%", f"%{search}%", f"%{search}%", f"%{search}%", f"%{search}%"
        )).fetchall()
    else:
        complaints = conn.execute("""
            SELECT * FROM complaints
            WHERE user_id = ?
            ORDER BY id DESC
        """, (session["user_id"],)).fetchall()

    conn.close()

    # Convert to list of tuples for Jinja2 index access (c[0], c[6] etc.)
    complaints = [tuple(c) for c in complaints]

    return render_template(
        "dashboard.html",
        complaints=complaints,
        name=session["user_name"],
        search=search
    )


# ================================================================
#  ADD COMPLAINT
# ================================================================

@app.route("/add_complaint", methods=["GET", "POST"])
def add_complaint():
    if "user_id" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":
        category   = (request.form.get("category")    or "").strip()
        issue_type = (request.form.get("issue_type")  or "").strip()
        description= (request.form.get("description") or "").strip()
        priority   = (request.form.get("priority")    or "").strip()

        if category == "Other":
            subject = (request.form.get("subject") or "").strip()
            if not subject or not description:
                return "Subject and description are required for Other category."
        else:
            subject = issue_type
            if not subject:
                return "Please select a common issue."

        file      = request.files.get("file")
        file_path = None

        if file and file.filename != "":
            if allowed_file(file.filename):
                filename  = secure_filename(file.filename)
                file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
                file.save(file_path)
            else:
                return "Invalid file type."

        conn = get_db()
        cur  = conn.cursor()

        cur.execute("""
            INSERT INTO complaints (user_id, subject, description, category, priority, file_path)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (session["user_id"], subject, description, category, priority, file_path))

        complaint_id = cur.lastrowid

        cur.execute("""
            INSERT INTO complaint_logs (complaint_id, status, remark, updated_by)
            VALUES (?, 'Pending', 'Complaint submitted', 'System')
        """, (complaint_id,))

        conn.commit()
        conn.close()

        # Email notifications
        _send_complaint_emails(complaint_id, subject, category, priority, description)

        return redirect(url_for("dashboard"))

    return render_template("add_complaint.html")


def _send_complaint_emails(complaint_id, subject, category, priority, description):
    admin_html = f"""
    <html><body style="font-family:Arial,sans-serif;background:#f8fafc;padding:20px;color:#0f172a;">
    <div style="max-width:600px;margin:auto;background:white;border:1px solid #e2e8f0;border-radius:14px;overflow:hidden;">
        <div style="background:#1e293b;color:white;padding:18px 24px;">
            <h2 style="margin:0;font-size:20px;">New Complaint — CMP-{complaint_id:03d}</h2>
        </div>
        <div style="padding:24px;">
            <table style="width:100%;border-collapse:collapse;">
                <tr><td style="padding:10px;border:1px solid #e2e8f0;"><strong>ID</strong></td><td style="padding:10px;border:1px solid #e2e8f0;">CMP-{complaint_id:03d}</td></tr>
                <tr><td style="padding:10px;border:1px solid #e2e8f0;"><strong>Subject</strong></td><td style="padding:10px;border:1px solid #e2e8f0;">{subject}</td></tr>
                <tr><td style="padding:10px;border:1px solid #e2e8f0;"><strong>Category</strong></td><td style="padding:10px;border:1px solid #e2e8f0;">{category}</td></tr>
                <tr><td style="padding:10px;border:1px solid #e2e8f0;"><strong>Priority</strong></td><td style="padding:10px;border:1px solid #e2e8f0;">{priority}</td></tr>
            </table>
            <div style="margin-top:16px;background:#f8fafc;border:1px solid #e2e8f0;padding:14px;border-radius:10px;">{description or 'No description'}</div>
        </div>
    </div></body></html>
    """
    send_email(ADMIN_EMAIL, f"New Complaint — CMP-{complaint_id:03d}", "", admin_html)

    user_email = session.get("user_email")
    if user_email:
        user_html = f"""
        <html><body style="font-family:Arial,sans-serif;background:#f8fafc;padding:20px;">
        <div style="max-width:600px;margin:auto;background:white;border:1px solid #e2e8f0;border-radius:14px;overflow:hidden;">
            <div style="background:#1e293b;color:white;padding:18px 24px;">
                <h2 style="margin:0;">Complaint Submitted ✓</h2>
            </div>
            <div style="padding:24px;">
                <p>Your complaint <strong>CMP-{complaint_id:03d}</strong> has been registered successfully.</p>
                <p>Status: <strong>Pending</strong> — We'll notify you when it's updated.</p>
            </div>
        </div></body></html>
        """
        send_email(user_email, f"Complaint Submitted — CMP-{complaint_id:03d}", "", user_html)


# ================================================================
#  DELETE COMPLAINT
# ================================================================

@app.route("/delete_complaint/<int:id>")
def delete_complaint(id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db()
    conn.execute("DELETE FROM complaints WHERE id = ? AND user_id = ?", (id, session["user_id"]))
    conn.commit()
    conn.close()

    return redirect(url_for("dashboard"))


# ================================================================
#  COMPLAINT DETAILS
# ================================================================

@app.route("/complaint/<int:id>")
def complaint_details(id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db()

    complaint = conn.execute(
        "SELECT * FROM complaints WHERE id = ? AND user_id = ?",
        (id, session["user_id"])
    ).fetchone()

    if not complaint:
        conn.close()
        return render_template("error.html", message="Complaint not found.")

    logs = conn.execute("""
        SELECT status, remark, updated_by, updated_at
        FROM complaint_logs
        WHERE complaint_id = ?
        ORDER BY updated_at DESC, id DESC
    """, (id,)).fetchall()

    conn.close()

    complaint = tuple(complaint)
    logs      = [tuple(l) for l in logs]

    return render_template("complaint_details.html", complaint=complaint, logs=logs)


# ================================================================
#  ADMIN DASHBOARD
# ================================================================

@app.route("/admin")
def admin():
    if "admin" not in session:
        return redirect(url_for("admin_login"))

    conn = get_db()

    complaints = conn.execute("""
        SELECT
            complaints.id,
            complaints.user_id,
            complaints.subject,
            complaints.description,
            complaints.category,
            complaints.priority,
            complaints.status,
            complaints.created_at,
            complaints.file_path,
            complaints.admin_remark,
            complaints.assigned_to,
            users.name  AS user_name,
            users.email AS user_email
        FROM complaints
        JOIN users ON complaints.user_id = users.id
        ORDER BY complaints.id DESC
    """).fetchall()

    complaints = [dict(c) for c in complaints]

    total_count       = conn.execute("SELECT COUNT(*) FROM complaints").fetchone()[0]
    pending_count     = conn.execute("SELECT COUNT(*) FROM complaints WHERE status = 'Pending'").fetchone()[0]
    in_progress_count = conn.execute("SELECT COUNT(*) FROM complaints WHERE status = 'In Progress'").fetchone()[0]
    resolved_count    = conn.execute("SELECT COUNT(*) FROM complaints WHERE status = 'Resolved'").fetchone()[0]
    important_count   = conn.execute("SELECT COUNT(*) FROM complaints WHERE priority IN ('High','Urgent')").fetchone()[0]

    today       = date.today().isoformat()
    today_count = conn.execute(
        "SELECT COUNT(*) FROM complaints WHERE DATE(created_at) = ?", (today,)
    ).fetchone()[0]

    category_summary = [dict(r) for r in conn.execute("""
        SELECT category, COUNT(*) as count
        FROM complaints GROUP BY category ORDER BY count DESC
    """).fetchall()]

    # Agents list for assignment dropdown
    agents = [dict(r) for r in conn.execute(
        "SELECT id, name, email FROM users WHERE role = 'agent' ORDER BY name"
    ).fetchall()]

    conn.close()

    return render_template(
        "admin.html",
        complaints=complaints,
        total_count=total_count,
        pending_count=pending_count,
        in_progress_count=in_progress_count,
        resolved_count=resolved_count,
        important_count=important_count,
        today_count=today_count,
        category_summary=category_summary,
        agents=agents
    )


# ================================================================
#  UPDATE COMPLAINT (Admin)
# ================================================================

@app.route("/update_complaint/<int:id>", methods=["POST"])
def update_complaint(id):
    if "admin" not in session and "agent_id" not in session:
        return redirect(url_for("login"))

    status      = (request.form.get("status")      or "Pending").strip()
    remark      = (request.form.get("remark")      or "").strip()
    assigned_to = request.form.get("assigned_to")
    updated_by  = "Admin" if "admin" in session else session.get("agent_name", "Agent")

    conn = get_db()

    # Get user email for notification
    row = conn.execute("""
        SELECT users.email, complaints.subject
        FROM complaints JOIN users ON complaints.user_id = users.id
        WHERE complaints.id = ?
    """, (id,)).fetchone()

    if assigned_to:
        conn.execute("""
            UPDATE complaints SET status = ?, admin_remark = ?, assigned_to = ? WHERE id = ?
        """, (status, remark, assigned_to, id))
    else:
        conn.execute("""
            UPDATE complaints SET status = ?, admin_remark = ? WHERE id = ?
        """, (status, remark, id))

    conn.execute("""
        INSERT INTO complaint_logs (complaint_id, status, remark, updated_by)
        VALUES (?, ?, ?, ?)
    """, (id, status, remark, updated_by))

    conn.commit()
    conn.close()

    # Notify user by email
    if row:
        user_email        = row["email"]
        complaint_subject = row["subject"]

        html_message = f"""
        <html><body style="font-family:Arial,sans-serif;background:#f8fafc;padding:20px;">
        <div style="max-width:600px;margin:auto;background:white;border:1px solid #e2e8f0;border-radius:14px;overflow:hidden;">
            <div style="background:#1e293b;color:white;padding:18px 24px;">
                <h2 style="margin:0;">Complaint Status Updated</h2>
            </div>
            <div style="padding:24px;">
                <p>Your complaint <strong>CMP-{id:03d} — {complaint_subject}</strong> has been updated.</p>
                <p>New Status: <strong>{status}</strong></p>
                <p>Remark: <em>{remark if remark else 'No remark added'}</em></p>
            </div>
        </div></body></html>
        """
        send_email(user_email, f"Complaint Update — CMP-{id:03d}", "", html_message)

    redirect_to = "agent_dashboard" if "agent_id" in session else "admin"
    return redirect(url_for(redirect_to))


# ================================================================
#  AGENT DASHBOARD
# ================================================================

@app.route("/agent")
def agent_dashboard():
    if "agent_id" not in session:
        return redirect(url_for("login"))

    conn = get_db()

    # Agents only see complaints assigned to them
    complaints = conn.execute("""
        SELECT
            complaints.id,
            complaints.subject,
            complaints.description,
            complaints.category,
            complaints.priority,
            complaints.status,
            complaints.created_at,
            complaints.file_path,
            complaints.admin_remark,
            users.name  AS user_name,
            users.email AS user_email
        FROM complaints
        JOIN users ON complaints.user_id = users.id
        WHERE complaints.assigned_to = ?
        ORDER BY complaints.id DESC
    """, (session["agent_id"],)).fetchall()

    complaints = [dict(c) for c in complaints]

    total      = len(complaints)
    pending    = sum(1 for c in complaints if c["status"] == "Pending")
    in_prog    = sum(1 for c in complaints if c["status"] == "In Progress")
    resolved   = sum(1 for c in complaints if c["status"] == "Resolved")

    conn.close()

    return render_template(
        "agent_dashboard.html",
        complaints=complaints,
        name=session["agent_name"],
        total=total,
        pending=pending,
        in_progress=in_prog,
        resolved=resolved
    )


# ================================================================
#  ADMIN — CREATE AGENT ACCOUNT
# ================================================================

@app.route("/admin/create_agent", methods=["GET", "POST"])
def create_agent():
    if "admin" not in session:
        return redirect(url_for("admin_login"))

    error   = None
    success = None

    if request.method == "POST":
        name     = (request.form.get("name")     or "").strip()
        email    = (request.form.get("email")    or "").strip()
        password = (request.form.get("password") or "").strip()

        if not name or not email or not password:
            error = "All fields are required."
        else:
            hashed = generate_password_hash(password)
            try:
                conn = get_db()
                conn.execute(
                    "INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, 'agent')",
                    (name, email, hashed)
                )
                conn.commit()
                conn.close()
                success = f"Agent '{name}' created successfully!"
            except sqlite3.IntegrityError:
                error = "Email already exists."

    return render_template("create_agent.html", error=error, success=success)


# ================================================================
#  LOGOUT
# ================================================================

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


# ================================================================
#  CLOUD DEPLOY READY
# ================================================================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)