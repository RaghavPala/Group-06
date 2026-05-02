# TODO

## 1. Fix enrollment QR generation — persist code to DB on first create
`smart_attendance/attendance/routes.py` — `/enroll/qr` route

Currently generates a new enrollment code on every call but never saves it to the DB, so student `/enroll/join` lookups always 404. 

Fix: on first QR request for a course, generate + persist the code. On subsequent calls, return the already-saved code instead of generating a new one.

## 2. Fix hardcoded course_id in instructor dashboard
`templates/instructor_dashboard.html` — `loadEnrollQR()` (line 299)

`course_id` is hardcoded as `CS3354.001`. Should be dynamic — pulled from the currently selected/active course in the UI.
