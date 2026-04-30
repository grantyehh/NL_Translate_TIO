#!/usr/bin/env bun
// tio-validator MCP: validate a chunk of Turtle against the TIO ontology
// loaded from ~/grant/ttls/. Surfaces parse errors, blacklisted predicates,
// unknown TIO predicates/classes, expectation structural rules, and orphans.

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";
import * as path from "node:path";
import { fileURLToPath } from "node:url";
import { loadOntology } from "./ontology.js";
import { validate, validateJsonLd } from "./validator.js";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const TTL_DIR = path.resolve(__dirname, "..", "..", "..", "ttls");

const ontology = loadOntology(TTL_DIR);
console.error(
  `[tio-validator] loaded ontology: ${ontology.classes.size} classes, ${ontology.predicates.size} predicates, ${ontology.functions.size} functions`
);

const server = new McpServer({ name: "tio-validator", version: "0.1.0" });

server.tool(
  "validate_ttl",
  "Validate a Turtle (.ttl) intent against the TIO ontology. Returns structured errors + warnings. You MUST call this on every TTL you produce before finalizing; if it returns errors, fix them and call again.",
  {
    ttl: z.string().describe("the Turtle text to validate"),
  },
  async ({ ttl }) => {
    const report = validate(ttl, ontology);
    return {
      content: [{ type: "text" as const, text: JSON.stringify(report, null, 2) }],
    };
  }
);

server.tool(
  "validate_jsonld",
  "Validate an API-friendly TIO JSON-LD intent payload. Returns structured errors + warnings. You MUST call this on every JSON-LD output before finalizing; if it returns errors, fix them and call again.",
  {
    jsonld: z.string().describe("the JSON-LD text to validate"),
  },
  async ({ jsonld }) => {
    const report = validateJsonLd(jsonld);
    return {
      content: [{ type: "text" as const, text: JSON.stringify(report, null, 2) }],
    };
  }
);

const transport = new StdioServerTransport();
await server.connect(transport);
console.error("[tio-validator] mcp server ready on stdio");
