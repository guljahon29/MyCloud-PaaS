
import os
import sqlite3
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "mycloud-demo-secret-key")

DB_NAME = "mycloud.db"


def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_db() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )
        """)
        db.execute("""
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                language TEXT NOT NULL,
                status TEXT DEFAULT 'Created'
            )
        """)


def login_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return func(*args, **kwargs)
    return wrapper


@app.route("/")
def home():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return render_template("index.html", page="home")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if len(username) < 3 or len(password) < 6:
            flash("Login kamida 3, parol esa 6 belgidan iborat bo'lsin.")
            return redirect(url_for("register"))

        try:
            with get_db() as db:
                db.execute(
                    "INSERT INTO users (username, password) VALUES (?, ?)",
                    (username, generate_password_hash(password))
                )
            flash("Hisob yaratildi. Endi tizimga kiring!")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("Bu login band. Boshqa login tanlang.")

    return render_template("index.html", page="register")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        with get_db() as db:
            user = db.execute(
                "SELECT * FROM users WHERE username = ?", (username,)
            ).fetchone()

        if user and check_password_hash(user["password"], password):
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            return redirect(url_for("dashboard"))

        flash("Login yoki parol noto'g'ri.")

    return render_template("index.html", page="login")


@app.route("/dashboard")
@login_required
def dashboard():
    with get_db() as db:
        projects = db.execute(
            "SELECT * FROM projects WHERE user_id = ? ORDER BY id DESC",
            (session["user_id"],)
        ).fetchall()

    return render_template(
        "index.html", page="dashboard", projects=projects
    )


@app.route("/add_project", methods=["POST"])
@login_required
def add_project():
    name = request.form.get("name", "").strip()
    language = request.form.get("language", "Python")

    if name:
        with get_db() as db:
            db.execute(
                "INSERT INTO projects (user_id, name, language) VALUES (?, ?, ?)",
                (session["user_id"], name, language)
            )
        flash("Loyiha muvaffaqiyatli qo'shildi!")

    return redirect(url_for("dashboard"))


@app.route("/deploy/<int:project_id>", methods=["POST"])
@login_required
def deploy(project_id):
    with get_db() as db:
        project = db.execute(
            "SELECT * FROM projects WHERE id = ? AND user_id = ?",
            (project_id, session["user_id"])
        ).fetchone()

        if project:
            db.execute(
                "UPDATE projects SET status = 'Demo live' WHERE id = ?",
                (project_id,)
            )
            flash("Demo loyiha ishga tushirildi!")

    return redirect(url_for("dashboard"))


@app.route("/demo/<int:project_id>")
@login_required
def demo(project_id):
    with get_db() as db:
        project = db.execute(
            "SELECT * FROM projects WHERE id = ? AND user_id = ?",
            (project_id, session["user_id"])
        ).fetchone()

    if not project or project["status"] != "Demo live":
        return "Demo loyiha hali ishga tushirilmagan.", 404

    return render_template("index.html", page="demo", project=project)


@app.route("/delete/<int:project_id>", methods=["POST"])
@login_required
def delete_project(project_id):
    with get_db() as db:
        db.execute(
            "DELETE FROM projects WHERE id = ? AND user_id = ?",
            (project_id, session["user_id"])
        )

    flash("Loyiha o'chirildi.")
    return redirect(url_for("dashboard"))


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


init_db()

if __name__ == "__main__":
    app.run(debug=True)
