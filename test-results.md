# Test Execution Results

Generated: 2026-04-03T09:48:59.316Z

================================================================================

Command: SERVER_PORT=3000 python test_auth.py
Exit Code: 0

Output:
============================================================
API Test Suite: Auth Endpoints
============================================================

Checking server connectivity...
✓ Server responding (status 404)


[SETUP] Attempting to register and login test user for auth token
  → Register status: 201
  ✓ Auth: Got token from register response

[TEST] POST /api/auth/register - Create user
  ✓ PASSED (status 409)

[TEST] POST /api/auth/login - Login with correct credentials
  ✓ PASSED: Login returned token (status 200)

[TEST] POST /api/auth/login - Invalid credentials
  ✓ PASSED (status 401)

[TEST] GET /api/auth/profile - Valid auth
  ✓ PASSED (status 200)

[TEST] PATCH /api/auth/profile - Update profile (auth required)
  ✓ PASSED (status 200)

[TEST] GET /api/auth/profile - Invalid token
  ✓ PASSED (status 401)

============================================================
Results: 6 passed, 0 failed, 0 skipped
============================================================

================================================================================

