# Test Execution Results

Generated: 2026-04-13T12:57:50.579Z

================================================================================

Command: SERVER_PORT=3000 python test-api.py
Exit Code: 0

Output:
    Request: POST http://localhost:3000/api/auth/register
    Status: 201
    Body: {"success": true, "data": {"user": {"id": "8f36f970-47c3-4b83-94e6-d0b68c05434a", "email": "testbot@example.com", "name": "Test Bot", "role": "USER"}, "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VySWQiOiI4ZjM2Zjk3MC00N2MzLTRiODMtOTRlNi1kMGI2OGMwNTQzNGEiLCJlbWFpbCI6InRlc3Rib3RAZXhhbXBsZS5jb20iLCJyb2xlIjoiVVNFUiIsImlhdCI6MTc3NjA4NTA3MCwiZXhwIjoxNzc2Njg5ODcwfQ.SZA3TQgLvqJ3nxwt0-4mngbeKZwx-OupP1G1ASUKTEc"}}
    Request: POST http://localhost:3000/api/auth/register
    Status: 201
    Body: {"success": true, "data": {"user": {"id": "4738ff9e-ce38-4188-b117-8a13cee50e8f", "email": "testbot2@example.com", "name": "Test Bot 2", "role": "USER"}, "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VySWQiOiI0NzM4ZmY5ZS1jZTM4LTQxODgtYjExNy04YTEzY2VlNTBlOGYiLCJlbWFpbCI6InRlc3Rib3QyQGV4YW1wbGUuY29tIiwicm9sZSI6IlVTRVIiLCJpYXQiOjE3NzYwODUwNzAsImV4cCI6MTc3NjY4OTg3MH0.n3ey_MXiC84zUDDOIMMxwTWlyMpFkg3X-rLKX4yG2IE"}}
    Request: POST http://localhost:3000/api/auth/login
    Status: 200
    Body: {"success": true, "data": {"user": {"id": "8f36f970-47c3-4b83-94e6-d0b68c05434a", "email": "testbot@example.com", "name": "Test Bot", "role": "USER"}, "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VySWQiOiI4ZjM2Zjk3MC00N2MzLTRiODMtOTRlNi1kMGI2OGMwNTQzNGEiLCJlbWFpbCI6InRlc3Rib3RAZXhhbXBsZS5jb20iLCJyb2xlIjoiVVNFUiIsImlhdCI6MTc3NjA4NTA3MCwiZXhwIjoxNzc2Njg5ODcwfQ.SZA3TQgLvqJ3nxwt0-4mngbeKZwx-OupP1G1ASUKTEc"}}
    Request: GET http://localhost:3000/api/auth/profile
    Status: 200
    Body: {"success": true, "data": {"user": {"id": "8f36f970-47c3-4b83-94e6-d0b68c05434a", "email": "testbot@example.com", "name": "Test Bot", "role": "USER", "whatsappEnabled": true}}}
    Request: PATCH http://localhost:3000/api/auth/profile
    Status: 200
    Body: {"success": true, "data": {"user": {"id": "8f36f970-47c3-4b83-94e6-d0b68c05434a", "email": "testbot@example.com", "name": "Test Bot", "role": "USER", "whatsappEnabled": true}}}
    Request: POST http://localhost:3000/api/auth/login
    Status: 401
    Body: {"success": false, "message": "Invalid email or password", "error": {"code": "UNAUTHORIZED"}}
    Request: GET http://localhost:3000/api/auth/profile
    Status: 401
    Body: {"success": false, "message": "Invalid or expired token", "error": {"code": "UNAUTHORIZED"}}
Passed: 6, Failed: 0, Skipped: 0

================================================================================

