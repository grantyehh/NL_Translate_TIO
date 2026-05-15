---
name: tio-intent-common-model
description: ALWAYS load when producing TIO JSON-LD. Core TIO classes (icm:Intent, icm:Expectation with DeliveryExpectation/PropertyExpectation/ReportingExpectation subclasses, icm:Target, icm:Context), JSON-LD modeling guidance, and the hallucination blacklist. Turtle-derived vocabulary is reference only.
---

# IntentCommonModel (icm)

_Auto-generated from `~/grant/ttls/*.ttl`. Regenerate with `bun run scripts/ttl-to-skills.ts`. Vocabulary is TTL-derived reference material; final output must be JSON-LD._

## JSON-LD Output Rule

This skill is generated from TTL ontology sources, so it uses prefix names such as `icm:Intent` and `met:Metric` as vocabulary references. Final agent output must still be the API-friendly JSON-LD object defined in `CLAUDE.md`. Do not output Turtle, RDF triples, TTL code fences, or a Turtle conversion.


## Hallucination Blacklist

These predicates look plausible but **do not exist in TIO**. Never use them:

- `icm:hasValue` ❌ — use `icm:valuesOfTargetProperty` with a paired values resource
- `icm:hasProperty` ❌ — target properties are modeled implicitly via `icm:PropertyExpectation`
- `icm:condition` ❌ — use the **class** `log:Condition` (from the `tio-logical-operators` skill)
- `icm:expectation` ❌ — Expectations are independent resources; they link to Intent via their own target, not the other way round

If a predicate you want isn't listed in a TIO skill, **it does not exist**. Re-model instead of inventing.

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

- **icm:ConditionReport**
  - The report for a condition object is provided by an instance of class icm:ConditionReport.
- **icm:Context** — subClassOf: icm:IntentElement
  - The class icm:Context expresses that its instances are providing contextual information to other intent elements. Context objects provide additional information which impacts the interpretation of requirements. The intent common model does not define specific types of context, but intent extension models can define subclasses of icm:Context to do so.
- **icm:ContextReport**
  - A report about a context is provided by an instance of class icm:ContextReport.
- **icm:DeliveryExpectation** — subClassOf: icm:Expectation
  - The class icm:DeliveryExpectation expresses that its instance is a special type of expectation for specifying the requirement that something needs to be delivered. The details are expressed by its properties.
- **icm:DeliveryExpectationReport** — subClassOf: icm:ExpectationReport
  - The report for a delivery expectation is provided by an instance of class icm:DeliveryExpectationReport within an Intent Report.
- **icm:Expectation** — subClassOf: icm:IntentElement
  - The class icm:Expectation expresses that its intent is an expectation object. It defines a set of requirements within an Intent.
- **icm:ExpectationReport**
  - The class icm:ExpectationReport with its subclasses represent the reports for expectations defined in an intent.
- **icm:Information** — subClassOf: icm:IntentElement
  - The instances of class icm:Information provide additional information about resources and in particular intent or intent report elements. Information objects provide additional insights and context but without impacting the interpretation of requirements. The intent common model does not define specific types of information, but intent extension models can add subclasses of icm:Information to do so.
- **icm:Intent** — subClassOf: icm:IntentElement
  - The class icm:Intent expresses that its instance is an intent object. As such it defines requirements.
- **icm:IntentReport**
  - Intent reports are instances of the class icm:IntentReport.
- **icm:ObservationReportingExpectation** — subClassOf: icm:ReportingExpectation
  - Requesting intent reports with reporting expectations of class icm:ObservationReportingExpectaion leads to intent reports containing observations for metrics used in the intent.
- **icm:PropertyExpectation** — subClassOf: icm:Expectation
  - The class icm:PropertyExpectation expresses that its instance is a special type of expectation for specifying requirements based on properties such as, for example, metrics, KPI, states and other observations.
- **icm:PropertyExpectationReport** — subClassOf: icm:ExpectationReport
  - The report for a property expectation is provided by an instance of class icm:PropertyExpectationReport within an intent report.
- **icm:Reason** — subClassOf: icm:ExpectationReport
  - Instances of class icm:Reason specify explanations for intent handling results.
- **icm:ReportingExpectation** — subClassOf: icm:Expectation
  - The class icm:ReportingExpectation expresses that its instance is a special type of expectation for specifying the conditions and scope of intent reports. It allows subscribing to intent reports and determine its content and condition of generation.
- **icm:ReportingExpectationReport** — subClassOf: icm:ExpectationReport
  - The report for a reporting expectation is provided by an instance of class icm:ReportingExpectationReport.
- **icm:Target** — subClassOf: rdfs:Container, icm:IntentElement
  - The class icm:Target expresses that its instance is a target specification. Targets define a set of resources that are expected to fulfill the requirements they are associated with through an expectation.
- **icm:TargetReport**
  - The report for a target is provided by an instance of class icm:TargetReport.

## Properties

- **icm:about**
  - The property icm:about references the intent element the intent report element is reporting about.
- **icm:chooseFrom** — domain: icm:DeliveryExpectation; range: rdfs:Container
  - The property icm:chooseFrom provides a container of resources in its range. These are the resources, from which a choice can be made. The intent handler can choose a single resource or several depending on the use case specific needs. These resources would then be considered additions to the target assigned to the delivery expectation.
- **icm:context** — range: icm:Context
  - The property icm:context allows assigning context objects to resources and in particular to elements of an intent. The intent common model does not specific types of context, but intent extension models can define sub properties of icm:context specific to subclasses of context.
- **icm:contextReport** — range: icm:ContextReport
  - The property icm:contextReport can be used to assign context reports to elements of the intent report that reports about the elements of an intent that had the respective context.
- **icm:deliveryDescription** — domain: icm:DeliveryExpectation; range: rdfs:Resource
  - The property icm:deliveryDescription is a parameter used in delivery expectations. It expresses where a detailed description of the expected delivery can be found and specifies the resource that contains if.
- **icm:deliveryType** — domain: icm:DeliveryExpectation; range: rdfs:Class
  - The property icm:deliveryType is a parameter used in delivery expectations. It expresses the requirement that the target resource shall be an instance of the specified class.
- **icm:information** — range: icm:Information
  - The property icm:information allows assigning information objects to resources and in particular to elements of an intent or intent report. The intent common model does not define specific types of information, but intent extension models can add subclasses of icm:Information and also define respective sub properties of icm:information with a range specific to subclasses of information.
- **icm:intentHandlingState** — domain: icm:IntentReport; range: imo:IntentHandlingState
  - The intent handler maintains an intent handling state machine for every intent. An intent report states the intent handling state at the moment of intent report generation using of the property icm:intentHandlingState.
- **icm:intentUpdateState** — domain: icm:IntentReport; range: imo:IntentHandlingState
  - The intent handler maintains an intent update state machine for every intent. An intent report states the intent update state at the moment of intent report generation using of the property icm:intentUpdateState.
- **icm:reason** — range: icm:Reason
  - The property icm:reason would assign a reason to an intent report element.
- **icm:reportDestination** — domain: icm:ReportingExpectation
  - The property icm:reportDestination is used with a reporting expectation, and it specifies where to send the required report to. The object of the property is a resource that represents a wanted receiver of the intent report. When a report is generated, it would be sent to this receiver.
- **icm:reportDestinations** — domain: icm:ReportingExpectation; range: rdfs:Container
  - The property icm:reportDestinations is used with a reporting expectation, and it specifies where to send the required report to. The object of the property is a container with member resources that represent the wanted receivers of the intent report. When a report is generated, it would be sent to all receivers specified in the container.
- **icm:reportGenerated** — domain: icm:IntentReport; range: <http://www.w3.org/2006/time#Instant>
  - The property icm:reportGenerated assigns the timestamp of report generation to an intent report instance.
- **icm:reportNumber** — domain: icm:IntentReport; range: <http://www.w3.org/2001/XMLSchema#positiveInteger>
  - The property icm:reportNumber assigns a sequence number to the intent report instance.
- **icm:reportTriggers** — domain: icm:ReportingExpectation; range: rdfs:Container
  - The property icm:reportTriggers specifies the events that shall initiate the generation and distribution of an intent report. It is a property used in reporting expectations.
- **icm:result** — range: <http://www.w3.org/2001/XMLSchema#boolean>
  - The property icm:result states the evaluation result of the intent element at the time of report generation. It is a boolean truth value.
- **icm:resultFrom**
  - The property icm:resultFrom associates an element of the intent report with another element of an intent report. Its subject is the report of an intent element that has a boolean truth value resulting from a logical evaluation. The object of icm:resultFrom is the report of an element in the intent that directly contributed to that evaluation.
- **icm:target** — domain: icm:Expectation; range: icm:Target
  - The property icm:target assigns an object of class icm:Target to an expectation. It therefore specifies the targets for all requirements within this expectation.
- **icm:targetCount** — domain: icm:TargetReport; range: <http://www.w3.org/2001/XMLSchema#nonNegativeInteger>
  - The property icm:targetCount specifies the number of member resources of the target report object.
- **icm:targetReport** — domain: icm:ExpectationReport; range: icm:TargetReport
  - The report for a target is assigned to an expectation report with the property icm:targetReport.

## Functions / Operators

_Modeled as instances of `fun:Function`. Use in condition expressions or wherever a function reference is expected._

- **icm:intentElements**
  - The function icm:intentElements represents a container of all individual intent element resources used to express requirements for the intent elements given as arguments. This includes the given intent element object itself and its parents. It represents all intent elements in the subtree that contains the function argument.
- **icm:valuesOfTargetProperty** — returns: <http://www.w3.org/2001/XMLSchema#boolean>
  - The function icm:valuesOfTargetProperty represents a container of all values that are assigned to members of the target container with the properties specified as function argument. If multiple properties are specified as arguments the result is a superset of all values from all specified properties.

## Canonical JSON-LD Patterns

### 1. Delivery — "Provide service X"
```json
{
  "@type": "DeliveryExpectation",
  "id": "exp-delivery-01",
  "name": "Deliver Enterprise Service",
  "description": "Deliver an enterprise connectivity service.",
  "expectationObject": {
    "id": "svc:example",
    "name": "Example Service",
    "@type": "Service"
  }
}
```

### 2. Property — "Ensure metric X < Y on target Z"
```json
{
  "@type": "PropertyExpectation",
  "id": "exp-latency-01",
  "name": "Latency Constraint",
  "description": "Latency should stay below 20 ms.",
  "expectationObject": {
    "id": "svc:example",
    "name": "Example Service",
    "@type": "Service"
  },
  "expectationTarget": [
    {
      "name": "Latency",
      "targetProperty": "latency",
      "matchCondition": "LESS_THAN",
      "targetValue": {
        "value": 20,
        "unit": "ms"
      }
    }
  ]
}
```

### 3. Multiple properties on one target
```json
{
  "@type": "PropertyExpectation",
  "id": "exp-sla-01",
  "name": "SLA Constraints",
  "description": "Throughput should exceed 200 Mbps and latency should stay below 15 ms.",
  "expectationObject": {
    "id": "svc:example",
    "name": "Example Service",
    "@type": "Service"
  },
  "expectationTarget": [
    {
      "name": "Throughput",
      "targetProperty": "throughput",
      "matchCondition": "GREATER_THAN",
      "targetValue": {
        "value": 200,
        "unit": "Mbps"
      }
    },
    {
      "name": "Latency",
      "targetProperty": "latency",
      "matchCondition": "LESS_THAN",
      "targetValue": {
        "value": 15,
        "unit": "ms"
      }
    }
  ]
}
```

### 4. Context — "During time window X, do Y"
```json
{
  "intentContext": [
    {
      "@type": "Context",
      "name": "Weekend Evening",
      "description": "Weekend evening time window."
    }
  ]
}
```
