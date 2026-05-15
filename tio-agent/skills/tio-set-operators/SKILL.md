---
name: tio-set-operators
description: Load when the intent references sets, membership, union/intersection, or aggregation operations over targets or property values.
---

# SetOperators (set)

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

## Functions / Operators

_Modeled as instances of `fun:Function`. Use in condition expressions or wherever a function reference is expected._

- **set:difference** — returns: rdfs:Container
  - The function set:difference represents a container of all members of the first argument container, which are not members of the other given containers as well. If no argument is given, the resulting container is empty. If only one argument is given, the resulting container is identical to the argument.
- **set:elementOf** — returns: <http://www.w3.org/2001/XMLSchema#boolean>
  - The function set:elementOf represents the result of an evaluation. It assumes the boolean type result value true, if the resource given in the first argument is a member of all the containers given by the remaining arguments.
- **set:empty** — returns: <http://www.w3.org/2001/XMLSchema#boolean>
  - The function set:empty represents the result of an evaluation. It assumes the boolean type result value true, if none of the containers given as arguments has any members.
- **set:forAll** — returns: <http://www.w3.org/2001/XMLSchema#boolean>
  - The function set:forAll has at least three arguments. The first argument represents any individual member from the container provided in the second argument. The third and all following arguments are resources with Boolean value. This can for example be a function that evaluates to a Boolean result. The function set:forAll has a Boolean type result directly derived from the third argument. The set:forAll function replicates the evaluation of the third argument for every member of the second argument. This allows to express that a condition set by the third argument needs to be met by every member of the provided container. The first argument is a resource use do represent individual members of the container. It can be used in the expression of the condition or evaluation specified by the third argument.
- **set:includedIn** — returns: <http://www.w3.org/2001/XMLSchema#boolean>
  - The function set:includedIn represents the result of an evaluation. It assumes the boolean type result value true, if all members of the container in the first argument are also members of each container given by the remaining arguments.
- **set:intersection** — returns: rdfs:Container
  - The function set:intersection represents a container of only those resources that are members of all containers specified in the arguments. If no arguments are given, the resulting container is empty. If only one argument is given, the resulting container is identical to the argument.
- **set:intersectsWith** — returns: <http://www.w3.org/2001/XMLSchema#boolean>
  - The function set:intersectsWith represents the result of an evaluation. It assumes the boolean type result value true, if there are member objects in the first argument container that are also members in all other containers given as arguments.
- **set:isMember** — returns: <http://www.w3.org/2001/XMLSchema#boolean>
  - The function set:isMember has at least two arguments. It provides the result true if the resource provided as first argument is a member of any container provided by the remaining arguments.
- **set:membersAfter** — returns: rdfs:Container
  - The function set:membersAfter represents the result of a time based container member filtering. The first parameter refers to the property of a member that assigns a time-stamp to a member object. This is the timestamp to be used in the evaluation of this function. The second parameter specifies a point in time expressed as individual of the class t:Instant defined in the time ontology in OWL [owltime]. The third and all remaining parameters are containers. The function provides a container as result. The members of this result container are members of the union of all containers provided as parameters, which meet the condition that their time stamp is after the time stamp provided as second parameter. The property provided as first parameter is the one used to evaluate the condition. This property needs to be used for a member of the input containers for the member object to be considered in the evaluation and included in the result.
- **set:membersBefore** — returns: rdfs:Container
  - The function set:membersBefore represents the result of a time based container member filtering. The first parameter refers to the property of a member that assigns a time-stamp to a member object. This is the timestamp to be used in the evaluation of this function. The second parameter specifies a point in time expressed as individual of the class t:Instant defined in the time ontology in OWL [owltime]. The third and all remaining parameters are containers. The function provides a container as result. The members of this result container are members of the union of all containers provided as parameters, which meet the condition that their time stamp is before the time stamp provided as second parameter. The property provided as first parameter is the one used to evaluate the condition. This property needs to be used for a member of the input containers for the member object to be considered in the evaluation and included in the result.
- **set:membersSameTime** — returns: rdfs:Container
  - The function set:membersSameTime represents the result of a time based container member filtering. The first parameter refers to the property of a member that assigns a time-stamp to a member object. This is the timestamp to be used in the evaluation of this function. The second parameter specifies a point in time expressed as individual of the class t:Instant defined in the time ontology in OWL [owltime]. The third and all remaining parameters are containers. The function provides a container as result. The members of this result container are members of the union of all containers provided as parameters, which meet the condition that their time-stamp shows the same time as the time-stamp provided as second parameter. The property provided as first parameter is the one used to evaluate the condition. This property needs to be used for a member of the input containers for the member object to be considered in the evaluation and included in the result.
- **set:membersWhile** — returns: rdfs:Container
  - The function set:membersWhile represents the result of a time based container member filtering. The first parameter refers to the property of a member that assigns a time-stamp to a member object. This is the time-stamp to be used in the evaluation of this function. The second parameter specifies time interval in time expressed as individual of the class t:Interval defined in the time ontology in OWL [owltime]. The third and all remaining parameters are containers. The function provides a container as result. The members of this result container are members of the union of all containers provided as parameters, which meet the condition that their time-stamp lies within the time interval provided as second parameter. The property provided as first parameter is the one used to evaluate the condition. This property needs to be used for a member of the input containers for the member object to be considered in the evaluation and included in the result.
- **set:newestMember** — returns: rdf:Resource
  - The function set:newestMember selects the newest member of the container according to a time-stamp property of the member object. The first parameter refers to the property of a member that assigns a time-stamp. This is the time-stamp to be used in the evaluation of this function. The third and all remaining parameters are containers. The function provides the resource as result that is the newest member object within the union of all containers provided as parameters as indicated by the property of the member object that was specified as first function parameter.
- **set:oldestMember** — returns: rdf:Resource
  - The function set:oldestMember selects the oldest member of the container according to a time-stamp property of the member object. The first parameter refers to the property of a member that assigns a time-stamp. This is the time-stamp to be used in the evaluation of this function. The third and all remaining parameters are containers. The function provides the resource as result that is the oldest member object within the union of all containers provided as parameters as indicated by the property of the member object that was specified as first function parameter.
- **set:resourcesOfType** — returns: rdfs:Container
  - The function set:resourcesOfType represents a container of all resources that are instances of the given classes or its subclasses. Closed world assumption applies. If no argument is given, the resulting container is empty.
- **set:resourcesWithProperty** — returns: rdfs:Container
  - The function set:resourcesWithProperty represents a container of all resource instances that are subject of the properties given as argument. Closed world assumption applies. If no arguments are given, the resulting container is empty.
- **set:resourcesWithPropertyObject** — returns: rdfs:Container
  - The function set:resourcesWithPropertyObject represents a container of all resources, to which the property specified in the first argument is used to assign any of the objects of the remaining arguments. Closed world assumption applies.
- **set:typesOfMembers** — returns: rdfs:Container
  - The function set:typesOfMembers represents a container of all classes the elements of the containers in the function arguments are instances of. Duplicates are removed from the resulting container and only included once as member. If no arguments are given, the resulting container is empty.
- **set:union** — returns: rdfs:Container
  - The function set:union represents a container of all resources that are members of the containers specified in the function arguments. If no arguments are given, the resulting container is empty.
- **set:valuesOfObjectProperty** — returns: rdfs:Container
  - The function set:valuesOfObjectProperty represents a container of all values that are assigned with the property given as first argument to the objects provided by the remaining arguments. If and object has multiple values assigned with this property, or if multiple objects are specified, the result is a superset of all values assigned to provided objects with this property.
