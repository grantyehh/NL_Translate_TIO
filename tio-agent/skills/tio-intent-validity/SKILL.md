---
name: tio-intent-validity
description: Load when the intent has validity windows, expiry times, effective periods, or scheduled activation/deactivation.
---

# IntentValidityOntology (iv)

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

- **iv:Validity** — subClassOf: icm:Context, <http://www.w3.org/2006/time#TemporalEntity>
  - The class iv:Validity is a subclass of icm:Context. It represents and determines the validity of resources it is associated with using the property iv:validIf .
- **iv:ValidityChange** — subClassOf: imo:IntentHandlingEvent
  - The class iv:ValidityChange is a subclass of imo:intentHandlingEvent and represents events issued if the validity status of a resource is changing.
- **iv:ValidityChangeInvalid** — subClassOf: iv:ValidityChange
  - The class iv:ValidityChange is a subclass of iv:ValidityChange and represents events issued if the validity status of a resource is changing to invalid.
- **iv:ValidityChangeValid** — subClassOf: iv:ValidityChange
  - The class iv:ValidityChange is a subclass of iv:ValidityChange and represents events issued if the validity status of a resource is changing to valid.
- **iv:ValidityReport** — subClassOf: icm:ContextReport
  - Instances of class iv:ValidityReport are used in intent reports to provide reporting about validity context.
- **iv:ValidityReportingExpectation** — subClassOf: icm:ReportingExpectation
  - A validity reporting expectation is an instance of class iv:ValidityReportingExpectation within an intent. A validity reporting expectation is chosen to request an intent report, if the intent report shall explicitly state the validity of intent elements.

## Properties

- **iv:isValid** — range: <http://www.w3.org/2001/XMLSchema#Boolean>
  - The property iv:isValid is used to state the validity status of its object. It is used in intent reports. This means it states the validity at the time of report generation. The range of iv:isValid contains a Boolean literal value. It is set to true, if the object is valid and false if not.
- **iv:sameValidityAs**
  - The property iv:sameValidityAs specifies that the validity of the subject shall be the same as the validity of the object.
- **iv:validIf** — range: iv:Validity
  - The property iv:validIf assigns validity context to objects.
- **iv:valueIfNotValid**
  - The property iv:valueIfNotValid allows specifying a function result that shall be provided as a default for invalid functions.

## Functions / Operators

_Modeled as instances of `fun:Function`. Use in condition expressions or wherever a function reference is expected._

- **iv:validityOf** — returns: <http://www.w3.org/2001/XMLSchema#Boolean>
  - The property iv:validityOf is a function that states the validity status of its arguments. If all arguments are valid, then the result of iv:validityOf is true, if any resource used as argument is not valid the result of iv:validityOf is false.
