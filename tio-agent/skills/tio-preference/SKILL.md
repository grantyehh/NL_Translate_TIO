---
name: tio-preference
description: Load when the intent expresses preferences or priorities between alternative handling outcomes (trade-off semantics).
---

# PreferenceOfHandlingOutcomes (pre)

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

- **pre:JudgementRequest** — subClassOf: rdfs:Container
  - The class pre:JudgementRequest represents a request from the intent handler to an intent owner to provide its preference regarding the expected results of available solution options on the intent requirements. It is a subclass of rdfs:Container with members that refer to intent reports requesting the expected outcomes for available options.
- **pre:Preference**
  - The class pre:Preference represents preferences of an intent owner with respect to the options presented in a judgement request.
- **pre:PreferenceScore**
  - An instance of class pre:PreferenceScore is added to the preference object within the intent by the intent owner to present its preferences regarding an option and quantify its preference with a numerical score.
- **pre:ScoreInterpretation** — subClassOf: rdfs:Container
  - An instance of class pre:ScoreInterpretation is added to the preference object within the intent by the intent owner to provide further information about the interpretation of scores used when specifying preferences.

## Properties

- **pre:about** — domain: pre:Preference; range: pre:JudgementRequest
  - The property pre:about is a reference to the judgement request instance stated in the intent reports that are part of the judgement request.
- **pre:aboutOption** — domain: pre:PreferenceScore; range: icm:IntentReport
  - The property pre:aboutOption refers to the intent report, for which this preference score object states the score.
- **pre:judgementRequest** — domain: icm:IntentReport; range: pre:JudgementRequest
  - The property pre:judgementRequest associates a judgement request of class pre:JudgementRequest with an intent report.
- **pre:maxScore** — domain: pre:ScoreInterpretation
  - The property pre:maxScore states the maximum value or full score used in providing preference scores. If not provided, the highest sore used within the preferences of this intent owner within this judgement request is considered to be the maximum score.
- **pre:minScore** — domain: pre:ScoreInterpretation
  - The property pre:minScore states the minimum score value used in providing preference scores. If not provided, a minimum score of 0 is assumed by default.
- **pre:neutral** — domain: pre:Preference; range: icm:IntentReport
  - The property pre:neutral refers to an intent report the intent owner does not mind, but also does not express an explicit preference for. This is the assumed default for options without a dedicated preference statement. It is also assumed if the intent owner does not provide a preference statement before the preference deadline.
- **pre:objected** — domain: pre:Preference; range: icm:IntentReport
  - The property pre:objected refers to an intent report the intent owner considers problematic from its perspective. The respective solution should not be chosen by the intent handler.
- **pre:objectedThreshold** — domain: pre:ScoreInterpretation
  - The property pre:objectedThreshold defines the maximum score for objected options. An option with lower than this score should be avoided.
- **pre:preference** — domain: icm:Intent; range: pre:Preference
  - The property pre:preference associates a preference provided by an intent owner to an intent.
- **pre:preferenceDeadline** — domain: pre:JudgementRequest; range: <http://www.w3.org/2006/time#Instant>
  - The property pre:preferenceDeadline states the point in time until the preference needs to be provided. The intent handler waits for a preference statement provided by the intent owner until this point in time. If until then none or incomplete preference statements are received, the intent handler will proceed and select a solution with the information available.
- **pre:preferred** — domain: pre:Preference; range: icm:IntentReport
  - The property pre:preferred refers to an intent report the intent owner considers preferential. It is referring to an intent report presented by the judgement request.
- **pre:preferredThreshold** — domain: pre:ScoreInterpretation
  - The property pre:preferredThreshold defines the minimum score value for preferred options. An option with at least this score is considered to be preferred.
- **pre:score** — domain: pre:Preference; range: pre:PreferenceScore
  - The property pre:score associates a preference score to a preference.
- **pre:scoreInterpretation** — domain: pre:Preference; range: pre:ScoreInterpretation
  - A score interpretation is associated with a preference using the property pre:scoreInterpretation.
- **pre:scoreValue** — domain: pre:PreferenceScore
  - The property pre:scoreValue assigns a numerical value to the preference score object. This is the numerical score associated with an option.
