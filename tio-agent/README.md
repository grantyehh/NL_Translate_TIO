# tio-agent

自然語言 -> **API-friendly TIO JSON-LD** 的 agent PoC。

它用自製 OpenAI-compatible agent loop 接 MCP（fake network environment + TIO JSON-LD validator）與 local skills（TIO ontology 摘要），把模糊中文/英文網路意圖轉成可送往下游 intent API / compiler 的 JSON-LD payload。

```text
「確保視訊會議流量的延遲低於 20ms」
                   |
                   v
        agent CLI + OpenAI tool loop
          |        |          |
     read_skill  network-env  tio-validator
          |        |          |
     TIO skills  fake topology validate_jsonld
                   |
                   v
          clean TIO JSON-LD payload
```

## Quick Start

```bash
cd tio-agent
bun install
OPENAI_API_KEY=sk-... bun run agent
```

REPL 指令：`/reset` 清對話、`/exit` 離開。

## Output Shape

Agent 最終輸出是純 JSON，不含 Markdown fence：

```json
{
  "@context": "https://tmforum.org/schemas/intent-ontology/v1.jsonld",
  "@type": "Intent",
  "id": "intent-video-conf-001",
  "name": "Video Conferencing Latency Intent",
  "description": "Ensure video conferencing traffic latency stays below 20 ms.",
  "intentOwner": {
    "id": "ops-manager-01",
    "name": "Network Operations Center"
  },
  "intentExpectation": [
    {
      "id": "exp-latency-01",
      "name": "Latency Expectation",
      "description": "The end-to-end latency must be kept below 20 ms.",
      "@type": "PropertyExpectation",
      "expectationObject": {
        "id": "svc:video-conf-traffic",
        "name": "Video conferencing traffic class",
        "@type": "Service",
        "topology": "enterprise-backup-taipei"
      },
      "expectationTarget": [
        {
          "name": "End-to-End Latency",
          "targetProperty": "latency",
          "matchCondition": "LESS_THAN",
          "targetValue": {
            "value": 20,
            "unit": "ms"
          }
        }
      ]
    }
  ],
  "intentContext": [],
  "intentReport": {
    "reportingInterval": "PT5M",
    "handlerResponse": "Continuous"
  }
}
```

## Main Pieces

- `agent/src/index.ts`: CLI, OpenAI client, MCP startup, tool registration.
- `agent/src/agent.ts`: hand-written tool-call loop.
- `agent/src/prompt.ts`: combines `CLAUDE.md` with the skill catalog and tool protocol.
- `skills/tio-*`: generated TIO module skills from `ttls/`.
- `mcps/network-env`: fake topology and service target resolver.
- `mcps/tio-validator`: exposes `validate_jsonld` for the API payload contract, and keeps `validate_ttl` for legacy/debug use.

## Notes

- `ttls/` is still the ontology source of truth for skill generation and legacy validation.
- `scripts/ttl-to-skills.ts` still regenerates the `skills/tio-*` knowledge files from ontology TTL files.
- The JSON-LD validator is intentionally a payload contract validator, not a full RDF JSON-LD expansion engine.
