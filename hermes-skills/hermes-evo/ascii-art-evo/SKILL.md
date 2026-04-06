---
name: ascii-art-evo
description: Hourly cron job that analyzes hermes-ascii scripts in ~/ascii-scripts/, improves them, and updates the implementations.
triggers:
  - "ascii art evolution"
  - "improve ascii scripts"
  - "evolve ascii backgrounds"
---

# ASCII Art Evolution Cron

Hourly self-improvement of the hermes-ascii animation scripts.

## What It Does

Every hour, this cron job:
1. Reads all scripts in `~/ascii-scripts/` (plasma.sh, spiral.sh, starfield.py, etc.)
2. Analyzes each for improvement opportunities
3. Implements improvements incrementally
4. Logs changes to `~/.hermes/cron/ascii-art-evo.log`

## Improvements It Applies

Each script is evaluated across:
- **Visual quality**: richer character sets, better color palettes, smoother gradients
- **Performance**: fewer forks/spawns, efficient loops, lower CPU usage
- **Animation**: smoother transitions, better frame timing, more interesting patterns
- **Code quality**: cleaner structure, better comments, bash 3.x compatibility
- **Novelty**: new pattern variations, different color themes, fresh algorithms

## Cron Setup

```bash
# Create the evolution script
# (automatically created by hermes-evo during setup)

# The cron job runs hourly with ascii-art-evo skill loaded
# See: mcp_cronjob(action='create', prompt=..., schedule='0 * * * *', skill='ascii-art-evo')
```

## Manual Trigger

```bash
# Run evolution now
~/hermes-evo/scripts/ascii-art-evo.sh

# Check last run
cat ~/.hermes/cron/ascii-art-evo.log | tail -50
```

## How Improvements Work

The evolution script uses a rotating review order:
- Week 1: plasma.sh, spiral.sh
- Week 2: starfield.py, matrix_rain.py
- Week 3: fire.py, particle_flow.py
- Week 4: life.sh, launcher scripts

Each run picks one script, reviews it, and applies one focused improvement rather than rewriting everything. Small incremental changes compound over time.

## Log Format

```
[YYYY-MM-DD HH:MM:SS] EVO START
[YYYY-MM-DD HH:MM:SS] Reviewing: plasma.sh
[YYYY-MM-DD HH:MM:SS] Issue found: color palette limited to 10 values
[YYYY-MM-DD HH:MM:SS] Improvement: expanded to 20-step gradient with HDR-like bloom
[YYYY-MM-DD HH:MM:SS] EVO COMPLETE - 1 improvement applied
```
