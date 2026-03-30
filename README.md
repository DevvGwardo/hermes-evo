# Hermes Evo — Self-Evolution Engine for Hermes

[![CI](https://github.com/DevvGwardo/hermes-evo/actions/workflows/ci.yml/badge.svg)](https://github.com/DevvGwardo/hermes-evo/actions/workflows/ci.yml)
[![Node.js 20+](https://img.shields.io/badge/node-20%2B-green)](https://nodejs.org)
[![TypeScript](https://img.shields.io/badge/typescript-5.0-blue)](https://www.typescriptlang.org)

> Monitors, evaluates, and improves your Hermes AI assistant — automatically.

**Hermes Evo** watches how your [Hermes](https://github.com/DevvGwardo/hermes-agent) assistant performs in real sessions, identifies recurring failure patterns, generates fix "skills", A/B tests them with statistical rigor, and deploys the winners — continuously, without human intervention.

It also acts as a **supervisor** — if the Hermes gateway goes down, the built-in watchdog detects it and restarts it automatically.

---

## Table of Contents

- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Usage Guide](#usage-guide)
  - [One-Shot Mode](#one-shot-mode)
  - [REPL Mode](#repl-mode)
  - [Cron Mode](#cron-mode)
  - [Dev Mode](#dev-mode)
  - [Test Failures Mode](#test-failures-mode)
  - [Watch Mode](#watch-mode)
- [How It Works](#how-it-works)
- [Configuration](#configuration)
- [Testing](#testing)
- [Architecture](#architecture)
- [Repository Structure](#repository-structure)
- [Dashboard](#dashboard)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)

---

## Prerequisites

- **Node.js 20+** — [install via nvm](https://github.com/nvm-sh/nvm)
- **Hermes gateway running** on `localhost:18789` — start it with `hermes gateway` or let the watchdog handle it
- **Gateway auth token** — stored in `~/.openclaw/openclaw.json` (created automatically by the Hermes CLI)

## Installation

```bash
git clone https://github.com/DevvGwardo/hermes-evo.git
cd hermes-evo
npm install
npm run build
```

## Quick Start

```bash
# Run one evolution cycle against your live Hermes gateway and exit
npm run evolve:once

# Start the interactive REPL with dashboard
npm run start:hub

# Run with synthetic test failures to verify the pipeline works
npx tsx src/cli.ts --test-failures
```

---

## Usage Guide

### One-Shot Mode

Runs a single evolution cycle and exits. Good for manual checks or scripting.

```bash
npm run evolve:once
# or
npx tsx src/cli.ts --once
```

What happens:
1. Connects to your Hermes gateway at `localhost:18789`
2. Fetches active sessions from the last 30 minutes
3. Scores them, detects failure patterns, generates skills
4. Runs A/B experiments, promotes winners
5. Exits

### REPL Mode

Starts an interactive command-line interface with the dashboard server.

```bash
npm run start:hub
```

Available commands:

| Command | Description |
|---------|-------------|
| `status` | Show hub status (running, cycles, experiments, deployed skills) |
| `trigger` | Trigger an evolution cycle immediately |
| `skills` | List all proposed and deployed skills |
| `approve <id>` | Approve a skill pending human review and deploy it |
| `logs` | Show recent evolution cycle history |
| `stats` | Show performance statistics |
| `watchdog` | Show gateway watchdog status |
| `restart` | Stop and restart the hub |
| `help` | Show available commands |
| `quit` | Exit |

### Cron Mode

Like one-shot, but saves a checkpoint between runs so state persists across invocations. Use this for scheduled runs.

```bash
npx tsx src/cli.ts --cron
```

Example crontab entry (run every 5 minutes):

```cron
*/5 * * * * cd /path/to/hermes-evo && npx tsx src/cli.ts --cron >> /tmp/hermes-evo.log 2>&1
```

### Dev Mode

Runs the hub and the React dashboard in parallel with hot reload.

```bash
npm run dev
```

- Hub: watches `src/` for changes and restarts
- Dashboard: Vite dev server at `http://localhost:5174`

### Test Failures Mode

Injects synthetic tool failures (Read/not_found, Bash/network_error, Grep/timeout) to exercise the full pipeline without needing real failures in your gateway.

```bash
npx tsx src/cli.ts --test-failures
```

This is the best way to verify the system is working end-to-end. You'll see:
- Pattern detection finding the injected failures
- Skill generation creating fixes
- A/B experiments running statistical tests
- Promoter recommending skills for approval

### Watch Mode

Auto-restarts the hub when source files change. Useful during development.

```bash
npx tsx src/cli.ts --watch
```

---

## How It Works

Hermes Evo runs a five-phase evolution cycle every 5 minutes:

```
Monitor → Evaluate → Build → Experiment → Integrate → (repeat)
```

| Phase | What happens |
|-------|-------------|
| **Monitor** | Fetches active sessions from the Hermes gateway, collects tool calls, errors, and latency into `SessionMetrics` |
| **Evaluate** | Scores sessions across 5 dimensions (accuracy, efficiency, speed, reliability, coverage) and mines recurring failure patterns |
| **Build** | For each top failure pattern, generates a new skill using parameterized templates, validates structure, computes a confidence score |
| **Experiment** | Runs A/B tests — compares sessions with the new skill (treatment) vs. without (control), then runs a two-proportion z-test |
| **Integrate** | Promotes winners (p < 0.05, improvement >= 10%) to `~/.hermes/skills/`, rejects losers, logs everything |

### Data Flow: Failure to Fix

```
Agent makes a tool call
  → Gateway records session
    → Monitor fetches session metrics
      → Scorer assigns performance score
        → Pattern Detector clusters failures
          → (frequency >= 3?) → Skill Generator creates fix
            → Experiment Runner: control vs treatment
              → (p < 0.05 AND improvement >= 10%?)
                → Deploy to ~/.hermes/skills/
                  → Next cycle uses the new skill
```

### Scoring

Sessions are scored on 5 weighted dimensions:

| Dimension | Weight | What it measures |
|-----------|--------|-----------------|
| **Accuracy** | 25% | Did the agent succeed at the task? |
| **Reliability** | 25% | Error rate (lower is better) |
| **Efficiency** | 20% | Tool calls vs. optimal (fewer is better) |
| **Speed** | 20% | Time to complete vs. baseline |
| **Coverage** | 10% | % of task types handled |

Weights are **adaptive** — if reliability drops below threshold, its weight automatically increases.

### Gateway Watchdog

The built-in watchdog monitors the Hermes gateway and restarts it automatically:

- Polls gateway health every 15 seconds
- Restarts after 3 consecutive failures via `hermes gateway start`
- 60-second cooldown between restart attempts
- Gives up after 10 restarts (requires manual intervention)
- Check status with the `watchdog` REPL command

---

## Configuration

All defaults live in `src/constants.ts` and can be overridden via environment variables:

| Setting | Default | Env var |
|---------|---------|---------|
| Cycle interval | 5 min | `CYCLE_INTERVAL_MS` |
| Failure threshold | 1 | `FAILURE_THRESHOLD` |
| Max skills per cycle | 3 | `MAX_SKILLS_PER_CYCLE` |
| Experiment sessions per arm | 5 | `EXPERIMENT_SESSIONS` |
| Min improvement to deploy | 10% | `MIN_IMPROVEMENT_PCT` |
| Statistical confidence | 80% | `STATISTICAL_CONFIDENCE` |
| Gateway URL | `http://localhost:18789` | `HERMES_GATEWAY_URL` |
| Poll interval | 10s | `HERMES_POLL_INTERVAL_MS` |
| Skill output dir | `~/.hermes/skills/` | `SKILL_OUTPUT_DIR` |
| Memory dir | `~/.hermes/evo-memory/` | `MEMORY_DIR` |
| Dashboard port | 5174 | `DASHBOARD_PORT` |

### Watchdog Settings

| Setting | Default | Env var |
|---------|---------|---------|
| Check interval | 15s | `WATCHDOG_CHECK_INTERVAL_MS` |
| Failure threshold | 3 | `WATCHDOG_FAILURE_THRESHOLD` |
| Restart cooldown | 60s | `WATCHDOG_RESTART_COOLDOWN_MS` |
| Max restarts | 10 | `WATCHDOG_MAX_RESTARTS` |
| Restart command | `hermes` | `WATCHDOG_RESTART_CMD` |
| Enable/disable | on | `WATCHDOG_ENABLED` |

### Example `.env` file

```bash
HERMES_GATEWAY_URL=http://localhost:18789
CYCLE_INTERVAL_MS=300000
FAILURE_THRESHOLD=3
MIN_IMPROVEMENT_PCT=10
STATISTICAL_CONFIDENCE=0.80
```

---

## Testing

### Unit & Integration Tests

```bash
# Run all 212 tests
npm test

# Watch mode (re-runs on changes)
npm run test:watch

# Single test file
npx vitest run tests/integration.test.ts

# With coverage report
npx vitest run --coverage
```

### Live Smoke Test

Runs against your actual Hermes gateway on `localhost:18789`. Verifies connectivity, session listing, history retrieval, and metrics extraction.

```bash
npx tsx tests/smoke-hermes.ts
```

### End-to-End Pipeline Test

Injects synthetic failures and runs the full evolution cycle against the live gateway:

```bash
npx tsx src/cli.ts --test-failures
```

### Type Check

```bash
npx tsc --noEmit
```

### Test Files

| File | What it covers |
|------|---------------|
| `tests/integration.test.ts` | Full promote/approve/reject flow, skill deployment |
| `tests/experiment.test.ts` | Experiment lifecycle, A/B runner, comparator |
| `tests/evaluator.test.ts` | Scorer, pattern detector, report generator |
| `tests/builder.test.ts` | Skill generation, validation, templates |
| `tests/memory.test.ts` | MemoryStore persistence |
| `tests/performance.test.ts` | Performance benchmarks |
| `tests/autoresearch-features.test.ts` | Git tracker, experiment branches |
| `tests/smoke-hermes.ts` | Live gateway smoke test |

---

## Architecture

```
hermes-evo/
├── src/
│   ├── hub.ts                    # EvoHub — main orchestrator
│   ├── cli.ts                    # Interactive REPL + CLI entry point
│   ├── server.ts                 # HTTP API server (dashboard backend)
│   ├── watchdog.ts               # Gateway health monitor + auto-restart
│   ├── types.ts                  # Shared TypeScript interfaces
│   ├── constants.ts              # Default configuration + env var parsing
│   ├── gateway.ts                # High-level gateway fetch helpers
│   ├── cycle.ts                  # Evolution cycle logic
│   ├── utils.ts                  # Tool call extraction, task type inference
│   ├── harness/
│   │   ├── monitor.ts            # Gateway event monitoring (WebSocket)
│   │   ├── sessionTracker.ts     # Per-session lifecycle tracking
│   │   └── toolAnalyzer.ts       # Tool call pattern analysis
│   ├── evaluator/
│   │   ├── scorer.ts             # Multi-dimensional performance scoring
│   │   ├── patternDetector.ts    # Failure pattern clustering
│   │   └── reportGenerator.ts    # Evaluation report assembly
│   ├── builder/
│   │   ├── skillGenerator.ts     # Generate skills from failure patterns
│   │   ├── skillValidator.ts     # Structural validation
│   │   ├── templateLibrary.ts    # Parameterized skill templates
│   │   └── marketplace.ts        # Skill marketplace integration
│   ├── experiment/
│   │   ├── runner.ts             # A/B test execution (observational mode)
│   │   ├── comparator.ts         # Two-proportion z-test statistics
│   │   ├── promoter.ts           # Promotion/rejection + human approval
│   │   ├── experimentLog.ts      # Experiment audit trail
│   │   ├── frontier.ts           # Performance frontier tracking
│   │   └── gitTracker.ts         # Git branch management for experiments
│   ├── memory/
│   │   ├── store.ts              # JSON file persistence
│   │   ├── failureCorpus.ts      # Recurring failure database
│   │   └── improvementLog.ts     # Audit trail of all improvements
│   └── hermes/
│       ├── gateway.ts            # Hermes gateway HTTP client
│       ├── sessionManager.ts     # Session listing + metrics extraction
│       └── skillManager.ts       # Skill deployment to ~/.hermes/skills/
├── dashboard/
│   └── src/
│       ├── App.tsx               # React dashboard UI
│       ├── main.tsx              # Dashboard entry point
│       └── api/
│           └── evoClient.ts      # Dashboard → hub API client
├── tests/                        # 7 test suites, 212 tests + smoke test
├── docs/                         # Architecture, API, config, examples
├── package.json
├── tsconfig.json
└── vitest.config.ts
```

---

## Dashboard

The web dashboard at `http://localhost:5174` shows real-time evolution status:

- **Performance scores** — overall health with trend
- **Failure patterns** — top failures ranked by frequency
- **Proposed skills** — generated fixes with approve/reject controls
- **Active experiments** — live A/B test results with statistical significance
- **Cycle history** — recent evolution cycles with phase breakdowns
- **Improvement log** — audit trail of all deployed changes

Start it with:

```bash
npm run dev           # dev mode (hot reload)
npm run start:hub     # production mode (built dashboard)
```

---

## Troubleshooting

### "0 sessions fetched"

The hub only looks at sessions from the last 30 minutes by default. If your gateway has no recent activity, you'll see 0 sessions. Options:

- Use `--test-failures` to inject synthetic data and verify the pipeline
- Set `ACTIVE_SESSION_MINUTES=1440` to look back 24 hours
- Send some messages through your Hermes gateway to generate fresh sessions

### "Unauthorized" from gateway

The gateway client reads its auth token from `~/.openclaw/openclaw.json`. Make sure this file exists and has a valid token. The Hermes CLI creates it automatically when you run `hermes gateway`.

### Skills stuck in "requires_approval"

By default, skills with 100% improvement (synthetic experiments) require human approval as a safety check. Approve them from the REPL:

```
OpenClaw Evo > skills          # list skills and their IDs
OpenClaw Evo > approve <id>    # deploy the skill
```

Or set `AUTO_APPROVE_CONFIDENCE=95` to auto-deploy skills with > 95% statistical confidence.

### Gateway watchdog keeps restarting

Check `watchdog` in the REPL. If the gateway is genuinely down, the watchdog will retry up to 10 times with 60s cooldown between attempts. After 10 failures, it gives up. Fix the gateway manually, then `restart` the hub.

### Build errors after pulling

```bash
rm -rf node_modules dist && npm install && npm run build
```

---

## Contributing

Contributions welcome! See [CONTRIBUTING.md](CONTRIBUTING.md).

Key areas:
- **Builder** — better skill generation algorithms
- **Evaluator** — more sophisticated scoring models
- **Experiment** — better statistical methods
- **Dashboard** — better visualizations

## License

MIT — see [LICENSE](LICENSE)
