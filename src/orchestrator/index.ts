/**
 * orchestrator/index.js
 *
 * Re-exports the full orchestrator API.
 */

export { detectProviders, summarizeProviders } from './providerDetector.js';
export type { ProviderAvailability } from './providerDetector.js';

export {
  AGENT_REQUIREMENTS,
  CATEGORY_REQUIREMENTS,
  resolveAgentModel,
  resolveCategoryModel,
  buildAgentConfig,
} from './fallbackChain.js';
export type { FallbackEntry, ResolvedModel, ModelRequirement } from './fallbackChain.js';

export {
  HookRegistry,
  buildHookRegistry,
  createCoreHooks,
  createContinuationHooks,
  createSkillHooks,
} from './hookSystem.js';
export type { HookContext, HookResult, Hook, HookFn } from './hookSystem.js';

export { ultrawork, ultraworkHelp } from './ultrawork.js';
export type { UltraworkResult, UltraworkOptions, TaskCategory } from './ultrawork.js';
