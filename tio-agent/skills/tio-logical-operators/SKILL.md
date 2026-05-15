---
name: tio-logical-operators
description: Load when the intent involves conditions ('if X then Y'), logical AND/OR/NOT combinators, trigger-based behavior, or references the class log:Condition.
---

# LogicalOperators (log)

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

- **log:Condition** — subClassOf: icm:IntentElement
  - The class log:Condition expresses that its instance is specifying a condition statement with a boolean result.

## Functions / Operators

_Modeled as instances of `fun:Function`. Use in condition expressions or wherever a function reference is expected._

- **log:allOf** — returns: <http://www.w3.org/2001/XMLSchema#boolean>
  - The function log:allOf represents a logical conjunction also known as AND logical operator. It evaluates to boolean true if all arguments are individually true, otherwise the result is false. If the list of arguments is empty the result is also false.
- **log:anyOf** — returns: <http://www.w3.org/2001/XMLSchema#boolean>
  - The function log:anyOf represents a logical disjunction also known as OR logical operator if there are only two arguments. It evaluates to boolean true if any (at least one) of the arguments are true, otherwise the result is false. If the list of arguments is empty the result is also false.
- **log:match** — returns: <http://www.w3.org/2001/XMLSchema#boolean>
  - The function log:match represents the boolean truth value of the statement triple in the function arguments. The first argument represents the subject, the second argument represents the predicate and the third argument represents the object of a statement. It is true, if and only if the statement represented by this triple is true in the current knowledge base. Closed world assumption applies. If no statement is given as arguments or if it is incomplete, the result is false.
- **log:matchAll** — returns: <http://www.w3.org/2001/XMLSchema#boolean>
  - The function log:matchAll represents a boolean truth value from multiple statement triples. A constituent statement is formed by using a member of the container in the first function argument as subject. The constituent statement is completed with the predicate from the second argument and the resource from the third argument. Therefore, the function needs to evaluate as many statements as there are members in the subject container. The function is evaluated with a logical conjunction of constituent statements. The result is boolean true, if all the constituent statements is true. Closed world assumption applies. If no complete statement is given by the function arguments, the result is false. This is also the case if the subject container in the first argument is empty, thus no subject is specified.
- **log:matchAny** — returns: <http://www.w3.org/2001/XMLSchema#boolean>
  - The function log:matchAny represents a boolean truth value from multiple statement triples. A constituent statement is formed by using a member of the container in the first function argument as subject. The constituent statement is completed with the predicate from the second argument and the resource from the third argument. Therefore, the function needs to evaluate as many statements as there are members in the subject container. The function is evaluated with a logical disjunction of constituent statements. The result is boolean true, if any of the constituent statements is true. Closed world assumption applies. If no complete statement is given by the function arguments, the result is false. This is also the case if the subject container in the first argument is empty, thus no subject is specified.
- **log:matchNone** — returns: <http://www.w3.org/2001/XMLSchema#boolean>
  - The function log:matchNone represents a boolean truth value from multiple statement triples. A constituent statement is formed by using a member of the container in the first function argument as subject. The constituent statement is completed with the predicate from the second argument and the resource from the third argument. Therefore, the function needs to evaluate as many statements as there are members in the subject container. The function is evaluated with a logical negation of constituent statements. The result is boolean true, if none of the constituent statements are true. Closed world assumption applies. If no complete statement is given by the function arguments, the result is false. This is also the case if the subject container in the first argument is empty, thus no subject is specified.
- **log:matchOne** — returns: <http://www.w3.org/2001/XMLSchema#boolean>
  - The function log:matchOne represents a boolean truth value from multiple statement triples. A constituent statement is formed by using a member of the container in the first function argument as subject. The constituent statement is completed with the predicate from the second argument and the resource from the third argument. Therefore, the function needs to evaluate as many statements as there are members in the subject container. The function is evaluated with a logical exclusive disjunction of constituent statements. The result is boolean true, if exactly one of the constituent statements is true. Closed world assumption applies. If no complete statement is given by the function arguments, the result is false. This is also the case if the subject container in the first argument is empty, thus no subject is specified.
- **log:matchStatement** — returns: <http://www.w3.org/2001/XMLSchema#boolean>
  - The function log:matchStatement represents the boolean truth value of the statement in the function argument. It is true, if and only if all statements in its arguments are true in the current knowledge base. Closed world assumption applies. If no statement is given as argument, the result is false.
- **log:noneOf** — returns: <http://www.w3.org/2001/XMLSchema#boolean>
  - The function log:noneOf represents an evaluation similar to logical negation. It evaluates to boolean true if all the arguments are false and to false is any of the arguments are true. If the list of arguments is empty the result is true.
- **log:oneOf** — returns: <http://www.w3.org/2001/XMLSchema#boolean>
  - The function log:oneOf represents an exclusive disjunction also known as XOR logical operator if there are only two arguments. It evaluates to boolean true if exactly one of the arguments is true, otherwise the result is false. If the list of arguments is empty the result is also false.
