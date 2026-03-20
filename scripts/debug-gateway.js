#!/usr/bin/env node
/**
 * Debug script to test OpenClaw gateway connectivity and session data.
 * Run: node scripts/debug-gateway.js
 */
const http = require('http');

function invoke(tool, args = {}) {
  return new Promise((resolve, reject) => {
    const data = JSON.stringify({ tool, args });
    const req = http.request({
      hostname: 'localhost',
      port: 18789,
      path: '/tools/invoke',
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    }, (res) => {
      let body = '';
      res.on('data', d => body += d);
      res.on('end', () => {
        try { resolve(JSON.parse(body)); }
        catch (e) { reject(new Error(`Invalid JSON: ${body.slice(0, 200)}`)); }
      });
    });
    req.on('error', reject);
    req.write(data);
    req.end();
  });
}

async function main() {
  console.log('=== OpenClaw Gateway Debug ===\n');

  // Test 1: Gateway reachable?
  try {
    const r = await invoke('gateway_status', {});
    console.log('✅ Gateway status:', JSON.stringify(r.result ?? r, null, 2));
  } catch (e) {
    console.log('❌ Gateway unreachable:', e.message);
    process.exit(1);
  }

  // Test 2: sessions_list
  console.log('\n--- sessions_list ---');
  try {
    const r = await invoke('sessions_list', { limit: 5, messageLimit: 0 });
    console.log('Raw response keys:', Object.keys(r));
    console.log('Result:', JSON.stringify(r.result ?? r, null, 2).slice(0, 500));
    if (r.result?.sessions) {
      console.log(`Found ${r.result.sessions.length} sessions`);
      r.result.sessions.forEach(s => console.log(' -', s.key, '|', s.kind, '|', s.displayName || ''));
    } else {
      console.log('No sessions found (or result.sessions missing)');
    }
  } catch (e) {
    console.log('❌ sessions_list error:', e.message);
  }

  // Test 3: sessions_list with different args
  console.log('\n--- sessions_list (no args) ---');
  try {
    const r = await invoke('sessions_list', {});
    console.log('Result:', JSON.stringify(r.result ?? r, null, 2).slice(0, 500));
  } catch (e) {
    console.log('❌ error:', e.message);
  }
}

main();
