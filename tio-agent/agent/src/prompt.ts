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

## Output Format Priority

- Final answers are API-friendly TIO JSON-LD payloads only. Never output Turtle, RDF triples, TTL code fences, or a Turtle conversion.
- Loaded \`tio-*\` skills may contain Turtle-derived prefix names or ontology snippets because the source ontology is TTL. Treat those only as vocabulary references and map the relevant semantics into the JSON-LD contract in \`CLAUDE.md\`.
- \`validate_ttl\` is legacy/debug-only. Do not call it for final answers; validate final payloads with \`validate_jsonld\`.

## Enterprise VPN SLA Specialization

- This agent is dedicated to Enterprise VPN SLA intents only. Do not translate non-Enterprise-VPN-SLA intents.
- Always load \`tio-intent-common-model\`, \`tio-enterprise-vpn-sla\`, \`tio-quantity\`, and \`tio-metrics-observations\` for valid Enterprise VPN SLA requests.
- Final JSON-LD should preserve \`evsla:EnterpriseVpnSlaIntent\`, \`evsla:EnterpriseVpnService\`, \`evsla:Tenant\`, \`evsla:HubAndSpokeTopology\`, \`evsla:HubSite\`, \`evsla:SpokeSite\`, and \`evsla:SlaExpectation\` using API-friendly JSON fields.
- SLA target properties should use \`evsla:latency\`, \`evsla:packetLoss\`, or \`evsla:guaranteedBandwidth\` when applicable.
- Include \`evsla:hasMetric\`, \`evsla:hasThreshold\`, \`evsla:hasStatistic\`, \`evsla:hasScope\`, \`evsla:hasMeasurementMethod\`, and \`evsla:hasTimeWindow\` on each expectation target.

## Stable JSON Structure

Keep final payloads structurally grouped and consistently ordered:

1. Intent metadata: \`@context\`, \`@type\`, \`id\`, \`name\`, \`description\`, \`ontologyType\`.
2. Ownership and customer: \`intentOwner\`, then \`tenant\`.
3. SLA requirements: \`intentExpectation\`; inside each expectation, keep \`expectationObject\` before \`expectationTarget\`.
4. Topology scope: \`intentContext\` with \`evsla:HubAndSpokeTopology\`, \`evsla:hasHub\`, and \`evsla:hasSpoke\`.
5. Reporting: \`intentReport\`.

Inside each \`expectationTarget\`, group the API comparison fields first (\`name\`, \`targetProperty\`, \`matchCondition\`, \`targetValue\`), then the EVSLA semantic fields (\`evsla:hasMetric\`, \`evsla:hasThreshold\`, \`evsla:hasStatistic\`, \`evsla:hasScope\`, \`evsla:hasMeasurementMethod\`, \`evsla:hasTimeWindow\`).

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

Start by loading \`tio-intent-common-model\`, \`tio-enterprise-vpn-sla\`, \`tio-quantity\`, and \`tio-metrics-observations\` via \`read_skill\` in parallel with any \`list_topologies\` / \`resolve_target\` calls — kick off everything that's independent in the same turn.

### Validate before finalizing (mandatory)

Every JSON-LD payload you produce MUST pass \`validate_jsonld\` before you present it to the user. Workflow:

1. Draft the JSON-LD mentally or in a scratch variable.
2. Call \`validate_jsonld\` with the JSON text.
3. If the report has \`errors\`, read each one, fix your JSON-LD, and call \`validate_jsonld\` again.
4. Iterate until \`ok: true\`, then output the final JSON object.

You do not need to mention the validation loop to the user; just show them clean JSON-LD.
`;
}
