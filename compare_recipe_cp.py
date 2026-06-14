#!/usr/bin/env python3
"""Recipe CP table: semantic quality vs token cost over the 5 conditions.

Arm 1 (LLM-only-strong) vs the floor (LLM-only-weak) vs the three independent
Arm-2 retrieval recipes (graphrag/kge/kag _weak). Each scored separately; never
mixed.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
P1 = ROOT / "phase1"
CONDITIONS = [
    ("LLM-only-strong", "llm_only"),
    ("LLM-only-weak", "llm_only_weak"),
    ("GraphRag-weak", "graphrag_weak"),
    ("KGE-weak", "kge_weak"),
    ("KAG-weak", "kag_weak"),
]
DIMS = ["metric", "threshold", "statistic", "scope", "measurement_method",
        "time_window", "operator", "tenant", "topology", "contract", "precision"]


def load(p):
    return json.load(open(p)) if p.is_file() else None


def main():
    rows = []
    for name, key in CONDITIONS:
        q = load(P1 / f"phase1_{key}.json")
        t = load(P1 / "token_usage" / f"token_usage_{key}.json")
        if not q:
            rows.append((name, None))
            continue
        sem = [x["semantic"] for x in q if x.get("semantic")]
        n = len(sem) or 1
        comp = sum(s["composite"] for s in sem) / n
        dims = {d: sum(s["dimensions"].get(d, 0.0) for s in sem) / n for d in DIMS}
        parse_ok = sum(1 for x in q if x.get("parse_ok")) / len(q)
        tok = sum(int(e.get("total_tokens", 0) or 0) for e in t) if t else 0
        rows.append((name, dict(comp=comp, dims=dims, parse=parse_ok, tok=tok, cases=len(q))))

    print("Recipe CP — semantic quality vs token cost")
    print("=" * 92)
    hdr = (f"{'Condition':16} | {'Parse':6} | {'Composite':9} | {'TotalTok':10} | "
           f"{'Tok/case':9} | {'CP(comp/ktok)':13}")
    print(hdr)
    print("-" * len(hdr))
    for name, r in rows:
        if r is None:
            print(f"{name:16} | (no data)")
            continue
        per = r["tok"] // r["cases"] if r["cases"] else 0
        cp = (r["comp"] / (per / 1000)) if per else 0.0
        print(f"{name:16} | {r['parse']*100:5.0f}% | {r['comp']:9.4f} | {r['tok']:10,} | "
              f"{per:9,} | {cp:13.3f}")

    print()
    print("Per-dimension (semantic):")
    dh = f"{'Condition':16} | " + " | ".join(f"{d[:5]:>5}" for d in DIMS)
    print(dh)
    print("-" * len(dh))
    for name, r in rows:
        if r is None:
            continue
        print(f"{name:16} | " + " | ".join(f"{r['dims'][d]:5.2f}" for d in DIMS))


if __name__ == "__main__":
    main()
