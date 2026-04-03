# Test Execution Results

Generated: 2026-04-03T10:09:35.606Z

================================================================================

Command: SERVER_PORT=3000 python test-api.py
Exit Code: 0

Output:
============================================================
API Test Suite - Auth Endpoints
============================================================

Checking server connectivity...
✓ Server responding (status 404)


[SETUP] Registering test user...
  ↩ Register status: 201
  ✓ Got token from register response

[TEST] POST /api/auth/register - Happy path
  ✓ PASSED (status 409)

[TEST] POST /api/auth/login - Happy path
  ✓ PASSED (status 200) - token obtained

[TEST] POST /api/auth/login - Invalid credentials
  ✓ PASSED (status 401)

[TEST] GET /api/auth/profile - With valid auth
  ✓ PASSED (status 200)

[TEST] GET /api/auth/profile - With invalid token
  ✓ PASSED (status 401)

[TEST] PATCH /api/auth/profile - With valid auth
  ✓ PASSED (status 200)

[TEST] PATCH /api/auth/profile - Without auth
  ✓ PASSED (status 401)

============================================================
Results: 7 passed, 0 failed, 0 skipped
============================================================

================================================================================

