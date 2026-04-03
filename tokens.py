import hmac
import hashlib
import math
import time

# hardcoded for demo, load from env in production
# 32 chars to match app.py's secret key length
SECRET_KEY = "change in prod (or not)"
WINDOW_SIZE = 30  # seconds per QR rotation
GRACE_PERIOD = 30  # extra seconds after a window ends where the old token still works
                  # needed for students who generate their QR right at the edge of a window


def get_current_epoch():
    # divides unix timestamp by 30 and floors it
    # every machine in the world computes the same number at the same moment — no shared state needed
    # increments by 1 every 30s, this is the heartbeat everything syncs to
    # test: call twice within same 30s window → same value both times
    # test: mock time.time() to land exactly on a boundary (e.g. t=60.0) → should flip to next epoch
    return math.floor(time.time() / WINDOW_SIZE)


def get_window_seconds_remaining():
    # how many seconds are left before the current 30s window ends
    # client uses this to know when to re-poll and re-render the QR
    # test: if int(time.time()) % 30 == 8 → should return 22
    return WINDOW_SIZE - (int(time.time()) % WINDOW_SIZE)


def generate_token(netid, course_id, epoch=None):
    # builds the signed string that gets encoded into the QR code
    # format: netid|course_id|epoch|signature
    # example: dal123456|CS4337.007|1234567|a3f9bc12d4e7f091
    # dot in course_id (CS4337.007) is fine, we split on | not .
    if epoch is None:
        epoch = get_current_epoch()

    payload = f"{netid}|{course_id}|{epoch}"

    # HMAC = keyed hash using SECRET_KEY
    # students can't tamper with netid/course_id and produce a valid sig without the key
    signature = hmac.new(
        SECRET_KEY.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()[:16]  # 16 chars is plenty of entropy for a 30s validity window

    return f"{payload}|{signature}"


def validate_token(token):
    # returns (True, {"netid": ..., "course_id": ..., "epoch": ...}) on success
    # returns (False, {"error": "reason"}) on any failure
    #
    # test cases to cover:
    # - valid token from current epoch → True
    # - valid token from previous epoch, within grace period → True
    # - valid token from previous epoch, outside grace period → False, "token expired"
    # - token from 2+ epochs ago → False, "token expired"
    # - correct format but tampered netid → False, "invalid signature"
    # - garbage string / wrong number of | delimiters → False, "malformed token"

    try:
        parts = token.split("|")
        if len(parts) != 4:
            return False, {"error": "malformed token"}
        netid, course_id, epoch_str, provided_sig = parts
        epoch = int(epoch_str)
    except (ValueError, AttributeError):
        return False, {"error": "malformed token"}

    # recompute expected sig and compare
    # compare_digest is timing-safe so you can't brute-force by measuring response time
    payload = f"{netid}|{course_id}|{epoch}"
    expected_sig = hmac.new(
        SECRET_KEY.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()[:16]

    if not hmac.compare_digest(expected_sig, provided_sig):
        return False, {"error": "invalid signature"}

    # check epoch validity
    current_epoch = get_current_epoch()
    seconds_into_window = int(time.time()) % WINDOW_SIZE

    if epoch == current_epoch:
        pass  # current window, always valid
    elif epoch == current_epoch - 1 and seconds_into_window <= GRACE_PERIOD:
        pass  # just-expired window, within grace period
    else:
        return False, {"error": "token expired"}

    return True, {"netid": netid, "course_id": course_id, "epoch": epoch}
