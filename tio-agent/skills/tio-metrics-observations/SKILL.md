---
name: tio-metrics-observations
description: Load when the intent references metrics, KPIs, states, or observable properties of a target — latency, throughput, packet loss, availability, signal strength, etc.
---

# MetricsAndObservations (met)

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

- **met:Observation**
  - An observation is a distinct value or fact that was observed or measured for a metric. An observation is represented by an individual of class met:Observation. They represent a measured or otherwise observed fact about a resource.

## Properties

- **met:metric**
  - Sub-properties of met:Metric represent observable and measurable items.
- **met:observed** — range: met:Observation
  - The property met:observed can be used to assign an instance of class met:Observation to other objects.
- **met:observedMetric** — domain: met:Observation; range: met:Metric
  - The property met:observedMetric states what was observed by an observation. This refers to a met:metric property that identifies a metric.
- **met:obtainedAt** — domain: met:Observation
  - The property met:obtainedAt states the point in time when the observation was obtained and the observation individual was created in the knowledge base.
