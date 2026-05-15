#!/usr/bin/env bun
// network-env MCP server (fake Enterprise VPN SLA PoC data).
// Tools: list_topologies, describe_topology, list_service_targets,
//        resolve_target, get_live_metrics.

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";
import { topologies, resolveTarget, fakeMetrics } from "./topologies.js";

const server = new McpServer({
  name: "enterprise-vpn-sla-env-fake",
  version: "0.1.0",
});

const asJson = (data: unknown) => ({
  content: [{ type: "text" as const, text: JSON.stringify(data, null, 2) }],
});

const asError = (msg: string) => ({
  content: [{ type: "text" as const, text: msg }],
  isError: true,
});

server.tool(
  "list_topologies",
  "List every known Enterprise VPN SLA topology (fake PoC data). Returns name, description, and service_count.",
  {},
  async () =>
    asJson(
      Object.values(topologies).map((t) => ({
        name: t.name,
        description: t.description,
        service_count: t.services.length,
      }))
    )
);

server.tool(
  "describe_topology",
  "Return the full Enterprise VPN SLA topology: hub/spoke sites, links, tenant services, and supported metrics.",
  { name: z.string().describe("topology name as returned by list_topologies") },
  async ({ name }) => {
    const t = topologies[name];
    if (!t) return asError(`unknown topology: ${name}`);
    return asJson(t);
  }
);

server.tool(
  "list_service_targets",
  "List Enterprise VPN service targets in a topology — these are the concrete IDs you can bind an SLA expectation to.",
  { topology: z.string() },
  async ({ topology }) => {
    const t = topologies[topology];
    if (!t) return asError(`unknown topology: ${topology}`);
    return asJson(t.services);
  }
);

server.tool(
  "resolve_target",
  "Given an Enterprise VPN SLA hint (e.g. '星河銀行總部至所有分點'), return candidate tenant VPN service targets in a topology.",
  {
    topology: z.string(),
    hint: z.string().describe("natural-language fragment to match against service names/types/attrs"),
  },
  async ({ topology, hint }) => asJson(resolveTarget(topology, hint))
);

server.tool(
  "get_live_metrics",
  "Return current (fake) Enterprise VPN SLA metrics — latency_ms, throughput_mbps, packet_loss_pct, sla_compliance_pct — for a target service, link, or topology summary.",
  {
    topology: z.string(),
    target_id: z
      .string()
      .optional()
      .describe("service id or link 'from->to'; omit for a topology-level summary"),
  },
  async ({ topology, target_id }) => {
    const t = topologies[topology];
    if (!t) return asError(`unknown topology: ${topology}`);
    return asJson(fakeMetrics(`${topology}:${target_id ?? "_summary"}`));
  }
);

const transport = new StdioServerTransport();
await server.connect(transport);
console.error("[enterprise-vpn-sla-env-fake] mcp server ready on stdio");
