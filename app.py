import re, secrets
from flask import Flask, request, redirect, url_for, render_template_string, session
from flask_bcrypt import Bcrypt
from datetime import timedelta

app = Flask(__name__)
app.secret_key = secrets.token_hex(32) # Change this before the final version, will log everyone out each time the server restarts
app.permanent_session_lifetime = timedelta(days=7)

bcrypt = Bcrypt(app)

users_db = {
    "dal123456": {
        "password": bcrypt.generate_password_hash("password1234*").decode('utf-8'),
        "is_instructor": False
    },
    "proftest": {
        "password": bcrypt.generate_password_hash("profpass1*").decode('utf-8'),
        "is_instructor": True
    }
}

# check if valid netid
# very old netids can be only characters (will likely only be applicable for professors who have been here a while)
# newer netids will be 3 letters followed by 6 digits
# all netids will be between 5-9 characters
def valid_netid(netid):
    return re.fullmatch(r"([a-z]{5,9}|[a-z]{3}[0-9]{6})", netid) is not None

@app.route('/login', methods=['GET', 'POST'])
def login():
    # check if already logged in
    if "netid" in session:
        if session.get("is_instructor"):
            return redirect(url_for("instructor_dashboard"))
        else:
            return redirect(url_for("student_dashboard"))
    # generic log in
    if request.method == 'POST':
        netid = request.form['netid'].strip()
        password = request.form['password'].strip()

        # validate netid is correct format
        if not valid_netid(netid):
            return "Invalid NetID format. Please ensure your NetID is all lowercase."

        # validate user exists
        if netid not in users_db:
            return "User not found. Please try again."

        # check password
        user = users_db[netid]
        hashed_password = user["password"]
        if bcrypt.check_password_hash(hashed_password, password):
            session.permanent = True
            session["netid"] = netid
            session["is_instructor"] = user["is_instructor"]

            if user["is_instructor"]:
                return redirect(url_for("instructor_dashboard"))
            else:
                return redirect(url_for('student_dashboard'))
        else:
            return "Incorrect password. Please try again."

    return render_template_string("""
        <form method="post">
            NetID: <input name="netid" type="text"><br>
            Password: <input name = "password" type="password"><br>
            <input type="submit">
        </form>
    """)

@app.route('/instructor_dashboard')
def instructor_dashboard():
        if "netid" not in session:
            return redirect(url_for("login"))

        if not session.get("is_instructor"):
            return "Access denied."

        return f"""
            Instructor Dashboard: {session['netid']}
            <form action="/logout" method="post">
                <button type="submit">Logout</button>
            </form>
        """

@app.route('/student_dashboard')
def student_dashboard():
    if "netid" not in session:
        return redirect(url_for("login"))

    if session.get("is_instructor"):
        return "Access denied."

    return f"""
        Student Dashboard: {session['netid']}
        <form action="/logout" method="post">
                <button type="submit">Logout</button>
        </form>
    """

@app.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return redirect(url_for("login"))