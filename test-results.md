# Test Execution Results

Generated: 2026-04-03T09:54:47.754Z

================================================================================

Command: SERVER_PORT=3000 python test-api.py
Exit Code: 0

Output:
============================================================
API Test Suite - auth endpoints
============================================================

Checking server connectivity...
✓ Server responding (status 404)


Registering test user testbot+1775210087@example.com ...
  register status: 201
  ✓ Auth: Got token from register response

[TEST] POST /api/auth/register - Happy path
  ✓ PASSED (status 409)

[TEST] POST /api/auth/login - Happy path
  ✓ PASSED (status 200) - token obtained

[TEST] POST /api/auth/login - Invalid credentials
  ✓ PASSED (status 401)

[TEST] GET /api/auth/profile - Invalid token
  ✓ PASSED (status 401)

[TEST] GET /api/auth/profile - Happy path (requires auth)
  ✓ PASSED

[TEST] PATCH /api/auth/profile - Update profile (requires auth)
  ✓ PASSED (status 200)

[TEST] PATCH /api/auth/profile - Invalid token
  ✓ PASSED (status 401)

============================================================
Results: 7 passed, 0 failed, 0 skipped
============================================================

================================================================================

