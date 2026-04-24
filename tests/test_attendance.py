import pytest
from app import app
from tokens import generate_token

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def login_student(client):
    client.post('/login', data={
        "netid": "dal123456",
        "password": "password1234*"
    })

def login_instructor(client):
    client.post('/login', data={
        "netid": "proftest",
        "password": "profpass1*"
    })

# Test Case #1: Valid instructor session, valid token, valid action
def test_scan_attendance_valid(client):
    login_instructor(client)
    token = generate_token("dal123456", "CS3354.001")
    response = client.post('/attendance/scan', json={"token": token})
    assert response.status_code == 200
    assert response.get_json()["message"] == "attendance marked"

# Test Case #2: Exceptional session (not logged in), valid token, valid action
def test_scan_attendance_not_authenticated(client):
    token = generate_token("dal123456", "CS3354.001")
    response = client.post('/attendance/scan', json={"token": token})
    assert response.status_code == 401
    assert response.get_json()["error"] == "not authenticated"

# Test Case #3: Invalid instructor session (student), valid token, valid action
def test_scan_attendance_student_access_denied(client):
    login_student(client)
    token = generate_token("dal123456", "CS3354.001")
    response = client.post('/attendance/scan', json={"token": token})
    assert response.status_code == 403
    assert response.get_json()["error"] == "access denied"

# Test Case #4: Valid instructor session, invalid token, valid action
def test_scan_attendance_malformed_token(client):
    login_instructor(client)
    response = client.post('/attendance/scan', json={"token": "badtoken"})
    assert response.status_code == 400
    assert response.get_json()["error"] == "invalid token: malformed token"

# Test Case #5: Valid instructor session, exceptional token (missing), valid action
def test_scan_attendance_missing_token(client):
    login_instructor(client)
    response = client.post('/attendance/scan', json={})
    assert response.status_code == 400
    assert response.get_json()["error"] == "missing token"

# Test Case #6: Valid instructor session, valid token, invalid/cancel action
def test_scan_attendance_no_action(client):
    login_instructor(client)
    response = client.get('/instructor_dashboard')
    assert b"Instructor Dashboard" in response.data

# Test Case #7: Valid instructor session, invalid token signature, valid action
def test_scan_attendance_invalid_signature(client):
    login_instructor(client)
    token = generate_token("dal123456", "CS3354.001")
    parts = token.split("|")
    tampered_token = f"abc123456|{parts[1]}|{parts[2]}|{parts[3]}"
    response = client.post('/attendance/scan', json={"token": tampered_token})
    assert response.status_code == 400
    assert response.get_json()["error"] == "invalid token: invalid signature"

# Test Case #8: Valid instructor session, expired token, valid action
def test_scan_attendance_expired_token(client):
    login_instructor(client)
    token = "dal123456|CS3354.001|1|abcdef1234567890"
    response = client.post('/attendance/scan', json={"token": token})
    assert response.status_code == 400

# Test Case #9: Valid instructor session, valid token, no active session
def test_scan_attendance_no_active_session(client, monkeypatch):
    import views

    def fake_db_is_session_active(course_id):
        return False

    monkeypatch.setattr(views, "db_is_session_active", fake_db_is_session_active)

    login_instructor(client)
    token = generate_token("dal123456", "CS3354.001")
    response = client.post('/attendance/scan', json={"token": token})
    assert response.status_code == 403
    assert response.get_json()["error"] == "no active session"

# Test Case #10: Valid instructor session, valid token, already marked present
def test_scan_attendance_already_marked(client, monkeypatch):
    import views

    def fake_db_is_already_marked(netid, course_id):
        return True

    monkeypatch.setattr(views, "db_is_already_marked", fake_db_is_already_marked)

    login_instructor(client)
    token = generate_token("dal123456", "CS3354.001")
    response = client.post('/attendance/scan', json={"token": token})
    assert response.status_code == 409
    assert response.get_json()["error"] == "already marked present"