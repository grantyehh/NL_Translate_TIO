import { describe, expect, test } from "bun:test";

import { fakeMetrics, resolveTarget, topologies } from "./topologies.js";

describe("enterprise VPN SLA topology environment", () => {
  test("exposes only hub-and-spoke enterprise VPN SLA topologies", () => {
    expect(Object.keys(topologies)).toEqual(["enterprise-vpn-sla-hub-spoke"]);

    const topology = topologies["enterprise-vpn-sla-hub-spoke"];
    expect(topology.description).toContain("Enterprise VPN");
    expect(topology.services.every((service) => service.type === "enterprise-vpn")).toBe(true);
    expect(topology.services.length).toBe(20);
  });

  test("resolves tenant and hub/spoke hints to the concrete enterprise VPN service", () => {
    const result = resolveTarget(
      "enterprise-vpn-sla-hub-spoke",
      "確保星河銀行總部至所有分點之延遲在95%的時間內低於50ms"
    );

    expect(result.matches.map((service) => service.id)).toEqual(["svc:星河銀行-enterprise-vpn"]);
    expect(result.tried).toContain("星河銀行");
    expect(result.tried).toContain("evsla:latency");
    expect(result.tried).toContain("evsla:hubToAllSpokes");
  });

  test("resolves a specific spoke bandwidth SLA without matching other tenants", () => {
    const result = resolveTarget(
      "enterprise-vpn-sla-hub-spoke",
      "提供宏海物流總部至高雄倉儲中心100Mbps以上保證頻寬"
    );

    expect(result.matches.map((service) => service.id)).toEqual(["svc:宏海物流-enterprise-vpn"]);
    expect(result.tried).toContain("高雄倉儲中心");
    expect(result.tried).toContain("evsla:guaranteedBandwidth");
    expect(result.tried).toContain("evsla:specificSpoke");
  });

  test("returns enterprise SLA metrics for a target service", () => {
    const metrics = fakeMetrics("enterprise-vpn-sla-hub-spoke:svc:星河銀行-enterprise-vpn");

    expect(metrics.status).toBe("healthy");
    expect(metrics).toHaveProperty("latency_ms");
    expect(metrics).toHaveProperty("packet_loss_pct");
    expect(metrics).toHaveProperty("throughput_mbps");
    expect(metrics).toHaveProperty("sla_compliance_pct");
  });
});
