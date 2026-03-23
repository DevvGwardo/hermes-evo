import { failureCorpus } from './src/memory/failureCorpus.js';
import { generateFromFailure } from './src/builder/skillGenerator.js';
import { validate } from './src/builder/skillValidator.js';
import { readFileSync, readdirSync } from 'node:fs';
import { join } from 'node:path';

const HOME = process.env.HOME;
const deployedSkillNames = new Set();
const skillDir = join(HOME!, '.openclaw/skills/');
for (const entry of readdirSync(skillDir)) {
  if (entry.startsWith('.') || ['clawbert','moltsland'].includes(entry)) continue;
  try {
    const content = readFileSync(join(skillDir, entry, 'SKILL.md'), 'utf-8');
    const match = content.match(/^#\s+(.+)/);
    if (match) deployedSkillNames.add(match[1].trim());
  } catch {}
}
console.log('Deployed:', [...deployedSkillNames]);

const patterns = await failureCorpus.getPatterns(1);
console.log('Patterns:', patterns.map(p => p.toolName + '/' + p.errorType));

const candidates: {p: typeof patterns[number]; result: ReturnType<typeof generateFromFailure>}[] = [];
for (const p of patterns) {
  const result = generateFromFailure(p);
  if (!result.skill) { console.log('No skill for', p.toolName); continue; }
  if (deployedSkillNames.has(result.skill.name)) { console.log('Already deployed:', result.skill.name); continue; }
  candidates.push({p, result});
}
console.log('Candidates:', candidates.map(c => c.p.toolName + '/' + c.p.errorType));
console.log('Count:', candidates.length);
