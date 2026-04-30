// Build the system prompt: CLAUDE.md verbatim + an appended skill catalog
// so the LLM knows which skills it can `read_skill` on.

import type { SkillMeta } from "./skills.js";

export function buildSystemPrompt(claudeMd: string, skills: SkillMeta[]): string {
  const catalog = skills.map((s) => `- \`${s.name}\`: ${s.description}`).join("\n");
  return `${claudeMd.trim()}

---

## Skill Catalog (call the \`read_skill\` tool with the listed name to load)

${catalog}

## Tool Use Protocol

- Invoke tools via standard function-calling — no special tags needed. Emit multiple tool_calls in one response when they're independent (e.g. load several skills in parallel, or probe several topologies in parallel).
- When you have sufficient context, stop calling tools and output your final answer as normal assistant content.
- Final answer MUST be exactly one valid JSON object following the JSON-LD contract in the Output Format section above. Do not use Markdown fences.

### Be proactive, not ping-pong

Before you ask the user anything, **exhaust the tools you already have**. A clarifying question costs the user a round-trip; extra tool calls cost only a few hundred tokens. Default to tools.

Concrete grounding procedure:
1. \`list_topologies\` to see what exists.
2. Call \`resolve_target(topology, hint)\` **on every topology in parallel** for each NL entity reference. This is cheap — one tool_call per topology, fire them all at once.
3. Count plausible matches across all topologies:
   - **Exactly one topology returns a match** → ground there. Use that service ID in \`expectationObject.id\`.
   - **Multiple topologies match** → ask one clarifying question naming the specific candidates.
   - **Zero matches across all topologies** → ask one clarifying question, or suggest the NL may reference a service this network doesn't have.
4. Only ask the user when step 3 genuinely requires human disambiguation. Never ask just because you didn't bother to probe.

Start by loading \`tio-intent-common-model\` via \`read_skill\` in parallel with any other skills you expect to need and any \`list_topologies\` / \`resolve_target\` calls — kick off everything that's independent in the same turn.

### Validate before finalizing (mandatory)

Every JSON-LD payload you produce MUST pass \`validate_jsonld\` before you present it to the user. Workflow:

1. Draft the JSON-LD mentally or in a scratch variable.
2. Call \`validate_jsonld\` with the JSON text.
3. If the report has \`errors\`, read each one, fix your JSON-LD, and call \`validate_jsonld\` again.
4. Iterate until \`ok: true\`, then output the final JSON object.

You do not need to mention the validation loop to the user; just show them clean JSON-LD.
`;
}
