/**
 * tests/performance.test.ts
 *
 * Performance benchmarks for OpenClaw Evo using vitest + performance.now().
 *
 * Benchmarks:
 *   1. Score 1000 sessions          < 100 ms
 *   2. Pattern detection (1000 s.)  < 200 ms
 *   3. Generate 10 skills           < 500 ms
 *   4. MemoryStore save/load 1 MB   <  50 ms
 *   5. Full evolution cycle (50 s.) < 3000 ms
 *
 * Temp files are written to os.tmpdir() to avoid polluting the repo.
 * Mock data generators produce realistic SessionMetrics, FailurePatterns,
 * and GeneratedSkill objects with varied dimensions.
 */

import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { rm, mkdir } from 'node:fs/promises';
import { join } from 'node:path';
import { randomUUID } from 'node:crypto';
import * as os from 'node:os';
import { vi } from 'vitest';

import { scoreSessions } from '../src/evaluator/scorer.js';
import { detectPatterns } from '../src/evaluator/patternDetector.js';
import { generateBatch, generateFromFailure } from '../src/builder/skillGenerator.js';
import { MemoryStore } from '../src/memory/store.js';
import type { SessionMetrics, ToolCall, FailurePattern, GeneratedSkill } from '../src/types.js';

// ─────────────────────────────────────────────────────────────────────────────
// Mock data generators
// ─────────────────────────────────────────────────────────────────────────────

const TASK_TYPES = [
  'file_manipulation',
  'web_search',
  'api_call',
  'data_processing',
  'code_review',
  'debugging',
  'shell_command',
  'database_query',
  'text_editing',
  'image_processing',
];

const TOOL_NAMES = [
  'read', 'write', 'edit', 'delete', 'move', 'copy',
  'http', 'fetch', 'request', 'post', 'get',
  'search', 'google', 'look_up',
  'exec', 'run', 'bash', 'shell',
  'parse', 'encode', 'decode', 'validate',
  'inspect', 'trace',
];

const ERROR_STRINGS: Array<[string, string]> = [
  ['timeout', 'Request timed out after 30000ms — connection aborted'],
  ['rate_limit', 'Rate limit exceeded: 429 Too Many Requests'],
  ['not_found', 'ENOENT: no such file or directory at /tmp/data.json'],
  ['permission_error', 'Permission denied: access to /etc/shadow forbidden'],
  ['network_error', 'ECONNREFUSED: connection refused by target host'],
  ['validation_error', 'Validation failed: expected string, got undefined'],
  ['auth_error', 'Unauthorized: invalid or expired auth token'],
];

function randomItem<T>(arr: T[]): T {
  return arr[Math.floor(Math.random() * arr.length)];
}

function randomInt(min: number, max: number): number {
  return Math.floor(Math.random() * (max - min + 1)) + min;
}

// ── Session mock generator ───────────────────────────────────────────────────

/**
 * Generate a realistic tool call.
 * About 15% of calls fail with one of the ERROR_STRINGS.
 */
function makeMockToolCall(sessionStart: number, index: number): ToolCall {
  const toolName = randomItem(TOOL_NAMES);
  const isError = Math.random() < 0.15;
  const errorEntry = isError ? randomItem(ERROR_STRINGS) : null;
  const durationMs = randomInt(20, 800);
  const startTime = sessionStart + index * randomInt(10, 200);

  return {
    id: randomUUID(),
    name: toolName,
    input: {
      path: `/tmp/${randomUUID().slice(0, 8)}.txt`,
      ...(Math.random() > 0.5 ? { recursive: true } : {}),
    },
    output: isError ? undefined : { result: 'ok', items: randomInt(1, 50) },
    error: errorEntry ? errorEntry[1] : undefined,
    startTime,
    endTime: startTime + durationMs,
    success: !isError,
  };
}

/**
 * Generate a single realistic SessionMetrics object.
 */
function makeMockSession(overrides: Partial<SessionMetrics> = {}): SessionMetrics {
  const sessionId = `perf-session-${randomUUID().slice(0, 8)}`;
  const startTime = Date.now() - randomInt(5_000, 120_000);
  const toolCallCount = randomInt(2, 12);
  const toolCalls: ToolCall[] = Array.from({ length: toolCallCount }, (_, i) =>
    makeMockToolCall(startTime, i),
  );
  const errorCount = toolCalls.filter((tc) => !tc.success).length;
  const successCount = toolCallCount - errorCount;
  const avgLatencyMs =
    toolCalls.reduce((sum, tc) => sum + ((tc.endTime ?? tc.startTime) - tc.startTime), 0) /
    Math.max(toolCallCount, 1);

  return {
    sessionId,
    toolCalls,
    startTime,
    endTime: startTime + randomInt(500, 30_000),
    success: successCount > errorCount,
    errorCount,
    totalToolCalls: toolCallCount,
    avgLatencyMs,
    taskType: randomItem(TASK_TYPES),
    ...overrides,
  };
}

/**
 * Generate an array of N mock sessions.
 */
function generateMockSessions(count: number): SessionMetrics[] {
  return Array.from({ length: count }, () => makeMockSession());
}

// ── FailurePattern mock generator ────────────────────────────────────────────

/**
 * Generate a realistic failure pattern with populated exampleContexts.
 * Uses only error types that map to valid template names.
 */
function makeMockFailurePattern(overrides: Partial<FailurePattern> = {}): FailurePattern {
  const errorEntry = randomItem(ERROR_STRINGS);
  const id = `perf-fp-${randomUUID().slice(0, 8)}`;
  const frequency = randomInt(2, 20);
  const taskType = randomItem(TASK_TYPES);
  const toolName = randomItem(TOOL_NAMES);

  const exampleContexts = Array.from({ length: Math.min(frequency, 3) }, (_, i) => ({
    sessionId: `sess-${randomUUID().slice(0, 8)}`,
    taskDescription: `Task: ${taskType} — step ${i + 1}`,
    toolInput: {
      path: `/tmp/input-${i}.json`,
      options: { timeout: 30_000 },
    },
    errorOutput: errorEntry[1],
    timestamp: new Date(Date.now() - randomInt(0, 3_600_000)),
  }));

  return {
    id,
    toolName,
    errorType: errorEntry[0],
    errorMessage: errorEntry[1].slice(0, 80),
    frequency,
    severity: errorEntry[0] === 'timeout' ? 'high' : errorEntry[0] === 'permission_error' ? 'critical' : 'medium',
    exampleContexts,
    firstSeen: new Date(Date.now() - randomInt(86_400_000, 604_800_000)),
    lastSeen: new Date(),
    autoFixAvailable: false,
    suggestedFix:
      'Check the target resource is available and accessible before retrying.',
    ...overrides,
  };
}

// ─────────────────────────────────────────────────────────────────────────────
// Mock failureCorpus so the build phase finds patterns in the hub's tmp store
// ─────────────────────────────────────────────────────────────────────────────

function makeTestPattern(toolName: string, errorType: string, errorMsg: string): FailurePattern {
  return {
    id: `test-fp-${randomUUID().slice(0, 8)}`,
    toolName,
    errorType,
    errorMessage: errorMsg.slice(0, 80),
    frequency: 5,
    severity: errorType === 'timeout' ? 'high' : 'medium',
    exampleContexts: [
      {
        sessionId: `sess-${randomUUID().slice(0, 8)}`,
        taskDescription: `Task for ${toolName}`,
        toolInput: { path: '/tmp/test.json' },
        errorOutput: errorMsg,
        timestamp: new Date(),
      },
    ],
    firstSeen: new Date(Date.now() - 86_400_000),
    lastSeen: new Date(),
    autoFixAvailable: false,
    suggestedFix: 'Check the target resource availability before retrying.',
  };
}

// ── Mock the failureCorpus module before importing EvoHub ────────────────────
vi.mock('../src/memory/failureCorpus.js', () => {
  const testPatterns = [
    makeTestPattern('read', 'not_found', 'File not found'),
    makeTestPattern('http', 'timeout', 'Request timed out after 30000ms'),
  ];
  return {
    failureCorpus: {
      getPatterns: vi.fn(() => Promise.resolve(testPatterns)),
      recordFailure: vi.fn(() => Promise.resolve()),
      getCorpus: vi.fn(() => Promise.resolve({ failures: [], lastUpdated: new Date() })),
      clear: vi.fn(() => Promise.resolve()),
      markFixed: vi.fn(() => Promise.resolve()),
    },
  };
});

// ── Mock the experiment runner so it completes instantly (no real gateway needed) ─
vi.mock('../src/experiment/runner.js', () => ({
  experimentRunner: {
    createExperiment: vi.fn((skill: GeneratedSkill) => ({
      id: `exp-${skill.id}-test`,
      name: `A/B: ${skill.name}`,
      description: `Test experiment for ${skill.name}`,
      treatmentSkillId: skill.id,
      controlSkillId: 'baseline',
      taskSet: [],
      status: 'pending' as const,
      controlResults: [],
      treatmentResults: [],
      statisticalSignificance: 0,
      improvementPct: 0,
      startedAt: new Date(),
    })),
    run: vi.fn(async (exp: import('../src/types.js').Experiment) => {
      exp.status = 'completed';
      exp.completedAt = new Date();
      exp.controlResults = [
        { taskId: 't1', success: false, toolCalls: 3, durationMs: 5000, score: 0 },
        { taskId: 't2', success: true, toolCalls: 2, durationMs: 4000, score: 80 },
      ];
      exp.treatmentResults = [
        { taskId: 't1', success: true, toolCalls: 2, durationMs: 4000, score: 90 },
        { taskId: 't2', success: true, toolCalls: 2, durationMs: 3500, score: 95 },
      ];
      exp.statisticalSignificance = 0.97;
      exp.improvementPct = 85;
      return exp;
    }),
  },
}));

// Import EvoHub after vi.mock is set up
import { EvoHub } from '../src/hub.js';

// ─────────────────────────────────────────────────────────────────────────────
// Temp directory helpers
// ─────────────────────────────────────────────────────────────────────────────

function makeTempDir(): string {
  return join(os.tmpdir(), `openclaw-evo-perf-${randomUUID().slice(0, 8)}`);
}

afterEach(async () => {
  vi.restoreAllMocks();
});

// ─────────────────────────────────────────────────────────────────────────────
// BENCHMARK 1 — Score 1000 sessions < 100 ms
// ─────────────────────────────────────────────────────────────────────────────

describe('Performance benchmarks', () => {

  describe('scoreSessions — 1000 sessions', () => {
    it('scores 1000 sessions in under 100 ms', () => {
      const sessions = generateMockSessions(1000);

      // Warm up the JIT with a smaller batch first
      scoreSessions(sessions.slice(0, 10));

      const start = performance.now();
      const result = scoreSessions(sessions, 60_000, 3);
      const elapsed = performance.now() - start;

      expect(result.overall).toBeGreaterThan(0);
      expect(result.overall).toBeLessThanOrEqual(100);
      expect(elapsed).toBeLessThan(100);
    });
  });

  // ─────────────────────────────────────────────────────────────────────────
  // BENCHMARK 2 — Pattern detection in 1000 sessions < 200 ms
  // ─────────────────────────────────────────────────────────────────────────

  describe('detectPatterns — 1000 sessions', () => {
    it('detects patterns in 1000 sessions in under 200 ms', () => {
      const sessions = generateMockSessions(1000);

      const start = performance.now();
      const patterns = detectPatterns(sessions, 1);
      const elapsed = performance.now() - start;

      // Should surface real patterns from the ~15% error rate
      expect(patterns.length).toBeGreaterThan(0);
      for (const p of patterns) {
        expect(p.frequency).toBeGreaterThan(0);
        expect(['low', 'medium', 'high', 'critical']).toContain(p.severity);
        expect(p.toolName).toBeTruthy();
      }
      expect(elapsed).toBeLessThan(200);
    });
  });

  // ─────────────────────────────────────────────────────────────────────────
  // BENCHMARK 3 — Generate 10 skills < 500 ms
  // ─────────────────────────────────────────────────────────────────────────

  describe('generateBatch — 10 skills', () => {
    it('generates 10 skills from failure patterns in under 500 ms', () => {
      const patterns: FailurePattern[] = Array.from({ length: 10 }, (_, i) =>
        makeMockFailurePattern({ id: `perf-fp-${i}` }),
      );

      const start = performance.now();
      const results = generateBatch(patterns, { skipValidation: false });
      const elapsed = performance.now() - start;

      expect(results.length).toBeGreaterThan(0);
      for (const r of results) {
        expect(r.skill.id).toBeTruthy();
        expect(r.skill.name.length).toBeGreaterThan(0);
        expect(r.skill.implementation.length).toBeGreaterThan(100);
        expect(r.skill.triggerPhrases.length).toBeGreaterThan(0);
        expect(r.skill.confidence).toBeGreaterThanOrEqual(0);
        expect(r.skill.confidence).toBeLessThanOrEqual(1);
      }
      expect(elapsed).toBeLessThan(500);
    });

    it('generateFromFailure (single skill) also completes in under 200 ms', () => {
      const pattern = makeMockFailurePattern();

      const start = performance.now();
      const result = generateFromFailure(pattern, { skipValidation: false });
      const elapsed = performance.now() - start;

      expect(result.skill.id).toBeTruthy();
      expect(elapsed).toBeLessThan(200);
    });
  });

  // ─────────────────────────────────────────────────────────────────────────
  // BENCHMARK 4 — MemoryStore save/load 1 MB < 50 ms
  // ─────────────────────────────────────────────────────────────────────────

  describe('MemoryStore — 1 MB save/load', () => {
    it('saves and loads 1 MB of data in under 50 ms total', async () => {
      const tmpDir = makeTempDir();
      await mkdir(tmpDir, { recursive: true });

      try {
        const store = new MemoryStore(join(tmpDir, 'perf-mem-store'));
        await store.init();

        // Build a ~1 MB payload (1 048 576 bytes ≈ 1 MB)
        const chunk = 'x'.repeat(10_000); // 10 KB per chunk
        const largePayload = {
          history: Array.from({ length: 105 }, (_, i) => ({
            id: `record-${i}`,
            data: chunk,
            metadata: {
              timestamp: new Date().toISOString(),
              tags: ['performance', 'benchmark', 'openclaw', 'evo'],
              index: i,
            },
          })),
          summary: {
            totalRecords: 105,
            bytesPerRecord: 10_240,
            generatedAt: new Date().toISOString(),
          },
        };

        // Verify it's actually ~1 MB
        const jsonString = JSON.stringify(largePayload);
        const sizeBytes = Buffer.byteLength(jsonString, 'utf-8');
        expect(sizeBytes).toBeGreaterThan(900_000); // at least 900 KB

        // ── Save ──────────────────────────────────────────────────────────
        const saveStart = performance.now();
        await store.save('perf-1mb', largePayload);
        const saveElapsed = performance.now() - saveStart;

        expect(saveElapsed).toBeLessThan(30);

        // ── Load ───────────────────────────────────────────────────────────
        const loadStart = performance.now();
        const loaded = await store.load<typeof largePayload>('perf-1mb');
        const loadElapsed = performance.now() - loadStart;

        expect(loadElapsed).toBeLessThan(30);
        expect(loaded).not.toBeNull();
        expect(loaded!.summary.totalRecords).toBe(105);
        expect(loaded!.history.length).toBe(105);
        expect(loaded!.history[50].data).toBe(chunk);

        // Total round-trip
        expect(saveElapsed + loadElapsed).toBeLessThan(50);

        await store.delete('perf-1mb');
      } finally {
        await rm(tmpDir, { recursive: true, force: true });
      }
    });
  });

  // ─────────────────────────────────────────────────────────────────────────
  // BENCHMARK 5 — Full evolution cycle with 50 sessions < 3 seconds
  // ─────────────────────────────────────────────────────────────────────────

  describe('EvoHub.runOnce — 50 sessions', () => {
    it('runs a full evolution cycle with 50 sessions in under 3 seconds', async () => {
      const hubTmpDir = makeTempDir();
      await mkdir(hubTmpDir, { recursive: true });

      try {
        // ── Mock fetch so experiment runner completes without a live gateway ──
        let sessionIdx = 0;
        vi.stubGlobal(
          'fetch',
          vi.fn(async (url: string) => {
            const urlStr = String(url);
            if (urlStr.match(/\/api\/sessions$/) && !urlStr.includes('?')) {
              return {
                ok: true,
                json: () => Promise.resolve({ sessionId: `mock-perf-${sessionIdx++}` }),
              } as Response;
            }
            if (urlStr.match(/\/api\/sessions\/[^/]+$/)) {
              return {
                ok: true,
                json: () =>
                  Promise.resolve({
                    sessionId: urlStr.split('/').pop(),
                    status: 'completed',
                    success: true,
                    toolCalls: [],
                    startTime: Date.now() - 5000,
                    endTime: Date.now(),
                  }),
              } as Response;
            }
            if (urlStr.match(/\/api\/skills\/[^/]+$/)) {
              const skillId = urlStr.split('/').pop() ?? 'unknown';
              return {
                ok: true,
                json: () =>
                  Promise.resolve({
                    id: skillId,
                    name: 'Perf Test Skill',
                    description:
                      'Mock skill for performance testing — auto-generated by the benchmark harness',
                    triggerPhrases: ['perf test'],
                    implementation:
                      '// Mock implementation for performance benchmark testing.\n' +
                      `// Skill ID: ${skillId}\n` +
                      'export async function handler(input: string) {\n' +
                      '  return { success: true, result: "mock" };\n' +
                      '}',
                    examples: [{ input: 'test', expectedOutput: 'ok', explanation: 'mock' }],
                    confidence: 0.9,
                    status: 'proposed',
                    generatedAt: new Date().toISOString(),
                  }),
              } as unknown as Response;
            }
            return { ok: false, status: 404, text: () => Promise.resolve('Not Found'), json: () => Promise.resolve({}) } as unknown as Response;
          }),
        );

        // ── Generate 50 realistic sessions ────────────────────────────────
        const sessions = generateMockSessions(50);

        // ── Instantiate hub with temp memory dir ──────────────────────────
        const hub = new EvoHub({
          MEMORY_DIR: hubTmpDir,
          CYCLE_INTERVAL_MS: 3_600_000,
          OPENCLAW_GATEWAY_URL: 'http://localhost:18789',
          OPENCLAW_POLL_INTERVAL_MS: 10_000,
          FAILURE_THRESHOLD: 2,
          MAX_SKILLS_PER_CYCLE: 3,
          EXPERIMENT_SESSIONS: 5,
        });

        // Seed recentMetrics so evaluate phase has real data
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        (hub as any).recentMetrics = sessions;

        // ── Run the cycle and time it ─────────────────────────────────────
        const start = performance.now();
        await hub.runOnce();
        const elapsed = performance.now() - start;

        // ── Assertions ────────────────────────────────────────────────────
        expect(elapsed).toBeLessThan(3000);

        const cycles = hub.getCompletedCycles();
        const history = hub.getCycleHistory();
        const allCycles = cycles.length > 0 ? cycles : history;
        expect(allCycles.length).toBeGreaterThan(0);

        const lastCycle = allCycles[allCycles.length - 1];
        expect(lastCycle.status).toMatch(/^(completed|failed)$/);

        // The cycle phases should have run
        expect(lastCycle.phases.monitor.durationMs).toBeGreaterThanOrEqual(0);
        expect(lastCycle.phases.evaluate.durationMs).toBeGreaterThanOrEqual(0);
        expect(lastCycle.phases.build.durationMs).toBeGreaterThanOrEqual(0);
        expect(lastCycle.phases.experiment.durationMs).toBeGreaterThanOrEqual(0);
        expect(lastCycle.phases.integrate.durationMs).toBeGreaterThanOrEqual(0);
      } finally {
        await rm(hubTmpDir, { recursive: true, force: true });
      }
    });
  });
});
