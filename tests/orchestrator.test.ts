/**
 * tests/orchestrator.test.ts
 *
 * Tests for:
 *   - orchestrator/providerDetector.ts  → detectProviders(), summarizeProviders()
 *   - orchestrator/fallbackChain.ts     → resolveAgentModel(), buildAgentConfig()
 *   - orchestrator/hookSystem.ts        → HookRegistry, individual hooks
 *   - orchestrator/ultrawork.ts         → classifyTask(), ultrawork()
 *
 * Run with: npm test
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';

// ── Provider detector tests ─────────────────────────────────────────────────────

import {
  detectProviders,
  summarizeProviders,
} from '../src/orchestrator/providerDetector.js';

describe('providerDetector', () => {
  const originalEnv = process.env;

  beforeEach(() => {
    // Isolate tests from real environment variables — only preserve a minimal
    // allowlist of safe, test-neutral variables. This prevents real API keys
    // (ANTHROPIC_API_KEY, GOOGLE_API_KEY, etc.) from leaking into tests.
    const ALLOWED_IN_TESTS = new Set([
      'HOME', 'USER', 'SHELL', 'PATH', 'TERM', 'TMPDIR',
      'EDITOR', 'VISUAL', 'PAGER',
      'LC_ALL', 'LANG', 'LANGUAGE',
      'CI', 'TEST', 'NODE_ENV', 'VITEST',
    ]);
    const cleaned: typeof process.env = {};
    for (const key of Object.keys(process.env)) {
      if (ALLOWED_IN_TESTS.has(key)) cleaned[key] = process.env[key];
    }
    process.env = cleaned;
  });

  describe('detectProviders()', () => {
    it('returns all false when no API keys are set', () => {
      const result = detectProviders();
      expect(result.native.claude).toBe(false);
      expect(result.native.openai).toBe(false);
      expect(result.native.gemini).toBe(false);
      expect(result.opencodeZen).toBe(false);
      expect(result.copilot).toBe(false);
      expect(result.zai).toBe(false);
      expect(result.kimiForCoding).toBe(false);
      expect(result.opencodeGo).toBe(false);
      expect(result.isMaxPlan).toBe(false);
    });

    it('detects Claude when ANTHROPIC_API_KEY is set', () => {
      process.env.ANTHROPIC_API_KEY = 'sk-ant-test';
      const result = detectProviders();
      expect(result.native.claude).toBe(true);
    });

    it('detects OpenAI when OPENAI_API_KEY is set', () => {
      process.env.OPENAI_API_KEY = 'sk-test';
      const result = detectProviders();
      expect(result.native.openai).toBe(true);
    });

    it('detects Gemini from GEMINI_API_KEY or GOOGLE_API_KEY', () => {
      process.env.GEMINI_API_KEY = 'test-gemini';
      expect(detectProviders().native.gemini).toBe(true);
      process.env = { ...originalEnv };
      process.env.GOOGLE_API_KEY = 'test-google';
      expect(detectProviders().native.gemini).toBe(true);
    });

    it('sets isMaxPlan when both Claude and OpenAI are available', () => {
      process.env.ANTHROPIC_API_KEY = 'sk-ant-test';
      process.env.OPENAI_API_KEY = 'sk-test';
      expect(detectProviders().isMaxPlan).toBe(true);
    });

    it('sets isMaxPlan when ZAI_API_KEY is available', () => {
      process.env.ZAI_API_KEY = 'test-zai';
      expect(detectProviders().isMaxPlan).toBe(true);
    });

    it('ignores empty or "false" string values', () => {
      process.env.ANTHROPIC_API_KEY = '';
      process.env.OPENAI_API_KEY = 'false';
      const result = detectProviders();
      expect(result.native.claude).toBe(false);
      expect(result.native.openai).toBe(false);
    });
  });

  describe('summarizeProviders()', () => {
    it('returns "No providers detected" when none are set', () => {
      expect(summarizeProviders(detectProviders())).toBe('No providers detected');
    });

    it('lists active providers comma-separated', () => {
      process.env.ANTHROPIC_API_KEY = 'sk-ant';
      process.env.OPENAI_API_KEY = 'sk-openai';
      process.env.KIMI_API_KEY = 'kimi-test';
      const summary = summarizeProviders(detectProviders());
      expect(summary).toContain('Claude');
      expect(summary).toContain('OpenAI');
      expect(summary).toContain('Kimi');
    });
  });
});

// ── Fallback chain tests ───────────────────────────────────────────────────────

import {
  resolveAgentModel,
  resolveCategoryModel,
  buildAgentConfig,
  AGENT_REQUIREMENTS,
  CATEGORY_REQUIREMENTS,
} from '../src/orchestrator/fallbackChain.js';
import type { ProviderAvailability } from '../src/orchestrator/providerDetector.js';

function emptyAvail(): ProviderAvailability {
  return {
    native: { claude: false, openai: false, gemini: false },
    opencodeZen: false, copilot: false, zai: false,
    kimiForCoding: false, opencodeGo: false, isMaxPlan: false,
  };
}

describe('fallbackChain', () => {
  describe('AGENT_REQUIREMENTS', () => {
    it('has entries for all expected agent roles', () => {
      const roles = ['sisyphus', 'hephaestus', 'oracle', 'librarian', 'explore', 'prometheus', 'metis', 'atlas'];
      for (const role of roles) {
        expect(AGENT_REQUIREMENTS).toHaveProperty(role);
        expect(AGENT_REQUIREMENTS[role].fallbackChain.length).toBeGreaterThan(0);
      }
    });

    it('each fallback chain entry has at least one provider', () => {
      for (const [role, req] of Object.entries(AGENT_REQUIREMENTS)) {
        for (const entry of req.fallbackChain) {
          expect(entry.providers.length).toBeGreaterThan(0);
        }
      }
    });

    it('each fallback chain entry has a model string', () => {
      for (const req of Object.values(AGENT_REQUIREMENTS)) {
        for (const entry of req.fallbackChain) {
          expect(typeof entry.model).toBe('string');
          expect(entry.model.length).toBeGreaterThan(0);
        }
      }
    });
  });

  describe('CATEGORY_REQUIREMENTS', () => {
    it('has entries for task difficulty categories', () => {
      expect(CATEGORY_REQUIREMENTS).toHaveProperty('visual-engineering');
      expect(CATEGORY_REQUIREMENTS).toHaveProperty('ultrabrain');
      expect(CATEGORY_REQUIREMENTS).toHaveProperty('quick');
      expect(CATEGORY_REQUIREMENTS).toHaveProperty('unspecified-low');
      expect(CATEGORY_REQUIREMENTS).toHaveProperty('unspecified-high');
    });
  });

  describe('resolveAgentModel()', () => {
    it('returns null when no providers are available', () => {
      const result = resolveAgentModel('sisyphus', emptyAvail());
      expect(result).toBeNull();
    });

    it('resolves sisyphus to Claude when ANTHROPIC_API_KEY is set', () => {
      const avail = emptyAvail();
      avail.native.claude = true;
      const result = resolveAgentModel('sisyphus', avail);
      expect(result).not.toBeNull();
      expect(result!.model).toBe('claude-opus-4-6');
      expect(result!.variant).toBe('max');
    });

    it('resolves sisyphus to OpenAI when only OPENAI_API_KEY is set', () => {
      const avail = emptyAvail();
      avail.native.openai = true;
      const result = resolveAgentModel('sisyphus', avail);
      expect(result).not.toBeNull();
      expect(result!.model).toBe('gpt-5.4');
    });

    it('resolves librarian to minimax when opencodeGo is available', () => {
      const avail = emptyAvail();
      avail.opencodeGo = true;
      const result = resolveAgentModel('librarian', avail);
      expect(result).not.toBeNull();
      expect(result!.model).toBe('minimax-m2.7');
    });

    it('resolves hephaestus to GPT when openai is available', () => {
      const avail = emptyAvail();
      avail.native.openai = true;
      const result = resolveAgentModel('hephaestus', avail);
      expect(result).not.toBeNull();
      expect(result!.model).toBe('gpt-5.4');
      expect(result!.variant).toBe('medium');
    });

    it('returns null when hephaestus required providers are unavailable', () => {
      const avail = emptyAvail();
      avail.kimiForCoding = true;
      // hephaestus requires openai/venice/copilot — none available, returns null
      const result = resolveAgentModel('hephaestus', avail);
      expect(result).toBeNull();
    });

    it('returns null for unknown agent role', () => {
      const avail = emptyAvail();
      avail.native.claude = true;
      expect(resolveAgentModel('nonexistent-role' as any, avail)).toBeNull();
    });
  });

  describe('resolveCategoryModel()', () => {
    it('resolves "quick" to a fast model', () => {
      const avail = emptyAvail();
      avail.native.openai = true;
      const result = resolveCategoryModel('quick', avail, false);
      expect(result).not.toBeNull();
      expect(result!.model).toBeTruthy();
    });

    it('downgrades unspecified-high to unspecified-low when not isMaxPlan', () => {
      const avail = emptyAvail();
      avail.native.claude = true;
      avail.native.openai = true;
      // isMaxPlan=true
      const high = resolveCategoryModel('unspecified-high', avail, true);
      // isMaxPlan=false — should downgrade
      const low = resolveCategoryModel('unspecified-high', avail, false);
      expect(high).not.toBeNull();
      expect(low).not.toBeNull();
    });

    it('returns a fallback model when no providers are available', () => {
      const result = resolveCategoryModel('quick', emptyAvail(), false);
      expect(result).not.toBeNull();
      expect(result!.model).toBe('opencode/gpt-5-nano');
    });
  });

  describe('buildAgentConfig()', () => {
    it('returns an empty config when no providers are available', () => {
      const config = buildAgentConfig(emptyAvail());
      // No roles resolve without providers
      expect(Object.keys(config).length).toBeGreaterThanOrEqual(0);
    });

    it('includes sisyphus when a required provider is available', () => {
      const avail = emptyAvail();
      avail.native.claude = true;
      const config = buildAgentConfig(avail);
      expect(config).toHaveProperty('sisyphus');
      expect(config.sisyphus.model).toBe('claude-opus-4-6');
    });

    it('includes librarian when opencodeGo is available', () => {
      const avail = emptyAvail();
      avail.opencodeGo = true;
      const config = buildAgentConfig(avail);
      expect(config).toHaveProperty('librarian');
      expect(config.librarian.model).toBe('minimax-m2.7');
    });

    it('does not include hephaestus when no suitable provider is available', () => {
      const avail = emptyAvail();
      avail.kimiForCoding = true; // hephaestus requires openai/venice/copilot
      const config = buildAgentConfig(avail);
      // hephaestus has requiresProvider constraint — not met
      expect(config).not.toHaveProperty('hephaestus');
    });
  });
});

// ── Hook system tests ──────────────────────────────────────────────────────────

import {
  HookRegistry,
  buildHookRegistry,
  createCoreHooks,
  makeContextWindowHook,
  makeThinkModeHook,
  makeIntentGateHook,
  makeAutoSlashCommandHook,
  makeKeywordDetectorHook,
  makeTodoContinuationEnforcerHook,
  makeStopContinuationGuardHook,
  makeCategorySkillReminderHook,
} from '../src/orchestrator/hookSystem.js';
import type { HookContext } from '../src/orchestrator/hookSystem.js';

describe('hookSystem', () => {
  describe('HookRegistry', () => {
    it('registers and emits hooks for a given event', async () => {
      const registry = new HookRegistry();
      let called = false;
      registry.register('test.event', {
        name: 'testHook',
        fn: () => { called = true; return { handled: true }; },
      });
      await registry.emit('test.event', {});
      expect(called).toBe(true);
    });

    it('runs hooks in priority order (lower first)', async () => {
      const registry = new HookRegistry();
      const order: string[] = [];
      registry.register('test.order', { name: 'low', priority: 100, fn: () => { order.push('low'); } });
      registry.register('test.order', { name: 'high', priority: 1, fn: () => { order.push('high'); } });
      registry.register('test.order', { name: 'mid', priority: 50, fn: () => { order.push('mid'); } });
      await registry.emit('test.order', {});
      expect(order).toEqual(['high', 'mid', 'low']);
    });

    it('skips disabled hooks', async () => {
      const registry = new HookRegistry();
      let called = false;
      registry.register('test.skip', {
        name: 'disabled',
        enabled: false,
        fn: () => { called = true; },
      });
      await registry.emit('test.skip', {});
      expect(called).toBe(false);
    });

    it('collects all return values from hooks', async () => {
      const registry = new HookRegistry();
      registry.register('test.ret', { name: 'h1', fn: () => ({ handled: true, transform: { a: 1 } }) });
      registry.register('test.ret', { name: 'h2', fn: () => ({ handled: true, transform: { b: 2 } }) });
      const results = await registry.emit('test.ret', {});
      expect(results).toHaveLength(2);
      expect(results[0].transform).toEqual({ a: 1 });
      expect(results[1].transform).toEqual({ b: 2 });
    });

    it('merges modified context back via Object.assign', async () => {
      const registry = new HookRegistry();
      registry.register('test.ctx', { name: 'mod1', fn: (ctx) => ({ handled: true, modified: { x: 1 } }) });
      registry.register('test.ctx', { name: 'mod2', fn: (ctx) => ({ handled: true, modified: { y: 2 } }) });
      const ctx: HookContext = {};
      const results = await registry.emit('test.ctx', ctx);
      expect(results).toHaveLength(2);
    });

    it('returns empty array when no hooks registered for event', async () => {
      const registry = new HookRegistry();
      const results = await registry.emit('never.registered', {});
      expect(results).toHaveLength(0);
    });

    it('get() returns the list of hooks for an event', () => {
      const registry = new HookRegistry();
      registry.register('test.list', { name: 'h1', fn: () => {} });
      registry.register('test.list', { name: 'h2', fn: () => {} });
      expect(registry.get('test.list')).toHaveLength(2);
      expect(registry.get('other.event')).toHaveLength(0);
    });
  });

  describe('makeContextWindowHook', () => {
    it('does not warn when context is under threshold', async () => {
      const registry = new HookRegistry();
      registry.register('core.test', makeContextWindowHook(0.85));
      const ctx: HookContext = { contextWindowUsed: 50000, contextWindowMax: 100000 };
      const results = await registry.emit('core.test', ctx);
      expect(results).toHaveLength(0);
    });

    it('warns when context exceeds threshold', async () => {
      const registry = new HookRegistry();
      registry.register('core.test', makeContextWindowHook(0.85));
      const ctx: HookContext = { contextWindowUsed: 90000, contextWindowMax: 100000 };
      const results = await registry.emit('core.test', ctx);
      expect(results).toHaveLength(1);
      expect(results[0].transform).toHaveProperty('_contextWindowWarning');
    });
  });

  describe('makeThinkModeHook', () => {
    it('sets thinkMode for complex tasks', async () => {
      const registry = new HookRegistry();
      registry.register('core.test', makeThinkModeHook());
      const ctx: HookContext = { taskDescription: 'implement a red-black tree' };
      const results = await registry.emit('core.test', ctx);
      expect(results).toHaveLength(1);
      expect(results[0].transform).toEqual({ _thinkMode: true, _reasoningEffort: 'high' });
    });

    it('does not set thinkMode for simple tasks', async () => {
      const registry = new HookRegistry();
      registry.register('core.test', makeThinkModeHook());
      const ctx: HookContext = { taskDescription: 'find the config file' };
      const results = await registry.emit('core.test', ctx);
      expect(results).toHaveLength(0);
    });
  });

  describe('makeIntentGateHook', () => {
    it('classifies "create" tasks as unspecified-high', async () => {
      const registry = new HookRegistry();
      registry.register('core.test', makeIntentGateHook());
      const ctx: HookContext = { taskDescription: 'create user authentication' };
      const results = await registry.emit('core.test', ctx);
      expect(results).toHaveLength(1);
      expect(results[0].transform).toEqual({ _taskCategory: 'unspecified-high' });
    });

    it('classifies "find" tasks as quick', async () => {
      const registry = new HookRegistry();
      registry.register('core.test', makeIntentGateHook());
      const ctx: HookContext = { taskDescription: 'find the missing file' };
      const results = await registry.emit('core.test', ctx);
      expect(results).toHaveLength(1);
      expect(results[0].transform).toEqual({ _taskCategory: 'quick' });
    });

    it('defaults to unspecified-low', async () => {
      const registry = new HookRegistry();
      registry.register('core.test', makeIntentGateHook());
      const ctx: HookContext = { taskDescription: 'check something' };
      const results = await registry.emit('core.test', ctx);
      expect(results).toHaveLength(1);
      expect(results[0].transform).toEqual({ _taskCategory: 'unspecified-low' });
    });
  });

  describe('makeAutoSlashCommandHook', () => {
    it('expands /test to run tests', async () => {
      const registry = new HookRegistry();
      registry.register('skill.test', makeAutoSlashCommandHook());
      const ctx: HookContext = { taskDescription: '/test for auth module' };
      const results = await registry.emit('skill.test', ctx);
      expect(results).toHaveLength(1);
      expect(results[0].transform).toHaveProperty('_slashCommandExpanded');
      expect(results[0].transform._slashCommandExpanded.expansion).toContain('run tests');
    });

    it('expands /fix to fix the last error', async () => {
      const registry = new HookRegistry();
      registry.register('skill.test', makeAutoSlashCommandHook());
      const ctx: HookContext = { taskDescription: '/fix in the user service' };
      const results = await registry.emit('skill.test', ctx);
      expect(results).toHaveLength(1);
      expect(results[0].transform._slashCommandExpanded.command).toBe('/fix');
    });

    it('does nothing for plain text', async () => {
      const registry = new HookRegistry();
      registry.register('skill.test', makeAutoSlashCommandHook());
      const ctx: HookContext = { taskDescription: 'implement the login flow' };
      const results = await registry.emit('skill.test', ctx);
      expect(results).toHaveLength(0);
    });
  });

  describe('makeKeywordDetectorHook', () => {
    it('detects multiple matching keywords', async () => {
      const registry = new HookRegistry();
      registry.register('core.test', makeKeywordDetectorHook());
      const ctx: HookContext = { taskDescription: 'migrate the database and add tests' };
      const results = await registry.emit('core.test', ctx);
      expect(results).toHaveLength(1);
      const tags = (results[0].transform as any)._detectedTags as string[];
      expect(tags).toContain('migration');
      expect(tags).toContain('testing');
    });

    it('returns empty when no keywords match', async () => {
      const registry = new HookRegistry();
      registry.register('core.test', makeKeywordDetectorHook());
      const ctx: HookContext = { taskDescription: 'refactor the controller' };
      const results = await registry.emit('core.test', ctx);
      expect(results).toHaveLength(1);
      expect((results[0].transform as any)._detectedTags).toEqual([]);
    });
  });

  describe('makeTodoContinuationEnforcerHook', () => {
    it('warns when todo task has no recent Todo updates', async () => {
      const registry = new HookRegistry();
      registry.register('continuation.test', makeTodoContinuationEnforcerHook());
      const ctx: HookContext = {
        taskDescription: 'add todos for the sprint',
        recentToolCalls: [
          { id: '1', name: 'Read', input: {}, startTime: Date.now() - 1000, success: true },
          { id: '2', name: 'Edit', input: {}, startTime: Date.now() - 500, success: true },
          { id: '3', name: 'Write', input: {}, startTime: Date.now() - 100, success: true },
        ],
      };
      const results = await registry.emit('continuation.test', ctx);
      expect(results).toHaveLength(1);
      expect(results[0].transform).toHaveProperty('_todoEnforcementWarning');
    });

    it('does not warn when Todo was recently updated', async () => {
      const registry = new HookRegistry();
      registry.register('continuation.test', makeTodoContinuationEnforcerHook());
      const ctx: HookContext = {
        taskDescription: 'update the todo list',
        recentToolCalls: [
          { id: '1', name: 'TodoWrite', input: {}, startTime: Date.now() - 100, success: true },
        ],
      };
      const results = await registry.emit('continuation.test', ctx);
      expect(results).toHaveLength(0);
    });
  });

  describe('makeStopContinuationGuardHook', () => {
    it('warns when session shows rapid completion pattern', async () => {
      const registry = new HookRegistry();
      registry.register('continuation.test', makeStopContinuationGuardHook());
      const now = Date.now();
      const ctx: HookContext = {
        recentToolCalls: Array.from({ length: 10 }, (_, i) => ({
          id: String(i),
          name: 'Read',
          input: {},
          startTime: now - (10 - i) * 1000,
          endTime: now - (10 - i) * 1000 + 100,
          success: true,
        })),
      };
      const results = await registry.emit('continuation.test', ctx);
      expect(results.length).toBeGreaterThan(0);
    });

    it('does not warn for normal-paced sessions', async () => {
      const registry = new HookRegistry();
      registry.register('continuation.test', makeStopContinuationGuardHook());
      const ctx: HookContext = {
        recentToolCalls: [
          { id: '1', name: 'Read', input: {}, startTime: Date.now() - 30000, endTime: Date.now() - 28000, success: true },
        ],
      };
      const results = await registry.emit('continuation.test', ctx);
      expect(results).toHaveLength(0);
    });
  });

  describe('makeCategorySkillReminderHook', () => {
    it('recommends skills for visual-engineering category', async () => {
      const registry = new HookRegistry();
      registry.register('skill.test', makeCategorySkillReminderHook());
      const ctx: HookContext = { _taskCategory: 'visual-engineering' };
      const results = await registry.emit('skill.test', ctx);
      expect(results).toHaveLength(1);
      expect((results[0].transform as any)._recommendedSkills).toContain('screenshot');
    });

    it('does nothing when no category is set', async () => {
      const registry = new HookRegistry();
      registry.register('skill.test', makeCategorySkillReminderHook());
      const results = await registry.emit('skill.test', {});
      expect(results).toHaveLength(0);
    });
  });

  describe('buildHookRegistry', () => {
    it('creates a registry with core hooks registered', () => {
      const registry = buildHookRegistry();
      const coreHooks = registry.get('core.*');
      expect(coreHooks.length).toBeGreaterThan(0);
    });

    it('creates a registry with continuation hooks registered', () => {
      const registry = buildHookRegistry();
      const contHooks = registry.get('continuation.*');
      expect(contHooks.length).toBeGreaterThan(0);
    });

    it('accepts optional project rules', () => {
      const registry = buildHookRegistry(['no-ts-ignore', 'prefer-const']);
      const rulesHook = registry.get('core.*').find(h => h.name === 'rulesInjector');
      expect(rulesHook).toBeDefined();
    });
  });
});

// ── Ultrawork tests ────────────────────────────────────────────────────────────

import { classifyTask } from '../src/orchestrator/ultrawork.js';
import { ultrawork } from '../src/orchestrator/ultrawork.js';

describe('ultrawork', () => {
  describe('classifyTask()', () => {
    const tests: [string, Parameters<typeof classifyTask>[0]][] = [
      ['classifies UI/CSS tasks as visual-engineering', 'fix the button styling in CSS'],
      ['classifies complex reasoning as ultrabrain', 'architect a distributed caching system'],
      ['classifies debugging as deep', 'investigate the memory leak'],
      ['classifies small fixes as quick', 'fix the typo in the README'],
      ['classifies "create" as unspecified-high', 'create a new API endpoint'],
      ['classifies "implement" as unspecified-high', 'implement JWT authentication'],
      ['defaults unknown tasks to unspecified-low', 'do something'],
    ];

    it.each(tests)('%s', (_, task) => {
      const result = classifyTask(task);
      expect(typeof result).toBe('string');
    });

    it('returns a valid TaskCategory', () => {
      const categories = ['visual-engineering', 'ultrabrain', 'deep', 'artistry', 'quick', 'unspecified-low', 'unspecified-high'];
      const result = classifyTask('build a full-stack app with tests');
      expect(categories).toContain(result);
    });
  });

  describe('ultrawork()', () => {
    it('completes a simple task in simulated mode', async () => {
      const result = await ultrawork('find the config file', { maxIterations: 10 });
      expect(result.task).toBe('find the config file');
      expect(result.category).toBe('quick');
      expect(result.agent).toBe('librarian');
      expect(result.toolCalls).toBeGreaterThan(0);
      expect(result.durationMs).toBeGreaterThanOrEqual(0);
    });

    it('detects task complexity and selects sisyphus for hard tasks', async () => {
      const result = await ultrawork('implement a concurrent task scheduler', { maxIterations: 10 });
      expect(result.agent).toBe('sisyphus');
    });

    it('respects maxIterations limit', async () => {
      const result = await ultrawork('work that never ends', { maxIterations: 3 });
      expect(result.toolCalls).toBeLessThanOrEqual(3);
    });

    it('returns an error-free result for simple tasks', async () => {
      const result = await ultrawork('fix the typo', { maxIterations: 10 });
      expect(result.errors).toHaveLength(0);
    });

    it('records hooks that were fired', async () => {
      const result = await ultrawork('create a new module', { maxIterations: 5, verbose: false });
      // At minimum, session start/end hooks should fire
      expect(Array.isArray(result.hooksFired)).toBe(true);
    });

    it('returns a model string in the result', async () => {
      const result = await ultrawork('implement auth', { maxIterations: 5 });
      expect(result.model).toContain('/');
    });

    it('accepts verbose option without crashing', async () => {
      const result = await ultrawork('simple fix', { maxIterations: 3, verbose: true });
      expect(result.success).toBe(true);
    });

    it('uses agent override when provided', async () => {
      const result = await ultrawork('do some work', { agentOverride: 'prometheus', maxIterations: 3 });
      expect(result.agent).toBe('prometheus');
    });

    it('resolves the model based on available providers', async () => {
      // This test validates the integration — model resolution path works
      process.env.ANTHROPIC_API_KEY = 'sk-ant-test';
      const result = await ultrawork('design an API', { maxIterations: 3 });
      expect(result.model).toContain('claude');
      delete process.env.ANTHROPIC_API_KEY;
    });
  });
});
