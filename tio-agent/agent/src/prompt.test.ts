import { describe, expect, test } from "bun:test";

import { buildSystemPrompt } from "./prompt.js";

describe("buildSystemPrompt", () => {
  test("keeps JSON-LD final output higher priority than TTL-derived skills", () => {
    const prompt = buildSystemPrompt("## Output Format\nJSON-LD only", [
      {
        name: "tio-intent-common-model",
        description: "Turtle-derived vocabulary is reference only.",
        file: "/tmp/tio-intent-common-model/SKILL.md",
      },
    ]);

    expect(prompt).toContain("Final answers are API-friendly TIO JSON-LD payloads only");
    expect(prompt).toContain("Turtle-derived prefix names or ontology snippets");
    expect(prompt).toContain("validate_ttl` is legacy/debug-only");
    expect(prompt).toContain("validate final payloads with `validate_jsonld`");
  });

  test("specializes the agent to enterprise VPN SLA intents only", () => {
    const prompt = buildSystemPrompt("## Role\nEnterprise VPN SLA only", []);

    expect(prompt).toContain("Enterprise VPN SLA");
    expect(prompt).toContain("tio-enterprise-vpn-sla");
    expect(prompt).toContain("evsla:HubAndSpokeTopology");
    expect(prompt).toContain("Do not translate non-Enterprise-VPN-SLA intents");
  });

  test("asks the model to keep enterprise VPN SLA payloads structurally grouped", () => {
    const prompt = buildSystemPrompt("## Role\nEnterprise VPN SLA only", []);

    expect(prompt).toContain("Stable JSON Structure");
    expect(prompt).toContain("tenant");
    expect(prompt).toContain("expectationObject");
    expect(prompt).toContain("intentContext");
  });
});
