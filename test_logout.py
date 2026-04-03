import pytest
from app import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

# Test Case #1: Click Logout
def test_logout(client):
    # log in a user to set the session
    client.post('/login', data={
        "netid": "dal123456",
        "password": "password1234*"
    })

    # Now logout
    response = client.post('/logout', follow_redirects=True)
    
    assert b"NetID:" in response.data
    assert b"Password:" in response.data

# Test Case #2: No Click (invalid)
def test_no_logout_action(client):
    # Log in a user to set the session
    client.post('/login', data={
        "netid": "dal123456",
        "password": "password1234*"
    })

    response = client.get('/student_dashboard')
    assert b"Student Dashboard" in response.data
    assert b"Logout" in response.data