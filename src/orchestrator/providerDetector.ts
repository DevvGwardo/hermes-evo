/**
 * orchestrator/providerDetector.js
 *
 * Detects which AI providers are available based on environment variables
 * and API key presence. Used by the fallback chain resolver to build the
 * best possible model config from whatever keys the user actually has.
 */

export interface ProviderAvailability {
  native: {
    claude: boolean;
    openai: boolean;
    gemini: boolean;
  };
  opencodeZen: boolean;
  copilot: boolean;
  zai: boolean;
  kimiForCoding: boolean;
  opencodeGo: boolean;
  isMaxPlan: boolean;
}

function envHas(key: string): boolean {
  const val = process.env[key];
  return val !== undefined && val !== '' && val !== 'false';
}

/** Check if a generic/proxied provider has its key set. */
export function genericProviderHas(provider: string): boolean {
  const key = PROVIDER_KEY_MAP[provider];
  if (!key) return false;
  return envHas(key);
}

const PROVIDER_KEY_MAP: Record<string, string> = {
  opencode: 'OPENCODE_API_KEY',
  opencodeZen: 'OPENCODE_ZEN_API_KEY',
  venice: 'VENICE_API_KEY',
  moonshotai: 'MOONSHOT_API_KEY',
  'moonshotai-cn': 'MOONSHOT_API_KEY',
  xai: 'XAI_API_KEY',
  firmware: 'FIRMWARE_API_KEY',
  'ollama-cloud': 'OLLAMA_CLOUD_API_KEY',
  aihubmix: 'AIHUBMIX_API_KEY',
};

export function detectProviders(): ProviderAvailability {
  return {
    native: {
      claude: envHas('ANTHROPIC_API_KEY'),
      openai: envHas('OPENAI_API_KEY'),
      gemini: envHas('GEMINI_API_KEY') || envHas('GOOGLE_API_KEY'),
    },
    opencodeZen: envHas('OPENCODE_ZEN_API_KEY'),
    copilot: envHas('GITHUB_COPILOT_API_KEY') || envHas('COPILOT_API_KEY'),
    zai: envHas('ZAI_API_KEY'),
    kimiForCoding: envHas('KIMI_FOR_CODING_API_KEY') || envHas('KIMI_API_KEY'),
    opencodeGo: envHas('OPENCODE_GO_API_KEY'),
    // Max plan = has at least 2 native providers or a premium key
    isMaxPlan: (
      (envHas('ANTHROPIC_API_KEY') && envHas('OPENAI_API_KEY')) ||
      envHas('OPENCODE_ZEN_API_KEY') ||
      envHas('ZAI_API_KEY')
    ),
  };
}

export function summarizeProviders(avail: ProviderAvailability): string {
  const active: string[] = [];
  if (avail.native.claude) active.push('Claude');
  if (avail.native.openai) active.push('OpenAI');
  if (avail.native.gemini) active.push('Gemini');
  if (avail.opencodeZen) active.push('OpenCode Zen');
  if (avail.copilot) active.push('GitHub Copilot');
  if (avail.zai) active.push('ZAI');
  if (avail.kimiForCoding) active.push('Kimi');
  if (avail.opencodeGo) active.push('OpenCode Go');
  return active.length === 0
    ? 'No providers detected'
    : active.join(', ');
}
