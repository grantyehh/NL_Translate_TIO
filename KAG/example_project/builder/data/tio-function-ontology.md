---
name: tio-function-ontology
description: Load when the intent references functions, procedures, function signatures, parameter binding, or functional composition.
---

# FunctionOntology (fun)

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

- **fun:Error** — subClassOf: imo:Error
  - Instances of class fun:Error are types of errors related to functions and function evaluation. It is a specialization of class imo:Error, which refers to all errors happening in intent handling.
- **fun:Warning** — subClassOf: imo:Warning
  - Instances of class fun:Warning are types of warnings related to functions and function evaluation. It is a specialization of class imo:Warning, which refers to all warnings generated in intent handling.

## Properties

- **fun:argumentNames** — domain: fun:function; range: rdfs:List
  - The property fun:argumentNames is used in function definitions. It allows connecting each argument of the function to a property of the function. The range of fun:argumentNames is a list which contains one entry per function argument in the order of function arguments. Each entry refers to a property and is interpreted as a property of the function. The properties can be provided directly in the function definition and outside the arguments as well. The values provided for a property in the arguments has preference and would override the values assigned directly to the function. This means the equivalent properties used directly in the function definition are defaults.
- **fun:argumentTypes** — domain: fun:function; range: rdfs:List
  - The property fun:argumentTypes defines the type of each argument of a function. It uses a collection of types expressing the type of each respective argument of the function. For example, if the 1st member of the collection of fun:argumentTypes is rdf:Container and the second member is quan:Quantity, this means that the first argument of the function needs to be a container and the second argument needs to be a quantity. If the function can have more arguments than matched by elements in fun:argumentTypes, the last defined type determines the type of all additional arguments.
- **fun:arityMax** — domain: fun:Function; range: <http://www.w3.org/2001/XMLSchema#nonNegativeInteger>
  - Defines the maximum number of arguments the function would consider. If the argument collection of the function contains more entries, only the entries up to the max arity are considered, and further entries are ignored.
- **fun:arityMin** — domain: fun:Function; range: <http://www.w3.org/2001/XMLSchema#nonNegativeInteger>
  - Defines the minimum number of arguments the function requires.
- **fun:resultIfInvalid** — domain: fun:Function
  - The property fun:resultIfInvalid allows specifying a result value to be used in case the function is not valid.
- **fun:resultType** — domain: fun:Function
  - Defines the type of the function evaluation result. This is synonymous to the type of value associated with the subject from function evaluation.
