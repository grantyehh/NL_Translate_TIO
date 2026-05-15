---
name: tio-proposal-best-intent
description: Load when the intent involves proposal/best-intent selection semantics across multiple candidate intents.
---

# ProposalBestIntent (pbi)

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

- **pbi:BestProposalExpectation** — subClassOf: icm:ReportingExpectation
  - The class pbi:BestProposalExpectation is used to request proposals of best intent. It is a subclass of icm:ReportingExpectation, which also implies that the proposal is communicated through an intent report.
- **pbi:BestProposalReport** — subClassOf: icm:ExpectationReport
  - The class pbi:BestProposalReport is used to provide the proposals corresponding to a best proposal expectation in the intent. It is a subclass of icm:ExpectationReport.
- **pbi:Proposal**
  - The class pbi:Proposal is used to provide an individual proposal. Typically, there a proposal created for every requirement in scope of a best proposal expectation as stated by its target.

## Properties

- **pbi:proposal** — domain: icm:IntentReport; range: pbi:BestProposalReport
  - The property pbi:Proposal refers to the best intent proposals contained in the intent report.
- **pbi:proposed** — domain: pbi:BestProposalReport; range: pbi:Proposal
  - The property pbi:proposed is used in the domain of a best proposal report to refer to an individual proposal.
- **pbi:proposedBest** — domain: pbi:Proposal
  - The property pbi:proposedBest refers to an object that states the proposed values.
- **pbi:proposedFor** — domain: pbi:Proposal
  - The property pbi:proposedFor is used to state what requirement object from the intent the proposal is made for.
