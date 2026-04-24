import secrets
from datetime import timedelta

from flask import Flask

from smart_attendance.attendance.routes import attendance_bp
from smart_attendance.auth.routes import auth_bp, initialize_users
from smart_attendance.extensions import bcrypt


def create_app():
    app = Flask(__name__)
    app.secret_key = secrets.token_hex(32)
    app.permanent_session_lifetime = timedelta(days=7)

    bcrypt.init_app(app)

    with app.app_context():
        initialize_users()

    app.register_blueprint(auth_bp)
    app.register_blueprint(attendance_bp)

    return app
