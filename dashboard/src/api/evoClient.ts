// evoClient.ts — fetches evolution data from the Evo hub API server
// Uses SSE streaming (/api/stream) for real-time updates, with HTTP polling fallback

import type {
  DashboardData,
  HubStatus,
  DashboardMetrics,
  FailurePattern,
  EvolutionCycle,
  ProposedSkill,
  Experiment,
  ScorePoint,
} from '../types';

const POLL_INTERVAL_MS = 10000; // Fallback polling (only used when SSE is down)

// ---------- API client ----------

async function fetchJson<T>(path: string): Promise<T | null> {
  try {
    const res = await fetch(path, { signal: AbortSignal.timeout(5000) });
    if (!res.ok) return null;
    return (await res.json()) as T;
  } catch {
    return null;
  }
}

// ---------- Data mappers ----------
// The hub API returns data in src/types.ts format. We map it to dashboard types.

async function getHubStatus(): Promise<HubStatus> {
  const raw = await fetchJson<Record<string, unknown>>('/api/status');
  if (raw) {
    const cycle = raw.currentCycle as Record<string, unknown> | undefined;
    return {
      running: raw.running === true,
      phase: (cycle?.status as HubStatus['phase']) ?? (raw.running ? 'idle' : 'idle'),
      cycleCount: (raw.totalCyclesRun as number) ?? 0,
      lastCycleAt: raw.lastCycleAt ? String(raw.lastCycleAt) : null,
      uptimeSeconds: 0,
    };
  }
  return { running: false, phase: 'idle', cycleCount: 0, lastCycleAt: null, uptimeSeconds: 0 };
}

async function getCycles(): Promise<EvolutionCycle[]> {
  const raw = await fetchJson<unknown[]>('/api/cycles');
  if (!Array.isArray(raw)) return [];

  return raw.map((c: unknown, i: number) => {
    const cycle = c as Record<string, unknown>;
    const phases = cycle.phases as Record<string, unknown> | undefined;
    const evalPhase = phases?.evaluate as Record<string, unknown> | undefined;

    return {
      id: String(cycle.id ?? `cycle-${i}`),
      cycleIndex: (cycle.cycleNumber as number) ?? i + 1,
      startedAt: String(cycle.startedAt ?? new Date().toISOString()),
      completedAt: cycle.completedAt ? String(cycle.completedAt) : null,
      phase: String(cycle.status ?? 'completed'),
      status: (cycle.status as EvolutionCycle['status']) ?? 'completed',
      score: evalPhase?.overallScore != null ? Number(evalPhase.overallScore) / 100 : null,
      summary: `Cycle ${(cycle.cycleNumber as number) ?? i + 1}`,
    };
  });
}

async function getSkills(): Promise<ProposedSkill[]> {
  const raw = await fetchJson<unknown[]>('/api/skills');
  if (!Array.isArray(raw)) return [];

  return raw.map((s: unknown) => {
    const skill = s as Record<string, unknown>;
    return {
      id: String(skill.id ?? ''),
      name: String(skill.name ?? ''),
      description: String(skill.description ?? ''),
      confidence: Math.round(((skill.confidence as number) ?? 0) * 100),
      targetFailure: String(skill.targetFailurePattern ?? ''),
      targetFailureId: String(skill.targetFailurePattern ?? ''),
      status: (skill.status as ProposedSkill['status']) ?? 'pending',
      createdAt: String(skill.createdAt ?? new Date().toISOString()),
      filePath: (skill.filePath as string) ?? null,
    };
  });
}

async function getExperiments(): Promise<Experiment[]> {
  const raw = await fetchJson<unknown[]>('/api/experiments');
  if (!Array.isArray(raw)) return [];

  return raw.map((e: unknown) => {
    const exp = e as Record<string, unknown>;
    const control = exp.controlResults as unknown[] | undefined;
    const treatment = exp.treatmentResults as unknown[] | undefined;

    const controlRate = control?.length
      ? control.filter((r: unknown) => (r as Record<string, unknown>).success).length / control.length * 100
      : 0;
    const treatmentRate = treatment?.length
      ? treatment.filter((r: unknown) => (r as Record<string, unknown>).success).length / treatment.length * 100
      : 0;
    const improvement = controlRate > 0 ? ((treatmentRate - controlRate) / controlRate) * 100 : 0;

    return {
      id: String(exp.id ?? ''),
      name: String(exp.name ?? exp.id ?? ''),
      type: 'A/B' as const,
      status: (exp.status as Experiment['status']) ?? 'running',
      startedAt: String(exp.startedAt ?? new Date().toISOString()),
      metrics: {
        control: Math.round(controlRate),
        variant: Math.round(treatmentRate),
        improvement: Math.round(improvement * 10) / 10,
        sampleSize: (control?.length ?? 0) + (treatment?.length ?? 0),
        significance: (exp.confidence as number) ?? 0,
      },
      proposedSkillId: (exp.treatmentSkillId as string) ?? null,
    };
  });
}

async function getFailurePatterns(): Promise<FailurePattern[]> {
  const raw = await fetchJson<unknown[]>('/api/failures');
  if (!Array.isArray(raw)) return [];

  return raw.map((p: unknown) => {
    const pat = p as Record<string, unknown>;
    return {
      id: String(pat.id ?? ''),
      toolName: String(pat.toolName ?? ''),
      errorType: String(pat.errorType ?? ''),
      message: String(pat.errorMessage ?? ''),
      frequency: (pat.frequency as number) ?? 0,
      severity: (pat.severity as FailurePattern['severity']) ?? 'low',
      firstSeen: String(pat.firstSeen ?? ''),
      lastSeen: String(pat.lastSeen ?? ''),
      occurrences: (pat.frequency as number) ?? 0,
    };
  });
}

function buildScoreHistory(cycles: EvolutionCycle[]): ScorePoint[] {
  return cycles
    .filter((c) => c.status === 'completed' && c.score !== null)
    .map((c) => ({
      timestamp: c.completedAt ?? c.startedAt,
      cycleIndex: c.cycleIndex,
      score: Math.round((c.score ?? 0) * 100),
      phase: c.phase,
    }));
}

async function getMetrics(): Promise<DashboardMetrics> {
  const [hub, cycles, skills, experiments, failures] = await Promise.all([
    getHubStatus(),
    getCycles(),
    getSkills(),
    getExperiments(),
    getFailurePatterns(),
  ]);

  const completedCycles = cycles.filter(c => c.status === 'completed' && c.score !== null);
  const overallScore = completedCycles.length > 0
    ? Math.round(completedCycles.reduce((s, c) => s + ((c.score ?? 0) * 100), 0) / completedCycles.length)
    : 0;

  return {
    totalCycles: hub.cycleCount,
    deployedSkills: skills.filter(s => s.status === 'deployed').length,
    activeExperiments: experiments.filter(e => e.status === 'running').length,
    failurePatterns: failures.length,
    overallScore,
    scoreHistory: buildScoreHistory(cycles),
    uptimeSeconds: hub.uptimeSeconds,
  };
}

async function getDashboardData(): Promise<DashboardData> {
  const [hub, metrics, failurePatterns, cycles, proposedSkills, experiments] =
    await Promise.all([
      getHubStatus(),
      getMetrics(),
      getFailurePatterns(),
      getCycles(),
      getSkills(),
      getExperiments(),
    ]);

  return { hub, metrics, failurePatterns, cycles, proposedSkills, experiments };
}

// ---------- SSE streaming with polling fallback ----------

type Listener = (data: DashboardData) => void;

/** Map raw SSE snapshot (server format) to DashboardData (dashboard format). */
function mapSnapshot(raw: Record<string, unknown>): DashboardData {
  const status = raw.status as Record<string, unknown> | undefined;
  const cycles = raw.cycles as unknown[] | undefined;
  const skills = raw.skills as unknown[] | undefined;
  const experiments = raw.experiments as unknown[] | undefined;
  const failures = raw.failures as unknown[] | undefined;

  // Build hub status
  const cycle = status?.currentCycle as Record<string, unknown> | undefined;
  const hub: HubStatus = {
    running: status?.running === true,
    phase: (cycle?.status as HubStatus['phase']) ?? (status?.running ? 'idle' : 'idle'),
    cycleCount: (status?.totalCyclesRun as number) ?? 0,
    lastCycleAt: status?.lastCycleAt ? String(status.lastCycleAt) : null,
    uptimeSeconds: 0,
  };

  // Map cycles
  const mappedCycles: EvolutionCycle[] = Array.isArray(cycles)
    ? cycles.map((c: unknown, i: number) => {
        const cc = c as Record<string, unknown>;
        const phases = cc.phases as Record<string, unknown> | undefined;
        const evalPhase = phases?.evaluate as Record<string, unknown> | undefined;
        return {
          id: String(cc.id ?? `cycle-${i}`),
          cycleIndex: (cc.cycleNumber as number) ?? i + 1,
          startedAt: String(cc.startedAt ?? new Date().toISOString()),
          completedAt: cc.completedAt ? String(cc.completedAt) : null,
          phase: String(cc.status ?? 'completed'),
          status: (cc.status as EvolutionCycle['status']) ?? 'completed',
          score: evalPhase?.overallScore != null ? Number(evalPhase.overallScore) / 100 : null,
          summary: `Cycle ${(cc.cycleNumber as number) ?? i + 1}`,
        };
      })
    : [];

  // Map skills
  const mappedSkills: ProposedSkill[] = Array.isArray(skills)
    ? skills.map((s: unknown) => {
        const sk = s as Record<string, unknown>;
        return {
          id: String(sk.id ?? ''),
          name: String(sk.name ?? ''),
          description: String(sk.description ?? ''),
          confidence: Math.round(((sk.confidence as number) ?? 0) * 100),
          targetFailure: String(sk.targetFailurePattern ?? ''),
          targetFailureId: String(sk.targetFailurePattern ?? ''),
          status: (sk.status as ProposedSkill['status']) ?? 'pending',
          createdAt: String(sk.createdAt ?? new Date().toISOString()),
          filePath: (sk.filePath as string) ?? null,
        };
      })
    : [];

  // Map experiments
  const mappedExperiments: Experiment[] = Array.isArray(experiments)
    ? experiments.map((e: unknown) => {
        const exp = e as Record<string, unknown>;
        const control = exp.controlResults as unknown[] | undefined;
        const treatment = exp.treatmentResults as unknown[] | undefined;
        const controlRate = control?.length
          ? control.filter((r: unknown) => (r as Record<string, unknown>).success).length / control.length * 100
          : 0;
        const treatmentRate = treatment?.length
          ? treatment.filter((r: unknown) => (r as Record<string, unknown>).success).length / treatment.length * 100
          : 0;
        const improvement = controlRate > 0 ? ((treatmentRate - controlRate) / controlRate) * 100 : 0;
        return {
          id: String(exp.id ?? ''),
          name: String(exp.name ?? exp.id ?? ''),
          type: 'A/B' as const,
          status: (exp.status as Experiment['status']) ?? 'running',
          startedAt: String(exp.startedAt ?? new Date().toISOString()),
          metrics: {
            control: Math.round(controlRate),
            variant: Math.round(treatmentRate),
            improvement: Math.round(improvement * 10) / 10,
            sampleSize: (control?.length ?? 0) + (treatment?.length ?? 0),
            significance: (exp.confidence as number) ?? 0,
          },
          proposedSkillId: (exp.treatmentSkillId as string) ?? null,
        };
      })
    : [];

  // Map failure patterns
  const mappedFailures: FailurePattern[] = Array.isArray(failures)
    ? failures.map((p: unknown) => {
        const pat = p as Record<string, unknown>;
        return {
          id: String(pat.id ?? ''),
          toolName: String(pat.toolName ?? ''),
          errorType: String(pat.errorType ?? ''),
          message: String(pat.errorMessage ?? ''),
          frequency: (pat.frequency as number) ?? 0,
          severity: (pat.severity as FailurePattern['severity']) ?? 'low',
          firstSeen: String(pat.firstSeen ?? ''),
          lastSeen: String(pat.lastSeen ?? ''),
          occurrences: (pat.frequency as number) ?? 0,
        };
      })
    : [];

  // Build metrics from the mapped data
  const completedCycles = mappedCycles.filter(c => c.status === 'completed' && c.score !== null);
  const overallScore = completedCycles.length > 0
    ? Math.round(completedCycles.reduce((s, c) => s + ((c.score ?? 0) * 100), 0) / completedCycles.length)
    : 0;

  const metrics: DashboardMetrics = {
    totalCycles: hub.cycleCount,
    deployedSkills: mappedSkills.filter(s => s.status === 'deployed').length,
    activeExperiments: mappedExperiments.filter(e => e.status === 'running').length,
    failurePatterns: mappedFailures.length,
    overallScore,
    scoreHistory: buildScoreHistory(mappedCycles),
    uptimeSeconds: hub.uptimeSeconds,
  };

  return {
    hub,
    metrics,
    failurePatterns: mappedFailures,
    cycles: mappedCycles,
    proposedSkills: mappedSkills,
    experiments: mappedExperiments,
  };
}

function createStreamingClient() {
  let listeners: Listener[] = [];
  let eventSource: EventSource | null = null;
  let fallbackTimer: ReturnType<typeof setTimeout> | null = null;
  let sseConnected = false;

  function notify(data: DashboardData) {
    listeners.forEach((l) => l(data));
  }

  function startFallbackPolling() {
    if (fallbackTimer) return;
    async function poll() {
      try {
        const data = await getDashboardData();
        notify(data);
      } catch {
        // silent
      }
      if (!sseConnected) {
        fallbackTimer = setTimeout(poll, POLL_INTERVAL_MS);
      }
    }
    poll();
  }

  function stopFallbackPolling() {
    if (fallbackTimer) {
      clearTimeout(fallbackTimer);
      fallbackTimer = null;
    }
  }

  function connectSSE() {
    if (eventSource) return;

    const es = new EventSource('/api/stream');
    eventSource = es;

    es.addEventListener('dashboard', (e: MessageEvent) => {
      try {
        const raw = JSON.parse(e.data) as Record<string, unknown>;
        const data = mapSnapshot(raw);
        notify(data);
      } catch {
        // Malformed event — skip
      }
    });

    es.onopen = () => {
      sseConnected = true;
      stopFallbackPolling();
    };

    es.onerror = () => {
      sseConnected = false;
      // EventSource auto-reconnects. Start fallback polling in the meantime.
      startFallbackPolling();
    };
  }

  function disconnectSSE() {
    if (eventSource) {
      eventSource.close();
      eventSource = null;
    }
    sseConnected = false;
  }

  return {
    start() {
      connectSSE();
      // Also fire one immediate poll so UI isn't blank while SSE connects
      getDashboardData().then(notify).catch(() => {});
    },
    stop() {
      disconnectSSE();
      stopFallbackPolling();
    },
    subscribe(listener: Listener): () => void {
      listeners.push(listener);
      return () => {
        listeners = listeners.filter((l) => l !== listener);
      };
    },
    refresh() {
      return getDashboardData();
    },
  };
}

export const evoClient = {
  getHubStatus,
  getMetrics,
  getDashboardData,
  getFailurePatterns,
  getCycles,
  getProposedSkills: getSkills,
  getExperiments,
  approveSkill: async (id: string): Promise<void> => {
    await fetch(`/api/approvals/${id}/approve`, { method: 'POST', signal: AbortSignal.timeout(5000) });
  },
  rejectSkill: async (id: string): Promise<void> => {
    await fetch(`/api/approvals/${id}/reject`, { method: 'POST', signal: AbortSignal.timeout(5000) });
  },
  triggerEvolve: async (): Promise<boolean> => {
    try {
      const res = await fetch('/api/evolve', { method: 'POST', signal: AbortSignal.timeout(60000) });
      return res.ok;
    } catch {
      return false;
    }
  },
  polling: createStreamingClient(),
};
