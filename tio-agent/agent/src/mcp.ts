// Connect to MCP servers from .mcp.json and expose their tools as plain
// {name, description, schema, call} bindings the agent loop can dispatch.

import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio.js";
import * as fs from "node:fs";

export interface McpConfig {
  mcpServers: Record<string, { command: string; args?: string[]; env?: Record<string, string> }>;
}

export interface McpToolBinding {
  server: string;
  name: string;
  description: string;
  schema: Record<string, unknown>;
  call: (args: Record<string, unknown>) => Promise<string>;
}

export interface ConnectedMcp {
  bindings: McpToolBinding[];
  close: () => Promise<void>;
}

export function loadMcpConfig(file: string): McpConfig {
  if (!fs.existsSync(file)) return { mcpServers: {} };
  return JSON.parse(fs.readFileSync(file, "utf-8"));
}

export async function connectMcps(config: McpConfig): Promise<ConnectedMcp> {
  const bindings: McpToolBinding[] = [];
  const clients: Client[] = [];

  for (const [server, spec] of Object.entries(config.mcpServers)) {
    const client = new Client({ name: "grant-agent", version: "0.1.0" });
    const transport = new StdioClientTransport({
      command: spec.command,
      args: spec.args ?? [],
      env: { ...(process.env as Record<string, string>), ...(spec.env ?? {}) },
    });
    await client.connect(transport);
    clients.push(client);

    const { tools } = await client.listTools();
    for (const t of tools) {
      bindings.push({
        server,
        name: t.name,
        description: t.description ?? "",
        schema: (t.inputSchema as Record<string, unknown>) ?? { type: "object", properties: {} },
        call: async (args) => {
          const res = await client.callTool({ name: t.name, arguments: args });
          if (res.isError) {
            return `TOOL_ERROR: ${JSON.stringify(res.content)}`;
          }
          const parts = (res.content as Array<{ type: string; text?: string }>) ?? [];
          return parts.map((p) => (p.type === "text" ? p.text : JSON.stringify(p))).join("\n");
        },
      });
    }
  }

  return {
    bindings,
    close: async () => {
      for (const c of clients) {
        try {
          await c.close();
        } catch {
          /* best effort */
        }
      }
    },
  };
}
