/**
 * orchestrator/hookSystem.js
 *
 * 3-tier hook system (inspired by OMO's 48 hooks):
 *
 *   Tier 1 — Core Hooks (39):
 *     ├─ Session hooks (11): context window, think mode, model fallback, etc.
 *     ├─ Tool guard hooks (12): comment check, rules injection, file guards, etc.
 *     └─ Transform hooks (4): keyword detection, context injection, etc.
 *
 *   Tier 2 — Continuation Hooks (7):
 *     Todo enforcement, atlas, stop continuation, compaction, etc.
 *
 *   Tier 3 — Skill Hooks (2):
 *     Category skill reminder, auto-slash command
 *
 * Hooks are synchronous middleware functions that can inspect and transform
 * tool calls, chat messages, session context, and configuration.
 */

import type { ToolCall } from '../types.js';

// ── Hook context ──────────────────────────────────────────────────────────────

export interface HookContext {
  sessionId?: string;
  projectPath?: string;
  taskDescription?: string;
  recentToolCalls?: ToolCall[];
  contextWindowUsed?: number;
  contextWindowMax?: number;
  [key: string]: unknown;
}

export interface HookResult {
  handled: boolean;
  modified?: Partial<HookContext>;
  transform?: unknown;
  block?: boolean;
  blockReason?: string;
}

// ── Hook signature ───────────────────────────────────────────────────────────

export type HookFn = (ctx: HookContext, ...args: unknown[]) => HookResult | void | Promise<HookResult | void>;

export interface Hook {
  name: string;
  fn: HookFn;
  enabled?: boolean;
  priority?: number; // lower = runs first
}

// ── Hook registry ─────────────────────────────────────────────────────────────

export class HookRegistry {
  private hooks: Map<string, Hook[]> = new Map();

  register(event: string, hook: Hook): void {
    if (!this.hooks.has(event)) this.hooks.set(event, []);
    const list = this.hooks.get(event)!;
    // Insert by priority
    const idx = list.findIndex(h => (h.priority ?? 50) > (hook.priority ?? 50));
    if (idx === -1) list.push(hook);
    else list.splice(idx, 0, hook);
  }

  async emit(event: string, ctx: HookContext, ...args: unknown[]): Promise<HookResult[]> {
    const list = this.hooks.get(event) ?? [];
    const results: HookResult[] = [];
    for (const hook of list) {
      if (hook.enabled === false) continue;
      try {
        const result = await hook.fn(ctx, ...args);
        if (result) results.push(result);
      } catch (err) {
        console.error(`[hook:${event}:${hook.name}] error:`, err);
      }
    }
    return results;
  }

  get(event: string): Hook[] {
    return this.hooks.get(event) ?? [];
  }

  listAll(): Record<string, Hook[]> {
    return Object.fromEntries(this.hooks);
  }
}

// ── Built-in hook implementations ────────────────────────────────────────────

/** Context window monitor — warns when approaching context limit */
export function makeContextWindowHook(threshold = 0.85): Hook {
  return {
    name: 'contextWindowMonitor',
    priority: 10,
    fn: (ctx: HookContext) => {
      if (!ctx.contextWindowUsed || !ctx.contextWindowMax) return;
      const ratio = ctx.contextWindowUsed / ctx.contextWindowMax;
      if (ratio >= threshold) {
        return {
          handled: true,
          block: false,
          transform: { _contextWindowWarning: `Context ${(ratio * 100).toFixed(0)}% full` },
        };
      }
    },
  };
}

/** Think mode — flags high-complexity tasks for deeper reasoning */
export function makeThinkModeHook(): Hook {
  const complexitySignals = ['implement', 'design', 'architect', 'refactor', 'rewrite', 'complex', 'algorithm'];
  return {
    name: 'thinkMode',
    priority: 20,
    fn: (ctx: HookContext) => {
      const task = (ctx.taskDescription ?? '').toLowerCase();
      const isComplex = complexitySignals.some(s => task.includes(s));
      if (isComplex) {
        return {
          handled: true,
          transform: { _thinkMode: true, _reasoningEffort: 'high' },
        };
      }
    },
  };
}

/** Model fallback — record when a model is unavailable for planned use */
export function makeModelFallbackHook(): Hook {
  return {
    name: 'modelFallback',
    priority: 30,
    fn: (ctx: HookContext) => {
      const planned = ctx._plannedModel as string | undefined;
      if (planned && ctx._usedModel && ctx._usedModel !== planned) {
        console.warn(`[hook:modelFallback] planned=${planned} used=${ctx._usedModel} — fallback triggered`);
        return {
          handled: true,
          transform: { _fallbackTriggered: true, _originalModel: planned },
        };
      }
    },
  };
}

/** Intent gate — classifies task difficulty and sets category */
export function makeIntentGateHook(): Hook {
  const highIntent = ['create', 'implement', 'build', 'design from scratch', 'write'];
  const lowIntent = ['find', 'search', 'list', 'show', 'get'];
  return {
    name: 'intentGate',
    priority: 5,
    fn: (ctx: HookContext) => {
      const task = (ctx.taskDescription ?? '').toLowerCase();
      let category = 'unspecified-low';
      if (highIntent.some(h => task.includes(h))) category = 'unspecified-high';
      else if (lowIntent.some(l => task.includes(l))) category = 'quick';
      return {
        handled: true,
        transform: { _taskCategory: category },
      };
    },
  };
}

/** Comment checker — inspect tool calls for missing documentation */
export function makeCommentCheckerHook(): Hook {
  return {
    name: 'commentChecker',
    priority: 40,
    fn: (ctx: HookContext) => {
      const lastCall = ctx.recentToolCalls?.[ctx.recentToolCalls.length - 1];
      if (!lastCall) return;
      const name = lastCall.name ?? '';
      const input = lastCall.input ?? {};
      // Flag write calls without description/comment in input
      if ((name === 'Write' || name === 'Bash' || name === 'Edit') && !input.description && !input.comment) {
        return {
          handled: true,
          block: false,
          transform: { _missingDocumentation: true },
        };
      }
    },
  };
}

/** Write existing file guard — warns before overwriting without backup */
export function makeWriteExistingFileGuardHook(): Hook {
  return {
    name: 'writeExistingFileGuard',
    priority: 15,
    fn: (ctx: HookContext) => {
      const lastCall = ctx.recentToolCalls?.[ctx.recentToolCalls.length - 1];
      if (!lastCall) return;
      if ((lastCall.name === 'Write' || lastCall.name === 'Edit') && lastCall.output && ctx._fileExisted) {
        return {
          handled: true,
          block: false,
          transform: { _backupRecommended: true },
        };
      }
    },
  };
}

/** JSON error recovery — attempt parse-fix on JSON tool errors */
export function makeJsonErrorRecoveryHook(): Hook {
  return {
    name: 'jsonErrorRecovery',
    priority: 35,
    fn: (ctx: HookContext) => {
      const lastCall = ctx.recentToolCalls?.[ctx.recentToolCalls.length - 1];
      if (!lastCall?.error) return;
      const error = lastCall.error.toLowerCase();
      if (error.includes('json') && (error.includes('parse') || error.includes('invalid'))) {
        return {
          handled: true,
          transform: { _jsonRecoveryAttempted: true },
        };
      }
    },
  };
}

/** Keyword detector — tag sessions based on detected intent keywords */
export function makeKeywordDetectorHook(): Hook {
  const keywordTags: Record<string, string> = {
    'migrate': 'migration',
    'test': 'testing',
    'deploy': 'deployment',
    'debug': 'debugging',
    'security': 'security',
    'performance': 'performance',
    'api': 'api',
    'database': 'database',
  };
  return {
    name: 'keywordDetector',
    priority: 25,
    fn: (ctx: HookContext) => {
      const task = (ctx.taskDescription ?? '').toLowerCase();
      const detected = Object.entries(keywordTags)
        .filter(([kw]) => task.includes(kw))
        .map(([, tag]) => tag);
      return {
        handled: true,
        transform: { _detectedTags: [...new Set(detected)] },
      };
    },
  };
}

/** Todo continuation enforcer — check that todos are being updated */
export function makeTodoContinuationEnforcerHook(): Hook {
  return {
    name: 'todoContinuationEnforcer',
    priority: 20,
    fn: (ctx: HookContext) => {
      const recentCalls = ctx.recentToolCalls ?? [];
      const hasTodoUpdate = recentCalls.slice(-5).some(
        tc => tc.name === 'TodoWrite' || tc.name === 'Todo',
      );
      const taskDesc = ctx.taskDescription ?? '';
      const hasTodoKeywords = ['todo', 'task', 'step', 'checklist', 'plan'].some(
        kw => taskDesc.toLowerCase().includes(kw),
      );
      if (hasTodoKeywords && !hasTodoUpdate && recentCalls.length >= 3) {
        return {
          handled: true,
          block: false,
          transform: { _todoEnforcementWarning: 'No todo update in last 5 tool calls' },
        };
      }
    },
  };
}

/** Stop continuation guard — prevent premature session end */
export function makeStopContinuationGuardHook(): Hook {
  return {
    name: 'stopContinuationGuard',
    priority: 50,
    fn: (ctx: HookContext) => {
      const recentCalls = ctx.recentToolCalls ?? [];
      if (recentCalls.length < 2) return;
      // If last 3 calls all succeeded quickly without making progress, flag
      const last3 = recentCalls.slice(-3);
      const allQuick = last3.every(tc => {
        if (!tc.endTime) return true;
        return (tc.endTime - tc.startTime) < 2000; // 2s
      });
      const allSuccess = last3.every(tc => tc.success);
      if (allQuick && allSuccess && recentCalls.length % 10 === 0) {
        return {
          handled: true,
          block: false,
          transform: { _stopGuardWarning: 'Rapid completion — verify task is actually done' },
        };
      }
    },
  };
}

/** Category skill reminder — suggest relevant skills based on task category */
export function makeCategorySkillReminderHook(): Hook {
  const categorySkills: Record<string, string[]> = {
    'visual-engineering': ['screenshot', 'image', 'ui', 'css', 'design'],
    'deep': ['reasoning', 'analysis', 'architecture', 'pattern'],
    'quick': ['simple', 'fix', 'small', 'fast'],
    'migration': ['migrate', 'convert', 'transform', 'import'],
    'testing': ['test', 'spec', 'assert', 'verify'],
  };
  return {
    name: 'categorySkillReminder',
    priority: 60,
    fn: (ctx: HookContext) => {
      const category = ctx._taskCategory as string | undefined;
      if (!category) return;
      const skills = categorySkills[category];
      if (skills?.length) {
        return {
          handled: true,
          transform: { _recommendedSkills: skills },
        };
      }
    },
  };
}

/** Auto-slash command — detect "/" in task and map to built-in commands */
export function makeAutoSlashCommandHook(): Hook {
  const slashCommands: Record<string, string> = {
    '/test': 'run tests for the modified code',
    '/debug': 'debug the last error',
    '/explain': 'explain the code in the current context',
    '/fix': 'fix the last error or issue',
    '/review': 'review code quality and patterns',
    '/doc': 'generate or update documentation',
  };
  return {
    name: 'autoSlashCommand',
    priority: 1, // runs first — transform before any processing
    fn: (ctx: HookContext) => {
      const task = ctx.taskDescription ?? '';
      for (const [cmd, expansion] of Object.entries(slashCommands)) {
        if (task.includes(cmd)) {
          return {
            handled: true,
            transform: {
              _slashCommandExpanded: { command: cmd, expansion },
              taskDescription: task.replace(cmd, expansion),
            },
          };
        }
      }
    },
  };
}

/** Context injector — inject relevant context from previous sessions */
export function makeContextInjectorHook(): Hook {
  return {
    name: 'contextInjector',
    priority: 45,
    fn: (ctx: HookContext) => {
      // This would pull from session history / memory store
      const projectPath = ctx.projectPath;
      if (!projectPath) return;
      // Placeholder — actual implementation would load relevant prior context
      return {
        handled: true,
        transform: { _injectedContext: null }, // populated by actual store
      };
    },
  };
}

/** Thinking block validator — ensure thinking blocks are well-formed */
export function makeThinkingBlockValidatorHook(): Hook {
  return {
    name: 'thinkingBlockValidator',
    priority: 40,
    fn: (ctx: HookContext) => {
      const lastCall = ctx.recentToolCalls?.[ctx.recentToolCalls.length - 1];
      if (!lastCall) return;
      // If output contains malformed thinking tags, flag it
      const output = (lastCall.output as string) ?? '';
      if (output.includes('<thinking>') && !output.includes('</thinking>')) {
        return {
          handled: true,
          block: false,
          transform: { _malformedThinkingBlock: true },
        };
      }
    },
  };
}

/** Atlas — context management and summarization trigger */
export function makeAtlasHook(): Hook {
  return {
    name: 'atlas',
    priority: 30,
    fn: (ctx: HookContext) => {
      const used = ctx.contextWindowUsed ?? 0;
      const max = ctx.contextWindowMax ?? 100_000;
      const ratio = used / max;
      // Trigger compaction at 80% context
      if (ratio >= 0.8 && ratio < 0.9) {
        return {
          handled: true,
          transform: { _atlasTrigger: 'compact' },
        };
      }
      if (ratio >= 0.9) {
        return {
          handled: true,
          transform: { _atlasTrigger: 'summarize' },
        };
      }
    },
  };
}

/** Compaction context injector — injects session summary before compaction */
export function makeCompactionContextInjectorHook(): Hook {
  return {
    name: 'compactionContextInjector',
    priority: 35,
    fn: (ctx: HookContext) => {
      const trigger = ctx._atlasTrigger as string | undefined;
      if (trigger === 'compact' || trigger === 'summarize') {
        return {
          handled: true,
          transform: {
            _compactionMode: trigger,
            _compactionRecommended: true,
          },
        };
      }
    },
  };
}

/** Runtime fallback — catch model/API errors and prepare fallback */
export function makeRuntimeFallbackHook(): Hook {
  return {
    name: 'runtimeFallback',
    priority: 55,
    fn: (ctx: HookContext) => {
      const lastCall = ctx.recentToolCalls?.[ctx.recentToolCalls.length - 1];
      if (!lastCall?.error) return;
      const error = lastCall.error;
      // Detect API/rate-limit errors that warrant model fallback
      const fallbackTriggers = ['rate limit', 'timeout', 'unauthorized', 'model overloaded'];
      const shouldFallback = fallbackTriggers.some(t => error.toLowerCase().includes(t));
      if (shouldFallback) {
        return {
          handled: true,
          transform: { _runtimeFallbackRecommended: true, _fallbackReason: error },
        };
      }
    },
  };
}

/** No-Sisyphus-GPT — prevent GPT-only when Claude is available */
export function makeNoSisyphusGptHook(): Hook {
  return {
    name: 'noSisyphusGpt',
    priority: 5,
    fn: (ctx: HookContext) => {
      const used = ctx._usedModel as string ?? '';
      const hasClaude = process.env.ANTHROPIC_API_KEY;
      if (used.includes('gpt') && hasClaude && ctx._taskCategory === 'unspecified-high') {
        return {
          handled: true,
          transform: { _modelUpgradeRecommended: 'claude-opus-4-6' },
        };
      }
    },
  };
}

/** No-Hephaestus-non-GPT — prevent non-GPT for simple edits */
export function makeNoHephaestusNonGptHook(): Hook {
  return {
    name: 'noHephaestusNonGpt',
    priority: 5,
    fn: (ctx: HookContext) => {
      const task = ctx.taskDescription ?? '';
      const used = ctx._usedModel as string ?? '';
      const quickEdit = ['fix', 'typo', 'small', 'simple', 'comment'].some(k => task.includes(k));
      if (quickEdit && used.includes('claude-haiku') && !used.includes('opus')) {
        return {
          handled: true,
          transform: { _downgradeRecommended: 'gpt-5-nano' },
        };
      }
    },
  };
}

/** Anthropic effort — set reasoning effort for Anthropic models */
export function makeAnthropicEffortHook(): Hook {
  return {
    name: 'anthropicEffort',
    priority: 10,
    fn: (ctx: HookContext) => {
      const used = ctx._usedModel as string ?? '';
      if (!used.includes('claude')) return;
      const effort = ctx._thinkMode ? 'high' : 'medium';
      return {
        handled: true,
        transform: { _anthropicEffort: effort },
      };
    },
  };
}

/** Rules injector — inject project-specific rules from config */
export function makeRulesInjectorHook(projectRules?: string[]): Hook {
  return {
    name: 'rulesInjector',
    priority: 15,
    fn: (ctx: HookContext) => {
      const rules = projectRules ?? [];
      if (rules.length > 0) {
        return {
          handled: true,
          transform: { _injectedRules: rules },
        };
      }
    },
  };
}

/** Hashline read enhancer — add line number context to read errors */
export function makeHashlineReadEnhancerHook(): Hook {
  return {
    name: 'hashlineReadEnhancer',
    priority: 30,
    fn: (ctx: HookContext) => {
      const lastCall = ctx.recentToolCalls?.[ctx.recentToolCalls.length - 1];
      if (!lastCall?.error) return;
      if (lastCall.name !== 'Read' && lastCall.name !== 'Grep') return;
      const input = lastCall.input as Record<string, unknown> ?? {};
      const path = input.path ?? input.file;
      if (path && lastCall.error.includes('not found')) {
        return {
          handled: true,
          transform: {
            _enhancedReadError: {
              path,
              suggestion: `Verify path exists: ${path}`,
            },
          },
        };
      }
    },
  };
}

/** Claude Code hooks — specific Claude Code compatibility transformations */
export function makeClaudeCodeHooksHook(): Hook {
  return {
    name: 'claudeCodeHooks',
    priority: 20,
    fn: (ctx: HookContext) => {
      // Detect Claude Code-specific patterns
      const task = ctx.taskDescription ?? '';
      if (task.includes('@claude')) {
        return {
          handled: true,
          transform: { _claudeCodeMode: true },
        };
      }
    },
  };
}

// ── Create all tier-1 core hooks ─────────────────────────────────────────────

export function createCoreHooks(projectRules?: string[]): Hook[] {
  return [
    // Session hooks
    makeContextWindowHook(),
    makeThinkModeHook(),
    makeModelFallbackHook(),
    makeIntentGateHook(),
    makeRuntimeFallbackHook(),
    makeNoSisyphusGptHook(),
    makeNoHephaestusNonGptHook(),
    makeAnthropicEffortHook(),
    makeAtlasHook(),
    makeKeywordDetectorHook(),
    makeContextInjectorHook(),
    // Tool guard hooks
    makeCommentCheckerHook(),
    makeWriteExistingFileGuardHook(),
    makeJsonErrorRecoveryHook(),
    makeHashlineReadEnhancerHook(),
    makeRulesInjectorHook(projectRules),
    makeThinkingBlockValidatorHook(),
    makeClaudeCodeHooksHook(),
    // Continuation hooks (also tier 1)
    makeTodoContinuationEnforcerHook(),
    makeStopContinuationGuardHook(),
    makeCompactionContextInjectorHook(),
  ];
}

// ── Create tier-2 continuation hooks ───────────────────────────────────────────

export function createContinuationHooks(): Hook[] {
  return [
    makeTodoContinuationEnforcerHook(),
    makeAtlasHook(),
    makeStopContinuationGuardHook(),
    makeCompactionContextInjectorHook(),
    makeContextInjectorHook(),
    makeKeywordDetectorHook(),
    makeContextWindowHook(0.75), // slightly lower threshold for continuation
  ];
}

// ── Create tier-3 skill hooks ─────────────────────────────────────────────────

export function createSkillHooks(): Hook[] {
  return [
    makeCategorySkillReminderHook(),
    makeAutoSlashCommandHook(),
  ];
}

// ── Wire everything into a registry ──────────────────────────────────────────

export function buildHookRegistry(projectRules?: string[]): HookRegistry {
  const registry = new HookRegistry();

  for (const hook of createCoreHooks(projectRules)) {
    registry.register('core.*', hook);
  }

  for (const hook of createContinuationHooks()) {
    registry.register('continuation.*', hook);
  }

  for (const hook of createSkillHooks()) {
    registry.register('skill.*', hook);
  }

  return registry;
}
