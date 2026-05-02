import hashlib
import hmac
import math
import time

SECRET_KEY = "change in prod (or not)"
WINDOW_SIZE = 30
GRACE_PERIOD = 30


def get_current_epoch():
    return math.floor(time.time() / WINDOW_SIZE)


def get_window_seconds_remaining():
    return WINDOW_SIZE - (int(time.time()) % WINDOW_SIZE)


def generate_token(netid, course_id, epoch=None):
    if epoch is None:
        epoch = get_current_epoch()

    payload = f"{netid}|{course_id}|{epoch}"
    signature = hmac.new(
        SECRET_KEY.encode(),
        payload.encode(),
        hashlib.sha256,
    ).hexdigest()[:16]
    return f"{payload}|{signature}"


def validate_token(token):
    try:
        parts = token.split("|")
        if len(parts) != 4:
            return False, {"error": "malformed token"}
        netid, course_id, epoch_str, provided_sig = parts
        epoch = int(epoch_str)
    except (ValueError, AttributeError):
        return False, {"error": "malformed token"}

    payload = f"{netid}|{course_id}|{epoch}"
    expected_sig = hmac.new(
        SECRET_KEY.encode(),
        payload.encode(),
        hashlib.sha256,
    ).hexdigest()[:16]

    if not hmac.compare_digest(expected_sig, provided_sig):
        return False, {"error": "invalid signature"}

    current_epoch = get_current_epoch()
    seconds_into_window = int(time.time()) % WINDOW_SIZE

    if epoch == current_epoch:
        pass
    elif epoch == current_epoch - 1 and seconds_into_window <= GRACE_PERIOD:
        pass
    else:
        return False, {"error": "token expired"}

    return True, {"netid": netid, "course_id": course_id, "epoch": epoch}
