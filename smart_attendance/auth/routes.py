import re

from flask import Blueprint, redirect, render_template_string, request, session, url_for

from smart_attendance.db import repository
from smart_attendance.extensions import bcrypt

auth_bp = Blueprint("auth", __name__)


# NetIDs are lowercase: either 5–9 letters, or the UTD-style 3 letters + 6 digits.
def valid_netid(netid):
    return re.fullmatch(r"([a-z]{5,9}|[a-z]{3}[0-9]{6})", netid) is not None


@auth_bp.route("/")
def home():
    return redirect(url_for("auth.login"))


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if "netid" in session:
        if session.get("is_instructor"):
            return redirect(url_for("auth.instructor_dashboard"))
        return redirect(url_for("auth.student_dashboard"))

    if request.method == "POST":
        netid = request.form["netid"].strip()
        password = request.form["password"].strip()

        if not valid_netid(netid):
            return "Invalid NetID format. Please ensure your NetID is all lowercase."

        # Auth is backed by the users table — bcrypt hash lives in users.password_hash.
        user = repository.get_user_by_netid(netid)
        if not user:
            return "User not found. Please try again."

        if bcrypt.check_password_hash(user["password_hash"], password):
            session.permanent = True
            session["netid"] = user["netid"]
            session["is_instructor"] = user["is_instructor"]

            if user["is_instructor"]:
                return redirect(url_for("auth.instructor_dashboard"))
            return redirect(url_for("auth.student_dashboard"))

        return "Incorrect password. Please try again."

    return render_template_string(
        """
        <form method="post">
            NetID: <input name="netid" type="text"><br>
            Password: <input name="password" type="password"><br>
            <input type="submit">
        </form>
    """
    )


@auth_bp.route("/instructor_dashboard")
def instructor_dashboard():
    if "netid" not in session:
        return redirect(url_for("auth.login"))

    if not session.get("is_instructor"):
        return "Access denied."

    return f"""
            Instructor Dashboard: {session['netid']}
            <form action="/logout" method="post">
                <button type="submit">Logout</button>
            </form>
        """


@auth_bp.route("/student_dashboard")
def student_dashboard():
    if "netid" not in session:
        return redirect(url_for("auth.login"))

    if session.get("is_instructor"):
        return "Access denied."

    return f"""
        Student Dashboard: {session['netid']}
        <form action="/logout" method="post">
                <button type="submit">Logout</button>
        </form>
    """


@auth_bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("auth.login"))
