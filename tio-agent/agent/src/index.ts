#!/usr/bin/env bun
// CLI entry. Usage from the grant/ repo root:
//   OPENAI_API_KEY=sk-... bun run agent/src/index.ts
// or via the root package.json script once wired up: `bun run agent`.

import OpenAI from "openai";
import * as fs from "node:fs";
import * as path from "node:path";
import * as readline from "node:readline/promises";
import { stdin as input, stdout as output } from "node:process";

import { Agent, type TraceEvent } from "./agent.js";
import { buildSystemPrompt } from "./prompt.js";
import { listSkills, readSkill } from "./skills.js";
import { connectMcps, loadMcpConfig } from "./mcp.js";

const DIM = (s: string) => `\x1b[2m${s}\x1b[0m`;
const CYAN = (s: string) => `\x1b[36m${s}\x1b[0m`;
const GREEN = (s: string) => `\x1b[32m${s}\x1b[0m`;
const YELLOW = (s: string) => `\x1b[33m${s}\x1b[0m`;
const RED = (s: string) => `\x1b[31m${s}\x1b[0m`;

async function main() {
  const apiKey = process.env.OPENAI_API_KEY;
  if (!apiKey) {
    console.error(RED("OPENAI_API_KEY is required. export it or put it in ~/grant/.env"));
    process.exit(1);
  }
  const model = process.env.OPENAI_MODEL ?? "gpt-4o";
  // Any OpenAI-compatible endpoint works: Ollama, OpenRouter, Groq, Together, etc.
  const baseURL = process.env.OPENAI_BASE_URL;
  const cwd = process.cwd();
  const claudeMdPath = path.join(cwd, "CLAUDE.md");
  const mcpConfigPath = path.join(cwd, ".mcp.json");
  const skillsDir = path.join(cwd, "skills");

  if (!fs.existsSync(claudeMdPath)) {
    console.error(RED(`CLAUDE.md not found at ${claudeMdPath}. Run from ~/grant.`));
    process.exit(1);
  }

  const claudeMd = fs.readFileSync(claudeMdPath, "utf-8");
  const skills = listSkills(skillsDir);
  const systemPrompt = buildSystemPrompt(claudeMd, skills);

  const mcpConfig = loadMcpConfig(mcpConfigPath);
  const mcp = await connectMcps(mcpConfig);

  // All tools: MCP-discovered + local skill reader
  const tools = [
    ...mcp.bindings.map((b) => ({
      name: b.name,
      description: b.description,
      schema: b.schema,
      call: b.call,
    })),
    {
      name: "read_skill",
      description:
        "Load the full content of a skill by name. Use after consulting the Skill Catalog in the system prompt.",
      schema: {
        type: "object",
        properties: {
          name: { type: "string", description: "skill name, e.g. tio-intent-common-model" },
        },
        required: ["name"],
      },
      call: async (args: Record<string, unknown>) => {
        const name = String(args.name ?? "");
        try {
          return readSkill(skillsDir, name);
        } catch (e) {
          return `ERROR: ${(e as Error).message}`;
        }
      },
    },
  ];

  // Banner
  console.log(DIM("━".repeat(60)));
  console.log(`grant agent  ${DIM(`model=${model}`)}${baseURL ? DIM(`  baseURL=${baseURL}`) : ""}`);
  console.log(DIM(`tools: ${tools.length} registered (${mcp.bindings.length} MCP + 1 skill-reader)`));
  console.log(DIM(`skills: ${skills.length} available`));
  console.log(DIM(`type /exit to quit, /reset to clear conversation history`));
  console.log(DIM("━".repeat(60)));

  const onTrace = (e: TraceEvent) => {
    if (e.kind === "tool_call") {
      const argStr = e.args ? JSON.stringify(e.args) : "";
      console.log(DIM(`[tool] ${CYAN(e.name!)}(${argStr})`));
    } else if (e.kind === "tool_result") {
      const preview = (e.text ?? "").slice(0, 200).replace(/\n/g, " ");
      const more = (e.text ?? "").length > 200 ? ` … (+${(e.text ?? "").length - 200} chars)` : "";
      console.log(DIM(`  └─ ${preview}${more}`));
    } else if (e.kind === "error") {
      console.log(RED(`[error] ${e.name ?? ""} ${e.text ?? ""}`));
    }
  };

  const openai = new OpenAI({ apiKey, ...(baseURL ? { baseURL } : {}) });
  const agent = new Agent({ openai, model, systemPrompt, tools, onTrace });

  const rl = readline.createInterface({ input, output });
  const cleanup = async () => {
    await mcp.close();
    rl.close();
  };
  process.on("SIGINT", async () => {
    console.log();
    await cleanup();
    process.exit(0);
  });

  while (true) {
    let line: string;
    try {
      line = await rl.question(YELLOW("you> "));
    } catch {
      break; // EOF
    }
    const trimmed = line.trim();
    if (!trimmed) continue;
    if (trimmed === "/exit" || trimmed === "/quit") break;
    if (trimmed === "/reset") {
      agent.reset();
      console.log(DIM("conversation reset"));
      continue;
    }

    try {
      const answer = await agent.send(trimmed);
      console.log(GREEN("agent>"), answer, "\n");
    } catch (e) {
      console.error(RED(`agent error: ${(e as Error).message}`));
    }
  }

  await cleanup();
}

main().catch((e) => {
  console.error(RED(`fatal: ${(e as Error).stack ?? e}`));
  process.exit(1);
});
