import csv
import io

from flask import Blueprint, Response, jsonify, request, session

from smart_attendance.db import repository
from smart_attendance.services.tokens import (
    generate_token,
    get_current_epoch,
    get_window_seconds_remaining,
    validate_token,
)
from smart_attendance.utils.codes import generate_enrollment_code

attendance_bp = Blueprint("attendance", __name__)

db_get_student_courses = repository.get_student_courses
db_get_course = repository.get_course
db_is_session_active = repository.is_session_active
db_get_course_by_enrollment_code = repository.get_course_by_enrollment_code
db_is_enrolled = repository.is_enrolled
db_enroll_student = repository.enroll_student
db_get_instructor_courses = repository.get_instructor_courses
db_get_course_students = repository.get_course_students
db_end_session = repository.end_session
db_get_session_status = repository.get_session_status


# Instructor creates a new course. Enrollment code is server-generated so the
# instructor can't pick a predictable one. Returns the code so the UI can show
# it / render a QR for students to join with.
@attendance_bp.route("/course", methods=["POST"])
def create_course():
    if "netid" not in session:
        return jsonify({"error": "not authenticated"}), 401
    if not session.get("is_instructor"):
        return jsonify({"error": "access denied"}), 403

    body = request.get_json() or {}
    course_id = body.get("course_id")
    course_name = body.get("course_name")

    if not course_id or not course_name:
        return jsonify({"error": "missing course_id or course_name"}), 400

    enrollment_code = generate_enrollment_code()
    created = repository.create_course(
        course_id, course_name, session["netid"], enrollment_code
    )
    if not created:
        return jsonify({"error": "course_id already exists"}), 409

    return jsonify(
        {
            "course_id": course_id,
            "course_name": course_name,
            "enrollment_code": enrollment_code,
        }
    ), 201


# Instructor opens a class session — this is what flips `is_active` TRUE so
# that /attendance/scan starts accepting tokens. Only the course's owning
# instructor can start a session for it.
@attendance_bp.route("/session/start", methods=["POST"])
def start_session():
    if "netid" not in session:
        return jsonify({"error": "not authenticated"}), 401
    if not session.get("is_instructor"):
        return jsonify({"error": "access denied"}), 403

    body = request.get_json() or {}
    course_id = body.get("course_id")
    # Reasonable defaults: 15-minute scan window inside a 75-minute class.
    window_minutes = int(body.get("window_minutes", 15))
    duration_minutes = int(body.get("duration_minutes", 75))

    if not course_id:
        return jsonify({"error": "missing course_id"}), 400

    course = repository.get_course(course_id)
    if not course:
        return jsonify({"error": "course not found"}), 404
    if course["instructor"] != session["netid"]:
        return jsonify({"error": "not your course"}), 403

    session_id = repository.start_session(course_id, window_minutes, duration_minutes)
    return jsonify(
        {
            "session_id": session_id,
            "course_id": course_id,
            "window_minutes": window_minutes,
            "duration_minutes": duration_minutes,
        }
    ), 201


@attendance_bp.route("/session/end", methods=["POST"])
def end_session():
    if "netid" not in session:
        return jsonify({"error": "not authenticated"}), 401
    if not session.get("is_instructor"):
        return jsonify({"error": "access denied"}), 403
    body = request.get_json() or {}
    course_id = body.get("course_id")
    if not course_id:
        return jsonify({"error": "missing course_id"}), 400
    course = repository.get_course(course_id)
    if not course:
        return jsonify({"error": "course not found"}), 404
    if course["instructor"] != session["netid"]:
        return jsonify({"error": "not your course"}), 403
    ended = repository.end_session(course_id)
    if not ended:
        return jsonify({"error": "no active session"}), 404
    return jsonify({"message": "session ended", "course_id": course_id})


@attendance_bp.route("/session/status/<course_id>", methods=["GET"])
def get_session_status(course_id):
    if "netid" not in session:
        return jsonify({"error": "not authenticated"}), 401
    if not session.get("is_instructor"):
        return jsonify({"error": "access denied"}), 403
    course = repository.get_course(course_id)
    if not course:
        return jsonify({"error": "course not found"}), 404
    if course["instructor"] != session["netid"]:
        return jsonify({"error": "not your course"}), 403
    status = repository.get_session_status(course_id)
    return jsonify(status)


# Returns students who have been marked present in today's active session.
# Used by the instructor dashboard to populate the Present panel on load and after each scan.
@attendance_bp.route("/session/present/<course_id>", methods=["GET"])
def get_session_present(course_id):
    if "netid" not in session:
        return jsonify({"error": "not authenticated"}), 401
    if not session.get("is_instructor"):
        return jsonify({"error": "access denied"}), 403
    course = repository.get_course(course_id)
    if not course:
        return jsonify({"error": "course not found"}), 404
    if course["instructor"] != session["netid"]:
        return jsonify({"error": "not your course"}), 403
    present = repository.get_session_present(course_id)
    return jsonify({"present": present})


@attendance_bp.route("/enroll/qr", methods=["GET"])
def get_enrollment_qr():
    if "netid" not in session:
        return jsonify({"error": "not authenticated"}), 401
    if not session.get("is_instructor"):
        return jsonify({"error": "access denied"}), 403

    course_id = request.args.get("course_id")

    course = repository.get_course(course_id)
    if not course:
        return jsonify({"error": "course not found"}), 404
    if course["instructor"] != session["netid"]:
        return jsonify({"error": "not your course"}), 403

    return jsonify({"enrollment_code": course["enrollment_code"]})


@attendance_bp.route("/course/<course_id>/students", methods=["GET"])
def get_course_students(course_id):
    if "netid" not in session:
        return jsonify({"error": "not authenticated"}), 401
    if not session.get("is_instructor"):
        return jsonify({"error": "access denied"}), 403
    course = repository.get_course(course_id)
    if not course:
        return jsonify({"error": "course not found"}), 404
    if course["instructor"] != session["netid"]:
        return jsonify({"error": "not your course"}), 403
    students = repository.get_course_students(course_id)
    return jsonify({"students": students})


@attendance_bp.route("/instructor/courses", methods=["GET"])
def get_instructor_courses():
    if "netid" not in session:
        return jsonify({"error": "not authenticated"}), 401
    if not session.get("is_instructor"):
        return jsonify({"error": "access denied"}), 403
    courses = repository.get_instructor_courses(session["netid"])
    return jsonify({"courses": courses})


@attendance_bp.route("/enroll/join", methods=["POST"])
def join_course():
    if "netid" not in session:
        return jsonify({"error": "not authenticated"}), 401
    if session.get("is_instructor"):
        return jsonify({"error": "access denied"}), 403

    netid = session["netid"]
    body = request.get_json()
    enrollment_code = body.get("enrollment_code")

    if not enrollment_code:
        return jsonify({"error": "missing enrollment_code"}), 400

    course = repository.get_course_by_enrollment_code(enrollment_code)
    if not course:
        return jsonify({"error": "invalid enrollment code"}), 404

    course_id = course["course_id"]

    if repository.is_enrolled(netid, course_id):
        return jsonify({"error": "already enrolled"}), 409

    success = repository.enroll_student(netid, course_id)
    if not success:
        return jsonify({"error": "enrollment failed"}), 500

    return jsonify({"message": "enrolled", "course_id": course_id})


@attendance_bp.route("/attendance/qr", methods=["GET"])
def get_attendance_qr():
    if "netid" not in session:
        return jsonify({"error": "not authenticated"}), 401
    if session.get("is_instructor"):
        return jsonify({"error": "access denied"}), 403

    netid = session["netid"]
    student = repository.get_student(netid)
    if not student:
        return jsonify({"error": "student not found"}), 404

    courses = repository.get_student_courses(netid)
    epoch = get_current_epoch()
    seconds_remaining = get_window_seconds_remaining()

    tokens = [
        {"course_id": course_id, "token": generate_token(netid, course_id, epoch)}
        for course_id in courses
    ]

    return jsonify(
        {
            "epoch": epoch,
            "seconds_remaining": seconds_remaining,
            "tokens": tokens,
        }
    )


@attendance_bp.route("/attendance/scan", methods=["POST"])
def scan_attendance():
    if "netid" not in session:
        return jsonify({"error": "not authenticated"}), 401
    if not session.get("is_instructor"):
        return jsonify({"error": "access denied"}), 403

    body = request.get_json()
    token = body.get("token")

    if not token:
        return jsonify({"error": "missing token"}), 400

    valid, result = validate_token(token)
    if not valid:
        return jsonify({"error": f"invalid token: {result['error']}"}), 400

    netid = result["netid"]
    course_id = result["course_id"]

    if not repository.is_session_active(course_id):
        return jsonify({"error": "no active session"}), 403

    if repository.is_already_marked(netid, course_id):
        return jsonify({"error": "already marked present"}), 409

    success = repository.mark_attendance(netid, course_id)
    if not success:
        return jsonify({"error": "failed to record attendance"}), 500

    return jsonify(
        {
            "message": "attendance marked",
            "netid": netid,
            "course_id": course_id,
        }
    )


# Instructor-only CSV dump of every attendance record for a course,
# one CSV row per (session, student-who-attended).
@attendance_bp.route("/attendance/export", methods=["GET"])
def export_attendance():
    if "netid" not in session:
        return jsonify({"error": "not authenticated"}), 401
    if not session.get("is_instructor"):
        return jsonify({"error": "access denied"}), 403

    course_id = request.args.get("course_id")
    if not course_id:
        return jsonify({"error": "missing course_id"}), 400
    if not repository.get_course(course_id):
        return jsonify({"error": "course not found"}), 404

    rows = repository.get_course_attendance(course_id)

    # Build the CSV in memory. Small per-course volume makes streaming overkill.
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        ["netid", "name", "email", "class_date", "session_id", "scanned_at"]
    )
    for row in rows:
        writer.writerow(
            [
                row["netid"],
                row["name"],
                row["email"],
                row["class_date"],
                row["session_id"],
                row["scanned_at"],
            ]
        )

    return Response(
        buf.getvalue(),
        mimetype="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="attendance_{course_id}.csv"'
        },
    )
