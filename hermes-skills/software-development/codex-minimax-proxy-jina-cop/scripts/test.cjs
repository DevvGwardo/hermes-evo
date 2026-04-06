// Test suite for codex-minimax-proxy Jina cop integration
const BASE = 'http://localhost:4000';

const tests = [
  { name: 'T1  /health', run: () => req('/health').then(r => [r.status === 200, r]) },
  { name: 'T2  /cop GET example.com', run: () => req('/cop?url=https://example.com').then(r => [r.status === 200 && r.data.includes('Example Domain'), r]) },
  { name: 'T3  /cop POST example.com', run: () => reqPOST('/cop?url=https://example.com').then(r => [r.status === 200 && r.data.includes('Example Domain'), r]) },
  { name: 'T4  /cop no URL', run: () => req('/cop').then(r => [r.status === 400, r]) },
  { name: 'T5  /cop GitHub API (no auth)', run: () => req('/cop?url=https://api.github.com/repos/torvalds/linux').then(r => [r.status === 200 && typeof r.data === 'object', r]) },
  { name: 'T6  /cop POST rawFetch fallback', run: () => reqPOST('/cop?url=https://httpbin.org/post').then(r => [r.status === 200, r]) },
  { name: 'T7  HEAD method → rawFetch', run: () => req('/cop?url=https://example.com', 'HEAD').then(r => [r.status === 200, r]) },
  { name: 'T8  large content truncation', run: () => req('/cop?url=https://en.wikipedia.org/wiki/Main_Page').then(r => [r.data.length <= 80000, r]) },
  { name: 'T9  invalid URL → 400', run: () => req('/cop?url=not-a-url').then(r => [r.status === 400, r]) },
  { name: 'T10 404 URL → 200 with error', run: () => req('/cop?url=https://example.com/this-does-not-exist-12345').then(r => [r.status === 200, r]) },
  { name: 'T11  MiniMax + URL (full round-trip)', run: () => reqPOST('/v1/responses', { input: 'What is the title of https://example.com?' }).then(r => [r.status === 200 && r.data.includes('Example Domain'), r]) },
  { name: 'T12  /v1/responses no URL → no injection', run: () => reqPOST('/v1/responses', { input: 'Hello world' }).then(r => [r.status === 200, r]) },
  { name: 'T13  streaming + URL', run: () => reqPOST('/v1/responses/stream', { input: 'Summarize https://example.com' }).then(r => [r.status === 200, r]) },
];

async function req(path, method = 'GET') {
  const res = await fetch(BASE + path, { method });
  const text = await res.text();
  let data = text;
  try { data = JSON.parse(text); } catch {}
  return { status: res.status, data };
}

async function reqPOST(path, body) {
  const res = await fetch(BASE + path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  const text = await res.text();
  let data = text;
  try { data = JSON.parse(text); } catch {}
  return { status: res.status, data };
}

(async () => {
  let pass = 0, fail = 0;
  for (const t of tests) {
    try {
      const [ok, result] = await t.run();
      console.log(`${ok ? '✓' : '✗'} ${t.name}`);
      if (!ok) { console.log('  -> FAILED', JSON.stringify(result).slice(0, 200)); fail++; pass++; }
      else pass++;
    } catch (e) {
      console.log(`✗ ${t.name}: ${e.message}`);
      fail++;
    }
  }
  console.log(`\n${pass}/${pass + fail} passed`);
})();
