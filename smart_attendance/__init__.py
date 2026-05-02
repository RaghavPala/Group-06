import secrets
from datetime import timedelta

from flask import Flask

from smart_attendance.attendance.routes import attendance_bp
from smart_attendance.auth.routes import auth_bp
from smart_attendance.db.postgres import is_database_enabled
from smart_attendance.extensions import bcrypt


def create_app():
    app = Flask(__name__)
    app.secret_key = secrets.token_hex(32)
    app.permanent_session_lifetime = timedelta(days=7)

    bcrypt.init_app(app)

    # Fail fast if the DB isn't configured. We used to silently fall back to an
    # in-memory stub layer, which hid misconfiguration; every route now requires
    # a real Postgres connection.
    if not is_database_enabled():
        raise RuntimeError(
            "DATABASE_URL must be set. Run db-schema-seeding/schema.sql + "
            "seed.sql (or `docker compose up`) and export DATABASE_URL before "
            "starting the app."
        )

    app.register_blueprint(auth_bp)
    app.register_blueprint(attendance_bp)

    return app
