import re, secrets
from flask import Flask, request, redirect, url_for, render_template, session
from flask_bcrypt import Bcrypt
from datetime import timedelta
from views import attendance_bp, db_get_student_courses, db_get_course, db_is_session_active, generate_token, get_current_epoch, get_window_seconds_remaining

app = Flask(__name__)
app.secret_key = secrets.token_hex(32) # Change this before the final version, will log everyone out each time the server restarts
app.permanent_session_lifetime = timedelta(days=7)


app.register_blueprint(attendance_bp)

@app.route('/')
def index():
    return redirect(url_for("login"))

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
            return render_template("login.html", error="Incorrect password. Please try again.")

    return render_template("login.html")

@app.route('/instructor_dashboard')
def instructor_dashboard():
    if "netid" not in session:
        return redirect(url_for("login"))
    if not session.get("is_instructor"):
        return "Access denied.", 403
    return render_template("instructor_dashboard.html", netid=session["netid"])

@app.route('/student_dashboard')
def student_dashboard():
    if "netid" not in session:
        return redirect(url_for("login"))
    if session.get("is_instructor"):
        return "Access denied.", 403

    netid = session["netid"]
    course_ids = db_get_student_courses(netid)
    epoch = get_current_epoch()
    seconds_remaining = get_window_seconds_remaining()

    courses = []
    for cid in course_ids:
        course = db_get_course(cid) or {"course_id": cid, "name": cid}
        active = db_is_session_active(cid)
        token = generate_token(netid, cid, epoch) if active else None
        courses.append({
            "course_id": cid,
            "name": course.get("name", cid),
            "active": active,
            "token": token,
        })

    return render_template("student_dashboard.html",
                           netid=netid,
                           courses=courses,
                           seconds_remaining=seconds_remaining)

@app.route('/enroll/join-form', methods=['POST'])
def join_course_form():
    """HTML form version of enroll/join for the student dashboard modal."""
    if "netid" not in session:
        return redirect(url_for("login"))
    from views import db_get_course_by_enrollment_code, db_is_enrolled, db_enroll_student
    netid = session["netid"]
    code = request.form.get("enrollment_code", "").strip().upper()
    if not code:
        return redirect(url_for("student_dashboard"))
    course = db_get_course_by_enrollment_code(code)
    if not course:
        return redirect(url_for("student_dashboard"))
    cid = course["course_id"]
    if not db_is_enrolled(netid, cid):
        db_enroll_student(netid, cid)
    return redirect(url_for("student_dashboard"))

@app.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return redirect(url_for("login"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True)
