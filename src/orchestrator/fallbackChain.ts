/**
 * orchestrator/fallbackChain.js
 *
 * Multi-model fallback chain system inspired by OMO.
 * Each agent role has an ordered list of (provider, model) pairs.
 * The resolver walks the chain and returns the first available option.
 *
 * Roles:
 *   sisyphus   — primary coding agent (task-complete loop)
 *   hephaestus — code editing / modification
 *   oracle     — reasoning / analysis
 *   librarian  — fast context / file lookup
 *   explore    — exploration / search
 *   prometheus — planning / architecture
 *   metis      — strategy / high-level reasoning
 *   atlas      — context management
 */

import type { ProviderAvailability } from './providerDetector.js';
import { genericProviderHas } from './providerDetector.js';

export interface FallbackEntry {
  providers: string[];
  model: string;
  variant?: string; // e.g. 'max', 'high', 'medium'
}

export interface ResolvedModel {
  model: string;
  variant?: string;
  provider: string;
}

export interface ModelRequirement {
  fallbackChain: FallbackEntry[];
  variant?: string;
  requiresModel?: string;
  requiresAnyModel?: boolean;
  requiresProvider?: string[];
}

// ── Agent role requirements ──────────────────────────────────────────────────

export const AGENT_REQUIREMENTS: Record<string, ModelRequirement> = {
  sisyphus: {
    fallbackChain: [
      { providers: ['anthropic', 'github-copilot', 'opencode'], model: 'claude-opus-4-6', variant: 'max' },
      { providers: ['opencode-go'], model: 'kimi-k2.5' },
      { providers: ['kimi-for-coding'], model: 'k2p5' },
      { providers: ['opencode', 'moonshotai', 'moonshotai-cn'], model: 'kimi-k2.5' },
      { providers: ['openai', 'github-copilot', 'opencode'], model: 'gpt-5.4', variant: 'medium' },
      { providers: ['zai-coding-plan', 'opencode'], model: 'glm-5' },
      { providers: ['opencode'], model: 'big-pickle' },
    ],
    requiresAnyModel: true,
  },
  hephaestus: {
    fallbackChain: [
      { providers: ['openai', 'github-copilot', 'venice', 'opencode'], model: 'gpt-5.4', variant: 'medium' },
    ],
    requiresProvider: ['openai', 'github-copilot', 'venice', 'opencode'],
  },
  oracle: {
    fallbackChain: [
      { providers: ['openai', 'github-copilot', 'opencode'], model: 'gpt-5.4', variant: 'high' },
      { providers: ['google', 'github-copilot', 'opencode'], model: 'gemini-3.1-pro', variant: 'high' },
      { providers: ['anthropic', 'github-copilot', 'opencode'], model: 'claude-opus-4-6', variant: 'max' },
      { providers: ['opencode-go'], model: 'glm-5' },
    ],
  },
  librarian: {
    fallbackChain: [
      { providers: ['opencode-go'], model: 'minimax-m2.7' },
      { providers: ['opencode'], model: 'minimax-m2.7-highspeed' },
      { providers: ['anthropic', 'opencode'], model: 'claude-haiku-4-5' },
      { providers: ['opencode'], model: 'gpt-5-nano' },
    ],
  },
  explore: {
    fallbackChain: [
      { providers: ['github-copilot', 'xai'], model: 'grok-code-fast-1' },
      { providers: ['opencode-go'], model: 'minimax-m2.7-highspeed' },
      { providers: ['opencode'], model: 'minimax-m2.7' },
      { providers: ['anthropic', 'opencode'], model: 'claude-haiku-4-5' },
      { providers: ['opencode'], model: 'gpt-5-nano' },
    ],
  },
  prometheus: {
    fallbackChain: [
      { providers: ['anthropic', 'github-copilot', 'opencode'], model: 'claude-opus-4-6', variant: 'max' },
      { providers: ['openai', 'github-copilot', 'opencode'], model: 'gpt-5.4', variant: 'high' },
      { providers: ['opencode-go'], model: 'glm-5' },
      { providers: ['google', 'github-copilot', 'opencode'], model: 'gemini-3.1-pro' },
    ],
  },
  metis: {
    fallbackChain: [
      { providers: ['anthropic', 'github-copilot', 'opencode'], model: 'claude-opus-4-6', variant: 'max' },
      { providers: ['openai', 'github-copilot', 'opencode'], model: 'gpt-5.4', variant: 'high' },
      { providers: ['opencode-go'], model: 'glm-5' },
      { providers: ['kimi-for-coding'], model: 'k2p5' },
    ],
  },
  atlas: {
    fallbackChain: [
      { providers: ['anthropic', 'github-copilot', 'opencode'], model: 'claude-sonnet-4-6' },
      { providers: ['opencode-go'], model: 'kimi-k2.5' },
      { providers: ['openai', 'github-copilot', 'opencode'], model: 'gpt-5.4', variant: 'medium' },
      { providers: ['opencode-go'], model: 'minimax-m2.7' },
    ],
  },
};

// ── Category requirements (task difficulty tiers) ─────────────────────────────

export const CATEGORY_REQUIREMENTS: Record<string, ModelRequirement> = {
  'visual-engineering': {
    fallbackChain: [
      { providers: ['google', 'github-copilot', 'opencode'], model: 'gemini-3.1-pro', variant: 'high' },
      { providers: ['zai-coding-plan', 'opencode'], model: 'glm-5' },
      { providers: ['anthropic', 'github-copilot', 'opencode'], model: 'claude-opus-4-6', variant: 'max' },
    ],
  },
  ultrabrain: {
    fallbackChain: [
      { providers: ['openai', 'opencode'], model: 'gpt-5.4', variant: 'xhigh' },
      { providers: ['google', 'github-copilot', 'opencode'], model: 'gemini-3.1-pro', variant: 'high' },
      { providers: ['anthropic', 'github-copilot', 'opencode'], model: 'claude-opus-4-6', variant: 'max' },
    ],
  },
  deep: {
    fallbackChain: [
      { providers: ['openai', 'github-copilot', 'venice', 'opencode'], model: 'gpt-5.4', variant: 'medium' },
      { providers: ['anthropic', 'github-copilot', 'opencode'], model: 'claude-opus-4-6', variant: 'max' },
    ],
  },
  quick: {
    fallbackChain: [
      { providers: ['openai', 'github-copilot', 'opencode'], model: 'gpt-5.4-mini' },
      { providers: ['anthropic', 'github-copilot', 'opencode'], model: 'claude-haiku-4-5' },
      { providers: ['google', 'github-copilot', 'opencode'], model: 'gemini-3-flash' },
      { providers: ['opencode-go'], model: 'minimax-m2.7' },
    ],
  },
  'unspecified-low': {
    fallbackChain: [
      { providers: ['anthropic', 'github-copilot', 'opencode'], model: 'claude-sonnet-4-6' },
      { providers: ['openai', 'opencode'], model: 'gpt-5.3-codex', variant: 'medium' },
      { providers: ['opencode-go'], model: 'kimi-k2.5' },
      { providers: ['google', 'github-copilot', 'opencode'], model: 'gemini-3-flash' },
    ],
  },
  'unspecified-high': {
    fallbackChain: [
      { providers: ['anthropic', 'github-copilot', 'opencode'], model: 'claude-opus-4-6', variant: 'max' },
      { providers: ['openai', 'github-copilot', 'opencode'], model: 'gpt-5.4', variant: 'high' },
      { providers: ['zai-coding-plan', 'opencode'], model: 'glm-5' },
      { providers: ['kimi-for-coding'], model: 'k2p5' },
    ],
  },
};

// ── Resolution ────────────────────────────────────────────────────────────────

function providerIsAvailable(provider: string, avail: ProviderAvailability): boolean {
  switch (provider) {
    case 'anthropic':    return avail.native.claude;
    case 'openai':       return avail.native.openai;
    case 'google':       return avail.native.gemini;
    case 'opencodeZen':  return avail.opencodeZen;
    case 'github-copilot': return avail.copilot;
    case 'zai-coding-plan': return avail.zai;
    case 'kimi-for-coding': return avail.kimiForCoding;
    case 'opencodeGo':
    case 'opencode-go':  return avail.opencodeGo;
    // Generic/proxied providers — only available if their env key is set
    case 'opencode':
    case 'venice':
    case 'moonshotai':
    case 'moonshotai-cn':
    case 'xai':
    case 'firmware':
    case 'ollama-cloud':
    case 'aihubmix':
      return genericProviderHas(provider);
    default:
      return false;
  }
}

function anyProviderAvailable(providers: string[], avail: ProviderAvailability): boolean {
  return providers.some(p => providerIsAvailable(p, avail));
}

export function resolveModelFromChain(
  chain: FallbackEntry[],
  avail: ProviderAvailability,
): ResolvedModel | null {
  for (const entry of chain) {
    const activeProvider = entry.providers.find(p => providerIsAvailable(p, avail));
    if (activeProvider) {
      return {
        model: entry.model,
        variant: entry.variant,
        provider: activeProvider,
      };
    }
  }
  return null;
}

export function resolveAgentModel(
  role: string,
  avail: ProviderAvailability,
): ResolvedModel | null {
  const req = AGENT_REQUIREMENTS[role];
  if (!req) return null;

  // requiresAnyModel: at least ONE entry in the chain must be available
  if (req.requiresAnyModel && !req.fallbackChain.some(e => anyProviderAvailable(e.providers, avail))) {
    return null;
  }

  // requiresProvider: any of these must be available
  if (req.requiresProvider && !req.requiresProvider.some(p => providerIsAvailable(p, avail))) {
    return null;
  }

  const resolved = resolveModelFromChain(req.fallbackChain, avail);
  if (!resolved && req.requiresAnyModel) return null;

  return resolved ?? {
    model: 'opencode/gpt-5-nano',
    variant: undefined,
    provider: 'opencode',
  };
}

export function resolveCategoryModel(
  category: string,
  avail: ProviderAvailability,
  isMaxPlan: boolean,
): ResolvedModel | null {
  let req = CATEGORY_REQUIREMENTS[category];
  if (!req) return null;

  // Downgrade unspecified-high to unspecified-low on non-max plans
  if (category === 'unspecified-high' && !isMaxPlan) {
    req = CATEGORY_REQUIREMENTS['unspecified-low'] ?? req;
  }

  const resolved = resolveModelFromChain(req.fallbackChain, avail);
  return resolved ?? {
    model: 'opencode/gpt-5-nano',
    variant: undefined,
    provider: 'opencode',
  };
}

export function buildAgentConfig(avail: ProviderAvailability): Record<string, ResolvedModel> {
  const config: Record<string, ResolvedModel> = {};

  for (const role of Object.keys(AGENT_REQUIREMENTS)) {
    const resolved = resolveAgentModel(role, avail);
    if (resolved) {
      config[role] = resolved;
    }
  }

  return config;
}
