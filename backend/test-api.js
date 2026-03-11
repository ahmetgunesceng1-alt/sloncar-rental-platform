const http = require('http');
const assert = require('assert');

// Module system for startup attempts
const module_system = 'commonjs';

let server;
let serverStarted = false;

// STEP 0: Check if server is already running on port 3001
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

// Try starting the server from common entry points if it's not running
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
      await new Promise((r) => setTimeout(r, 1000));
      break;
    } catch (err) {
      console.log('Startup attempt failed:', err && err.message ? err.message : err);
    }
  }

  if (!serverStarted) {
    console.log('Could not start server automatically. Assuming server is running on port 3001...');
  }
}

// Utilities
const TIMEOUT_MS = 20000;
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
      timeout: 5000,
    };
    const req = http.request(options, (res) => {
      let data = '';
      res.on('data', (chunk) => data += chunk);
      res.on('end', () => {
        let parsed;
        try { parsed = JSON.parse(data); } catch (e) { parsed = data; }
        resolve({ status: res.statusCode, body: parsed, headers: res.headers });
      });
    });
    req.on('error', (err) => reject(err));
    if (body) req.write(JSON.stringify(body));
    req.end();
  });
}

// Tests
async function runTests() {
  await ensureServer();
  console.log('Running tests...');

  // Test 1: GET /api/cars - happy path or auth required
  try {
    const res = await makeRequest('GET', '/api/cars');
    if (res.status === 200) {
      try {
        assert(Array.isArray(res.body), 'Expected body to be an array for GET /api/cars');
        assert(res.headers['content-type'] && res.headers['content-type'].includes('application/json'), 'Expected Content-Type application/json');
        // If array has items, ensure basic shape
        if (res.body.length > 0) {
          const item = res.body[0];
          assert(typeof item === 'object' && item !== null, 'Expected array items to be objects');
          // require at least one key on the object
          assert(Object.keys(item).length > 0, 'Expected item to have at least one key');
        }
        console.log('✓ GET /api/cars returned 200 and JSON array');
        passed++;
      } catch (err) {
        console.log('✗ GET /api/cars - response shape assertion failed:', err.message);
        failed++;
      }
    } else if (res.status === 401 || res.status === 403) {
      console.log('✓ GET /api/cars requires auth (status ' + res.status + ')');
      passed++;
    } else {
      console.log('✗ GET /api/cars unexpected status:', res.status);
      failed++;
    }
  } catch (err) {
    console.log('✗ GET /api/cars request failed:', err.message);
    failed++;
  }

  // Test 2: GET /api/cars/:id with non-existent id -> expect 404 or 400
  try {
    const nonExistentId = '000000000000000000000000';
    const res = await makeRequest('GET', '/api/cars/' + nonExistentId);
    if (res.status === 404 || res.status === 400) {
      console.log('✓ GET /api/cars/:id non-existent returned', res.status);
      passed++;
    } else if (res.status === 200) {
      // Some APIs may return 200 with a body indicating not found; try to detect
      const body = res.body;
      const asString = (typeof body === 'string') ? body : JSON.stringify(body);
      if (asString && asString.toLowerCase().includes('not found')) {
        console.log('✓ GET /api/cars/:id returned 200 with not found message');
        passed++;
      } else {
        console.log('✗ GET /api/cars/:id expected 404/400 but got 200');
        failed++;
      }
    } else if (res.status === 401 || res.status === 403) {
      console.log('✓ GET /api/cars/:id requires auth (status ' + res.status + ')');
      passed++;
    } else {
      console.log('✗ GET /api/cars/:id unexpected status:', res.status);
      failed++;
    }
  } catch (err) {
    console.log('✗ GET /api/cars/:id request failed:', err.message);
    failed++;
  }

  console.log('\nResults: ' + passed + ' passed, ' + failed + ' failed');
}

// RUN with timeout and cleanup
const timeout = setTimeout(() => {
  console.error('✗ Tests timed out');
  if (server && server.close) server.close();
  process.exit(1);
}, TIMEOUT_MS);

runTests()
  .then(() => {
    clearTimeout(timeout);
    if (server && server.close) server.close(() => process.exit(failed > 0 ? 1 : 0));
    else process.exit(failed > 0 ? 1 : 0);
  })
  .catch((err) => {
    clearTimeout(timeout);
    console.error('Test error:', err);
    if (server && server.close) server.close();
    process.exit(1);
  });
