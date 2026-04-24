import sys

from smart_attendance.attendance import routes as _routes


sys.modules[__name__] = _routes
