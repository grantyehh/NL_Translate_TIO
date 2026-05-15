import { describe, expect, test } from "bun:test";

import { formatAgentAnswer } from "./format.js";

describe("formatAgentAnswer", () => {
  test("pretty-prints valid JSON objects with two-space indentation", () => {
    const output = formatAgentAnswer('{"@type":"Intent","tenant":{"name":"星河銀行"},"intentExpectation":[]}');

    expect(output).toBe(`{
  "@type": "Intent",
  "tenant": {
    "name": "星河銀行"
  },
  "intentExpectation": []
}`);
  });

  test("leaves non-JSON answers untouched", () => {
    expect(formatAgentAnswer("請提供 Enterprise VPN SLA intent。")).toBe("請提供 Enterprise VPN SLA intent。");
  });
});
