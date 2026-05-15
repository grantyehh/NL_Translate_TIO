---
name: tio-enterprise-vpn-sla
description: ALWAYS load for this agent's core task: enterprise VPN hub-and-spoke SLA assurance intents. Vocabulary for evsla:EnterpriseVpnSlaIntent, evsla:EnterpriseVpnService, evsla:Tenant, evsla:HubAndSpokeTopology, hub/spoke sites, SLA metrics, thresholds, statistics, measurement methods, and monitoring windows.
---

# EnterpriseVpnSlaOntology (evsla)

_Auto-generated from `~/grant/ttls/*.ttl`. Regenerate with `bun run scripts/ttl-to-skills.ts`. Vocabulary is TTL-derived reference material; final output must be JSON-LD._

## JSON-LD Output Rule

This skill is generated from TTL ontology sources, so it uses prefix names such as `icm:Intent` and `met:Metric` as vocabulary references. Final agent output must still be the API-friendly JSON-LD object defined in `CLAUDE.md`. Do not output Turtle, RDF triples, TTL code fences, or a Turtle conversion.


> Always combine with the `tio-intent-common-model` skill — that skill owns the core Intent/Expectation/Target vocabulary this module extends.

## Prefixes

```text
@prefix icm: <http://tio.models.tmforum.org/tio/v3.6.0/IntentCommonModel/> .
@prefix log: <http://tio.models.tmforum.org/tio/v3.6.0/LogicalOperators/> .
@prefix set: <http://tio.models.tmforum.org/tio/v3.6.0/SetOperators/> .
@prefix fun: <http://tio.models.tmforum.org/tio/v3.6.0/FunctionOntology/> .
@prefix imo: <http://tio.models.tmforum.org/tio/v3.6.0/IntentManagementOntology/> .
@prefix ig: <http://tio.models.tmforum.org/tio/v3.6.0/IntentGuaranteeOntology/> .
@prefix pro: <http://tio.models.tmforum.org/tio/v3.6.0/IntentProbing/> .
@prefix insp: <http://tio.models.tmforum.org/tio/v3.6.0/IntentSpecification/> .
@prefix iv: <http://tio.models.tmforum.org/tio/v3.6.0/IntentValidityOntology/> .
@prefix mf: <http://tio.models.tmforum.org/tio/v3.6.0/MathFunctions> .
@prefix met: <http://tio.models.tmforum.org/tio/v3.6.0/MetricsAndObservations/> .
@prefix pre: <http://tio.models.tmforum.org/tio/v3.6.0/PreferenceOfHandlingOutcomes/> .
@prefix pbi: <http://tio.models.tmforum.org/tio/v3.6.0/ProposalBestIntent/> .
@prefix quan: <http://tio.models.tmforum.org/tio/v3.6.0/QuantityOntology/> .
@prefix ut: <http://tio.models.tmforum.org/tio/v3.6.0/Utility/> .
@prefix evsla: <http://tio.models.tmforum.org/tio/v3.6.0/EnterpriseVpnSlaOntology/> .
@prefix rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix owl:  <http://www.w3.org/2002/07/owl#> .
```

## Classes

- **evsla:EnterpriseVpnService** — subClassOf: rdfs:Resource
  - The enterprise VPN service that is the target of an SLA assurance intent.
- **evsla:EnterpriseVpnSlaIntent** — subClassOf: icm:Intent
  - An intent for assuring SLA requirements over an enterprise VPN service, especially hub-and-spoke VPN connectivity.
- **evsla:HubAndSpokeTopology** — subClassOf: icm:Context
  - A topology context in which one hub site connects to one or more spoke sites.
- **evsla:HubSite** — subClassOf: evsla:Site
  - The central headquarters or hub site in a hub-and-spoke enterprise VPN topology.
- **evsla:MeasurementMethod** — subClassOf: icm:Context
  - A measurement method used to observe SLA metrics, such as active measurement or TWAMP.
- **evsla:Scope** — subClassOf: icm:Context
  - The measurement or guarantee scope of an SLA metric, such as hub-to-all-spokes, per-spoke or a specific spoke.
- **evsla:Site** — subClassOf: rdfs:Resource
  - A tenant site participating in an enterprise VPN topology.
- **evsla:SlaExpectation** — subClassOf: icm:PropertyExpectation
  - A property expectation expressing one or more SLA guarantees for a VPN service.
- **evsla:SpokeSite** — subClassOf: evsla:Site
  - A branch, remote office or spoke site connected to the hub in a hub-and-spoke enterprise VPN topology.
- **evsla:Statistic** — subClassOf: icm:Context
  - A statistical interpretation for an SLA metric, such as p95, p99, average, maximum or minimum.
- **evsla:Tenant** — subClassOf: rdfs:Resource
  - The enterprise customer or tenant that owns or consumes the VPN service under SLA assurance.
- **evsla:TimeWindow** — subClassOf: icm:Context
  - A monitoring, aggregation or SLA evaluation window, such as five minutes, one hour or monthly SLA.

## Properties

- **evsla:appliesPerSpoke** — domain: evsla:SlaExpectation; range: <http://www.w3.org/2001/XMLSchema#boolean>
  - States whether an SLA guarantee is evaluated independently for each spoke.
- **evsla:forTenant** — range: evsla:Tenant
  - Associates an enterprise VPN SLA intent, service, topology or expectation with the tenant it applies to.
- **evsla:guaranteedBandwidth** — subPropertyOf: met:metric
  - Metric property for the minimum guaranteed bandwidth provided to a spoke or VPN path.
- **evsla:hasHub** — domain: evsla:HubAndSpokeTopology; range: evsla:HubSite
  - Associates a hub-and-spoke topology with its hub site.
- **evsla:hasMeasurementMethod** — domain: evsla:SlaExpectation; range: evsla:MeasurementMethod
  - Associates an SLA expectation with the measurement method used to observe its metric.
- **evsla:hasMetric** — domain: evsla:SlaExpectation; range: rdf:Property
  - Associates an SLA expectation with the metric property being guaranteed or monitored.
- **evsla:hasScope** — domain: evsla:SlaExpectation; range: evsla:Scope
  - Associates an SLA expectation with its measurement or guarantee scope.
- **evsla:hasSpoke** — domain: evsla:HubAndSpokeTopology; range: evsla:SpokeSite
  - Associates a hub-and-spoke topology with a spoke site.
- **evsla:hasStatistic** — domain: evsla:SlaExpectation; range: evsla:Statistic
  - Associates an SLA expectation with a statistical interpretation such as p95, p99 or minimum.
- **evsla:hasThreshold** — domain: evsla:SlaExpectation; range: quan:Quantity
  - Associates an SLA expectation with a threshold quantity, such as 50 ms, 0.1 percent or 100 Mbps.
- **evsla:hasTimeWindow** — domain: evsla:SlaExpectation; range: evsla:TimeWindow
  - Associates an SLA expectation with the monitoring or SLA evaluation time window.
- **evsla:hasTopology** — range: evsla:HubAndSpokeTopology
  - Associates an intent or VPN service with its topology context.
- **evsla:latency** — subPropertyOf: met:metric
  - Metric property for network latency between hub and spoke sites.
- **evsla:packetLoss** — subPropertyOf: met:metric
  - Metric property for packet loss rate between hub and spoke sites.
- **evsla:serviceTarget** — domain: icm:Expectation; range: evsla:EnterpriseVpnService; subPropertyOf: icm:target
  - Associates an SLA expectation with the enterprise VPN service being constrained.
