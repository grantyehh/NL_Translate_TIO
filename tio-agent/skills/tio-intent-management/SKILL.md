---
name: tio-intent-management
description: Load when modeling intent lifecycle, intent-handler relationships, ownership, or management metadata — as opposed to expressing the intent content itself.
---

# IntentManagementOntology (imo)

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

- **imo:BaseOntologyModel** — subClassOf: imo:TIOmodel
  - The class imo:BaseOntologyModel is a subclass of imo:TIOmodel. Its instances are models within the TM Forum Intent Ontology. Intent common models and intent extension models rely on the fundamental vocabulary and semantics defined by a base ontology model.
- **imo:Complies** — subClassOf: imo:IntentHandlingEvent
  - The class imo:Complies represents a state transition event in the intent handling state machine. It indicates that the system got compliant to the requirements expressed by the Intent.
- **imo:Degrades** — subClassOf: imo:IntentHandlingEvent
  - The class imo:Degrades represents a state transition event in the intent handling state machine. It indicates that the system lost its compliance to the requirements expressed by the Intent.
- **imo:Event** — subClassOf: <http://www.w3.org/2006/time#Instant>
  - The class imo:Event represents an event of intent management within an intent management function. An event is also a subclass of t:Instance from the time ontology. This means it represents the point in time the event instance was issued by the intent manager.
- **imo:Handler** — subClassOf: imo:LCMrole
  - The class imo:Handler expresses that its instance has the role of intent handler in intent life-cycle management.
- **imo:HandlingEnded** — subClassOf: imo:IntentHandlingEvent
  - The class imo:HandlingEnded represents a state transition event in the intent handling state machine. It indicates that the intent handler has finished all tasks associated with the removal of the intent. This is typically the last event generated for an intent.
- **imo:IntentAccepted** — subClassOf: imo:IntentHandlingEvent
  - The class imo:IntentAccepted represents a state transition event in the intent handling state machine. It indicates that the intent is accepted by the intent handler.
- **imo:IntentCommonModel** — subClassOf: imo:TIOmodel
  - The class imo:IntentCommonModel is a subclass of imo:TIOmodel. Its instances are intent common models within the TM Forum Intent Ontology.
- **imo:IntentExtensionModel** — subClassOf: imo:TIOmodel
  - The class imo:IntentExtensionModel is a subclass of imo:TIOmodel. Its instances are an intent extension model within the TM Forum Intent Ontology.
- **imo:IntentHandlingEvent** — subClassOf: imo:Event
  - The class imo:intentHandlingEvent represents events of the intent handling and intent update state machines.
- **imo:IntentHandlingState**
  - The class imo:IntentHandlingState is the class of all individuals that represent states of the intent handler.
- **imo:IntentManager**
  - The class imo:IntentManager expresses that its instance is an Intent Management Function.
- **imo:IntentReceived** — subClassOf: imo:IntentHandlingEvent
  - The class imo:IntentReceived represents a state transition event in the intent handling state machine. It indicates that a new intent was received and that handling of this intent is starting.
- **imo:IntentRejected** — subClassOf: imo:IntentHandlingEvent
  - The class imo:IntentRejected represents a state transition event in the intent handling state machine. It indicates that the intent handler has rejected the intent.
- **imo:IntentRemoval** — subClassOf: imo:IntentHandlingEvent
  - The class imo:IntentRemoval represents a state transition event in the intent handling state machine. It indicates that the intent owner has ordered a removal of the intent.
- **imo:LCMrole**
  - The class imo:LCMrole expresses that its instance has a role in intent life-cycle management. Its subclasses specify which role that is.
- **imo:Owner** — subClassOf: imo:LCMrole
  - The class imo:Owner expresses that its instance has the role of intent owner in intent life-cycle management.
- **imo:TIOmodel**
  - The class imo:TIOmodel expresses that its instance is an ontology model within the TM Forum Intent Ontology
- **imo:UpdateAccepted** — subClassOf: imo:IntentHandlingEvent
  - The class imo:UpdateAccepted represents a state transition event in the intent update state machine. This event indicates that the update was accepted and the intent handler proceeds with replacing the intent content. The update state imo:StateUpdating is reached.
- **imo:UpdateFinished** — subClassOf: imo:IntentHandlingEvent
  - The class imo:UpdateFinished represents a state transition event in the intent update state machine. This event indicates that the intent handler has finished executing a successful update. The update state machine returns to its waiting state imo:StateNoUpdate.
- **imo:UpdateReceived** — subClassOf: imo:IntentHandlingEvent
  - The class imo:UpdateReceived represents a state transition event in the intent update state machine. This event indicates that update handling is initiated, and the intent handler is assessing if it can accept the update. The update state machine has entered the state imo:StateUpdateReceived.
- **imo:UpdateRejected** — subClassOf: imo:IntentHandlingEvent
  - The class imo:UpdateRejected represents a state transition event in the intent update state machine. This event indicates that the update was rejected, and the intent handler continues with the previous version of the intent. The new version of the intent is discarded and the update state returns to imo:StateNoUpdate.

## Properties

- **imo:associatedValueCombination** — domain: rdfs:Class; range: fun:Function
  - The property imo:associatedValueCombination specifies the combination function to be applied if multiple contributors to the associated value of an instance a class are used.
- **imo:associatedValueType** — domain: rdfs:Class
  - The property imo:associatedValueType specifies the type of the associated value of instances of a class. If this property is used in the definition of a class, instances of this class have associated values.
- **imo:event** — range: imo:IntentHandlingEvent
  - The property imo:event can be used to assign an intent handling event.
- **imo:eventFor** — domain: imo:Event; range: rdf:Resource
  - The property imo:eventFor is used in the class definition of subclasses of imo:Event. It is therefore part of the defintion of new event types. It specifies the Intent instance the event of this class is supposed to be issued for. This intent instance will be reflected by the imo:eventIssuedFor property used with event instances.
- **imo:eventIssuedBy** — domain: imo:Event; range: imo:IntentManager
  - The property imo:eventIssuedBy refers to the instance of the intent management function that has issued the intent.
- **imo:eventIssuedFor** — domain: imo:Event; range: rdf:Resource
  - The property imo:eventIssuedFor refers to the resource the event is generated for. This can for example be the intent instance the event was issued from the handling procedure for this intent and because of a situation reached concerning this intent.
- **imo:handler** — range: imo:IntentManager
  - The property imo:handler expresses that the resource of type imo:IntentManager in its object has the role of an intent handler for the subject. The subject is typically an intent or associated intent report.
- **imo:handlingState** — range: imo:IntentHandlingState
  - The property imo:handlingState can be used to assign an intent handling state.
- **imo:owner** — range: imo:IntentManager
  - The property imo:owner expresses that the resource of type imo:IntentManager in its object has the role of an intent owner for the subject. The subject is typically an intent or associated intent report.
- **imo:updateState** — range: imo:IntentHandlingState
  - The property imo:updateState can be used to assign an intent update state

## Functions / Operators

_Modeled as instances of `fun:Function`. Use in condition expressions or wherever a function reference is expected._

- **imo:handlingStateOf** — returns: imo:IntentHandlingState
  - The function imo:handlingStateOf represents the current state in the intent handling state machine for the handling of the intent in the function argument.
- **imo:timeOfLastEventFor** — returns: <http://www.w3.org/2006/time#Instant>
  - The function imo:timeOfLastEventFor represents the point in time when the last event of the specified event type was generated for an intent. The first argument specifies the event type and the second argument specifies the event instance. If no event of this type was issued yet for the intent, the reception of the intent is used as last event time. This means there is always a time provided.
- **imo:timeOfLastEventsFor** — returns: <http://www.w3.org/2006/time#Instant>
  - The function imo:timeOfLastEventsFor represents the point in time when the last event of the specified event types was generated for an intent. The first argument specifies a container. Its members represent the event types to be considered. The second argument specifies the intent instance for which the events were issued. If no event of these types was issued yet for the intent, the reception of the intent is used as last event time. This means there is always a time provided.
- **imo:timeOfLastReportFor** — returns: <http://www.w3.org/2006/time#Instant>
  - The function imo:timeOfLastReportFor represents the point in time when the last intent report was generated for the intent specified in the function argument. If no report was issued yet, the reception of the intent is used as last report time. This means there is always a time provided.
- **imo:updateStateOf** — returns: imo:IntentHandlingState
  - The function imo:updateStateOf represents the current state in the intent handling state machine for the handling of an update of the intent in the function argument
