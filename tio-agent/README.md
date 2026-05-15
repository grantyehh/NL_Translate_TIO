# tio-agent

Enterprise VPN hub-and-spoke SLA 自然語言 -> **API-friendly TIO JSON-LD** 的 agent PoC。

它用自製 OpenAI-compatible agent loop 接 MCP（fake Enterprise VPN SLA network environment + TIO JSON-LD validator）與 local skills（TIO/EVSLA ontology 摘要），把模糊中文/英文企業 VPN SLA 意圖轉成可送往下游 intent API / compiler 的 JSON-LD payload。

這個 agent 現在專門處理 Enterprise VPN hub-and-spoke SLA，不再負責 5G slice、datacenter fabric、一般 traffic class 或其他 intent translation。

```text
「確保星河銀行總部至所有分點之延遲在95%的時間內低於50ms」
                   |
                   v
        agent CLI + OpenAI tool loop
          |        |          |
     read_skill  network-env  tio-validator
          |        |          |
  TIO/EVSLA skills  fake EVSLA topology validate_jsonld
                   |
                   v
      clean Enterprise VPN SLA TIO JSON-LD payload
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
  "id": "intent-星河銀行-latency-001",
  "name": "Enterprise VPN Hub-Spoke SLA Intent",
  "description": "Ensure 星河銀行 hub-to-spoke latency stays below 50 ms for 95 percent of the time.",
  "intentOwner": {
    "id": "ops-manager-01",
    "name": "Network Operations Center"
  },
  "tenant": {
    "id": "tenant-星河銀行",
    "name": "星河銀行",
    "@type": "evsla:Tenant"
  },
  "intentExpectation": [
    {
      "id": "exp-latency-01",
      "name": "Hub-to-Spoke Latency SLA Expectation",
      "description": "Hub-to-spoke latency must stay below 50 ms for 95 percent of the time.",
      "@type": "PropertyExpectation",
      "ontologyType": "evsla:SlaExpectation",
      "expectationObject": {
        "id": "svc:星河銀行-enterprise-vpn",
        "name": "星河銀行 Enterprise VPN Service",
        "@type": "Service",
        "ontologyType": "evsla:EnterpriseVpnService"
      },
      "expectationTarget": [
        {
          "name": "Hub-to-Spoke Latency",
          "targetProperty": "evsla:latency",
          "matchCondition": "LESS_THAN",
          "targetValue": {
            "value": 50,
            "unit": "ms",
            "@type": "quan:Quantity"
          },
          "evsla:hasMetric": "evsla:latency",
          "evsla:hasThreshold": {
            "value": 50,
            "unit": "ms",
            "@type": "quan:Quantity"
          },
          "evsla:hasStatistic": "evsla:p95",
          "evsla:hasScope": "evsla:hubToAllSpokes",
          "evsla:hasMeasurementMethod": "evsla:twamp",
          "evsla:hasTimeWindow": "evsla:fiveMinuteWindow"
        }
      ]
    }
  ],
  "intentContext": [
    {
      "id": "topology-星河銀行-hub-spoke",
      "@type": "Context",
      "name": "Hub-and-Spoke Topology",
      "evsla:hasHub": {
        "@type": "evsla:HubSite",
        "name": "台北總部"
      },
      "evsla:hasSpoke": [
        {
          "@type": "evsla:SpokeSite",
          "name": "新竹分行"
        },
        {
          "@type": "evsla:SpokeSite",
          "name": "台中分行"
        },
        {
          "@type": "evsla:SpokeSite",
          "name": "高雄分行"
        }
      ],
      "ontologyType": "evsla:HubAndSpokeTopology"
    }
  ],
  "intentReport": {
    "reportingInterval": "PT5M",
    "handlerResponse": "Continuous"
  },
  "ontologyType": "evsla:EnterpriseVpnSlaIntent"
}
```

## Main Pieces

- `agent/src/index.ts`: CLI, OpenAI client, MCP startup, tool registration.
- `agent/src/agent.ts`: hand-written tool-call loop.
- `agent/src/prompt.ts`: combines `CLAUDE.md` with the skill catalog and tool protocol.
- `skills/tio-*`: generated TIO/EVSLA module skills from `ttls/`.
- `mcps/network-env`: fake Enterprise VPN SLA hub-and-spoke topology and service target resolver.
- `mcps/tio-validator`: exposes `validate_jsonld` for the API payload contract with Enterprise VPN SLA checks, and keeps `validate_ttl` for legacy/debug use.

## Notes

- `ttls/` is still the ontology source of truth for skill generation and legacy validation, including `EnterpriseVpnSlaOntology.ttl`.
- `scripts/ttl-to-skills.ts` still regenerates the `skills/tio-*` knowledge files from ontology TTL files.
- The JSON-LD validator is intentionally a payload contract validator, not a full RDF JSON-LD expansion engine.
