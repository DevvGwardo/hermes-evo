/**
 * orchestrator/ultrawork.js
 *
 * The `ultrawork` command — OMO's single-entry orchestration.
 * Type `ultrawork [task]` and the system:
 *   1. Detects available providers
 *   2. Classifies task difficulty (category)
 *   3. Selects the right agent role
 *   4. Runs a task-complete loop (Sisyphus-style: keep going until done)
 *   5. Reports results
 *
 * This is the user-facing CLI command that ties all the pieces together.
 */

import chalk from 'chalk';
import { spawn } from 'child_process';
import { randomUUID } from 'crypto';
import { homedir } from 'os';
import { join } from 'path';
import { detectProviders, summarizeProviders } from './providerDetector.js';
import {
  resolveAgentModel,
  buildAgentConfig,
} from './fallbackChain.js';
import { HookRegistry, buildHookRegistry } from './hookSystem.js';
import type { HookContext } from './hookSystem.js';

const LOG_PREFIX = '[ultrawork]';

// ── Task classification ───────────────────────────────────────────────────────

export type TaskCategory =
  | 'visual-engineering'
  | 'ultrabrain'
  | 'deep'
  | 'artistry'
  | 'quick'
  | 'unspecified-low'
  | 'unspecified-high';

export function classifyTask(task: string): TaskCategory {
  const t = task.toLowerCase();

  const signals: [TaskCategory, string[]][] = [
    ['visual-engineering', ['ui', 'css', 'design', 'screenshot', 'visual', 'image', 'frontend', 'html', 'svg']],
    ['ultrabrain', ['reasoning', 'complex', 'architect', 'design system', 'full-stack', 'algorithm', 'research']],
    ['deep', ['analyze', 'understand', 'explain', 'investigate', 'debug complex', 'performance']],
    ['artistry', ['creative', 'writing', 'content', 'prose', 'narrative']],
    ['quick', ['fix', 'typo', 'small', 'simple', 'fast', 'quick', 'one-line', 'single', 'find', 'search', 'list', 'show', 'get', 'check']],
    ['unspecified-high', ['implement', 'create', 'build', 'write', 'develop', 'construct']],
  ];

  for (const [category, keywords] of signals) {
    if (keywords.some(kw => t.includes(kw))) return category;
  }
  return 'unspecified-low';
}

// ── Result type ───────────────────────────────────────────────────────────────

export interface UltraworkResult {
  task: string;
  category: TaskCategory;
  agent: string;
  model: string;
  success: boolean;
  toolCalls: number;
  durationMs: number;
  errors: string[];
  hooksFired: string[];
}

export interface UltraworkOptions {
  projectPath?: string;
  sessionId?: string;
  maxIterations?: number;
  verbose?: boolean;
  agentOverride?: string;
}

// ── Main ultrawork function ───────────────────────────────────────────────────

export async function ultrawork(
  task: string,
  options: UltraworkOptions = {},
): Promise<UltraworkResult> {
  const startMs = Date.now();
  const maxIterations = options.maxIterations ?? 50;
  const verbose = options.verbose ?? false;

  const providers = detectProviders();
  const providerSummary = summarizeProviders(providers);

  console.log(chalk.cyan(`${LOG_PREFIX} Starting: "${task}"`));
  console.log(chalk.gray(`${LOG_PREFIX} Providers: ${providerSummary}`));

  const category = classifyTask(task);
  console.log(chalk.gray(`${LOG_PREFIX} Category: ${category}`));

  // Build agent config from available providers
  const agentConfig = buildAgentConfig(providers);

  // Determine which agent role to use
  const agentRole = options.agentOverride ?? (category === 'quick' ? 'librarian' : 'sisyphus');
  const resolved = options.agentOverride
    ? resolveAgentModel(agentRole, providers)
    : (agentConfig[agentRole] ?? resolveAgentModel('sisyphus', providers));

  if (!resolved) {
    console.warn(chalk.yellow(`${LOG_PREFIX} No suitable model found for role ${agentRole}`));
    return {
      task,
      category,
      agent: agentRole,
      model: 'unknown',
      success: false,
      toolCalls: 0,
      durationMs: Date.now() - startMs,
      errors: ['No model available for required role'],
      hooksFired: [],
    };
  }

  console.log(chalk.gray(`${LOG_PREFIX} Agent: ${agentRole} → ${resolved.provider}/${resolved.model}${resolved.variant ? ` (${resolved.variant})` : ''}`));

  // Build hook context
  const hookCtx: HookContext = {
    sessionId: options.sessionId,
    projectPath: options.projectPath,
    taskDescription: task,
    contextWindowUsed: 0,
    contextWindowMax: 100_000,
    _plannedModel: resolved.model,
  };

  // Initialize hooks
  const registry = buildHookRegistry();
  const hooksFired: string[] = [];

  // ── Pre-task hook run ────────────────────────────────────────────────────
  const preResults = await registry.emit('core.session.start', hookCtx);
  for (const r of preResults) {
    if (r.handled) hooksFired.push('session.start');
    if (r.modified) Object.assign(hookCtx, r.modified);
  }

  // ── Task-complete loop (Sisyphus) ─────────────────────────────────────────
  // This is the key differentiator: keeps running until the task is done,
  // not until a token budget runs out. Each iteration:
  //   1. Run one agent step with the resolved model
  //   2. Emit tool hooks
  //   3. Check continuation guards
  //   4. If done (no errors in N steps) → break
  //   5. If stuck (same error repeated) → attempt recovery hooks
  //   6. If max iterations → abort
  let iteration = 0;
  let consecutiveSuccesses = 0;
  const errors: string[] = [];
  const recentErrors: string[] = [];

  while (iteration < maxIterations) {
    iteration++;

    if (verbose) {
      console.log(chalk.gray(`${LOG_PREFIX} Iteration ${iteration}/${maxIterations}`));
    }

    // Emit pre-iteration hooks
    const iterResults = await registry.emit('core.iteration.start', hookCtx, { iteration });
    for (const r of iterResults) {
      if (r.handled) hooksFired.push(`iteration.${iteration}`);
      if (r.modified) Object.assign(hookCtx, r.modified);
    }

    // Simulate agent step (actual implementation would call the agent here)
    const stepResult = await executeAgentStep(hookCtx, resolved.model);

    if (verbose) {
      console.log(chalk.gray(`${LOG_PREFIX}   → ${stepResult.success ? 'ok' : 'error'}: ${stepResult.name ?? 'no-tool'}`));
    }

    // Update hook context with recent tool call
    const recentCalls = hookCtx.recentToolCalls ?? [];
    hookCtx.recentToolCalls = [...recentCalls.slice(-9), stepResult];

    // Emit post-step hooks
    const postResults = await registry.emit('core.tool.after', hookCtx, stepResult);
    for (const r of postResults) {
      if (r.handled) hooksFired.push(`tool.after:${stepResult.name}`);
      if (r.modified) Object.assign(hookCtx, r.modified);
      if (r.block) {
        errors.push(`Blocked by hook ${r.blockReason ?? 'unknown'}`);
        break;
      }
    }

    if (stepResult.error) {
      errors.push(stepResult.error);
      recentErrors.push(stepResult.error);
      consecutiveSuccesses = 0;
    } else {
      consecutiveSuccesses++;
    }

    // Emit continuation guards
    const contResults = await registry.emit('continuation.check', hookCtx);
    for (const r of contResults) {
      if (r.handled) hooksFired.push(`continuation.check`);
      if (r.modified?._stopGuardWarning) {
        console.log(chalk.yellow(`${LOG_PREFIX} ⚠ ${r.modified._stopGuardWarning}`));
      }
      if (r.modified?._todoEnforcementWarning) {
        console.log(chalk.yellow(`${LOG_PREFIX} ⚠ ${r.modified._todoEnforcementWarning}`));
      }
    }

    // Detect task completion: 3 consecutive successes with no errors
    if (consecutiveSuccesses >= 3) {
      console.log(chalk.green(`${LOG_PREFIX} Task appears complete (${consecutiveSuccesses} consecutive successes)`));
      break;
    }

    // Detect stuck state: same error 3 times in a row
    const uniqueRecentErrors = [...new Set(recentErrors.slice(-3))];
    if (recentErrors.length >= 3 && uniqueRecentErrors.length === 1) {
      console.log(chalk.yellow(`${LOG_PREFIX} ⚠ Stuck on repeated error: "${uniqueRecentErrors[0]}"`));
      const recoveryResults = await registry.emit('core.recovery.stuck', hookCtx, { error: uniqueRecentErrors[0] });
      if (recoveryResults.length === 0) {
        console.log(chalk.yellow(`${LOG_PREFIX} No recovery hooks — aborting`));
        break;
      }
    }
  }

  // ── Post-task hooks ──────────────────────────────────────────────────────
  const postResults = await registry.emit('core.session.end', hookCtx);
  for (const r of postResults) {
    if (r.handled) hooksFired.push('session.end');
  }

  const durationMs = Date.now() - startMs;
  const success = errors.length === 0 || consecutiveSuccesses >= 3;

  console.log(chalk.cyan(`${LOG_PREFIX} Done in ${iteration} iterations, ${durationMs}ms`));
  if (!success && errors.length > 0) {
    console.log(chalk.red(`${LOG_PREFIX} Errors: ${[...new Set(errors)].slice(0, 3).join('; ')}`));
  }

  return {
    task,
    category,
    agent: agentRole,
    model: `${resolved.provider}/${resolved.model}`,
    success,
    toolCalls: iteration,
    durationMs,
    errors: [...new Set(errors)].slice(0, 5),
    hooksFired: [...new Set(hooksFired)].slice(0, 20),
  };
}

// ── Simulated agent step ──────────────────────────────────────────────────────
// In production, this calls the actual agent via gateway or direct API.
// Here we simulate the shape of the result for demonstration.

interface SimulatedToolCall {
  id: string;
  name: string;
  input: Record<string, unknown>;
  output?: unknown;
  error?: string;
  startTime: number;
  endTime?: number;
  success: boolean;
}

async function executeAgentStep(
  ctx: HookContext,
  model: string,
): Promise<SimulatedToolCall> {
  const id = `step-${Date.now()}-${randomUUID().slice(0, 8)}`;
  const startTime = Date.now();
  const agentSessionId = randomUUID();
  const agentName = `ultrawork-${Date.now()}`;
  const projectPath = ctx.projectPath ?? process.cwd();
  const brainDbPath = process.env.BRAIN_DB_PATH ?? join(homedir(), '.claude', 'brain', 'brain.db');

  // Derive a claude-compatible model alias from the resolved model string
  // (e.g. "anthropic/claude-opus-4-6" → "opus", "openai/gpt-4o" → "gpt-4o")
  const modelPart = model.includes('/') ? model.split('/').slice(1).join('/') : model;
  const modelAlias = modelPart.includes('opus') ? 'opus'
    : modelPart.includes('haiku') ? 'haiku'
    : modelPart.includes('sonnet') ? 'sonnet'
    : modelPart; // pass through for non-Claude models

  const task = ctx.taskDescription ?? 'Perform the assigned work step';

  // Build the agent prompt — mirrors brain_wake headless prompt structure
  const prompt = [
    'You have brain MCP tools available (brain_register, brain_pulse, brain_post, brain_read, brain_set, brain_get).',
    '',
    `Your name: "${agentName}"`,
    `Working directory: ${projectPath}`,
    '',
    'YOUR TASK:',
    task,
    '',
    'WHEN DONE:',
    '1. Call brain_pulse with status="done" and a summary of what you accomplished',
    '2. Call brain_post to announce your results',
    '3. /exit when you are done so resources are freed',
  ].join('\n');

  // Spawn a headless Claude Code agent — mirrors brain_wake layout="headless"
  const args = ['-p', prompt, '--dangerously-skip-permissions'];
  if (modelAlias) args.push('--model', modelAlias);

  const childEnv: NodeJS.ProcessEnv = {
    ...process.env,
    BRAIN_DB_PATH: brainDbPath,
    BRAIN_ROOM: projectPath,
    BRAIN_SESSION_ID: agentSessionId,
    BRAIN_SESSION_NAME: agentName,
  };

  return new Promise<SimulatedToolCall>((resolve) => {
    let stdout = '';
    let stderr = '';

    const child = spawn('claude', args, {
      cwd: projectPath,
      env: childEnv,
      stdio: ['ignore', 'pipe', 'pipe'],
    });

    child.stdout?.on('data', (chunk: Buffer) => { stdout += chunk.toString(); });
    child.stderr?.on('data', (chunk: Buffer) => { stderr += chunk.toString(); });

    // Default timeout: 2 minutes per step
    const timeoutMs = ((ctx._agentTimeoutSec as number | undefined) ?? 120) * 1000;
    const timer = setTimeout(() => {
      child.kill('SIGTERM');
    }, timeoutMs);

    child.on('close', (code) => {
      clearTimeout(timer);
      const endTime = Date.now();
      const output = stdout.trim() || stderr.trim() || '(no output)';

      if (code === 0) {
        resolve({
          id,
          name: 'brain_wake',
          input: { task, model, layout: 'headless', agentSessionId },
          output,
          startTime,
          endTime,
          success: true,
        });
      } else {
        resolve({
          id,
          name: 'brain_wake',
          input: { task, model, layout: 'headless', agentSessionId },
          output,
          error: stderr.trim() || `Agent exited with code ${code}`,
          startTime,
          endTime,
          success: false,
        });
      }
    });

    child.on('error', (err) => {
      clearTimeout(timer);
      resolve({
        id,
        name: 'brain_wake',
        input: { task, model, layout: 'headless', agentSessionId },
        error: `Spawn error: ${err.message}`,
        startTime,
        endTime: Date.now(),
        success: false,
      });
    });
  });
}

// ── CLI helper ────────────────────────────────────────────────────────────────

export function ultraworkHelp(): string {
  return `
${chalk.bold('ultrawork')} — OpenClaw Evo single-task command

${chalk.bold('Usage')}
  ultrawork <task description>
  ultrawork [options] <task description>

${chalk.bold('Options')}
  --project <path>      Set project path for context
  --agent <role>        Override agent role (sisyphus, librarian, prometheus, etc.)
  --max-iters <n>       Max iterations (default: 50)
  --verbose             Emit per-iteration logs
  --help                Show this help

${chalk.bold('Agent Roles')}
  sisyphus      Primary coding agent — runs until task complete
  librarian     Fast file/context lookup
  prometheus    Planning and architecture
  oracle        Deep reasoning and analysis
  atlas         Context management
  hephaestus    Code editing and modification

${chalk.bold('Examples')}
  ultrawork "implement user auth with JWT"
  ultrawork --agent prometheus "design a recommendation engine"
  ultrawork --verbose "fix all ESLint errors in src/"
`.trim();
}
