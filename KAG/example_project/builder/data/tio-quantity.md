---
name: tio-quantity
description: Load when the intent specifies numeric quantities with units (Mbps, milliseconds, percentages, packet counts, etc.).
---

# QuantityOntology (quan)

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

- **quan:MonetaryQuantity** — subClassOf: quan:quantity
  - The class quan:MonetaryQuantity refers to a quantity with currency based units.
- **quan:Quantity**
  - The class quan:Quantity defines a structured datatype for representing a numerical value in combination with a unit expression.

## Properties

- **quan:unit** — domain: quan:Quantity; range: <http://www.w3.org/2001/XMLSchema#string>
  - The property quan:unit assigns a unit to a quantity.

## Functions / Operators

_Modeled as instances of `fun:Function`. Use in condition expressions or wherever a function reference is expected._

- **quan:atLeast**
  - The function quan:atLeast defines a comparison of quantities. It provides a boolean result and is evaluated as "true" if the quantity of the first argument is equal to or bigger than the quantity of the second argument. Unit prefixes are considered.
- **quan:atMost** — returns: <http://www.w3.org/2001/XMLSchema#boolean>
  - The function quan:atMost defines a comparison of quantities. It provides a boolean result and is evaluated as "true" if the quantity of the first argument is equal to or smaller than the quantity of the second argument. Unit prefixes are considered.
- **quan:difference**
  - The function quan:difference defines a mathematical operation that provides the numerical difference between two quantities. It has two arguments, and it evaluates to the difference of the first argument value minus the second argument value. Unit prefixes are considered in the calculation. The unit expression of the first argument is used for the result.
- **quan:division**
  - The function quan:division defines a mathematical operation that provides the result of a division of two quantities. The first argument is the numerator and the second the denominator of the division. The function therefore has exactly two arguments. Unit prefixes are considered in the calculation. Both arguments can have different units and the unit expression of the result is generated based on the units of the arguments.
- **quan:exactly**
  - The function quan:exactly defines a comparison of quantities. It provides a boolean result and is evaluated as "true" if the quantity of all arguments are the same. Unit prefixes are considered.
- **quan:greater**
  - The function quan:greater defines a comparison of quantities. It provides a boolean result and is evaluated as true if the quantity of the first argument is greater than the quantity of the second argument. Unit prefixes are considered.
- **quan:greatest**
  - The function quan:greatest provides a result that is the largest quantity across all quantities provided as arguments. If no argument is provided the result has value 0 without unit. Units and unit prefixes are considered.
- **quan:greatestInSet**
  - The function quan:greatestInSet provides a result that is the largest quantity across all quantities across member elements of the union of all containers that are provided as arguments. If no argument is provided the result has value 0 without unit. Units and unit prefixes are considered.
- **quan:inRange**
  - The function quan:inRange defines a comparison of quantities. It provides a boolean result and is evaluated as "true" if the value of the quantity of the first argument is equal to or greater than the quantity of the second argument and if it is equal to or smaller than the quantity of the third argument. Unit prefixes are considered.
- **quan:mean**
  - The function quan:mean defines a mathematical operation that provides the arithmetic mean of quantities. The function can have any number of arguments of type quan:Quantity and the result is the arithmetic mean across all of them. The result is 0 with no unit if no argument is provided. If only one argument is given, then the result is identical with the argument. Units and unit prefixes are considered in the calculation. The arguments must have units that are of the same dimension and the unit assigned to the result is the unit of the first argument.
- **quan:meanOfSet**
  - The function quan:meanOfSet defines a mathematical operation that provides the arithmetic mean of quantities. The function can have any number of arguments of type rdfs:Container and the result is the arithmetic mean across all member elements of the union of these containers. The result is 0 with no unit if no member element of type quan:quantity is provided by any of the argument containers. Units and unit prefixes are considered in the calculation. The arguments must have units that are of the same dimension and the unit assigned to the result is the unit of the first member element processed from the first argument container.
- **quan:median**
  - The function quan:median defines a mathematical operation that provides the median value of quantities. The function can have any number of arguments of type quan:Quantity and the result is the arithmetic median value across all of them. The result is 0 with no unit if no argument is provided. If only one argument is given, then the result is identical with the argument. Units and unit prefixes are considered in the calculation. The arguments must have units that are of the same dimension and the unit assigned to the result is the unit of the first argument.
- **quan:medianOfSet**
  - The function quan:medianOfSet defines a mathematical operation that provides the median value of quantities. The function can have any number of arguments of type rdfs:Container and the result is the median value across all member elements of the union of these containers. The result is 0 with no unit if no member element of type quan:quantity is provided by any of the argument containers. Units and unit prefixes are considered in the calculation. The arguments must have units that are of the same dimension and the unit assigned to the result is the unit of the first member element processed from the first argument container.
- **quan:multiplication**
  - The function quan:multiplication defines a mathematical operation that provides the result of a multiplication of quantities. The function can have any number of arguments of type quan:Quantity and the result is the multiplication of all of them. The result is 0 with no unit if no argument is provided. If only one argument is given, then the result is identical with the argument. Units and unit prefixes are considered in the calculation. The result unit depends on the unit of contributing quantities and a suitable unit will be assigned.
- **quan:multiplicationOfSet**
  - The function quan:multiplicationOfSet defines a mathematical operation that provides the result of a multiplication of quantities. The function can have any number of arguments of type rdfs:Container and the result is the multiplication of all member elements of the union of these containers. The result is 0 with no unit if no member element of type quan:Quantity is provided by any of the argument containers. Units and unit prefixes are considered in the calculation. The result unit depends on the unit of contributing quantities and a suitable unit will be assigned.
- **quan:smaller**
  - The function quan:smaller defines a comparison of quantities. It provides a boolean result and is evaluated as true if the quantity of the first argument is smaller than the quantity of the second argument. Unit prefixes are considered.
- **quan:smallest**
  - The function quan:smallestInSet provides a result that is the smallest quantity across all quantities provided as arguments. If no argument is provided the result has value 0 without unit. Units and unit prefixes are considered.
- **quan:smallestInSet**
  - The function quan:smallestInSet provides a result that is the smallest quantity across all quantities across member elements of the union of all containers that are provided as arguments. If no argument is provided the result has value 0 without unit. Units and unit prefixes are considered.
- **quan:sum**
  - The function quan:sum defines a mathematical operation that provides the result of an addition of quantities. The function can have any number of arguments of type quan:Quantity and the result is the sum of all of them. The result is 0 with no unit if no argument is provided. If only one argument is given, then the result is identical with the argument. Units and unit prefixes are considered in the calculation. The arguments must have units that are of the same dimension and the unit assigned to the result is the unit of the first argument.
- **quan:sumOfSet**
  - The function quan:sumOfSet defines a mathematical operation that provides the result of an addition of quantities. The function can have any number of arguments of type rdfs:Container and the result is the sum of all member elements of the union of these containers. The result is 0 with no unit if no member element of type quan:quantity is provided by any of the argument containers. Units and unit prefixes are considered in the calculation. The arguments must have units that are of the same dimension and the unit assigned to the result is the unit of the first member element processed from the first argument container.
