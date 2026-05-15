import { describe, expect, test } from "bun:test";

import { validateJsonLd } from "./validator.js";

const validEnterpriseVpnSlaPayload = {
  "@context": "https://tmforum.org/schemas/intent-ontology/v1.jsonld",
  "@type": "Intent",
  id: "intent-evsla-test",
  name: "Enterprise VPN Hub-Spoke SLA Intent",
  description: "Assure latency for a tenant enterprise VPN.",
  intentOwner: {
    id: "ops-manager-01",
    name: "Network Operations Center",
  },
  tenant: {
    id: "tenant-星河銀行",
    name: "星河銀行",
    "@type": "evsla:Tenant",
  },
  intentExpectation: [
    {
      id: "exp-latency",
      name: "Hub-to-Spoke Latency SLA Expectation",
      description: "Keep latency below 50 ms for 95 percent of the time.",
      "@type": "PropertyExpectation",
      ontologyType: "evsla:SlaExpectation",
      expectationObject: {
        id: "svc:星河銀行-enterprise-vpn",
        name: "星河銀行 Enterprise VPN Service",
        "@type": "Service",
        ontologyType: "evsla:EnterpriseVpnService",
      },
      expectationTarget: [
        {
          name: "Hub-to-Spoke Latency",
          targetProperty: "evsla:latency",
          matchCondition: "LESS_THAN",
          targetValue: {
            value: 50,
            unit: "ms",
            "@type": "quan:Quantity",
          },
          "evsla:hasMetric": "evsla:latency",
          "evsla:hasThreshold": {
            value: 50,
            unit: "ms",
            "@type": "quan:Quantity",
          },
          "evsla:hasStatistic": "evsla:p95",
          "evsla:hasScope": "evsla:hubToAllSpokes",
          "evsla:hasMeasurementMethod": "evsla:twamp",
          "evsla:hasTimeWindow": "evsla:fiveMinuteWindow",
        },
      ],
    },
  ],
  intentContext: [
    {
      id: "topology-test",
      "@type": "Context",
      name: "Hub-and-Spoke Topology",
      "evsla:hasHub": {
        "@type": "evsla:HubSite",
        name: "台北總部",
      },
      "evsla:hasSpoke": [
        {
          "@type": "evsla:SpokeSite",
          name: "新竹分行",
        },
      ],
      ontologyType: "evsla:HubAndSpokeTopology",
    },
  ],
  intentReport: {
    reportingInterval: "PT5M",
    handlerResponse: "Continuous",
  },
  ontologyType: "evsla:EnterpriseVpnSlaIntent",
};

describe("validateJsonLd enterprise VPN SLA checks", () => {
  test("accepts a complete enterprise VPN SLA payload", () => {
    const report = validateJsonLd(JSON.stringify(validEnterpriseVpnSlaPayload));

    expect(report.ok).toBe(true);
    expect(report.errors).toEqual([]);
  });

  test("rejects payloads that omit enterprise VPN SLA fields", () => {
    const invalid = structuredClone(validEnterpriseVpnSlaPayload);
    delete (invalid as any).tenant;
    delete (invalid.intentExpectation[0].expectationTarget[0] as any)["evsla:hasScope"];
    invalid.intentContext = [];

    const report = validateJsonLd(JSON.stringify(invalid));

    expect(report.ok).toBe(false);
    expect(report.errors.map((error) => error.code)).toContain("JSONLD_EVSLA_TENANT");
    expect(report.errors.map((error) => error.code)).toContain("JSONLD_EVSLA_TARGET_FIELD");
    expect(report.errors.map((error) => error.code)).toContain("JSONLD_EVSLA_TOPOLOGY_CONTEXT");
  });
});
