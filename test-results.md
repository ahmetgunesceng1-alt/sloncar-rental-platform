# Test Execution Results

Generated: 2026-04-03T17:38:46.627Z

================================================================================

Command: SERVER_PORT=3000 python test-api.py
Exit Code: 0

Output:
============================================================
API Test Suite - Auth Endpoints
============================================================

Checking server connectivity...
✓ Server responding (status 404)


[SETUP] Attempting to register and login test user...
  → Register status: 201
  ✓ Got token from register response

[TEST] POST /api/auth/register - Register new user
  ✓ PASSED (status 201)

[TEST] POST /api/auth/login - Login with valid credentials
  ✓ PASSED (status 200) - token obtained

[TEST] GET /api/auth/profile - Fetch current user's profile
  ✓ PASSED (status 200)

[TEST] PATCH /api/auth/profile - Update current user's profile
  ✓ PASSED (status 200)

[TEST] POST /api/auth/login - Invalid credentials should be rejected
  ✓ PASSED (status 401)

[TEST] GET /api/auth/profile - Access with invalid token
  ✓ PASSED (status 401)

============================================================
Results: 6 passed, 0 failed, 0 skipped
============================================================

================================================================================

