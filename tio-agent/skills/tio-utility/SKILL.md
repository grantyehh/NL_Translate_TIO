---
name: tio-utility
description: Load only if no other TIO module covers the predicate you need — miscellaneous utility classes/predicates.
---

# Utility (ut)

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

- **ut:UtilityInformation** — subClassOf: icm:Information
  - Utility information is expressed by instances of class ut:UtilityInformation.
- **ut:UtilityProfile** — subClassOf: icm:Information
  - Instances of class ut:UtilityProfile contain information that explains the utility information provided.

## Properties

- **ut:elevatedMaxUtility** — range: ut:UtilityProfile; subPropertyOf: icm:information
  - The property ut:elevatedMaxUtility specifies the maximum elevated utility score provided by a utility function. This is the actual maximum utility score used including all implicit prioritization and score elevation.
- **ut:forMetric** — domain: ut:UtilityInformation; range: rdf:List
  - The property ut:forMetric maps function arguments to metrics. It contains a list representing a value pair. The first entry in this is the B-node used in the argument list provided by ut:withArguments. The second entry is the metric represented by this B-node. This specifies that values of this metric shall be used as argument of the function. This therefore also specifies for which metrics this utility function is supposed to be used.
- **ut:function** — domain: ut:UtilityInformation; range: fun:Function; subPropertyOf: icm:information
  - The property ut:function assigns a function to utility information. This function shall be used as utility function to calculate a utility score. A function suitable as utility function provides a result with a numeric datatype, such as xsd:decimal or a quantity without unit.
- **ut:maxUtility** — range: ut:UtilityProfile; subPropertyOf: icm:information
  - The property ut:maxUtility is a property of utility profile information. It defines the upper boundary of the value range of utility scores used. In this range ut:maxUtility is interpreted as the maximum business value.
- **ut:minUtility** — range: ut:UtilityProfile; subPropertyOf: icm:information
  - The property ut:minUtility is a property of utility profile information. It defines the lower boundary of the value range of utility scores used. In this range ut:minUtility corresponds to the utility score that marks the lowest business value.
- **ut:utility** — range: ut:UtilityInformation; subPropertyOf: icm:information
  - The property ut:utility assigns utility information to an element of an intent.
- **ut:utilityProfile** — range: ut:UtilityProfile; subPropertyOf: icm:information
  - The property ut:utilityProfile allows assigning utility profiles, for example to intent, other elements within an intent, such as expectations and conditions or utility information objects within an intent. It can also add utility profile information to intent manager capability profiles [TR298] or intent specifications [TR299].
- **ut:utilityResult** — range: ut:UtilityProfile
  - The property ut:utilityResult allows assigning calculated utility scores. It is, for example, used in intent reports to state the utility score associated with a metric observation.
- **ut:withArgument** — domain: ut:UtilityInformation; range: rdf:List
  - Utility information specifies the value assigned to an argument for the function using the property ut:withArgument. Its range contains a list with two entries. The first entry is a named argument of the function. The second entry is the value to be used.
- **ut:withArguments** — domain: ut:UtilityInformation; range: rdf:List
  - Utility information specifies the argument list to be used with the function using the property ut:withArguments. Its range contains a list populated with values and objects that should match the argument specification of the function specified as utility function.
