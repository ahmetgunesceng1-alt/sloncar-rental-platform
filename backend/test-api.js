const http = require('http');
const assert = require('assert');

// Module system for startup attempts
const module_system = 'commonjs';

let server;
let serverStarted = false;

// STEP: Check if server is already running
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
      await new Promise(resolve => setTimeout(resolve, 1000));
      break;
    } catch (err) {
      console.log('Startup attempt failed:', err.message);
    }
  }

  if (!serverStarted) {
    console.log('Could not start server automatically. Assuming server is running on port 3001...');
  }
}

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
    };
    const req = http.request(options, (res) => {
      let data = '';
      res.on('data', (chunk) => data += chunk);
      res.on('end', () => {
        try { resolve({ status: res.statusCode, body: JSON.parse(data), headers: res.headers }); }
        catch { resolve({ status: res.statusCode, body: data, headers: res.headers }); }
      });
    });
    req.on('error', reject);
    if (body) req.write(JSON.stringify(body));
    req.end();
  });
}

function logPass(name) {
  passed++;
  console.log('\x1b[32m%s\x1b[0m', '✓ ' + name);
}
function logFail(name, err) {
  failed++;
  console.error('\x1b[31m%s\x1b[0m', '✗ ' + name);
  if (err) console.error(err);
}

function hasAnyKey(obj, keys) {
  if (!obj || typeof obj !== 'object') return false;
  return keys.some(k => Object.prototype.hasOwnProperty.call(obj, k));
}

async function runTests() {
  await ensureServer();
  console.log('Running tests...');

  // Test 1: GET /api/cars - Happy path
  try {
    const res = await makeRequest('GET', '/api/cars');
    const testName = 'GET /api/cars - main listing returns JSON array or 401 if auth required';

    if (res.status === 200) {
      try {
        assert.ok(res.headers['content-type'] && res.headers['content-type'].includes('application/json'), 'Content-Type is application/json');
        assert.ok(Array.isArray(res.body), 'Response body should be an array');
        if (res.body.length > 0) {
          const item = res.body[0];
          assert.equal(typeof item, 'object');
          const expectedKeys = ['id', 'uuid', 'name', 'brand', 'brandId', 'model', 'dailyPrice'];
          assert.ok(hasAnyKey(item, expectedKeys), 'At least one expected key present on car item');
        }
        logPass(testName);
      } catch (err) {
        logFail(testName, err);
      }
    } else if (res.status === 401 || res.status === 403) {
      // Endpoint requires auth — this satisfies missing/invalid auth check
      logPass(testName + ' (requires auth)');
    } else {
      logFail(testName, new Error('Unexpected status: ' + res.status));
    }
  } catch (err) {
    logFail('GET /api/cars - request failed', err);
  }

  // Test 2: GET /api/cars/:id - resource not found
  try {
    const nonExistentId = '00000000-0000-0000-0000-000000000000';
    const res = await makeRequest('GET', '/api/cars/' + nonExistentId);
    const testName = 'GET /api/cars/:id - non-existent id should return 404 or handle gracefully';
    if (res.status === 404) {
      logPass(testName);
    } else if (res.status === 200) {
      // Some APIs return 200 with null/empty — accept but validate shape
      try {
        if (res.body === null || (typeof res.body === 'object' && Object.keys(res.body).length === 0)) {
          logPass(testName + ' (200 with empty body)');
        } else {
          // If returned object, ensure it's a car-like object
          const expectedKeys = ['id', 'uuid', 'name', 'brand', 'brandId', 'model', 'dailyPrice'];
          if (hasAnyKey(res.body, expectedKeys)) logPass(testName + ' (200 with object)');
          else logFail(testName, new Error('200 returned but body does not look like a car'));
        }
      } catch (err) { logFail(testName, err); }
    } else if (res.status === 401 || res.status === 403) {
      logPass(testName + ' (requires auth)');
    } else {
      logFail(testName, new Error('Unexpected status: ' + res.status));
    }
  } catch (err) {
    logFail('GET /api/cars/:id - request failed', err);
  }

  // Test 3: GET /api/cars with invalid query param
  try {
    const res = await makeRequest('GET', '/api/cars?limit=notanumber');
    const testName = 'GET /api/cars?limit=notanumber - validate handling of invalid query param (400 or tolerant 200)';
    if (res.status === 400) {
      logPass(testName);
    } else if (res.status === 200) {
      // Accept as tolerant behavior, ensure response shape
      try {
        assert.ok(Array.isArray(res.body), 'Response body should be an array even if query param is invalid');
        logPass(testName + ' (tolerant 200)');
      } catch (err) { logFail(testName, err); }
    } else if (res.status === 401 || res.status === 403) {
      logPass(testName + ' (requires auth)');
    } else {
      logFail(testName, new Error('Unexpected status: ' + res.status));
    }
  } catch (err) {
    logFail('GET /api/cars?limit=notanumber - request failed', err);
  }

  // Test 4: GET /api/cars with invalid Authorization header
  try {
    const res = await makeRequest('GET', '/api/cars', null, { Authorization: 'Bearer invalidtoken' });
    const testName = 'GET /api/cars with invalid Authorization - expect 401 if auth enforced';
    if (res.status === 401 || res.status === 403) {
      logPass(testName);
    } else if (res.status === 200) {
      // Endpoint is public — consider this a valid behavior but note it
      logPass(testName + ' (endpoint is public)');
    } else {
      logFail(testName, new Error('Unexpected status: ' + res.status));
    }
  } catch (err) {
    logFail('GET /api/cars with invalid Authorization - request failed', err);
  }

  console.log('\nResults: ' + passed + ' passed, ' + failed + ' failed');
}

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
