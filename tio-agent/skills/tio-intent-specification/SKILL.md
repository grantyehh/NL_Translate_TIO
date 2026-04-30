---
name: tio-intent-specification
description: Load when modeling intent specifications or intent templates — blueprints/schemas for intent instances rather than individual intents.
---

# IntentSpecification (insp)

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

- **insp:ContentTemplate** — subClassOf: insp:Template
  - Content templates are instances of class insp:ContentTemplate, which is a subclass of insp:Template.
- **insp:IntentSpecification**
  - Intent specifications are instances of class insp:IntentSpecification. An intent is assembled in accordance to an intent specification by finding an intent expression that complies to all rules and constraints expressed by the intent specification.
- **insp:ObjectTemplate** — subClassOf: insp:Template
  - An object template is an instance of class insp:ObjectTemplate, which is a subclass of insp:Template. Within intent specifications an object template can be used as substitute for any object within an intent expression.
- **insp:Template**
  - Templates are instances of subclasses of class insp:Template.
- **insp:VocabularyTemplate** — subClassOf: imo:Vocabulary, insp:Template
  - A vocabulary template is an instance of class insp:VocabularyTemplate, which is a subclass of insp:Template. A vocabulary template is also a subclass of imo:Vocabulary, which is a subclass of rdfs:Container.

## Properties

- **insp:allowedValues** — domain: insp:ObjectTemplate; range: rdfs:Container
  - The property insp:allowedValues is used to specify the set of candidate objects or values to choose from for substituting the object template in its domain within a conforming intent expression.
- **insp:alternative** — range: insp:ContentTemplate
  - The property insp:alternative specifies alternative content within intent specifications. Its range contains a list of all content templates representing viable alternatives. Each content template in the list alternative represents a statement or set of statements. Exactly one of these content templates and its statements needs to be used in place of insp:alternative when expressing an intent. This means a conforming intent expression must include a set of statements for every inst:alternative statement in the intent specification.
- **insp:applicableIf** — domain: insp:ContentTemplate; range: log:Condition
  - The property insp:applicableIf specifies that the content template in its domain is applicable to the intent expression if the condition in its range evaluates to true.
- **insp:applicableIfNot** — domain: insp:ContentTemplate; range: log:Condition
  - The property insp:applicableIfNot specifies that the content template in its domain is applicable to the intent expression if the condition in its range evaluates to false.
- **insp:availableVocabulary** — range: insp:VocabularyTemplate
  - The property insp:availableVocabulary assigns a vocabulary template to an intent within an intent specification. It implies that the intent and all its elements can only be expressed using the vocabulary specified by the vocabulary template. Multiple insp:availableVocabulary assigned to the same subject are interpreted as union of the individual vocabulary templates.
- **insp:chosenHandlingDomain** — subPropertyOf: met:metric
  - The property insp:chosenHandlingDomain refers to a chosen target autonomous domain. The intent expression is generated from the intent specification to express the requirements for that autonomous domain.
- **insp:chosenIntentHandler** — subPropertyOf: met:metric
  - The property insp:chosenIntentHandler refers to the instance of an intent manager within the chosen target autonomous domain. The intent expression is generated from the intent specification to be sent to this intent manager instance.
- **insp:content** — domain: insp:ContentTemplate
  - The property insp:content assigns the statements represented by the content template. The node used in its range is the source of statements to be transferred into the intent expression. All statements in that node shall be transferred. If insp:content is used multiple times within a content template, their contributions are additive and the superset of statements is applied.
- **insp:contentUsing** — domain: insp:ContentTemplate; range: insp:VocabularyTemplate
  - The property insp:contentUsing represents content that is expressed in accordance with vocabulary templates. If it is used as property of a content template and represents a choice regarding content to be used in an intent expression made by the process that assembles the intent. This content is chosen in accordance with available vocabulary according to the vocabulary template in its range.
- **insp:intentHandlerVendor** — subPropertyOf: met:metric
  - The property insp:intentHandlerVendor refers to the vendor of the intent manager that is chosen to be the handler of the Intent that is generated from the intent specification.
- **insp:intentOwner** — subPropertyOf: met:metric
  - The property insp:intentOwner refers to the intent manager that is assembling the intent from the intent specification.
- **insp:intentOwnerDomain** — subPropertyOf: met:metric
  - The property insp:intentOwnerDomain refers to the autonomous domain of the intent manager that is assembling the intent from the intent specification.
- **insp:intentOwnerVendor** — subPropertyOf: met:metric
  - The property insp:intentOwnerVendor refers to the vendor of the intent manager that is assembling the intent from the intent specification.
- **insp:mandatory** — range: insp:ContentTemplate
  - The property insp:mandatory specifies a content template that represents a statement or sets of statements that must be included in an intent expression. Its range contains a content template instance of class insp:ContentTemplate. This content template determines the statements that must be used as substitute for the insp:mandatory statement in a conforming intent expression.
- **insp:mandatoryIntent** — domain: insp:IntentSpecification; range: icm:Intent
  - The property insp:mandatoryIntent intent assigns intent expressions that must be used. This means an intent expression conforming to the intent specification must conform to this intent expression including all rules and dynamic content choices it allows.
- **insp:mandatorySpecification** — domain: insp:IntentSpecification; range: insp:IntentSpecification
  - The property insp:mandatorySpecification expresses that an eligible intent expression must conform to the intent specification provided in its range. This expresses, that the rules and constraints of that intent specification are mandatory for follow. Multiple statements using insp:mandatorySpecification with the same subject are in a conjunction (AND). This means an assembled intent expression must conform to all mandatory intent specifications.
- **insp:option** — range: insp:ContentTemplate
  - The property insp:option specifies a set of statements that can be used in an intent expression. The range of insp:option is a template of class insp:ContentTemplate. The statements and expressions of this content template would substitute the insp:option statement within a conforming intent expression if this option is chosen.
- **insp:optionalIntent** — domain: insp:IntentSpecification; range: icm:Intent
  - The property insp:optionalIntent assigns intent objects to an intent specification. An intent expression that resembles any of these intents conforms to the intent specification.
- **insp:optionalSpecification** — domain: insp:IntentSpecification; range: insp:IntentSpecification
  - The property insp:optionalSpecification expresses that an intent expression can be assembled following the intent specifications provided in its range. Multiple statements using insp:optionalSpecification with the same subject are in a disjunction (OR). This means an intent expression conforms overall if it conforms to at least one and potentially several of the optional specifications.
- **insp:templateType** — domain: insp:ObjectTemplate
  - The property insp:templateType specifies what type of object an object template instance is representing and substituting in an intent expression that conforms to the intent specification.

## Functions / Operators

_Modeled as instances of `fun:Function`. Use in condition expressions or wherever a function reference is expected._

- **insp:chosenAll** — returns: <http://www.w3.org/2001/XMLSchema#boolean>
  - The operator insp:chosenAll indicates true, if all content templates referred to by its arguments were chosen.
- **insp:chosenAllFor** — returns: <http://www.w3.org/2001/XMLSchema#boolean>
  - The operator insp:chosenAllFor indicates true, if for the intent element instance given as first argument all content templates referred to by its second and further arguments were chosen.
- **insp:chosenAny** — returns: <http://www.w3.org/2001/XMLSchema#boolean>
  - The operator insp:chosenAny indicates true, if any of the content templates referred to by its arguments were chosen.
- **insp:chosenAnyFor** — returns: <http://www.w3.org/2001/XMLSchema#boolean>
  - The first argument is of type rdfs:Resource. It is referring to an element of the intent. The second and remaining arguments have type insp:ContentTemplate.
- **insp:selectValues** — returns: rdfs:Container
  - The abstract function insp:selectValues represents a container of values that can be chosen to substitute an object template. The first argument of insp:selectValues is a variable that represents the values to be chosen. The second and further arguments are conditions that use the variable in its first argument to express condition statements. Every value possible for the variable in the first argument according to the conditions is a member of the resulting container. The conditions are in a conjunction. This means, a value needs to satisfy all conditions to be included in the result container.
- **insp:usedVocabularyFor** — returns: <http://www.w3.org/2001/XMLSchema#boolean>
  - The function insp:usedVocabularyFor indicates true, if for expressing the intent element referred to by the first argument all vocabulary is used specified in any of the remaining arguments. The second and remaining arguments are containers with members that refer to distinct elements of intent expression vocabulary.
- **insp:valueSelected** — returns: <http://www.w3.org/2001/XMLSchema#boolean>
  - The operator insp:valueSelected indicates true, if for the object template referred to by the first argument, the chosen value is a member of the containers provided as second or remaining arguments.
- **insp:valueSelectedFor** — returns: <http://www.w3.org/2001/XMLSchema#boolean>
  - The operator insp:valueSelectedFor indicates true, if certain values were chosen for the combination of an intent element and object template. The intent element to be considered is provided by the first argument and the object template is referred to by the second argument. The values to be checked are members of the containers provided by the third or remaining arguments.
