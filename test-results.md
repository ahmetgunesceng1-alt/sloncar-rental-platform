# Test Execution Results

Generated: 2026-04-08T13:11:44.458Z

================================================================================

Command: SERVER_PORT=3000 python test_auth_api.py
Exit Code: 0

Output:
============================================================
API Test Suite - Auth Endpoints
============================================================

Checking server connectivity...
✓ Server responding (status 404)


[SETUP] Attempting to register test user...
    ── Request ──
    POST http://localhost:3000/api/auth/register
    Headers: {"Content-Type": "application/json"}
    Body: {"email": "testbot+1775653904@example.com", "password": "TestPass123!", "name": "Test Bot"}
    ── Response ──
    Status: 201
    Body: {"success": true, "data": {"user": {"id": "54d1d137-ebe2-4538-a7e8-66a3b64780ab", "email": "testbot+1775653904@example.com", "name": "Test Bot", "role": "USER"}, "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VySWQiOiI1NGQxZDEzNy1lYmUyLTQ1MzgtYTdlOC02NmEzYjY0NzgwYWIiLCJlbWFpbCI6InRlc3Rib3QrMTc3NTY1MzkwNEBleGFtcGxlLmNvbSIsInJvbGUiOiJVU0VSIiwiaWF0IjoxNzc1NjUzOTA0LCJleHAiOjE3NzYyNTg3MDR9.GwpBuNBRtMxFj8n29js2ktJMBgDOr2HuI9jtLILSZS0"}}
  ✓ Auth: Got token from register response

[TEST] POST /api/auth/register - Create new user
    ── Request ──
    POST http://localhost:3000/api/auth/register
    Headers: {"Content-Type": "application/json"}
    Body: {"email": "testbot+1775653904@example.com", "password": "TestPass123!", "name": "Test Bot"}
    ── Response ──
    Status: 409
    Body: {"success": false, "message": "User with this email already exists", "error": {"code": "CONFLICT"}}
  ✓ PASSED (status 409)

[TEST] POST /api/auth/login - Happy path
  ✓ SKIPPED: auth token already obtained in setup_auth

[TEST] POST /api/auth/login - Invalid credentials
    ── Request ──
    POST http://localhost:3000/api/auth/login
    Headers: {"Content-Type": "application/json"}
    Body: {"email": "no-such-user@example.com", "password": "wrongpassword"}
    ── Response ──
    Status: 401
    Body: {"success": false, "message": "Invalid email or password", "error": {"code": "UNAUTHORIZED"}}
  ✓ PASSED (status 401)

[TEST] GET /api/auth/profile - With valid token
    ── Request ──
    GET http://localhost:3000/api/auth/profile
    Headers: {"Authorization": "[REDACTED]"}
    ── Response ──
    Status: 200
    Body: {"success": true, "data": {"user": {"id": "54d1d137-ebe2-4538-a7e8-66a3b64780ab", "email": "testbot+1775653904@example.com", "name": "Test Bot", "role": "USER", "whatsappEnabled": true}}}
  ✓ PASSED

[TEST] PATCH /api/auth/profile - Update profile
    ── Request ──
    PATCH http://localhost:3000/api/auth/profile
    Headers: {"Authorization": "[REDACTED]", "Content-Type": "application/json"}
    Body: {"name": "Test Bot Updated"}
    ── Response ──
    Status: 200
    Body: {"success": true, "data": {"user": {"id": "54d1d137-ebe2-4538-a7e8-66a3b64780ab", "email": "testbot+1775653904@example.com", "name": "Test Bot", "role": "USER", "whatsappEnabled": true}}}
  ✓ PASSED (status 200)

[TEST] GET /api/auth/profile - Invalid token
    ── Request ──
    GET http://localhost:3000/api/auth/profile
    Headers: {"Authorization": "[REDACTED]"}
    ── Response ──
    Status: 401
    Body: {"success": false, "message": "Invalid or expired token", "error": {"code": "UNAUTHORIZED"}}
  ✓ PASSED (status 401)

============================================================
Results: 5 passed, 0 failed, 1 skipped
============================================================

================================================================================

