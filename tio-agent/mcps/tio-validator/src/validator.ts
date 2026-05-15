// Validate TIO payloads against the ontology/API contract. The Turtle path is
// retained for legacy/debug ontology snippets; final agent output uses JSON-LD.

import { Parser, Store } from "n3";
import type { Ontology } from "./ontology.js";

const RDF = "http://www.w3.org/1999/02/22-rdf-syntax-ns#";
const RDFS = "http://www.w3.org/2000/01/rdf-schema#";
const XSD = "http://www.w3.org/2001/XMLSchema#";
const OWL = "http://www.w3.org/2002/07/owl#";
const ICM = "http://tio.models.tmforum.org/tio/v3.6.0/IntentCommonModel/";

// Canonical TIO short prefixes (matches the .ttl @prefix declarations)
const TIO_PREFIX_MAP: Record<string, string> = {
  [ICM]: "icm",
  "http://tio.models.tmforum.org/tio/v3.6.0/LogicalOperators/": "log",
  "http://tio.models.tmforum.org/tio/v3.6.0/SetOperators/": "set",
  "http://tio.models.tmforum.org/tio/v3.6.0/FunctionOntology/": "fun",
  "http://tio.models.tmforum.org/tio/v3.6.0/IntentManagementOntology/": "imo",
  "http://tio.models.tmforum.org/tio/v3.6.0/IntentGuaranteeOntology/": "ig",
  "http://tio.models.tmforum.org/tio/v3.6.0/IntentProbing/": "pro",
  "http://tio.models.tmforum.org/tio/v3.6.0/IntentSpecification/": "insp",
  "http://tio.models.tmforum.org/tio/v3.6.0/IntentValidityOntology/": "iv",
  "http://tio.models.tmforum.org/tio/v3.6.0/MathFunctions": "mf",
  "http://tio.models.tmforum.org/tio/v3.6.0/MetricsAndObservations/": "met",
  "http://tio.models.tmforum.org/tio/v3.6.0/PreferenceOfHandlingOutcomes/": "pre",
  "http://tio.models.tmforum.org/tio/v3.6.0/ProposalBestIntent/": "pbi",
  "http://tio.models.tmforum.org/tio/v3.6.0/QuantityOntology/": "quan",
  "http://tio.models.tmforum.org/tio/v3.6.0/Utility/": "ut",
};
const TIO_PREFIX_KEYS = Object.keys(TIO_PREFIX_MAP).sort((a, b) => b.length - a.length);
const INSTANCE_PREFIX_RE = /^http:\/\/example\.org\/tio-instance\/[^/]+\/(.+)$/;

// Predicates that look plausible but don't exist in TIO — pipe-fail if emitted.
const BLACKLIST: Record<string, string> = {
  [`${ICM}hasValue`]: "use icm:valuesOfTargetProperty with a paired values resource",
  [`${ICM}hasProperty`]: "target properties are modeled implicitly via icm:PropertyExpectation",
  [`${ICM}condition`]: "use the class log:Condition, not a property",
  [`${ICM}expectation`]:
    "Expectations are independent resources; they link to Intent via their target",
};

// Namespaces we don't validate against the ontology (stdlib / instance namespaces)
const SKIP_NAMESPACES = [RDF, RDFS, XSD, OWL];
const EXTERNAL_NAMESPACES = ["http://purl.org/dc/terms/", "http://www.w3.org/2004/02/skos/core#"];

export interface Issue {
  code: string;
  message: string;
  subject?: string;
  predicate?: string;
  object?: string;
}

export interface ValidationReport {
  ok: boolean;
  errors: Issue[];
  warnings: Issue[];
  stats: {
    quads: number;
    intents: number;
    expectations: number;
    targets: number;
  };
}

export interface JsonLdValidationReport {
  ok: boolean;
  errors: Issue[];
  warnings: Issue[];
  stats: {
    expectations: number;
    propertyExpectations: number;
    contexts: number;
  };
}

function shortName(uri: string, _ontology: Ontology): string {
  for (const ns of TIO_PREFIX_KEYS) {
    if (uri.startsWith(ns)) return `${TIO_PREFIX_MAP[ns]}:${uri.slice(ns.length)}`;
  }
  if (uri.startsWith(RDF)) return `rdf:${uri.slice(RDF.length)}`;
  if (uri.startsWith(RDFS)) return `rdfs:${uri.slice(RDFS.length)}`;
  if (uri.startsWith(XSD)) return `xsd:${uri.slice(XSD.length)}`;
  if (uri.startsWith(OWL)) return `owl:${uri.slice(OWL.length)}`;
  const inst = uri.match(INSTANCE_PREFIX_RE);
  if (inst) return `ex:${inst[1]}`;
  return `<${uri}>`;
}

function isKnown(uri: string, ontology: Ontology, kind: "class" | "predicate"): boolean {
  if (SKIP_NAMESPACES.some((n) => uri.startsWith(n))) return true;
  if (EXTERNAL_NAMESPACES.some((n) => uri.startsWith(n))) return true;
  if (!uri.startsWith(ontology.tioRoot)) return true; // external custom vocab — out of scope
  if (kind === "class") return ontology.classes.has(uri);
  return ontology.predicates.has(uri) || ontology.functions.has(uri);
}

export function validate(ttlText: string, ontology: Ontology): ValidationReport {
  const errors: Issue[] = [];
  const warnings: Issue[] = [];

  const store = new Store();
  try {
    store.addQuads(new Parser().parse(ttlText));
  } catch (e) {
    errors.push({ code: "PARSE_ERROR", message: (e as Error).message });
    return {
      ok: false,
      errors,
      warnings,
      stats: { quads: 0, intents: 0, expectations: 0, targets: 0 },
    };
  }

  const sn = (u: string) => shortName(u, ontology);

  // 1. Blacklisted / unknown predicates
  const seenPredicates = new Set<string>();
  for (const q of store.getQuads(null, null, null, null)) seenPredicates.add(q.predicate.value);
  for (const p of seenPredicates) {
    if (BLACKLIST[p]) {
      errors.push({
        code: "BLACKLISTED_PREDICATE",
        predicate: sn(p),
        message: `${sn(p)} does not exist in TIO — ${BLACKLIST[p]}`,
      });
    } else if (!isKnown(p, ontology, "predicate")) {
      errors.push({
        code: "UNKNOWN_PREDICATE",
        predicate: sn(p),
        message: `${sn(p)} is not declared in TIO. You likely hallucinated this — re-check the relevant tio-* skill.`,
      });
    }
  }

  // 2. Unknown rdf:type classes (only flag TIO-namespaced ones)
  for (const q of store.getQuads(null, `${RDF}type`, null, null)) {
    const cls = q.object.value;
    if (!isKnown(cls, ontology, "class") && cls.startsWith(ontology.tioRoot)) {
      errors.push({
        code: "UNKNOWN_CLASS",
        subject: sn(q.subject.value),
        object: sn(cls),
        message: `${sn(q.subject.value)} is typed as ${sn(cls)}, which is not a declared TIO class.`,
      });
    }
  }

  // 3. Structural rules for expectations
  const expectationSubclasses = [
    `${ICM}DeliveryExpectation`,
    `${ICM}PropertyExpectation`,
    `${ICM}ReportingExpectation`,
    `${ICM}Expectation`,
  ];
  const expectationSubjects = new Set<string>();
  for (const cls of expectationSubclasses)
    for (const q of store.getQuads(null, `${RDF}type`, cls, null))
      expectationSubjects.add(q.subject.value);
  for (const exp of expectationSubjects) {
    const targets = store.getQuads(exp, `${ICM}target`, null, null);
    if (targets.length === 0) {
      errors.push({
        code: "EXPECTATION_MISSING_TARGET",
        subject: sn(exp),
        message: `${sn(exp)} is an Expectation but has no icm:target.`,
      });
    } else if (targets.length > 1) {
      warnings.push({
        code: "EXPECTATION_MULTIPLE_TARGETS",
        subject: sn(exp),
        message: `${sn(exp)} has ${targets.length} icm:target triples; each Expectation should have exactly one.`,
      });
    }
    // target referenced by expectation must be typed icm:Target
    for (const t of targets) {
      const ty = store.getQuads(t.object.value, `${RDF}type`, `${ICM}Target`, null);
      if (ty.length === 0) {
        errors.push({
          code: "TARGET_NOT_TYPED",
          subject: sn(t.object.value),
          message: `${sn(t.object.value)} is referenced via icm:target but is not declared as icm:Target.`,
        });
      }
    }
  }

  // 4. Intent presence
  const intents = store.getQuads(null, `${RDF}type`, `${ICM}Intent`, null).map((q) => q.subject.value);
  if (intents.length === 0) {
    errors.push({
      code: "NO_INTENT",
      message: "No resource declared as icm:Intent. Every output must have exactly one icm:Intent.",
    });
  }

  // 5. Orphan detection: certain types are meaningless unless something points at
  // them (Target, Context, Condition, Quantity). An unreferenced one is dead weight.
  const LOG_CONDITION = "http://tio.models.tmforum.org/tio/v3.6.0/LogicalOperators/Condition";
  const QUAN_QUANTITY = "http://tio.models.tmforum.org/tio/v3.6.0/QuantityOntology/Quantity";
  const MUST_BE_REFERENCED = [`${ICM}Target`, `${ICM}Context`, LOG_CONDITION, QUAN_QUANTITY];
  const needsRef: Array<{ uri: string; type: string }> = [];
  for (const t of MUST_BE_REFERENCED)
    for (const q of store.getQuads(null, `${RDF}type`, t, null))
      needsRef.push({ uri: q.subject.value, type: t });

  const pointedAt = new Set<string>();
  for (const q of store.getQuads(null, null, null, null)) {
    if (q.object.termType === "NamedNode") pointedAt.add(q.object.value);
  }
  for (const { uri, type } of needsRef) {
    if (pointedAt.has(uri)) continue;
    warnings.push({
      code: "UNREFERENCED_RESOURCE",
      subject: sn(uri),
      message: `${sn(uri)} is typed as ${sn(type)} but no other resource points at it. An intent handler will never associate it with the intent — connect it (e.g. via icm:target, icm:context) or remove it.`,
    });
  }

  return {
    ok: errors.length === 0,
    errors,
    warnings,
    stats: {
      quads: store.size,
      intents: intents.length,
      expectations: expectationSubjects.size,
      targets: store.getQuads(null, `${RDF}type`, `${ICM}Target`, null).length,
    },
  };
}

function issue(code: string, message: string, subject?: string): Issue {
  return { code, message, ...(subject ? { subject } : {}) };
}

function isObject(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

function requireString(obj: Record<string, unknown>, key: string, errors: Issue[], subject: string) {
  if (typeof obj[key] !== "string" || !String(obj[key]).trim()) {
    errors.push(issue("JSONLD_REQUIRED_STRING", `${subject}.${key} must be a non-empty string.`, subject));
  }
}

function requireLiteral(
  obj: Record<string, unknown>,
  key: string,
  expected: string,
  code: string,
  errors: Issue[],
  subject: string
) {
  if (obj[key] !== expected) {
    errors.push(issue(code, `${subject}.${key} must be "${expected}".`, subject));
  }
}

function validateEnterpriseVpnSlaShape(doc: Record<string, unknown>, errors: Issue[]) {
  requireLiteral(doc, "ontologyType", "evsla:EnterpriseVpnSlaIntent", "JSONLD_EVSLA_INTENT_TYPE", errors, "$");

  if (!isObject(doc.tenant)) {
    errors.push(issue("JSONLD_EVSLA_TENANT", "$.tenant must be an evsla:Tenant object.", "$.tenant"));
  } else {
    requireString(doc.tenant, "id", errors, "$.tenant");
    requireString(doc.tenant, "name", errors, "$.tenant");
    requireLiteral(doc.tenant, "@type", "evsla:Tenant", "JSONLD_EVSLA_TENANT", errors, "$.tenant");
  }

  const expectations = Array.isArray(doc.intentExpectation) ? doc.intentExpectation : [];
  expectations.forEach((raw, idx) => {
    if (!isObject(raw)) return;
    const subject = `$.intentExpectation[${idx}]`;
    requireLiteral(raw, "ontologyType", "evsla:SlaExpectation", "JSONLD_EVSLA_EXPECTATION_TYPE", errors, subject);

    if (isObject(raw.expectationObject)) {
      requireLiteral(
        raw.expectationObject,
        "ontologyType",
        "evsla:EnterpriseVpnService",
        "JSONLD_EVSLA_SERVICE_TARGET",
        errors,
        `${subject}.expectationObject`
      );
    }

    const targets = Array.isArray(raw.expectationTarget) ? raw.expectationTarget : [];
    targets.forEach((target, targetIdx) => {
      if (!isObject(target)) return;
      const targetSubject = `${subject}.expectationTarget[${targetIdx}]`;
      for (const key of [
        "evsla:hasMetric",
        "evsla:hasThreshold",
        "evsla:hasStatistic",
        "evsla:hasScope",
        "evsla:hasMeasurementMethod",
        "evsla:hasTimeWindow",
      ]) {
        if (!(key in target)) {
          errors.push(issue("JSONLD_EVSLA_TARGET_FIELD", `${targetSubject}.${key} is required.`, targetSubject));
        }
      }
      if (typeof target.targetProperty === "string" && !target.targetProperty.startsWith("evsla:")) {
        errors.push(
          issue("JSONLD_EVSLA_TARGET_PROPERTY", `${targetSubject}.targetProperty must use evsla vocabulary.`, targetSubject)
        );
      }
      if (!isObject(target["evsla:hasThreshold"])) {
        errors.push(
          issue("JSONLD_EVSLA_THRESHOLD", `${targetSubject}.evsla:hasThreshold must be a quantity object.`, targetSubject)
        );
      }
    });
  });

  const contexts = Array.isArray(doc.intentContext) ? doc.intentContext : [];
  const topologyContext = contexts.find(
    (context) => isObject(context) && context.ontologyType === "evsla:HubAndSpokeTopology"
  );
  if (!isObject(topologyContext)) {
    errors.push(
      issue(
        "JSONLD_EVSLA_TOPOLOGY_CONTEXT",
        "$.intentContext must include an evsla:HubAndSpokeTopology context.",
        "$.intentContext"
      )
    );
    return;
  }

  if (!isObject(topologyContext["evsla:hasHub"])) {
    errors.push(issue("JSONLD_EVSLA_HUB", "Hub-and-spoke context must include evsla:hasHub.", "$.intentContext"));
  }
  if (!Array.isArray(topologyContext["evsla:hasSpoke"]) || topologyContext["evsla:hasSpoke"].length === 0) {
    errors.push(issue("JSONLD_EVSLA_SPOKE", "Hub-and-spoke context must include evsla:hasSpoke.", "$.intentContext"));
  }
}

export function validateJsonLd(text: string): JsonLdValidationReport {
  const errors: Issue[] = [];
  const warnings: Issue[] = [];
  let doc: unknown;

  try {
    doc = JSON.parse(text);
  } catch (e) {
    return {
      ok: false,
      errors: [issue("JSON_PARSE_ERROR", (e as Error).message)],
      warnings,
      stats: { expectations: 0, propertyExpectations: 0, contexts: 0 },
    };
  }

  if (!isObject(doc)) {
    return {
      ok: false,
      errors: [issue("JSONLD_TOP_LEVEL_OBJECT", "Top-level JSON-LD value must be an object.")],
      warnings,
      stats: { expectations: 0, propertyExpectations: 0, contexts: 0 },
    };
  }

  requireString(doc, "@context", errors, "$");
  requireString(doc, "@type", errors, "$");
  requireString(doc, "id", errors, "$");
  requireString(doc, "name", errors, "$");
  requireString(doc, "description", errors, "$");
  if (doc["@type"] !== "Intent") {
    errors.push(issue("JSONLD_INTENT_TYPE", '$.@type must be "Intent".', "$"));
  }

  if (!isObject(doc.intentOwner)) {
    errors.push(issue("JSONLD_INTENT_OWNER", "$.intentOwner must be an object.", "$.intentOwner"));
  } else {
    requireString(doc.intentOwner, "id", errors, "$.intentOwner");
    requireString(doc.intentOwner, "name", errors, "$.intentOwner");
  }

  const expectations = Array.isArray(doc.intentExpectation) ? doc.intentExpectation : [];
  if (!Array.isArray(doc.intentExpectation) || expectations.length === 0) {
    errors.push(issue("JSONLD_EXPECTATIONS", "$.intentExpectation must be a non-empty array.", "$.intentExpectation"));
  }

  let propertyExpectations = 0;
  expectations.forEach((raw, idx) => {
    const subject = `$.intentExpectation[${idx}]`;
    if (!isObject(raw)) {
      errors.push(issue("JSONLD_EXPECTATION_OBJECT", `${subject} must be an object.`, subject));
      return;
    }

    requireString(raw, "id", errors, subject);
    requireString(raw, "name", errors, subject);
    requireString(raw, "description", errors, subject);
    requireString(raw, "@type", errors, subject);

    const type = raw["@type"];
    if (type !== "DeliveryExpectation" && type !== "PropertyExpectation") {
      errors.push(
        issue(
          "JSONLD_EXPECTATION_TYPE",
          `${subject}.@type must be DeliveryExpectation or PropertyExpectation.`,
          subject
        )
      );
    }

    if (!isObject(raw.expectationObject)) {
      errors.push(issue("JSONLD_EXPECTATION_OBJECT_REF", `${subject}.expectationObject must be an object.`, subject));
    } else {
      requireString(raw.expectationObject, "id", errors, `${subject}.expectationObject`);
      requireString(raw.expectationObject, "name", errors, `${subject}.expectationObject`);
      requireString(raw.expectationObject, "@type", errors, `${subject}.expectationObject`);
    }

    const targets = Array.isArray(raw.expectationTarget) ? raw.expectationTarget : [];
    if (!Array.isArray(raw.expectationTarget) || targets.length === 0) {
      errors.push(issue("JSONLD_EXPECTATION_TARGET", `${subject}.expectationTarget must be a non-empty array.`, subject));
    }

    if (type === "PropertyExpectation") {
      propertyExpectations++;
      targets.forEach((target, targetIdx) => {
        const tSubject = `${subject}.expectationTarget[${targetIdx}]`;
        if (!isObject(target)) {
          errors.push(issue("JSONLD_TARGET_OBJECT", `${tSubject} must be an object.`, tSubject));
          return;
        }
        requireString(target, "name", errors, tSubject);
        requireString(target, "targetProperty", errors, tSubject);
        requireString(target, "matchCondition", errors, tSubject);
        if (!isObject(target.targetValue)) {
          errors.push(issue("JSONLD_TARGET_VALUE", `${tSubject}.targetValue must be an object.`, tSubject));
        }
      });
    }
  });

  if (!Array.isArray(doc.intentContext)) {
    errors.push(issue("JSONLD_CONTEXT_ARRAY", "$.intentContext must be an array.", "$.intentContext"));
  }
  if (!isObject(doc.intentReport)) {
    errors.push(issue("JSONLD_INTENT_REPORT", "$.intentReport must be an object.", "$.intentReport"));
  }

  validateEnterpriseVpnSlaShape(doc, errors);

  return {
    ok: errors.length === 0,
    errors,
    warnings,
    stats: {
      expectations: expectations.length,
      propertyExpectations,
      contexts: Array.isArray(doc.intentContext) ? doc.intentContext.length : 0,
    },
  };
}
