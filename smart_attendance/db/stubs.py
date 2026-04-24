from smart_attendance.db.postgres import is_database_enabled
from smart_attendance.db import repository


def db_get_student(netid):
    if is_database_enabled():
        return repository.get_student(netid)
    return {
        "netid": netid,
        "name": "Stub Student",
        "email": f"{netid}@utdallas.edu",
    }


def db_get_course(course_id):
    if is_database_enabled():
        return repository.get_course(course_id)
    return {
        "course_id": course_id,
        "name": "Stub Course",
        "instructor": "Prof. Stub",
    }


def db_get_course_by_enrollment_code(code):
    if is_database_enabled():
        return repository.get_course_by_enrollment_code(code)
    return {
        "course_id": "CS3354.001",
        "name": "Stub Course",
        "enrollment_code": code,
    }


def db_is_enrolled(netid, course_id):
    if is_database_enabled():
        return repository.is_enrolled(netid, course_id)
    return False


def db_enroll_student(netid, course_id):
    if is_database_enabled():
        return repository.enroll_student(netid, course_id)
    return True


def db_is_session_active(course_id):
    if is_database_enabled():
        return repository.is_session_active(course_id)
    return True


def db_is_already_marked(netid, course_id):
    if is_database_enabled():
        return repository.is_already_marked(netid, course_id)
    return False


def db_mark_attendance(netid, course_id):
    if is_database_enabled():
        return repository.mark_attendance(netid, course_id)
    return True


def db_get_student_courses(netid):
    if is_database_enabled():
        return repository.get_student_courses(netid)
    return ["CS3354.001", "CS3345.601"]
