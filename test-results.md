# Test Execution Results

Generated: 2026-03-23T14:11:11.528Z

================================================================================

Command: SERVER_PORT=3000 python test_api_auth.py
Exit Code: 0

Output:
============================================================
API Test Suite: auth endpoints
============================================================

Checking server connectivity...
✓ Server responding (status 404)


[SETUP] Registering test user to obtain auth token (if supported)
  → Register status: 201
  ✓ Auth: Got token from register response

[TEST] POST /api/auth/register - Create new user
  ✓ PASSED (status 409)

[TEST] POST /api/auth/login - Login with correct credentials
  ✓ PASSED (status 200) - token acquired

[TEST] POST /api/auth/login - Invalid credentials
  ✓ PASSED (status 401)

[TEST] GET /api/auth/profile - With valid auth token
  ✓ PASSED (status 200)

[TEST] GET /api/auth/profile - With invalid token
  ✓ PASSED (status 401)

[TEST] PATCH /api/auth/profile - With valid auth token
  ✓ PASSED (status 200)

[TEST] PATCH /api/auth/profile - With invalid token
  ✓ PASSED (status 401)

============================================================
Results: 7 passed, 0 failed, 0 skipped
============================================================

================================================================================

