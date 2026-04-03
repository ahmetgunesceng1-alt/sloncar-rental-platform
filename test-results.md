# Test Execution Results

Generated: 2026-04-03T18:13:41.077Z

================================================================================

Command: SERVER_PORT=3000 python test_auth_api.py
Exit Code: 0

Output:
============================================================
API Test Suite: auth endpoints
============================================================

Checking server connectivity...
✓ Server responding (status 404)


[SETUP] Registering test user testbot+1775240020@example.com ...
  → register status: 201
  ✓ Auth: Got token from register response

[TEST] POST /api/auth/register - Create new user
  ✓ PASSED (status 201)

[TEST] POST /api/auth/login - Invalid credentials
  ✓ PASSED (status 401)

[TEST] GET /api/auth/profile - With valid token
  ✓ PASSED

[TEST] GET /api/auth/profile - With invalid token
  ✓ PASSED (status 401)

[TEST] PATCH /api/auth/profile - With valid token
  ✓ PASSED (status 200)

============================================================
Results: 5 passed, 0 failed, 0 skipped
============================================================

================================================================================

