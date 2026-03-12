const http = require('http');
const assert = require('assert');

// Module system used by this test file
const module_system = 'commonjs';

let server;
let serverStarted = false;

// STEP 1: CHECK IF SERVER IS ALREADY RUNNING
async function checkServerRunning() {
  return new Promise((resolve) => {
    const req = http.request({ hostname: 'localhost', port: 3001, path: '/', method: 'GET', timeout: 1000 }, (res) => {
      resolve(true);
    });
    req.on('error', () => resolve(false));
    req.on('timeout', () => { req.destroy(); resolve(false); });
    req.end();
  });
}

// Try to start server only if not already running
async function ensureServer() {
  const isRunning = await checkServerRunning();
  if (isRunning) {
    console.log('Server is already running on port 3001');
    serverStarted = true;
    return;
  }

  process.env.NODE_ENV = process.env.NODE_ENV || 'test';
  process.env.PORT = process.env.PORT || '3001';

  const startupAttempts = [
    () => { const app = require('./src/app'); return app.listen(3001); },
    () => { const app = require('./app'); return app.listen(3001); },
    () => { const app = require('./src/index'); return app.listen(3001); },
    () => { const app = require('./index'); return app.listen(3001); },
    () => { const app = require('./src/server'); return app.listen(3001); },
  ];

  for (const attempt of startupAttempts) {
    try {
      server = await attempt();
      serverStarted = true;
      console.log('Test server started on port 3001');
      // Give server a moment to initialize
      await new Promise(resolve => setTimeout(resolve, 1000));
      break;
    } catch (err) {
      console.log('Startup attempt failed:', err && err.message ? err.message : err);
    }
  }

  if (!serverStarted) {
    console.log('Could not start server automatically. Assuming server is running on port 3001...');
  }
}

// STEP 2: DEFINE TEST UTILITIES
const TIMEOUT_MS = 10000;
let passed = 0;
let failed = 0;

function makeRequest(method, path, body, headers = {}) {
  return new Promise((resolve, reject) => {
    const url = new URL(path, 'http://localhost:3001');
    const options = {
      hostname: url.hostname,
      port: url.port,
      path: url.pathname + url.search,
      method,
      headers: { 'Content-Type': 'application/json', ...headers },
    };
    const req = http.request(options, (res) => {
      let data = '';
      res.on('data', (chunk) => data += chunk);
      res.on('end', () => {
        const ct = res.headers['content-type'] || '';
        // Try parse JSON, otherwise return raw text
        try { resolve({ status: res.statusCode, body: data ? JSON.parse(data) : null, headers: res.headers, contentType: ct }); }
        catch { resolve({ status: res.statusCode, body: data, headers: res.headers, contentType: ct }); }
      });
    });
    req.on('error', reject);
    if (body) {
      try { req.write(JSON.stringify(body)); }
      catch (e) { /* ignore */ }
    }
    req.end();
  });
}

// Helper to assert response JSON shape (very permissive)
function looksLikeCar(obj) {
  if (!obj || typeof obj !== 'object') return false;
  const keys = Object.keys(obj);
  const common = ['id', 'name', 'model', 'brand', 'plate', 'title'];
  return keys.some(k => common.includes(k));
}

// STEP 3: DEFINE TESTS
async function runTests() {
  await ensureServer();
  console.log('Running tests...');

  // Test 1: GET /api/cars - happy path or auth protected
  try {
    const res = await makeRequest('GET', '/api/cars');
    console.log('Test GET /api/cars ->', res.status);

    // Accept either public 200 or 401/403 if protected
    if (res.status === 200) {
      // Content-Type should indicate JSON
      assert.ok(res.contentType && res.contentType.includes('application/json'), 'Expected application/json content-type');
      // Body should be array or object with cars
      if (Array.isArray(res.body)) {
        // If array, ensure each item looks like a car (at least first one)
        if (res.body.length > 0) {
          assert.ok(looksLikeCar(res.body[0]), 'First item does not look like a car object');
        }
      } else if (res.body && typeof res.body === 'object') {
        // If object, check common properties somewhere
        // Accept payloads like { data: [...] } or single object
        if (Array.isArray(res.body.data)) {
          if (res.body.data.length > 0) {
            assert.ok(looksLikeCar(res.body.data[0]), 'First item in data does not look like a car object');
          }
        } else {
          // Single object
          assert.ok(looksLikeCar(res.body), 'Response object does not look like a car');
        }
      } else {
        throw new Error('Unexpected body type for GET /api/cars');
      }
      console.log('✓ GET /api/cars returned 200 and valid JSON shape');
      passed++;
    } else if (res.status === 401 || res.status === 403) {
      // Endpoint is protected — that's acceptable for this test suite
      console.log('✓ GET /api/cars returned auth failure as expected:', res.status);
      passed++;
    } else {
      throw new Error('Unexpected status for GET /api/cars: ' + res.status);
    }
  } catch (err) {
    failed++;
    console.error('✗ GET /api/cars failed:', err.message || err);
  }

  // Test 2: GET /api/cars/:id -> resource not found
  try {
    const res = await makeRequest('GET', '/api/cars/99999999');
    console.log('Test GET /api/cars/99999999 ->', res.status);
    if (res.status === 404) {
      // If JSON, check message
      if (res.body && typeof res.body === 'object') {
        const msg = res.body.message || res.body.error || JSON.stringify(res.body);
        assert.ok(typeof msg === 'string', 'Expected error message in 404 response');
      }
      console.log('✓ GET /api/cars/:id returned 404 for missing resource');
      passed++;
    } else if (res.status === 401 || res.status === 403) {
      console.log('✓ GET /api/cars/:id returned auth failure as expected:', res.status);
      passed++;
    } else if (res.status === 200) {
      // It's possible the stub id exists; if so, ensure shape
      if (res.contentType && res.contentType.includes('application/json')) {
        if (Array.isArray(res.body)) {
          if (res.body.length === 0) {
            // empty array treated as not found in some APIs
            console.log('✓ GET /api/cars/:id returned 200 with empty array (treated as not found)');
            passed++;
          } else {
            assert.ok(looksLikeCar(res.body[0]) || looksLikeCar(res.body), 'Returned resource does not look like a car');
            console.log('✓ GET /api/cars/:id returned 200 and resource looks like a car');
            passed++;
          }
        } else if (typeof res.body === 'object') {
          assert.ok(looksLikeCar(res.body), 'Returned resource does not look like a car');
          console.log('✓ GET /api/cars/:id returned 200 and resource looks like a car');
          passed++;
        } else {
          throw new Error('Unexpected body for GET /api/cars/:id');
        }
      } else {
        throw new Error('Expected JSON for GET /api/cars/:id');
      }
    } else {
      throw new Error('Unexpected status for GET /api/cars/:id: ' + res.status);
    }
  } catch (err) {
    failed++;
    console.error('✗ GET /api/cars/:id failed:', err.message || err);
  }

  // Test 3: POST /api/cars with invalid body -> expect 400 (or auth/method errors)
  try {
    const res = await makeRequest('POST', '/api/cars', {});
    console.log('Test POST /api/cars (empty body) ->', res.status);
    if (res.status === 400) {
      // Validation error expected
      if (res.body && typeof res.body === 'object') {
        const hasMsg = res.body.message || res.body.error || res.body.errors;
        assert.ok(hasMsg, 'Expected validation message on 400 response');
      }
      console.log('✓ POST /api/cars with invalid body returned 400 as expected');
      passed++;
    } else if (res.status === 401 || res.status === 403) {
      console.log('✓ POST /api/cars returned auth failure as expected:', res.status);
      passed++;
    } else if (res.status === 405) {
      console.log('✓ POST /api/cars returned 405 Method Not Allowed (endpoint may be read-only)');
      passed++;
    } else {
      throw new Error('Unexpected status for POST /api/cars (expected 400/401/403/405): ' + res.status);
    }
  } catch (err) {
    failed++;
    console.error('✗ POST /api/cars failed:', err.message || err);
  }

  console.log('\nResults: ' + passed + ' passed, ' + failed + ' failed');
}

// STEP 4: RUN TESTS WITH CLEANUP
const timeout = setTimeout(() => {
  console.error('✗ Tests timed out');
  if (server) server.close();
  process.exit(1);
}, TIMEOUT_MS);

runTests()
  .then(() => {
    clearTimeout(timeout);
    if (server) server.close(() => process.exit(failed > 0 ? 1 : 0));
    else process.exit(failed > 0 ? 1 : 0);
  })
  .catch((err) => {
    clearTimeout(timeout);
    console.error('Test error:', err);
    if (server) server.close();
    process.exit(1);
  });
