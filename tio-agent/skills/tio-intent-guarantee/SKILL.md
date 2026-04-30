---
name: tio-intent-guarantee
description: Load when the intent carries SLA-style guarantees, service-level commitments, or assurance semantics beyond plain expectations.
---

# IntentGuaranteeOntology (ig)

_Auto-generated from `~/grant/ttls/*.ttl`. Regenerate with `bun run scripts/ttl-to-skills.ts`._

> Always combine with the `tio-intent-common-model` skill — that skill owns the core Intent/Expectation/Target vocabulary this module extends.

## Prefixes

```turtle
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
@prefix rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix owl:  <http://www.w3.org/2002/07/owl#> .
```

## Classes

- **ig:ConfidenceLevelNotObtainable** — subClassOf: icm:Reason
  - The class ig:Complies specifies a reason for rejection of a guarantee. The requested confidence level is not possible to reach for during the guarantee period, according to predictions.
- **ig:ConfidenceLevelNotReached** — subClassOf: icm:Reason
  - The class ig:Complies specifies a reason for degradation of a guarantee. The requested confidence level was not reached during the evaluation window.
- **ig:ConflictingGuarantees** — subClassOf: icm:Reason
  - The class ig:Complies specifies a reason for rejection of a guarantee. A requirement is associated with more than one guarantee context, of which more than one is valid at some point in time during the upcoming guarantee period.
- **ig:Guarantee** — subClassOf: icm:Context
  - The class Guarantee is a context that, when associated with requirements (objects of type icm:Expectation, icm:Condition and icm:Intent), modifies the status of those requirements to guaranteed.
- **ig:GuaranteeAccepted** — subClassOf: imo:Event
  - The class ig:GuaranteeAccepted specifies an event. The meaning of the event is that the intent handler has concluded that it is capable of issuing a requested guarantee for the next guarantee period. The guarantee target state is GuaranteeStateCompliant.
- **ig:GuaranteePeriodNotObtainable** — subClassOf: icm:Reason
  - The class ig:Complies specifies a reason for rejection of a guarantee. It is not possible to guarantee the requirement during the requested guarantee period.
- **ig:GuaranteePeriodTooLong** — subClassOf: icm:Reason
  - The class ig:Complies specifies an reason for rejection of a guarantee. The requested guarantee period is too long for the intent handler to accurately predict and plan for the guarantee, this is a result of limitations in implementation.
- **ig:GuaranteePeriodUpdate** — subClassOf: imo:Event
  - The class ig:GuaranteePeriodUpdate specifies an event. The meaning of the event is that a new evaluation and planning phase has been initiated as a result of periodic updating or the end of the previous guarantee period. The guarantee target state is either GuaranteeStateCompliant or GuaranteeStateDegraded, depending on the outcome.
- **ig:GuaranteePeriodUpdateIntervalTooLong** — subClassOf: icm:Reason
  - The class ig:GuaranteePeriodUpdateIntervalTooLong specifies a warning. The requested guarantee period update interval is longer than the guarantee period. The result is that it is void and the guarantee period and update interval is the same.
- **ig:GuaranteeRejected** — subClassOf: icm:Event
  - The class ig:GuaranteeRejected specifies an event. The meaning of the event is that the intent handler has concluded that it is not capable of issuing a requested guarantee. The guarantee target state is ig:GuaranteeStateRejected.
- **ig:GuaranteeReportingExpectation** — subClassOf: icm:ReportingExpectation
  - The class ig:GuaranteeReportingExpectation specifies a reporting expectation for guarantees and is used to configure a specific guarantee period and conditions for when to issue reports related to guarantees.
- **ig:GuaranteeStateCompliant** — subClassOf: ig:State
  - The class ig:GuaratneeStateCompliant specifies a state. The meaning of the state is that the intent handler has concluded that it's capable of delivering the guarantee for the next guarantee period. Possible events transitioning from this state are imo:UpdateReceived and ig:GuaranteePeriodUpdate.
- **ig:GuaranteeStateDegraded** — subClassOf: ig:State
  - The class ig:GuaratneeStateDegraded specifies a state. The meaning of the state is that the intent handler has concluded that it's not capable of delivering the guarantee for the next guarantee period. Possible events transitioning from this state are imo:UpdateReceived and ig:GuaranteePeriodUpdate.
- **ig:State**
  - The class ig:State is a base-class of Guarantee states.

## Properties

- **ig:confidenceLevel** — range: <http://www.w3.org/2001/XMLSchema#decimal>
  - The property ig:confidenceLevel specifies a required, predicted or real (measured) confidence/probability level, as a value between 0-1 (percentage). If not specified the confidence is assumed to be 1 (100%).
- **ig:guaranteePeriod** — domain: ig:GuaranteeReportingExpectation; range: <http://www.w3.org/2001/XMLSchema#duration>
  - The property ig:guaranteePeriod specifies the duration of guarantee periods, in ISO8601 format. If not specified in a guarantee reporting expectation the guarantee period is the entire life-span of the associated intent, which is generally indefinite unless limited by other vocabulary.
- **ig:guaranteePeriodUpdateInterval** — domain: ig:GuaranteeReportingExpectation; range: <http://www.w3.org/2001/XMLSchema#duration>
  - The property ig:guaranteePeriodUpdateInterval specifies the interval of re-evaluation and planning of guarantee periods, in ISO8601 format. If not specified in a guarantee reporting expectation the guarantee period update interval is the same as the guarantee period.
- **ig:hasGuarantee** — range: ig:Guarantee
  - The property ig:hasGuarantee is used to associate a guarantee context with a requirement (objects of type icm:Expectation, icm:Condition and icm:Intent).
- **ig:state** — domain: ig:GuaranteeReport; range: ig:State
  - The property ig:state specifies the state of a guarantee.
- **ig:until** — domain: ig:GuaranteeReport; range: <http://www.w3.org/2001/XMLSchema#dateTime>
  - The property ig:until specifies the expiry date and time of a guarantee period, in ISO8601 format.
