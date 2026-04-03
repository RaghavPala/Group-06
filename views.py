import random
import string

from flask import Blueprint, request, jsonify, session

from tokens import generate_token, validate_token, get_current_epoch, get_window_seconds_remaining

attendance_bp = Blueprint("attendance", __name__)


# ---------------------------------------------------------------------------
# DB STUBS
# replace each function body with real DB calls when models are ready
# the return types and shapes here are the contract - don't change those
# ---------------------------------------------------------------------------

def db_get_student(netid):
    # stub: return student record or None if not found
    # real version: query users table by netid, return None if missing
    return {
        "netid": netid,
        "name": "Stub Student",
        "email": f"{netid}@utdallas.edu",
    }

def db_get_course(course_id):
    # stub: return course record or None if not found
    # real version: query courses table by course_id (e.g. "CS4337.007")
    return {
        "course_id": course_id,
        "name": "Stub Course",
        "instructor": "Prof. Stub",
    }

def db_get_course_by_enrollment_code(code):
    # stub: look up course by 8-char enrollment code, return None if invalid
    # real version: query courses table where enrollment_code == code
    return {
        "course_id": "CS3354.001",
        "name": "Stub Course",
        "enrollment_code": code,
    }

def db_is_enrolled(netid, course_id):
    # stub: always returns False (not enrolled) so join_course always proceeds
    # real version: check enrollments table for (netid, course_id) row
    return False

def db_enroll_student(netid, course_id):
    # stub: always succeeds
    # real version: insert row into enrollments table, return False on DB error
    return True

def db_is_session_active(course_id):
    # stub: always returns True (session always active)
    # real version: check if there's an active class session for this course right now
    # i.e. class started, attendance window hasn't closed yet (within 10min of start)
    return True

def db_is_already_marked(netid, course_id):
    # stub: always returns False (not yet marked)
    # real version: check attendance table for (netid, course_id, today's date)
    return False

def db_mark_attendance(netid, course_id):
    # stub: always succeeds
    # real version: insert attendance record into DB, return False on DB error
    return True

def db_get_student_courses(netid):
    # stub: returns two fake course IDs
    # real version: query enrollments table for all courses this student is in
    # course_id format is like "CS4337.007", "MATH2414.012", "PHYS2326.002"
    return ["CS3354.001", "CS3345.601"]


# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------

def generate_enrollment_code():
    # 8-char uppercase alphanumeric, kahoot-style
    # in production this should be generated once per course and stored in DB
    # not regenerated on every request like we're doing in the demo
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=8))


# ---------------------------------------------------------------------------
# ROUTES
# ---------------------------------------------------------------------------

# -- ENROLLMENT --

# GET /enroll/qr?course_id=CS4337.007
# who calls this: professor's dashboard, once per course to display enrollment QR
# what it does: returns the 8-char enrollment code as plain text
#               professor's dashboard renders it into a big QR via qrcode.js client-side
#               also shown as plaintext on screen as fallback for students who can't scan
# auth: instructor only (students have no reason to hit this)
# test: valid course_id with instructor session → 200 + enrollment_code in response
# test: no active session → 401
# test: student session (not instructor) → 403
# test: course_id that doesn't exist → 404 (once stubs are replaced with real DB)
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

    # in production: fetch the existing code from DB instead of generating a new one
    enrollment_code = generate_enrollment_code()

    return jsonify({"enrollment_code": enrollment_code})


# POST /enroll/join
# body: { "enrollment_code": "ABCD1234" }
# who calls this: student's PWA after scanning the enrollment QR or typing the code manually
#                 either way the client just sends the 8-char string here, same endpoint
# what it does: looks up which course that code belongs to, enrolls the student
# auth: student only (netid pulled from session, not from request body — can't spoof)
# test: valid code + student session → 200 + course_id in response
# test: no active session → 401
# test: instructor session hits this → 403
# test: enrollment_code missing from body → 400
# test: invalid/unknown enrollment code → 404 (once stubs are replaced)
# test: student already enrolled in that course → 409
@attendance_bp.route("/enroll/join", methods=["POST"])
def join_course():
    if "netid" not in session:
        return jsonify({"error": "not authenticated"}), 401
    if session.get("is_instructor"):
        return jsonify({"error": "access denied"}), 403

    # pull netid from session, not from request body
    # if we let the client send netid in the body, a student could enroll someone else
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


# -- ATTENDANCE --

# GET /attendance/qr
# who calls this: student's PWA, polling every 5s
# what it does: returns raw token strings for all of the student's enrolled courses
#               client renders each token into a QR locally using qrcode.js — no image gen server-side
#               all courses share the same 30s window clock so all QRs rotate at the same time
#               client checks seconds_remaining to know when to re-poll and re-render
# auth: student only (netid pulled from session)
# PWA side: QRCode.toCanvas(canvasElement, token) for each token in the response
# test: valid student session → 200, response has epoch + seconds_remaining + tokens array
# test: no active session → 401
# test: instructor session → 403
# test: poll twice within same 30s window → same epoch and same tokens both times
# test: mock time to cross a window boundary between polls → epoch increments, tokens change
@attendance_bp.route("/attendance/qr", methods=["GET"])
def get_attendance_qr():
    if "netid" not in session:
        return jsonify({"error": "not authenticated"}), 401
    if session.get("is_instructor"):
        return jsonify({"error": "access denied"}), 403

    # pull netid from session — client doesn't send it, can't spoof it
    netid = session["netid"]

    student = db_get_student(netid)
    if not student:
        return jsonify({"error": "student not found"}), 404

    courses = db_get_student_courses(netid)
    epoch = get_current_epoch()
    seconds_remaining = get_window_seconds_remaining()

    # one token per course, all same epoch
    # token format: netid|course_id|epoch|hmac_sig
    tokens = [
        {"course_id": course_id, "token": generate_token(netid, course_id, epoch)}
        for course_id in courses
    ]

    return jsonify({
        "epoch": epoch,
        "seconds_remaining": seconds_remaining,
        "tokens": tokens,
    })


# POST /attendance/scan
# body: { "token": "dal123456|CS4337.007|1234567|a3f9bc12d4e7f091" }
# who calls this: professor's webcam dashboard after reading the QR off a student's phone screen
#                 webcam decodes QR → gets raw token string → dashboard posts it here
# what it does: validates token (signature + epoch), checks session is active, marks student present
# auth: instructor only (only professor's dashboard should be scanning)
# test: valid token + active session + not yet marked → 200
# test: no active session → 401
# test: student session hits this → 403
# test: missing token in body → 400
# test: expired token (old epoch) → 400, "token expired"
# test: forged token (tampered netid) → 400, "invalid signature"
# test: valid token but no active class session → 403
# test: valid token but student already marked → 409
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

    # validate signature + epoch — see tokens.py for the full breakdown
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

    return jsonify({
        "message": "attendance marked",
        "netid": netid,
        "course_id": course_id,
    })
