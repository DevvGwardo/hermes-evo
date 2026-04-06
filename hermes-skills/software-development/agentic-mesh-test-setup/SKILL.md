---
name: agentic-mesh-test-setup
description: Test setup for agentic-mesh repo — vitest config, test file plan, and known bugs from refactor
---

# agentic-mesh test setup

Repo: `~/agentic-mesh/` (github.com/DevvGwardo/agentic-mesh)
TypeScript, no test suite existed — this skill documents the setup that was applied.

## Setup
```bash
cd ~/agentic-mesh
npm install --save-dev vitest @vitest/ui
```

package.json scripts added:
```json
"test": "vitest",
"test:run": "vitest run"
```

vitest.config.ts:
```typescript
import { defineConfig } from 'vitest/config';
export default defineConfig({
  test: {
    environment: 'node',
    globals: true,
    include: ['src/**/*.test.ts'],
  },
});
```

## Test files to write
1. `src/storage.test.ts` — temp mesh dir, writeContext/readContext/queryContexts/deleteContext/purgeStale, cache warm/dirty lifecycle
2. `src/hub.test.ts` — Hub, two mock WS clients, hub:join, mesh:op:publish, mesh:op:delete, verify broadcast
3. `src/mesh.test.ts` — DIRECT mode end-to-end: create Mesh, publish, query, verify stats

## Run
```bash
npm run test:run
```

## Bugs found during refactor (all fixed)
- `mesh.ts` summarizeActivity(): template literal `${hours}h` inside single-quoted string
- `hub.ts` handleMeshOp delete: no broadcast to peers
- `hub.ts` handleMeshOp delegate: didn't check readyState before sending WS
- `hub.ts` start(): two setInterval calls, second overwrote first, first never cleared on stop()
- `storage.ts` purgeStale(): read from disk instead of cache, stale entries never cleaned
- Shared `src/tool.ts` extracted from hermes/ and openclaw/ adapters (~180 lines deduped)
