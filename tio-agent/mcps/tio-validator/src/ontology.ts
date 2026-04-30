// Load every TIO .ttl into one store at startup and index the URIs that are
// legitimately declared — classes, properties, and fun:Function instances.
// The validator compares the agent's output predicates/classes against this set.

import { Parser, Store } from "n3";
import * as fs from "node:fs";
import * as path from "node:path";

const RDF = "http://www.w3.org/1999/02/22-rdf-syntax-ns#";
const RDFS = "http://www.w3.org/2000/01/rdf-schema#";
const OWL = "http://www.w3.org/2002/07/owl#";
const FUN_FUNCTION = "http://tio.models.tmforum.org/tio/v3.6.0/FunctionOntology/Function";
const TIO_ROOT = "http://tio.models.tmforum.org/tio/v3.6.0/";

export interface Ontology {
  classes: Set<string>;
  predicates: Set<string>;
  functions: Set<string>;
  tioRoot: string;
}

export function loadOntology(ttlDir: string): Ontology {
  const store = new Store();
  const parser = new Parser();
  // Sort for deterministic order — IntentCommonModel must load before files
  // that reference icm: without redeclaring the prefix.
  const files = fs.readdirSync(ttlDir).filter((f) => f.endsWith(".ttl")).sort();
  const combined = files
    .map((f) => fs.readFileSync(path.join(ttlDir, f), "utf-8"))
    .join("\n\n");
  store.addQuads(parser.parse(combined));

  const classes = new Set<string>();
  const predicates = new Set<string>();
  const functions = new Set<string>();

  const classTypes = [`${RDFS}Class`, `${OWL}Class`];
  const propTypes = [
    `${RDF}Property`,
    `${OWL}ObjectProperty`,
    `${OWL}DatatypeProperty`,
    `${OWL}AnnotationProperty`,
  ];
  for (const t of classTypes)
    for (const q of store.getQuads(null, `${RDF}type`, t, null)) classes.add(q.subject.value);
  for (const t of propTypes)
    for (const q of store.getQuads(null, `${RDF}type`, t, null)) predicates.add(q.subject.value);
  for (const q of store.getQuads(null, `${RDF}type`, FUN_FUNCTION, null))
    functions.add(q.subject.value);

  return { classes, predicates, functions, tioRoot: TIO_ROOT };
}
