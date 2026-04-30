// Local skills as LLM tools. The catalog (name + description from frontmatter)
// is cheap and goes straight into the system prompt; full SKILL.md is loaded
// on demand through the read_skill tool (progressive disclosure).

import * as fs from "node:fs";
import * as path from "node:path";

export interface SkillMeta {
  name: string;
  description: string;
  file: string;
}

export function listSkills(skillsDir: string): SkillMeta[] {
  if (!fs.existsSync(skillsDir)) return [];
  const out: SkillMeta[] = [];
  for (const entry of fs.readdirSync(skillsDir)) {
    const dir = path.join(skillsDir, entry);
    const file = path.join(dir, "SKILL.md");
    if (!fs.existsSync(file)) continue;
    const text = fs.readFileSync(file, "utf-8");
    const fm = parseFrontmatter(text);
    if (fm?.name && fm?.description) {
      out.push({ name: fm.name, description: fm.description, file });
    }
  }
  return out.sort((a, b) => a.name.localeCompare(b.name));
}

export function readSkill(skillsDir: string, name: string): string {
  const file = path.join(skillsDir, name, "SKILL.md");
  if (!fs.existsSync(file)) throw new Error(`skill not found: ${name}`);
  return fs.readFileSync(file, "utf-8");
}

function parseFrontmatter(text: string): Record<string, string> | null {
  const m = text.match(/^---\n([\s\S]*?)\n---/);
  if (!m) return null;
  const obj: Record<string, string> = {};
  for (const line of m[1].split("\n")) {
    const idx = line.indexOf(":");
    if (idx < 0) continue;
    const key = line.slice(0, idx).trim();
    const val = line.slice(idx + 1).trim();
    obj[key] = val;
  }
  return obj;
}
