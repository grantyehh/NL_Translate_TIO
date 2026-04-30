#!/usr/bin/env bun
// Convert TIO .ttl files in ../ttls into ONE skill PER module at
// ../skills/tio-<module-slug>/SKILL.md, with each skill's description
// narrowly targeted so the agent only loads what's relevant (progressive
// disclosure). Symlinks each into ../.claude/skills/ for Claude Code.

import { Parser, Store } from "n3";
import * as fs from "node:fs";
import * as path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const ROOT = path.resolve(__dirname, "..");
const TTL_DIR = path.join(ROOT, "ttls");
const SKILLS_DIR = path.join(ROOT, "skills");
const LOCAL_SKILL_PARENT = path.join(ROOT, ".claude", "skills");

const RDF = "http://www.w3.org/1999/02/22-rdf-syntax-ns#";
const RDFS = "http://www.w3.org/2000/01/rdf-schema#";
const OWL = "http://www.w3.org/2002/07/owl#";

// TIO's official short prefixes (as declared in the .ttl files).
// Note MathFunctions is declared WITHOUT a trailing slash upstream —
// that's not our mistake, so we match it that way.
const NS_PREFIX: Record<string, string> = {
  "http://tio.models.tmforum.org/tio/v3.6.0/IntentCommonModel/": "icm",
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
// Sort longest-first so startsWith matching picks the most specific namespace
// (protects against one namespace being a substring of another).
const NS_KEYS_LONGEST = Object.keys(NS_PREFIX).sort((a, b) => b.length - a.length);

interface ModuleMeta {
  prefix: string;
  slug: string;
  title: string;
  description: string;
  isCore?: boolean;
}

const MODULES: ModuleMeta[] = [
  {
    prefix: "icm",
    slug: "tio-intent-common-model",
    title: "IntentCommonModel (icm)",
    isCore: true,
    description:
      "ALWAYS load when emitting ANY TIO Turtle. Core TIO classes (icm:Intent, icm:Expectation with DeliveryExpectation/PropertyExpectation/ReportingExpectation subclasses, icm:Target, icm:Context), canonical turtle patterns, and the hallucination blacklist.",
  },
  {
    prefix: "log",
    slug: "tio-logical-operators",
    title: "LogicalOperators (log)",
    description:
      "Load when the intent involves conditions ('if X then Y'), logical AND/OR/NOT combinators, trigger-based behavior, or references the class log:Condition.",
  },
  {
    prefix: "set",
    slug: "tio-set-operators",
    title: "SetOperators (set)",
    description:
      "Load when the intent references sets, membership, union/intersection, or aggregation operations over targets or property values.",
  },
  {
    prefix: "fun",
    slug: "tio-function-ontology",
    title: "FunctionOntology (fun)",
    description:
      "Load when the intent references functions, procedures, function signatures, parameter binding, or functional composition.",
  },
  {
    prefix: "quan",
    slug: "tio-quantity",
    title: "QuantityOntology (quan)",
    description:
      "Load when the intent specifies numeric quantities with units (Mbps, milliseconds, percentages, packet counts, etc.).",
  },
  {
    prefix: "met",
    slug: "tio-metrics-observations",
    title: "MetricsAndObservations (met)",
    description:
      "Load when the intent references metrics, KPIs, states, or observable properties of a target — latency, throughput, packet loss, availability, signal strength, etc.",
  },
  {
    prefix: "mf",
    slug: "tio-math-functions",
    title: "MathFunctions (mf)",
    description:
      "Load when the intent uses comparison operators (>, <, =, ≠, ≥, ≤), logistic/polynomial functions, or arithmetic expressions over property values.",
  },
  {
    prefix: "ut",
    slug: "tio-utility",
    title: "Utility (ut)",
    description:
      "Load only if no other TIO module covers the predicate you need — miscellaneous utility classes/predicates.",
  },
  {
    prefix: "imo",
    slug: "tio-intent-management",
    title: "IntentManagementOntology (imo)",
    description:
      "Load when modeling intent lifecycle, intent-handler relationships, ownership, or management metadata — as opposed to expressing the intent content itself.",
  },
  {
    prefix: "ig",
    slug: "tio-intent-guarantee",
    title: "IntentGuaranteeOntology (ig)",
    description:
      "Load when the intent carries SLA-style guarantees, service-level commitments, or assurance semantics beyond plain expectations.",
  },
  {
    prefix: "pro",
    slug: "tio-intent-probing",
    title: "IntentProbing (pro)",
    description:
      "Load when the intent involves probing, proposal requests, or what-if queries against an intent handler.",
  },
  {
    prefix: "insp",
    slug: "tio-intent-specification",
    title: "IntentSpecification (insp)",
    description:
      "Load when modeling intent specifications or intent templates — blueprints/schemas for intent instances rather than individual intents.",
  },
  {
    prefix: "iv",
    slug: "tio-intent-validity",
    title: "IntentValidityOntology (iv)",
    description:
      "Load when the intent has validity windows, expiry times, effective periods, or scheduled activation/deactivation.",
  },
  {
    prefix: "pre",
    slug: "tio-preference",
    title: "PreferenceOfHandlingOutcomes (pre)",
    description:
      "Load when the intent expresses preferences or priorities between alternative handling outcomes (trade-off semantics).",
  },
  {
    prefix: "pbi",
    slug: "tio-proposal-best-intent",
    title: "ProposalBestIntent (pbi)",
    description:
      "Load when the intent involves proposal/best-intent selection semantics across multiple candidate intents.",
  },
];

// ------------------------------------------------------------------
// Load all ttls (combined — they cross-reference each other's prefixes)
// ------------------------------------------------------------------
const store = new Store();
const files = fs.readdirSync(TTL_DIR).filter((f) => f.endsWith(".ttl")).sort();
const combined = files
  .map((f) => `# ---- ${f} ----\n${fs.readFileSync(path.join(TTL_DIR, f), "utf-8")}`)
  .join("\n\n");
try {
  store.addQuads(new Parser().parse(combined));
} catch (e) {
  console.error("combined parse failed:", (e as Error).message);
  process.exit(1);
}
console.log(`loaded ${files.length} ttl files, ${store.size} quads`);

// ------------------------------------------------------------------
// Helpers
// ------------------------------------------------------------------
function literalEn(subject: string, predicate: string): string | undefined {
  const quads = store.getQuads(subject, predicate, null, null);
  for (const q of quads)
    if (q.object.termType === "Literal" && (q.object as any).language === "en")
      return q.object.value;
  for (const q of quads) if (q.object.termType === "Literal") return q.object.value;
  return undefined;
}
function objectUris(subject: string, predicate: string): string[] {
  return store
    .getQuads(subject, predicate, null, null)
    .filter((q) => q.object.termType === "NamedNode")
    .map((q) => q.object.value);
}
function subjectsOfType(typeUri: string): string[] {
  return store.getQuads(null, `${RDF}type`, typeUri, null).map((q) => q.subject.value);
}
function nsOf(uri: string): string {
  // Prefer an exact startsWith match against known TIO namespaces (handles
  // the mf: no-trailing-slash anomaly); fall back to last /# split.
  for (const ns of NS_KEYS_LONGEST) if (uri.startsWith(ns)) return ns;
  const m = uri.match(/^(.+[\/#])[^\/#]+$/);
  return m ? m[1] : uri;
}
function shortName(uri: string): string {
  const ns = nsOf(uri);
  if (NS_PREFIX[ns]) return `${NS_PREFIX[ns]}:${uri.slice(ns.length)}`;
  if (uri.startsWith(RDF)) return `rdf:${uri.slice(RDF.length)}`;
  if (uri.startsWith(RDFS)) return `rdfs:${uri.slice(RDFS.length)}`;
  if (uri.startsWith(OWL)) return `owl:${uri.slice(OWL.length)}`;
  return `<${uri}>`;
}
function oneLine(s?: string): string | undefined {
  return s?.replace(/\s+/g, " ").trim();
}

// ------------------------------------------------------------------
// Bucket classes / properties by prefix
// ------------------------------------------------------------------
const FUN_FUNCTION = "http://tio.models.tmforum.org/tio/v3.6.0/FunctionOntology/Function";
const FUN_RESULT_TYPE = "http://tio.models.tmforum.org/tio/v3.6.0/FunctionOntology/resultType";
const FUN_ARGUMENT_TYPES =
  "http://tio.models.tmforum.org/tio/v3.6.0/FunctionOntology/argumentTypes";

const classTypes = [`${RDFS}Class`, `${OWL}Class`];
const propTypes = [
  `${RDF}Property`,
  `${OWL}ObjectProperty`,
  `${OWL}DatatypeProperty`,
  `${OWL}AnnotationProperty`,
];
const classSet = new Set<string>();
for (const t of classTypes) for (const u of subjectsOfType(t)) classSet.add(u);
const propSet = new Set<string>();
for (const t of propTypes) for (const u of subjectsOfType(t)) propSet.add(u);
// Functions (set:, math:, and some fun: predicates) are modeled as instances of fun:Function
// rather than as classes or rdf:Property — treat them as a third category.
const funcSet = new Set<string>(subjectsOfType(FUN_FUNCTION));

type Bucket = { classes: string[]; properties: string[]; functions: string[] };
const byPrefix: Record<string, Bucket> = {};
const bucket = (p: string) => (byPrefix[p] ??= { classes: [], properties: [], functions: [] });
for (const c of classSet) {
  const p = NS_PREFIX[nsOf(c)];
  if (p) bucket(p).classes.push(c);
}
for (const p of propSet) {
  const pfx = NS_PREFIX[nsOf(p)];
  if (pfx) bucket(pfx).properties.push(p);
}
for (const f of funcSet) {
  const p = NS_PREFIX[nsOf(f)];
  if (p) bucket(p).functions.push(f);
}

// ------------------------------------------------------------------
// Render fragments
// ------------------------------------------------------------------
function prefixBlock(): string {
  const lines = ["```turtle"];
  for (const [ns, pfx] of Object.entries(NS_PREFIX)) lines.push(`@prefix ${pfx}: <${ns}> .`);
  lines.push("@prefix rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .");
  lines.push("@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .");
  lines.push("@prefix owl:  <http://www.w3.org/2002/07/owl#> .");
  lines.push("```");
  return lines.join("\n");
}

const BLACKLIST = `## Hallucination Blacklist

These predicates look plausible but **do not exist in TIO**. Never emit them:

- \`icm:hasValue\` ❌ — use \`icm:valuesOfTargetProperty\` with a paired values resource
- \`icm:hasProperty\` ❌ — target properties are modeled implicitly via \`icm:PropertyExpectation\`
- \`icm:condition\` ❌ — use the **class** \`log:Condition\` (from the \`tio-logical-operators\` skill)
- \`icm:expectation\` ❌ — Expectations are independent resources; they link to Intent via their own target, not the other way round

If a predicate you want isn't listed in a TIO skill, **it does not exist**. Re-model instead of inventing.
`;

const PATTERNS = `## Canonical Patterns

### 1. Delivery — "Provide service X"
\`\`\`turtle
ex:intent a icm:Intent .
ex:exp-del a icm:DeliveryExpectation ;
  icm:target ex:tgt ;
  rdfs:comment "Deliver an enterprise 5G slice service."@en .
ex:tgt a icm:Target ;
  rdfs:comment "Connectivity scope between Kaohsiung and Pingtung."@en .
\`\`\`

### 2. Property — "Ensure metric X < Y on target Z"
\`\`\`turtle
ex:tgt a icm:Target ;
  rdfs:comment "Video conferencing traffic."@en .
ex:exp-latency a icm:PropertyExpectation ;
  icm:target ex:tgt ;
  rdfs:comment "Latency should stay below 20 ms."@en .
ex:target-property-values icm:valuesOfTargetProperty rdf:value .
\`\`\`

### 3. Multiple properties on one target
\`\`\`turtle
ex:tgt a icm:Target ;
  rdfs:comment "Enterprise backup connectivity."@en .
ex:exp-throughput a icm:PropertyExpectation ;
  icm:target ex:tgt ;
  rdfs:comment "Downlink throughput should be greater than 200 Mbps."@en .
ex:exp-latency a icm:PropertyExpectation ;
  icm:target ex:tgt ;
  rdfs:comment "Latency should stay below 15 ms."@en .
ex:target-property-values icm:valuesOfTargetProperty rdf:value .
\`\`\`

### 4. Context — "During time window X, do Y"
\`\`\`turtle
ex:intent a icm:Intent ;
  icm:context ex:ctx .
ex:ctx a icm:Context ;
  rdfs:comment "Weekend evening time window."@en .
\`\`\`

### 5. Condition — "If X, then Y" (needs \`tio-logical-operators\`)
\`\`\`turtle
@prefix log: <http://tio.models.tmforum.org/tio/v3.6.0/LogicalOperators/> .
ex:cond a log:Condition ;
  rdfs:comment "Backhaul latency is greater than 15 ms."@en .
\`\`\`
`;

function renderClassesAndProperties(b: Bucket): string {
  const lines: string[] = [];
  b.classes.sort();
  b.properties.sort();
  if (b.classes.length) {
    lines.push("## Classes", "");
    for (const c of b.classes) {
      const supers = objectUris(c, `${RDFS}subClassOf`).map(shortName);
      const cmt = oneLine(literalEn(c, `${RDFS}comment`) ?? literalEn(c, `${RDFS}Comment`));
      lines.push(`- **${shortName(c)}**${supers.length ? ` — subClassOf: ${supers.join(", ")}` : ""}`);
      if (cmt) lines.push(`  - ${cmt}`);
    }
    lines.push("");
  }
  if (b.properties.length) {
    lines.push("## Properties", "");
    for (const p of b.properties) {
      const doms = objectUris(p, `${RDFS}domain`).map(shortName);
      const rngs = objectUris(p, `${RDFS}range`).map(shortName);
      const supers = objectUris(p, `${RDFS}subPropertyOf`).map(shortName);
      const cmt = oneLine(literalEn(p, `${RDFS}comment`) ?? literalEn(p, `${RDFS}Comment`));
      const meta: string[] = [];
      if (doms.length) meta.push(`domain: ${doms.join(" | ")}`);
      if (rngs.length) meta.push(`range: ${rngs.join(" | ")}`);
      if (supers.length) meta.push(`subPropertyOf: ${supers.join(", ")}`);
      lines.push(`- **${shortName(p)}**${meta.length ? ` — ${meta.join("; ")}` : ""}`);
      if (cmt) lines.push(`  - ${cmt}`);
    }
    lines.push("");
  }
  if (b.functions.length) {
    b.functions.sort();
    lines.push("## Functions / Operators", "");
    lines.push("_Modeled as instances of `fun:Function`. Use in condition expressions or wherever a function reference is expected._", "");
    for (const f of b.functions) {
      const result = objectUris(f, FUN_RESULT_TYPE).map(shortName);
      const cmt = oneLine(literalEn(f, `${RDFS}comment`) ?? literalEn(f, `${RDFS}Comment`));
      const meta: string[] = [];
      if (result.length) meta.push(`returns: ${result.join(" | ")}`);
      lines.push(`- **${shortName(f)}**${meta.length ? ` — ${meta.join("; ")}` : ""}`);
      if (cmt) lines.push(`  - ${cmt}`);
    }
    lines.push("");
  }
  return lines.join("\n");
}

// ------------------------------------------------------------------
// Clean up any legacy / stale skills (previous single-skill output)
// ------------------------------------------------------------------
function cleanDir(parent: string) {
  if (!fs.existsSync(parent)) return;
  for (const name of fs.readdirSync(parent)) {
    if (name.startsWith("tio-") || name === "tio-ontology") {
      fs.rmSync(path.join(parent, name), { recursive: true, force: true });
    }
  }
}
cleanDir(SKILLS_DIR);
cleanDir(LOCAL_SKILL_PARENT);
fs.mkdirSync(SKILLS_DIR, { recursive: true });
fs.mkdirSync(LOCAL_SKILL_PARENT, { recursive: true });

// ------------------------------------------------------------------
// Emit one skill per module
// ------------------------------------------------------------------
const stats: {
  slug: string;
  classes: number;
  properties: number;
  functions: number;
  bytes: number;
}[] = [];

for (const m of MODULES) {
  const b = byPrefix[m.prefix];
  if (!b || (!b.classes.length && !b.properties.length && !b.functions.length)) {
    console.log(`skip empty module: ${m.prefix}`);
    continue;
  }
  const parts: string[] = [];
  parts.push("---");
  parts.push(`name: ${m.slug}`);
  parts.push(`description: ${m.description}`);
  parts.push("---");
  parts.push("");
  parts.push(`# ${m.title}`);
  parts.push("");
  parts.push(
    `_Auto-generated from \`~/grant/ttls/*.ttl\`. Regenerate with \`bun run scripts/ttl-to-skills.ts\`._`
  );
  parts.push("");
  if (!m.isCore) {
    parts.push(
      `> Always combine with the \`tio-intent-common-model\` skill — that skill owns the core Intent/Expectation/Target vocabulary this module extends.`
    );
    parts.push("");
  }
  if (m.isCore) {
    parts.push(BLACKLIST);
  }
  parts.push("## Prefixes", "");
  parts.push(prefixBlock());
  parts.push("");
  parts.push(renderClassesAndProperties(b));
  if (m.isCore) parts.push(PATTERNS);

  const outText = parts.join("\n");
  const skillDir = path.join(SKILLS_DIR, m.slug);
  fs.mkdirSync(skillDir, { recursive: true });
  fs.writeFileSync(path.join(skillDir, "SKILL.md"), outText);

  const linkPath = path.join(LOCAL_SKILL_PARENT, m.slug);
  const linkTarget = path.join("..", "..", "skills", m.slug);
  fs.symlinkSync(linkTarget, linkPath, "dir");

  stats.push({
    slug: m.slug,
    classes: b.classes.length,
    properties: b.properties.length,
    functions: b.functions.length,
    bytes: outText.length,
  });
}

console.log("");
console.log(`generated ${stats.length} skills:`);
const pad = (s: string, n: number) => s.padEnd(n);
for (const s of stats) {
  console.log(
    `  ${pad(s.slug, 32)} ${String(s.classes).padStart(3)} cls, ${String(s.properties).padStart(3)} props, ${String(s.functions).padStart(3)} fns, ${String(s.bytes).padStart(6)} bytes`
  );
}
const totalBytes = stats.reduce((a, s) => a + s.bytes, 0);
console.log(`  total: ${totalBytes} bytes across ${stats.length} skills`);
