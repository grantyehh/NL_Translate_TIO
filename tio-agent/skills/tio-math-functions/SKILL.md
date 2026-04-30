---
name: tio-math-functions
description: Load when the intent uses comparison operators (>, <, =, ≠, ≥, ≤), logistic/polynomial functions, or arithmetic expressions over property values.
---

# MathFunctions (mf)

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

## Properties

- **mf:c** — domain: fun:Function; range: quan:Quantity
  - The property mf:c assigns a vertical offset to a function.
- **mf:coefficients** — domain: fun:Function; range: quan:Quantity
  - The property mf:coefficients specifies the list of coefficients that define a polynomial function.
- **mf:input** — domain: fun:Function
  - The property mf:input specifies the input value within a function argument.
- **mf:k** — domain: fun:Function; range: quan:Quantity
  - The property mf:k specifies the logistic growth of a logistic function.
- **mf:l** — domain: fun:Function; range: quan:Quantity
  - The property mf:l assigns a vertical stretch to a function.
- **mf:map** — domain: fun:Function; range: rdf:List
  - The property mf:map defines the mapping of input to result values applied in a mapping function. The range is a list with entries that are lists as well which represent individual mapping. The individual mapping lists have the result value as first entry and all other entries are values that are supposed to be mapped into this result.
- **mf:x0** — domain: fun:Function; range: quan:Quantity
  - The property mf:x0 assigns a horizontal shift to a function.

## Functions / Operators

_Modeled as instances of `fun:Function`. Use in condition expressions or wherever a function reference is expected._

- **mf:logistic** — returns: quan:Quantity
  - The property mf:logistic represents a logistic function.
- **mf:mapping** — returns: rdf:Resource
  - The property mf:mapping represents a mapping function.
- **mf:poly** — returns: quan:Quantity
  - The property mf:poly represents a polynomial function.
