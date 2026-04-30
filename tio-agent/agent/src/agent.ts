// The agent loop: send messages to OpenAI with the registered tools, handle
// tool_calls by dispatching to the matching handler, feed results back, repeat
// until the model produces a plain assistant message (= done).

import type OpenAI from "openai";
import type { ChatCompletionMessageParam, ChatCompletionTool } from "openai/resources/chat/completions";

export interface ToolBinding {
  name: string;
  description: string;
  schema: Record<string, unknown>;
  call: (args: Record<string, unknown>) => Promise<string>;
}

export interface TraceEvent {
  kind: "tool_call" | "tool_result" | "assistant_text" | "error";
  name?: string;
  args?: unknown;
  text?: string;
}

export interface AgentOptions {
  openai: OpenAI;
  model: string;
  systemPrompt: string;
  tools: ToolBinding[];
  maxSteps?: number;
  onTrace?: (e: TraceEvent) => void;
}

export class Agent {
  private messages: ChatCompletionMessageParam[] = [];
  private toolMap: Map<string, ToolBinding>;
  private openaiTools: ChatCompletionTool[];

  constructor(private opts: AgentOptions) {
    this.toolMap = new Map(opts.tools.map((t) => [t.name, t]));
    this.openaiTools = opts.tools.map((t) => ({
      type: "function",
      function: { name: t.name, description: t.description, parameters: t.schema as any },
    }));
  }

  async send(userInput: string): Promise<string> {
    this.messages.push({ role: "user", content: userInput });
    const maxSteps = this.opts.maxSteps ?? 16;

    for (let step = 0; step < maxSteps; step++) {
      const resp = await this.opts.openai.chat.completions.create({
        model: this.opts.model,
        messages: [
          { role: "system", content: this.opts.systemPrompt },
          ...this.messages,
        ],
        tools: this.openaiTools,
        tool_choice: "auto",
      });

      const msg = resp.choices[0]!.message;
      this.messages.push(msg as ChatCompletionMessageParam);

      const calls = msg.tool_calls ?? [];
      if (calls.length === 0) {
        const text = msg.content ?? "";
        this.opts.onTrace?.({ kind: "assistant_text", text });
        return text;
      }

      // Execute every tool call before continuing the loop
      await Promise.all(
        calls.map(async (tc) => {
          if (tc.type !== "function") return;
          const name = tc.function.name;
          let args: Record<string, unknown> = {};
          try {
            args = tc.function.arguments ? JSON.parse(tc.function.arguments) : {};
          } catch (e) {
            this.opts.onTrace?.({ kind: "error", name, text: `bad arguments: ${(e as Error).message}` });
          }
          this.opts.onTrace?.({ kind: "tool_call", name, args });

          const binding = this.toolMap.get(name);
          let result: string;
          if (!binding) {
            result = `ERROR: unknown tool ${name}`;
          } else {
            try {
              result = await binding.call(args);
            } catch (e) {
              result = `ERROR: ${(e as Error).message}`;
            }
          }
          this.opts.onTrace?.({ kind: "tool_result", name, text: result });
          this.messages.push({
            role: "tool",
            tool_call_id: tc.id,
            content: result,
          });
        })
      );
    }

    throw new Error(`agent exceeded ${maxSteps} steps without final answer`);
  }

  reset() {
    this.messages = [];
  }
}
