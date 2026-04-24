from flask import Blueprint, jsonify, request, session

from smart_attendance.db.stubs import (
    db_enroll_student,
    db_get_course,
    db_get_course_by_enrollment_code,
    db_get_student,
    db_get_student_courses,
    db_is_already_marked,
    db_is_enrolled,
    db_is_session_active,
    db_mark_attendance,
)
from smart_attendance.services.tokens import (
    generate_token,
    get_current_epoch,
    get_window_seconds_remaining,
    validate_token,
)
from smart_attendance.utils.codes import generate_enrollment_code

attendance_bp = Blueprint("attendance", __name__)


@attendance_bp.route("/enroll/qr", methods=["GET"])
def get_enrollment_qr():
    if "netid" not in session:
        return jsonify({"error": "not authenticated"}), 401
    if not session.get("is_instructor"):
        return jsonify({"error": "access denied"}), 403

    course_id = request.args.get("course_id")

    course = db_get_course(course_id)
    if not course:
        return jsonify({"error": "course not found"}), 404

    enrollment_code = generate_enrollment_code()
    return jsonify({"enrollment_code": enrollment_code})


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

    course = db_get_course_by_enrollment_code(enrollment_code)
    if not course:
        return jsonify({"error": "invalid enrollment code"}), 404

    course_id = course["course_id"]

    if db_is_enrolled(netid, course_id):
        return jsonify({"error": "already enrolled"}), 409

    success = db_enroll_student(netid, course_id)
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
    student = db_get_student(netid)
    if not student:
        return jsonify({"error": "student not found"}), 404

    courses = db_get_student_courses(netid)
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

    if not db_is_session_active(course_id):
        return jsonify({"error": "no active session"}), 403

    if db_is_already_marked(netid, course_id):
        return jsonify({"error": "already marked present"}), 409

    success = db_mark_attendance(netid, course_id)
    if not success:
        return jsonify({"error": "failed to record attendance"}), 500

    return jsonify(
        {
            "message": "attendance marked",
            "netid": netid,
            "course_id": course_id,
        }
    )
