// Build the TIO mechanism deck.
// Usage: node scripts/build_deck.js
//
// Output: mechanism_deck.pptx at repo root.

const pptxgen = require("pptxgenjs");
const path = require("path");

const ROOT = path.resolve(__dirname, "..");
const DIAG = path.join(ROOT, "docs", "diagrams");

const COLORS = {
  navy:       "21295C",
  navyLight:  "CADCFC",
  deepBlue:   "065A82",
  teal:       "1C7293",
  bg:         "F8FAFC",
  cardBg:     "FFFFFF",
  text:       "1E293B",
  muted:      "64748B",
  border:     "E2E8F0",
  graphrag:   "065A82", // deep blue
  kge:        "0D9488", // teal-green
  kag:        "B85042", // terracotta
  gold:       "D97706",
  green:      "059669",
};

const FONTS = {
  header: "Georgia",
  body:   "Calibri",
  mono:   "Consolas",
};

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13.3" x 7.5"
pres.author = "Grant";
pres.title  = "TIO Experiment — Mechanism Deck";

const W = 13.3, H = 7.5;

// ----- Helpers -----
function titleBar(slide, title, subtitle, accent = COLORS.navy) {
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0.35, w: 0.18, h: 1.0,
    fill: { color: accent }, line: { color: accent, width: 0 },
  });
  slide.addText(title, {
    x: 0.45, y: 0.30, w: W - 0.9, h: 0.7,
    fontSize: 28, fontFace: FONTS.header, bold: true,
    color: COLORS.navy, valign: "middle", margin: 0,
  });
  if (subtitle) {
    slide.addText(subtitle, {
      x: 0.45, y: 0.95, w: W - 0.9, h: 0.45,
      fontSize: 14, fontFace: FONTS.body, italic: true,
      color: COLORS.muted, valign: "middle", margin: 0,
    });
  }
}

function footer(slide, page, total, sectionLabel = "") {
  slide.addText(
    sectionLabel ? `TIO Experiment / Mechanism / ${sectionLabel}` : "TIO Experiment / Mechanism",
    {
      x: 0.5, y: H - 0.4, w: 8, h: 0.3,
      fontSize: 9, fontFace: FONTS.body, color: COLORS.muted, italic: true, margin: 0,
    }
  );
  slide.addText(`${page} / ${total}`, {
    x: W - 1.2, y: H - 0.4, w: 0.7, h: 0.3,
    fontSize: 9, fontFace: FONTS.body, color: COLORS.muted, align: "right", margin: 0,
  });
}

// Build a card with a left accent bar; returns the inner content box rect.
function card(slide, { x, y, w, h, accent, headerText, headerSize = 14 }) {
  slide.addShape(pres.shapes.RECTANGLE, {
    x, y, w, h,
    fill: { color: COLORS.cardBg },
    line: { color: COLORS.border, width: 1 },
    shadow: { type: "outer", color: "000000", opacity: 0.06, blur: 6, offset: 2, angle: 90 },
  });
  slide.addShape(pres.shapes.RECTANGLE, {
    x, y, w: 0.08, h,
    fill: { color: accent }, line: { color: accent, width: 0 },
  });
  if (headerText) {
    slide.addText(headerText, {
      x: x + 0.25, y: y + 0.12, w: w - 0.4, h: 0.4,
      fontSize: headerSize, fontFace: FONTS.header, bold: true,
      color: COLORS.navy, margin: 0, valign: "middle",
    });
  }
}

// Aspect ratios of generated diagrams (pixel w/h)
const DIAGRAM_ASPECT = {
  graphrag: 1292 / 1543,
  kge:      1429 / 1949,
  kag:      1356 / 1561,
};

function computeImageBox(name, maxH, maxW) {
  const aspect = DIAGRAM_ASPECT[name];
  let h = maxH, w = h * aspect;
  if (w > maxW) { w = maxW; h = w / aspect; }
  return { w, h };
}

// ====================================================================
// Slide 1: Title
// ====================================================================
let total = 16;
let s = pres.addSlide();
s.background = { color: COLORS.navy };

// decorative left strip
s.addShape(pres.shapes.RECTANGLE, {
  x: 1.0, y: 2.3, w: 0.15, h: 2.2,
  fill: { color: COLORS.gold }, line: { color: COLORS.gold, width: 0 },
});

s.addText("NL → TIO JSON-LD", {
  x: 1.4, y: 2.2, w: 11, h: 1.0,
  fontSize: 52, fontFace: FONTS.header, bold: true, color: "FFFFFF", margin: 0,
});
s.addText("GraphRAG / KGE / KAG 三條 pipeline 的機制與比較", {
  x: 1.4, y: 3.3, w: 11, h: 0.7,
  fontSize: 22, fontFace: FONTS.header, color: COLORS.navyLight, margin: 0,
});
s.addText("以 TC001 為範例貫穿全文", {
  x: 1.4, y: 4.05, w: 11, h: 0.4,
  fontSize: 15, fontFace: FONTS.body, italic: true, color: "94A3B8", margin: 0,
});

s.addText([
  { text: "Grant Yeh", options: { fontSize: 13, color: "FFFFFF", bold: true, breakLine: true } },
  { text: "CHT TIO_Experiment / new-methods", options: { fontSize: 11, color: COLORS.navyLight, italic: true } },
], {
  x: 1.0, y: H - 1.2, w: 6, h: 0.7,
  fontFace: FONTS.body, margin: 0,
});

// ====================================================================
// Slide 2: Problem & Common Setup
// ====================================================================
s = pres.addSlide();
s.background = { color: COLORS.bg };
titleBar(s, "問題與共用元件", "三條 pipeline 解決同一個問題,在同一套基礎上比較");

// Input card
card(s, { x: 0.6, y: 1.7, w: 6.0, h: 2.3, accent: COLORS.green, headerText: "Input — Natural Language Intent" });
s.addText(
  "「確保星河銀行總部至所有分點之延遲在 95% 的時間內低於 50ms。」",
  {
    x: 0.95, y: 2.25, w: 5.5, h: 1.0,
    fontSize: 14, fontFace: FONTS.body, color: COLORS.text, italic: true, margin: 0, valign: "top",
  }
);
s.addText("中文 / 英文混雜的非結構化句子,常見模式:租戶 + 拓樸 + 度量 + 門檻 + 時間窗", {
  x: 0.95, y: 3.20, w: 5.5, h: 0.7,
  fontSize: 11, fontFace: FONTS.body, color: COLORS.muted, margin: 0,
});

// Output card
card(s, { x: 6.8, y: 1.7, w: 6.0, h: 2.3, accent: COLORS.gold, headerText: "Output — TIO JSON-LD" });
s.addText([
  { text: "@type: Intent", options: { fontFace: FONTS.mono, breakLine: true } },
  { text: "ontologyType: evsla:EnterpriseVpnSlaIntent", options: { fontFace: FONTS.mono, breakLine: true } },
  { text: "intentExpectation: [ evsla:SlaExpectation { latency, p95, ... } ]", options: { fontFace: FONTS.mono, breakLine: true } },
  { text: "intentContext: [ evsla:HubAndSpokeTopology ]", options: { fontFace: FONTS.mono, breakLine: true } },
  { text: "intentReport: { reportingInterval, handlerResponse }", options: { fontFace: FONTS.mono } },
], {
  x: 7.15, y: 2.25, w: 5.55, h: 1.6,
  fontSize: 10, color: COLORS.text, margin: 0, valign: "top",
});

// Shared bottom: common components
card(s, { x: 0.6, y: 4.4, w: 12.2, h: 2.4, accent: COLORS.deepBlue, headerText: "Common Components(三條都共用)" });
const sharedItems = [
  { label: "LLM 模型", value: "gpt-5.4 (temperature=0)" },
  { label: "Ontology", value: "TM Forum Intent Ontology v3.6.0 (TTL,14+ namespace)" },
  { label: "Test 資料", value: "test_cases_20.json (20 題);few_shot_samples.json" },
  { label: "Prompt 套件", value: "evsla_prompt.build_evsla_system_prompt(tc_id, retrieval_mode=...)" },
  { label: "評分器", value: "evaluate_jsonld.py:parse_ok / ontology / metric / verbosity" },
];
const sharedX = 0.95, sharedY = 4.95, rowH = 0.32;
sharedItems.forEach((it, i) => {
  s.addText([
    { text: it.label + " ", options: { bold: true, color: COLORS.navy } },
    { text: "—  ", options: { color: COLORS.muted } },
    { text: it.value, options: { color: COLORS.text, fontFace: FONTS.mono, fontSize: 10 } },
  ], {
    x: sharedX, y: sharedY + i * rowH, w: 11.6, h: rowH,
    fontSize: 11, fontFace: FONTS.body, margin: 0, valign: "middle",
  });
});

footer(s, 2, total);

// ====================================================================
// Slide 3: 術語表 — evsla:latency 是什麼
// ====================================================================
s = pres.addSlide();
s.background = { color: COLORS.bg };
titleBar(s, "術語表 — 簡報中的 evsla:latency 是什麼意思", "TIO 知識本體裡的「詞彙」,不是網頁連結。後面會反覆出現,先看一眼就好。");

// ---- 上卡:拆解 ----
const gdX = 0.6, gdY = 1.55, gdW = 12.23, gdH = 2.65;
card(s, { x: gdX, y: gdY, w: gdW, h: gdH, accent: COLORS.deepBlue, headerText: "evsla:latency 拆成兩半看" });

// 大字:evsla : latency(兩色區分)
s.addText([
  { text: "evsla",   options: { color: COLORS.kge,      bold: true } },
  { text: " : ",     options: { color: COLORS.muted } },
  { text: "latency", options: { color: COLORS.graphrag, bold: true } },
], {
  x: gdX, y: gdY + 0.55, w: gdW, h: 0.6,
  fontSize: 32, fontFace: FONTS.mono, align: "center", margin: 0,
});

// 拆解說明(兩行)
s.addText([
  { text: "evsla", options: { fontFace: FONTS.mono, color: COLORS.kge, bold: true } },
  { text: "        =  ", options: { color: COLORS.muted } },
  { text: "namespace 前綴 ", options: { color: COLORS.text, bold: true } },
  { text: "(指向「企業 VPN SLA」這個子本體論,等於「分類」)", options: { color: COLORS.muted, italic: true, breakLine: true } },
  { text: "latency", options: { fontFace: FONTS.mono, color: COLORS.graphrag, bold: true } },
  { text: "    =  ", options: { color: COLORS.muted } },
  { text: "詞彙名稱 ", options: { color: COLORS.text, bold: true } },
  { text: "(該本體論裡這個概念的具體名字)", options: { color: COLORS.muted, italic: true } },
], {
  x: gdX + 0.6, y: gdY + 1.25, w: gdW - 1.2, h: 0.6,
  fontSize: 12, fontFace: FONTS.body, margin: 0, valign: "top", paraSpaceAfter: 2,
});

// URI 完整 vs 簡寫
s.addText([
  { text: "完整形式(URI):   ", options: { bold: true, color: COLORS.navy } },
  { text: "http://tio.models.tmforum.org/tio/v3.6.0/EnterpriseVpnSlaOntology/latency", options: { fontFace: FONTS.mono, color: COLORS.muted, breakLine: true } },
  { text: "簡寫(CURIE):     ", options: { bold: true, color: COLORS.navy } },
  { text: "evsla:latency", options: { fontFace: FONTS.mono, color: COLORS.text, bold: true } },
  { text: "       ← 簡報後面看到都是這種寫法,不要當成網址點", options: { color: COLORS.muted, italic: true } },
], {
  x: gdX + 0.6, y: gdY + 1.95, w: gdW - 1.2, h: 0.6,
  fontSize: 11, fontFace: FONTS.body, margin: 0, valign: "top", paraSpaceAfter: 4,
});

// ---- 下卡:namespace 對照表 ----
const tcY = gdY + gdH + 0.18, tcH = 2.55;
card(s, { x: gdX, y: tcY, w: gdW, h: tcH, accent: COLORS.gold, headerText: "本簡報常見的 namespace 前綴" });

const nsRows = [
  [
    { text: "Prefix", options: { bold: true, color: "FFFFFF", fill: { color: COLORS.navy } } },
    { text: "完整 ontology 名", options: { bold: true, color: "FFFFFF", fill: { color: COLORS.navy } } },
    { text: "白話內容", options: { bold: true, color: "FFFFFF", fill: { color: COLORS.navy } } },
  ],
  ["evsla:", "EnterpriseVpnSlaOntology",   "企業 VPN SLA 詞彙(本實驗主領域)"],
  ["icm:",   "IntentCommonModel",          "Intent 結構基底 schema(Intent / Expectation / Target / Context)"],
  ["met:",   "MetricsAndObservations",     "量測與觀察的上位概念(metric / measurement)"],
  ["quan:",  "QuantityOntology",           "量值(value + unit,例如 50 ms)"],
  ["rdfs:",  "RDF Schema(W3C 標準)",      "subClassOf / subPropertyOf / label / comment"],
  ["rdf:",   "RDF(W3C 標準)",             "type(節點屬於哪一類)"],
].map((row, i) => {
  if (i === 0) return row;
  return [
    { text: row[0], options: { fontFace: FONTS.mono, bold: true, color: COLORS.graphrag } },
    { text: row[1], options: { fontFace: FONTS.mono, color: COLORS.text } },
    { text: row[2], options: { color: COLORS.text } },
  ];
});

s.addTable(nsRows, {
  x: gdX + 0.3, y: tcY + 0.55, w: gdW - 0.6,
  colW: [1.6, 3.8, 6.23],
  rowH: 0.27,
  fontSize: 11, fontFace: FONTS.body, color: COLORS.text,
  border: { type: "solid", color: COLORS.border, pt: 1 },
  fill: { color: COLORS.cardBg },
  margin: 5,
  valign: "middle",
});

footer(s, 3, total);

// ====================================================================
// Slide 4: Running Example TC001
// ====================================================================
s = pres.addSlide();
s.background = { color: COLORS.bg };
titleBar(s, "貫穿全文的範例:TC001", "Hub-and-Spoke SLA,複雜度 Simple");

// big NL intent card
card(s, { x: 0.6, y: 1.7, w: 12.2, h: 1.7, accent: COLORS.green, headerText: "NL Intent" });
s.addText(
  "「確保星河銀行總部至所有分點之延遲在 95% 的時間內低於 50ms。」",
  {
    x: 1.0, y: 2.25, w: 11.5, h: 1.0,
    fontSize: 22, fontFace: FONTS.header, italic: true, color: COLORS.text, margin: 0, valign: "middle",
  }
);

// Two columns: structured fields | expected ontology terms
card(s, { x: 0.6, y: 3.6, w: 6.0, h: 3.3, accent: COLORS.deepBlue, headerText: "結構化欄位(從 test_cases_20.json)" });
const fields = [
  ["tenant", "星河銀行"],
  ["hub", "台北總部"],
  ["spokes", "新竹分行 / 台中分行 / 高雄分行"],
  ["metric", "latency"],
  ["threshold", "< 50 ms"],
  ["compliance_window", "95% of time"],
  ["statistic", "evsla:p95"],
  ["scope", "evsla:hubToAllSpokes"],
  ["measurement", "evsla:twamp"],
  ["time_window", "evsla:fiveMinuteWindow"],
];
fields.forEach((row, i) => {
  s.addText([
    { text: row[0], options: { bold: true, color: COLORS.navy, fontFace: FONTS.mono, fontSize: 10 } },
    { text: "  →  ", options: { color: COLORS.muted, fontSize: 10 } },
    { text: row[1], options: { color: COLORS.text, fontSize: 11 } },
  ], {
    x: 0.95, y: 4.15 + i * 0.27, w: 5.6, h: 0.27,
    margin: 0, valign: "middle", fontFace: FONTS.body,
  });
});

card(s, { x: 6.8, y: 3.6, w: 6.0, h: 3.3, accent: COLORS.gold, headerText: "Expected Ontology Terms (12 個)" });
const ontologyTerms = [
  "evsla:EnterpriseVpnService", "evsla:EnterpriseVpnSlaIntent",
  "evsla:HubAndSpokeTopology", "evsla:HubSite", "evsla:SpokeSite",
  "evsla:SlaExpectation", "evsla:Tenant",
  "evsla:latency", "evsla:p95", "evsla:hubToAllSpokes",
  "evsla:twamp", "evsla:fiveMinuteWindow",
];
// render as a 2-col grid of chip-like rounded rects
const chipsPerCol = 6;
ontologyTerms.forEach((term, i) => {
  const col = Math.floor(i / chipsPerCol), row = i % chipsPerCol;
  const cx = 6.95 + col * 2.85, cy = 4.20 + row * 0.42;
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x: cx, y: cy, w: 2.7, h: 0.32,
    fill: { color: "FEF3C7" }, line: { color: COLORS.gold, width: 1 }, rectRadius: 0.05,
  });
  s.addText(term, {
    x: cx, y: cy, w: 2.7, h: 0.32,
    fontSize: 10, fontFace: FONTS.mono, color: COLORS.text, align: "center", valign: "middle", margin: 0,
  });
});

footer(s, 4, total);

// ====================================================================
// Slide 5: 為什麼 GraphRAG 是重寫過的(舊版 vs 新版)
// ====================================================================
s = pres.addSlide();
s.background = { color: COLORS.bg };
titleBar(s, "為什麼 GraphRAG 是重寫過的", "舊版(Microsoft graphrag CLI) vs 新版(typed BFS,2026-05-19 重寫)");

// ---------- Left card: 舊版 ----------
const oldAccent = "94A3B8";  // gray
const oldX = 0.6, oldY = 1.45, oldW = 6.05, oldH = 4.55;
card(s, { x: oldX, y: oldY, w: oldW, h: oldH, accent: oldAccent, headerText: "舊版:Microsoft graphrag CLI" });

// Process flow as labeled box
s.addText("Pipeline 流程", {
  x: oldX + 0.25, y: oldY + 0.55, w: oldW - 0.4, h: 0.3,
  fontSize: 11, fontFace: FONTS.header, bold: true, color: COLORS.navy, margin: 0,
});
s.addText(
  "TTL files\n  → length_splitter(800 token / chunk)\n  → entity_extraction(LLM)\n  → community_detection(graph clustering)\n  → community_summarization(LLM)\n  → 主 LLM 看到「community 摘要散文」",
  {
    x: oldX + 0.25, y: oldY + 0.85, w: oldW - 0.4, h: 1.85,
    fontSize: 10, fontFace: FONTS.mono, color: COLORS.text, margin: 0, valign: "top",
  }
);

// problem
s.addShape(pres.shapes.RECTANGLE, {
  x: oldX + 0.25, y: oldY + 2.8, w: oldW - 0.5, h: 0.85,
  fill: { color: "FEE2E2" }, line: { color: "FCA5A5", width: 1 },
});
s.addText([
  { text: "❌ 問題", options: { bold: true, color: "991B1B", fontSize: 11 } },
  { text: "  TTL 是結構化資料,卻被當散文切 chunk + 3 道 LLM 重寫 → URI 全洗掉,LLM 只能用普通名詞填 JSON-LD。", options: { color: COLORS.text, fontSize: 10 } },
], {
  x: oldX + 0.35, y: oldY + 2.85, w: oldW - 0.7, h: 0.75,
  fontFace: FONTS.body, margin: 0, valign: "middle",
});

// results
s.addText([
  { text: "TC001 結果:", options: { bold: true, color: COLORS.navy, breakLine: true } },
  { text: "  evsla URI 數 = ", options: { color: COLORS.text } },
  { text: "0 個", options: { bold: true, color: "991B1B", fontSize: 13 } },
  { text: "  ", options: { breakLine: true } },
  { text: "  Avg Ontology coverage ≈ ", options: { color: COLORS.text } },
  { text: "0", options: { bold: true, color: "991B1B", fontSize: 13 } },
], {
  x: oldX + 0.25, y: oldY + 3.75, w: oldW - 0.4, h: 0.7,
  fontSize: 11, fontFace: FONTS.body, margin: 0, valign: "top",
});

// ---------- Right card: 新版 ----------
const newAccent = COLORS.graphrag;
const newX = oldX + oldW + 0.13, newY = oldY, newW = oldW, newH = oldH;
card(s, { x: newX, y: newY, w: newW, h: newH, accent: newAccent, headerText: "新版:typed RDF traversal" });

s.addText("Pipeline 流程", {
  x: newX + 0.25, y: newY + 0.55, w: newW - 0.4, h: 0.3,
  fontSize: 11, fontFace: FONTS.header, bold: true, color: COLORS.navy, margin: 0,
});
s.addText(
  "TTL files\n  → rdflib 直接載入(保留 URI 結構)\n  → 建 label_index + comment_index\n  → seed extraction + grounding\n  → typed BFS 2-hop(5 種 RDFS predicate)\n  → 主 LLM 看到 CURIE triples + comments",
  {
    x: newX + 0.25, y: newY + 0.85, w: newW - 0.4, h: 1.85,
    fontSize: 10, fontFace: FONTS.mono, color: COLORS.text, margin: 0, valign: "top",
  }
);

// good
s.addShape(pres.shapes.RECTANGLE, {
  x: newX + 0.25, y: newY + 2.8, w: newW - 0.5, h: 0.85,
  fill: { color: "DCFCE7" }, line: { color: "86EFAC", width: 1 },
});
s.addText([
  { text: "✅ 好處", options: { bold: true, color: "166534", fontSize: 11 } },
  { text: "  跳過 chunk / community detection 整段;LLM 看 CURIE 直接抄到 JSON-LD,不用腦補 URI。", options: { color: COLORS.text, fontSize: 10 } },
], {
  x: newX + 0.35, y: newY + 2.85, w: newW - 0.7, h: 0.75,
  fontFace: FONTS.body, margin: 0, valign: "middle",
});

s.addText([
  { text: "TC001 結果:", options: { bold: true, color: COLORS.navy, breakLine: true } },
  { text: "  evsla URI 數 = ", options: { color: COLORS.text } },
  { text: "15+", options: { bold: true, color: COLORS.green, fontSize: 13 } },
  { text: "  ", options: { breakLine: true } },
  { text: "  Avg Ontology coverage = ", options: { color: COLORS.text } },
  { text: "0.9889", options: { bold: true, color: COLORS.green, fontSize: 13 } },
], {
  x: newX + 0.25, y: newY + 3.75, w: newW - 0.4, h: 0.7,
  fontSize: 11, fontFace: FONTS.body, margin: 0, valign: "top",
});

// ---------- Bottom card: 通則(也解釋 KAG) ----------
const takeY = oldY + oldH + 0.18, takeH = 1.4;
card(s, { x: 0.6, y: takeY, w: 12.23, h: takeH, accent: COLORS.gold, headerText: "通則 — 也直接解釋了 KAG 為什麼 ontology coverage 最低" });

s.addText([
  { text: "結構化資料 → 結構化 context 才能保住結構。", options: { bold: true, color: COLORS.navy, fontSize: 13 } },
  { text: "  任何中介層(chunk / community summary / 自然語言段落)都會把 URI 洗掉,LLM 拿到散文後只能憑記憶猜 URI。", options: { color: COLORS.text, fontSize: 11, breakLine: true } },
  { text: "  →  ", options: { color: COLORS.muted, fontSize: 11 } },
  { text: "GraphRAG 舊版:結構化 corpus 卻被洗成散文(可改 → 我們改了);  ", options: { color: COLORS.text, fontSize: 11 } },
  { text: "KAG:corpus 一開始就是 SKILL.md 自然語言,本來就沒 URI 可保留(只能靠 generator prompt 硬約束 LLM 用 EVSLA 詞彙)。", options: { color: COLORS.text, fontSize: 11 } },
], {
  x: 0.95, y: takeY + 0.55, w: 11.55, h: takeH - 0.7,
  fontFace: FONTS.body, margin: 0, valign: "top", paraSpaceAfter: 2,
});

footer(s, 5, total);

// ====================================================================
// Slide 6: Three Pipelines at a Glance
// ====================================================================
s = pres.addSlide();
s.background = { color: COLORS.bg };
titleBar(s, "三條 Pipeline 一覽", "都做同一件事(NL → TIO JSON-LD),差別在 retrieval 機制");

const pipelines = [
  {
    name: "GraphRAG", subtitle: "Ontology-grounded Typed Traversal",
    accent: COLORS.graphrag,
    core: "在 TIO ontology 圖上做 2-hop typed BFS",
    bullets: [
      "資料源:TTL 直接讀",
      "Seed:LLM 抽 ontology terms",
      "Retrieval:沿 RDFS 結構性 predicate BFS",
      "Context:CURIE triples + comments",
    ],
    scoreLine: "Verbosity 100% · 最平衡",
  },
  {
    name: "KGE", subtitle: "TransE + Link Prediction",
    accent: COLORS.kge,
    core: "把整個 KG 訓成向量,雙空間 retrieval",
    bullets: [
      "資料源:TTL → triples.tsv",
      "離線:TransE 嵌入(PyKEEN, dim=128)",
      "Retrieval:text top-8 + KGE 鄰居 + link pred.",
      "Context:tagged entity list + predicted triples",
    ],
    scoreLine: "Ontology cov. 0.997 · 最廣但偏冗",
  },
  {
    name: "KAG", subtitle: "5-way Heavy Retrieval over Neo4j",
    accent: COLORS.kag,
    core: "OpenSPG/KAG kg-builder + static solver",
    bullets: [
      "資料源:16 份 SKILL.md (tio-agent 來)",
      "離線:Docker(Neo4j + 5 extractor 建 KG)",
      "Retrieval:5-way parallel(chunk/outline/...)",
      "Context:自然語言 chunks + task results",
    ],
    scoreLine: "Parse 100% · 基礎設施最重",
  },
];

const colW = 4.0, colGap = 0.13, colYstart = 1.7;
pipelines.forEach((p, i) => {
  const cx = 0.6 + i * (colW + colGap);
  card(s, { x: cx, y: colYstart, w: colW, h: 5.4, accent: p.accent });
  s.addText(p.name, {
    x: cx + 0.3, y: colYstart + 0.2, w: colW - 0.5, h: 0.55,
    fontSize: 26, fontFace: FONTS.header, bold: true, color: p.accent, margin: 0,
  });
  s.addText(p.subtitle, {
    x: cx + 0.3, y: colYstart + 0.75, w: colW - 0.5, h: 0.4,
    fontSize: 12, fontFace: FONTS.body, italic: true, color: COLORS.muted, margin: 0,
  });
  s.addText(p.core, {
    x: cx + 0.3, y: colYstart + 1.2, w: colW - 0.5, h: 0.7,
    fontSize: 13, fontFace: FONTS.header, color: COLORS.navy, margin: 0,
  });
  // bullets
  s.addText(
    p.bullets.map((b, j) => ({
      text: b, options: { bullet: true, breakLine: j < p.bullets.length - 1 },
    })),
    {
      x: cx + 0.3, y: colYstart + 2.05, w: colW - 0.5, h: 2.4,
      fontSize: 11, fontFace: FONTS.body, color: COLORS.text, paraSpaceAfter: 4, margin: 0,
    }
  );
  // score line at bottom
  s.addShape(pres.shapes.RECTANGLE, {
    x: cx + 0.25, y: colYstart + 4.7, w: colW - 0.5, h: 0.02,
    fill: { color: COLORS.border }, line: { color: COLORS.border, width: 0 },
  });
  s.addText(p.scoreLine, {
    x: cx + 0.3, y: colYstart + 4.78, w: colW - 0.5, h: 0.4,
    fontSize: 11, fontFace: FONTS.body, bold: true, color: p.accent, margin: 0,
  });
});

footer(s, 6, total);

// ====================================================================
// Slides 7, 9, 11: pipeline flowchart slides
// ====================================================================
function flowchartSlide({ name, displayName, subtitle, accent, page, narrationBullets }) {
  const sl = pres.addSlide();
  sl.background = { color: COLORS.bg };
  titleBar(sl, `${displayName}`, subtitle, accent);

  // Diagram on left, sized to fit
  const maxH = 5.6, maxW = 7.5;
  const { w: dw, h: dh } = computeImageBox(name, maxH, maxW);
  const diagX = 0.6;
  const diagY = 1.6 + (maxH - dh) / 2; // vertically center within reserved 5.6h
  sl.addImage({
    path: path.join(DIAG, `${name}.png`),
    x: diagX, y: diagY, w: dw, h: dh,
  });

  // Narration panel on right
  const panelX = diagX + maxW + 0.4;
  const panelW = W - panelX - 0.5;
  card(sl, { x: panelX, y: 1.6, w: panelW, h: 5.6, accent: accent, headerText: "敘述要點" });
  sl.addText(
    narrationBullets.map((b, i) => ({
      text: b,
      options: { bullet: true, breakLine: i < narrationBullets.length - 1 },
    })),
    {
      x: panelX + 0.3, y: 2.15, w: panelW - 0.5, h: 4.9,
      fontSize: 13, fontFace: FONTS.body, color: COLORS.text, paraSpaceAfter: 8, margin: 0, valign: "top",
    }
  );

  footer(sl, page, total, displayName);
}

flowchartSlide({
  name: "graphrag",
  displayName: "GraphRAG — Pipeline 全景圖",
  subtitle: "離線:載入 TTL + 三索引   ●   線上:seed → grounding → BFS → 序列化 → LLM",
  accent: COLORS.graphrag,
  page: 7,
  narrationBullets: [
    "離線只跑一次:把所有 TTL 合併成 rdflib.Graph,建 label / comment 兩個索引。",
    "Step 1:小 LLM 把 NL intent 抽成 ontology terms,過濾掉租戶名 / 數字 / 單位。",
    "Step 2:seed 先用 label_index 命中 URI;沒中走 comment embedding cosine fallback。",
    "Step 3:從 grounded URI 出發,只沿 subClassOf / type / domain / range 等 5 種 RDFS predicate 做 2-hop BFS。",
    "Step 4:子圖 triples 縮成 CURIE 序列化成 # triples + # comments block。",
    "Step 5:主 LLM 拿到 typed subgraph + 原始 NL,直接吐 JSON-LD。",
    "Step 6:normalize 補空欄位。",
  ],
});

// ====================================================================
// Slide 6: GraphRAG TC001 walkthrough (6 step cards)
// ====================================================================
function walkthroughSlide({ pipelineName, accent, page, steps }) {
  const sl = pres.addSlide();
  sl.background = { color: COLORS.bg };
  titleBar(sl, `${pipelineName} — TC001 逐步資料追蹤`, "看同一句 NL 在每個 step 變成什麼", accent);

  const grid = { cols: 3, rows: 2, x0: 0.6, y0: 1.6, w: 4.0, h: 2.65, gapX: 0.13, gapY: 0.18 };
  steps.forEach((st, i) => {
    const r = Math.floor(i / grid.cols), c = i % grid.cols;
    const cx = grid.x0 + c * (grid.w + grid.gapX);
    const cy = grid.y0 + r * (grid.h + grid.gapY);
    card(sl, { x: cx, y: cy, w: grid.w, h: grid.h, accent, headerText: st.title, headerSize: 13 });
    // body
    sl.addText(st.body, {
      x: cx + 0.25, y: cy + 0.6, w: grid.w - 0.4, h: grid.h - 0.75,
      fontSize: 10, fontFace: st.mono ? FONTS.mono : FONTS.body,
      color: COLORS.text, margin: 0, valign: "top",
    });
  });

  footer(sl, page, total, pipelineName);
}

walkthroughSlide({
  pipelineName: "GraphRAG", accent: COLORS.graphrag, page: 8,
  steps: [
    {
      title: "Step 1:LLM 抽 seed",
      mono: true,
      body: '輸入:NL intent\n\n輸出:\n["latency",\n "p95",\n "hub to all spokes",\n "5 minute window"]\n\n租戶 / 數字 / 單位被濾掉',
    },
    {
      title: "Step 2:grounding",
      mono: true,
      body: 'label_index 命中:\n  latency → evsla:latency\n  p95 → evsla:p95\n  hub to all spokes\n   → evsla:hubToAllSpokes\n\nembedding fallback:\n  5 minute window\n   → evsla:fiveMinuteWindow',
    },
    {
      title: "Step 3:typed BFS 2-hop",
      mono: true,
      body: "evsla:latency\n  rdfs:subPropertyOf met:metric\n  rdfs:domain evsla:SlaExpectation\n  rdfs:range quan:Quantity\nevsla:SlaExpectation\n  rdfs:subClassOf\n  icm:PropertyExpectation\nevsla:p95 rdf:type evsla:Statistic\n...(~30-60 triples)",
    },
    {
      title: "Step 4:序列化",
      mono: true,
      body: "# triples\nevsla:SlaExpectation rdfs:subClassOf icm:PropertyExpectation\nevsla:latency rdfs:domain evsla:SlaExpectation\n...\n\n# comments\n# evsla:latency → One-way latency measured by TWAMP...",
    },
    {
      title: "Step 5:主 LLM 生 JSON-LD",
      body: "主 LLM 同時看到:\n  (a) 序列化 subgraph\n  (b) 原始 NL intent\n  (c) few-shot 範例\n\n→ 結構從 (a) 抓\n→ 50 / ms / 95% 從 (b) 抓\n→ JSON-LD layout 從 (c) 抓",
    },
    {
      title: "Step 6:normalize + 輸出",
      mono: true,
      body: 'TC001.jsonld 命中:\n  ✓ evsla:latency\n  ✓ evsla:p95\n  ✓ evsla:hubToAllSpokes\n  ✓ evsla:twamp\n  ✓ evsla:fiveMinuteWindow\n  ✓ evsla:SlaExpectation\n  ✓ value: 50 ms / p95',
    },
  ],
});

// ====================================================================
// Slide 7: KGE flowchart
// ====================================================================
flowchartSlide({
  name: "kge",
  displayName: "KGE — Pipeline 全景圖",
  subtitle: "離線:訓 TransE + 文字嵌入   ●   線上:text top-8 → KGE 鄰居擴張 → link prediction → LLM",
  accent: COLORS.kge,
  page: 9,
  narrationBullets: [
    "離線需 retrain 才會跑:把 TTL 抽成 URI-URI triples → PyKEEN TransE(dim=128, epochs=80)。",
    "同時對每個 entity 算 text embedding(label + comment 餵 ada-002)。",
    "Step 1-2:NL intent 也算 ada-002 向量,跟 entity_text_emb cosine 找 top-8 seed。",
    "Step 3:每個 seed 在 KGE space 取 top-14 鄰居,擴張到 ≤ 45 個 entity。",
    "Step 4:用 TransE 的 score = -||h+r-t||₂,對 grounded URIs 做 link prediction,挖出沒寫在 TTL 但結構合理的 triple,top-18。",
    "Step 5-6:把 entity list + predicted triples 餵主 LLM。沒有後處理。",
    "特色:ontology coverage 最廣(0.997),但 prompt 偏冗,verbosity 容易爆。",
  ],
});

// ====================================================================
// Slide 8: KGE TC001 walkthrough
// ====================================================================
walkthroughSlide({
  pipelineName: "KGE", accent: COLORS.kge, page: 10,
  steps: [
    {
      title: "Step 1:query embed",
      mono: true,
      body: "NL intent\n  → ada-002\n  → q ∈ ℝ^1536\n  → L2-normalize",
    },
    {
      title: "Step 2:text top-8 seed",
      mono: true,
      body: "text_emb @ q 取 top-8:\n  [text] evsla:latency\n  [text] evsla:SlaExpectation\n  [text] evsla:p95\n  [text] evsla:hubToAllSpokes\n  [text] evsla:twamp\n  [text] evsla:EnterpriseVpnService\n  [text] evsla:fiveMinuteWindow\n  [text] met:metric",
    },
    {
      title: "Step 3:KGE 鄰居擴張",
      mono: true,
      body: "每 seed 在 KGE space cosine\n取 top-14,加標籤 [kge_neighbor]:\n  evsla:packetLoss\n  evsla:jitter\n  evsla:guaranteedBandwidth\n  met:Metric\n  icm:PropertyExpectation\n  quan:Quantity\n  ...\n總 entity ≤ 45",
    },
    {
      title: "Step 4:link prediction",
      mono: true,
      body: "對 grounded URI 跑 TransE:\nscore = -‖h + r - t‖₂\n\nTop-18 predicted triples,例:\nevsla:latency rdfs:subPropertyOf met:metric (-0.21)\nevsla:p95 rdf:type evsla:Statistic (-0.34)\nevsla:SlaExpectation rdfs:subClassOf\n  icm:PropertyExpectation (-0.28)",
    },
    {
      title: "Step 5:format context",
      mono: true,
      body: "### KGE-assisted term hints\n- [text] evsla:latency — ...\n- [kge_neighbor] evsla:packetLoss — ...\n...\n\n### KGE link prediction\nGrounded URIs:\n- ...\nPredicted likely triples:\n- ...",
    },
    {
      title: "Step 6:主 LLM 生 JSON-LD",
      body: "結果:\n  ✓ ontology coverage 略高\n    (0.9972 vs GraphRAG 0.9889)\n  ✗ verbosity 容易爆\n    (Avg node ~63 vs budget 50)\n\n下個改進方向:壓縮 prompt 進 LLM 的 entity 數",
    },
  ],
});

// ====================================================================
// Slide 9: KAG flowchart
// ====================================================================
flowchartSlide({
  name: "kag",
  displayName: "KAG — Pipeline 全景圖",
  subtitle: "離線:Docker + 5-extractor 建 Neo4j   ●   線上:planner → 5-way retrieval → 內建 generator",
  accent: COLORS.kag,
  page: 11,
  narrationBullets: [
    "離線最重:起 Docker(OpenSPG + Neo4j + MySQL + MinIO),knext push schema,跑 indexer 灌 16 份 SKILL.md。",
    "每份 markdown 切成 1000 字 chunk,5 個 extractor 各跑一次(chunk / outline / summary / table / atomic_query,其中 4 個會打 LLM)。",
    "Step 1:KAG 內建 planner LLM 把 NL intent 拆成 sub-queries。",
    "Step 2:5 路 retriever 同時跑(各 top_k=10),分別比對 atomic_query / outline / summary / vector / table。",
    "Step 3:kag_merger 去重排序,組成最終 context。",
    "Step 4:custom TIOJsonldGenerator(KAG 內建 LLM call,我們寫的 prompt 嚴格限定 EVSLA 詞彙)直接吐 JSON-LD。",
    "Step 5:fallback 補 intentReport 欄位。",
    "限制:corpus 是自然語言段落,URI 命中要靠 LLM 腦補,ontology coverage 比 GraphRAG / KGE 低。",
  ],
});

// ====================================================================
// Slide 10: KAG TC001 walkthrough
// ====================================================================
walkthroughSlide({
  pipelineName: "KAG", accent: COLORS.kag, page: 12,
  steps: [
    {
      title: "Step 1:planner",
      mono: true,
      body: "kag_static_planner(LLM)\n把 NL 拆成 sub-queries:\n\n1. What ontology terms describe\n   latency SLA in EVSLA?\n2. What scope = hub to all spokes?\n3. What statistic is p95?\n4. How is TWAMP used to\n   measure latency?",
    },
    {
      title: "Step 2:5-way 並行 retrieve",
      mono: true,
      body: "對每 sub-query 同時跑 5 個 retriever:\n\n  r1 atomic_query (top-10)\n  r2 outline (top-10)\n  r3 summary  (threshold 0.8)\n  r4 vector   (threshold 0.8)\n  r5 table    (top-10)",
    },
    {
      title: "Step 3:merger 合併",
      mono: true,
      body: "kag_merger 範例命中:\n\n[atomic_query] What protocol\n  measures hub-spoke latency?\n  → chunk: TWAMP measures...\n\n[summary] hub-and-spoke topo...\n\n[vector] SLA expectations\n  include latency, packet loss...",
    },
    {
      title: "Step 4:TIO generator",
      body: "TIOJsonldGenerator prompt:\n  - @type must be Intent\n  - 必須用 EVSLA 詞彙\n    (evsla:latency, p95, twamp...)\n  - 不可發明 URI\n\nLLM 看 sub-task results + 原 NL\n+ few-shot → 吐 JSON-LD",
    },
    {
      title: "Step 5:contract fallback",
      mono: true,
      body: "ensure_jsonld_contract:\nif intentReport 不是 dict:\n  → 補 {\n      reportingInterval: 'PT5M',\n      handlerResponse: 'Continuous'\n    }\n\n(KAG generator 偶爾漏寫)",
    },
    {
      title: "輸出觀察",
      body: "TC001 結果:\n  ✓ Parse OK\n  ✓ verbosity 守住\n  ✗ ontology coverage 0.93\n   (vs GraphRAG 0.99 / KGE 1.00)\n\n原因:retrieval 拉回來是自然語言段落,\nURI 命中要靠 LLM 自己腦補",
    },
  ],
});

// ====================================================================
// Slide 11: Evaluator — 評分指標說明
// ====================================================================
s = pres.addSlide();
s.background = { color: COLORS.bg };
titleBar(s, "Evaluator — 評分指標說明", "evaluate_jsonld.py + compare_reports.py / 比下一頁分數之前先讀這頁");

// Row 1: 3 cards
const evalRow1 = [
  {
    accent: COLORS.deepBlue,
    title: "1. Parse OK (%)",
    formula: "JSON 可 parse  ∧  contract validation 全過",
    body: [
      "JSON 語法合法,可被 json.loads()",
      "Top-level @type 必須是 \"Intent\"",
      "必要字串欄位齊全 (@context / id / name / description / intentOwner.{id,name})",
      "intentExpectation 是非空 array,每項有 @type ∈ {DeliveryExpectation, PropertyExpectation},expectationTarget 結構正確",
      "matchCondition 必須是 LESS_THAN / GREATER_THAN_OR_EQUAL / EQUALS / ... 等合法 enum",
    ],
    note: "code: validate_contract() / strip_markdown_json_fence()",
  },
  {
    accent: COLORS.gold,
    title: "2. Avg ICM",
    formula: "expected_tio_elements 命中率 (0.0 ~ 1.0)",
    body: [
      "每題的 expected_tio_elements 列出該 case 必須表達的 ICM 結構元素",
      "例:icm:Intent / icm:PropertyExpectation / icm:Target / icm:Context / icm:valuesOfTargetProperty",
      "Evaluator 用結構 mapping 表檢查 JSON-LD 是否表達該元素",
      "例 icm:Intent ⇔ 頂層 @type == \"Intent\"",
      "例 icm:Target ⇔ expectationTarget 非空",
      "命中數 / 全部 expected = coverage ratio",
    ],
    note: "code: expected_element_ok() / evaluate_expected_elements()",
  },
  {
    accent: COLORS.kge,
    title: "3. Avg Ontology",
    formula: "ontology_terms 字面命中率 (0.0 ~ 1.0)",
    body: [
      "每題的 ontology_terms 列出該 case 該出現的 TIO URI",
      "例 (TC001):evsla:latency / p95 / hubToAllSpokes / twamp / SlaExpectation / ...(共 12 個)",
      "Evaluator 把整份 JSON-LD 攤平成 string set,檢查每個 expected URI 是否出現在任意 key 或 value",
      "命中數 / 全部 expected = ratio",
      "純字面比對 — 拼錯 / 用別名都算不中",
    ],
    note: "code: flatten_json_terms() / evaluate_ontology_terms()",
  },
];

// Row 2: 2 cards (wider)
const evalRow2 = [
  {
    accent: COLORS.kag,
    title: "4. Avg Metric",
    formula: "performance_metrics 結構命中率 — 必須全部對齊才算 OK",
    body: [
      "每題的 performance_metrics 列出該度量的完整規格(metric / operator / threshold / statistic / scope / measurement_method / time_window)",
      "找 JSON-LD 中是否有 target 同時滿足:",
      "  • targetProperty == ontology_term (或 evsla:hasMetric 對得上)",
      "  • matchCondition == operator (LESS_THAN / ...)",
      "  • targetValue 的 value + unit 跟 threshold 完全相符",
      "  • statistic / scope / measurement_method / time_window 若指定就必須完全對齊",
      "→ 比 Ontology coverage 嚴格:不只 URI 出現,還要結構正確",
    ],
    note: "code: metric_target_ok() / evaluate_performance_metrics()",
  },
  {
    accent: COLORS.graphrag,
    title: "5. Verbosity OK (%) + Avg Nodes",
    formula: "json_node_count 落在 [min, max] 區間",
    body: [
      "每題的 expected_json_nodes 定 { target, min, max }",
      "例 (TC001):target=60, min=45, max=80",
      "Evaluator 遞迴算 JSON-LD 的總節點數(dict / list / scalar 都算 1)",
      "落在 [min, max] → ok(1),否則 too_sparse / too_verbose(0)",
      "Avg Nodes 是平均節點數,只是 informational,不直接打分",
      "→ 抓「prompt 太冗 / 太簡 → 輸出失真」這種問題",
    ],
    note: "code: count_json_nodes() / evaluate_json_node_budget()",
  },
];

function drawEvalCard(s, { x, y, w, h, accent, title, formula, body, note }) {
  card(s, { x, y, w, h, accent, headerText: title, headerSize: 14 });
  // formula highlight
  s.addText(formula, {
    x: x + 0.25, y: y + 0.55, w: w - 0.4, h: 0.35,
    fontSize: 11, fontFace: FONTS.mono, color: accent, bold: true, margin: 0, valign: "middle",
  });
  // body bullets
  s.addText(
    body.map((b, i) => ({
      text: b, options: { bullet: true, breakLine: i < body.length - 1 },
    })),
    {
      x: x + 0.3, y: y + 0.95, w: w - 0.5, h: h - 1.45,
      fontSize: 9.5, fontFace: FONTS.body, color: COLORS.text, paraSpaceAfter: 2, margin: 0, valign: "top",
    }
  );
  // code reference at bottom
  s.addText(note, {
    x: x + 0.25, y: y + h - 0.35, w: w - 0.4, h: 0.3,
    fontSize: 8.5, fontFace: FONTS.mono, color: COLORS.muted, italic: true, margin: 0, valign: "middle",
  });
}

// Row 1: 3 cards, equal width
const r1W = (W - 1.2 - 2 * 0.13) / 3; // 4.05
const r1Y = 1.5, r1H = 2.85;
evalRow1.forEach((m, i) => {
  drawEvalCard(s, { x: 0.6 + i * (r1W + 0.13), y: r1Y, w: r1W, h: r1H, ...m });
});

// Row 2: 2 cards, wider
const r2W = (W - 1.2 - 0.13) / 2; // 6.04
const r2Y = r1Y + r1H + 0.15, r2H = 2.5;
evalRow2.forEach((m, i) => {
  drawEvalCard(s, { x: 0.6 + i * (r2W + 0.13), y: r2Y, w: r2W, h: r2H, ...m });
});

footer(s, 13, total);

// ====================================================================
// Slide 14: Phase 1 評分比較表
// ====================================================================
s = pres.addSlide();
s.background = { color: COLORS.bg };
titleBar(s, "Phase 1 評分比較", "phase1/compare_four_way.txt(LLM-only 作為 baseline)");

const tableRows = [
  [
    { text: "Pipeline",        options: { bold: true, color: "FFFFFF", fill: { color: COLORS.navy }, align: "left" } },
    { text: "Parse OK",        options: { bold: true, color: "FFFFFF", fill: { color: COLORS.navy }, align: "center" } },
    { text: "Avg ICM",         options: { bold: true, color: "FFFFFF", fill: { color: COLORS.navy }, align: "center" } },
    { text: "Avg Ontology",    options: { bold: true, color: "FFFFFF", fill: { color: COLORS.navy }, align: "center" } },
    { text: "Avg Metric",      options: { bold: true, color: "FFFFFF", fill: { color: COLORS.navy }, align: "center" } },
    { text: "Avg Nodes",       options: { bold: true, color: "FFFFFF", fill: { color: COLORS.navy }, align: "center" } },
    { text: "Verbosity OK",    options: { bold: true, color: "FFFFFF", fill: { color: COLORS.navy }, align: "center" } },
  ],
  [
    { text: "LLM-only (baseline)", options: { color: COLORS.muted, italic: true } },
    { text: "95.00%",  options: { align: "center", color: COLORS.muted } },
    { text: "0.8975",  options: { align: "center", color: COLORS.muted } },
    { text: "0.0000",  options: { align: "center", color: COLORS.muted } },
    { text: "0.0000",  options: { align: "center", color: COLORS.muted } },
    { text: "39.50",   options: { align: "center", color: COLORS.muted } },
    { text: "25.00%",  options: { align: "center", color: COLORS.muted } },
  ],
  [
    { text: "GraphRAG",         options: { bold: true, color: COLORS.graphrag } },
    { text: "100.00%", options: { align: "center", bold: true } },
    { text: "1.0000",  options: { align: "center", bold: true } },
    { text: "0.9889",  options: { align: "center" } },
    { text: "1.0000",  options: { align: "center", bold: true } },
    { text: "62.65",   options: { align: "center" } },
    { text: "100.00%", options: { align: "center", bold: true, color: COLORS.green } },
  ],
  [
    { text: "KGE",               options: { bold: true, color: COLORS.kge } },
    { text: "95.00%",  options: { align: "center" } },
    { text: "1.0000",  options: { align: "center", bold: true } },
    { text: "0.9972",  options: { align: "center", bold: true, color: COLORS.green } },
    { text: "1.0000",  options: { align: "center", bold: true } },
    { text: "63.40",   options: { align: "center" } },
    { text: "0.00%",   options: { align: "center", bold: true, color: COLORS.kag } },
  ],
  [
    { text: "KAG",               options: { bold: true, color: COLORS.kag } },
    { text: "100.00%", options: { align: "center", bold: true } },
    { text: "0.9900",  options: { align: "center" } },
    { text: "0.9314",  options: { align: "center" } },
    { text: "1.0000",  options: { align: "center", bold: true } },
    { text: "61.80",   options: { align: "center" } },
    { text: "100.00%", options: { align: "center", bold: true, color: COLORS.green } },
  ],
];

s.addTable(tableRows, {
  x: 0.6, y: 1.75, w: 12.2,
  colW: [3.2, 1.4, 1.4, 1.6, 1.4, 1.4, 1.8],
  rowH: 0.55,
  fontSize: 13, fontFace: FONTS.body, color: COLORS.text,
  border: { type: "solid", color: COLORS.border, pt: 1 },
  fill: { color: COLORS.cardBg },
  margin: 6,
  valign: "middle",
});

// observations card below
card(s, { x: 0.6, y: 5.45, w: 12.2, h: 1.5, accent: COLORS.deepBlue, headerText: "三個關鍵觀察" });
s.addText([
  { text: "ICM / metric coverage:", options: { bold: true, color: COLORS.navy } },
  { text: " GraphRAG 與 KGE 並列滿分;KAG 略差(0.99 / 1.00),都遠勝 baseline。", options: { color: COLORS.text, breakLine: true } },
  { text: "Ontology coverage:", options: { bold: true, color: COLORS.navy } },
  { text: " KGE 0.9972 第一 — link prediction 把該出現的 URI 全壓進 prompt。", options: { color: COLORS.text, breakLine: true } },
  { text: "Verbosity:", options: { bold: true, color: COLORS.navy } },
  { text: " KGE 全敗 — node 數爆 budget,是下一階段要修的點(prompt 太冗)。", options: { color: COLORS.text } },
], {
  x: 0.95, y: 6.0, w: 11.7, h: 0.95,
  fontSize: 12, fontFace: FONTS.body, color: COLORS.text, paraSpaceAfter: 2, margin: 0, valign: "top",
});

footer(s, 14, total);

// ====================================================================
// Slide 15: TC001 中間表示對照
// ====================================================================
s = pres.addSlide();
s.background = { color: COLORS.bg };
titleBar(s, "TC001 三條 Pipeline 的中間表示對照", "同一句 NL,三種完全不同的 LLM 輸入");

const cmpHeaders = ["階段", "GraphRAG", "KGE", "KAG"];
const cmpRows = [
  ["NL intent 之後第 1 步",
   "seed terms\n['latency','p95',...]",
   "query 向量\nq ∈ ℝ^1536",
   "retrieval plan\n(4 個 sub-query)"],
  ["核心中間表示",
   "grounded URIs\n{evsla:latency,...}",
   "ranked entity list\ntop-8 + 鄰居 ≤ 45",
   "merged chunks\n5 路命中合併"],
  ["送給主 LLM 的 context",
   "# triples + # comments\n(CURIE 結構)",
   "tagged entity list +\npredicted triples\n(TransE score)",
   "task blocks\n(sub-task result + thought)"],
  ["檢索精度",
   "高(雜訊少)",
   "高(覆蓋廣)",
   "中(自然語言段落)"],
  ["檢索覆蓋率",
   "中(BFS 2-hop)",
   "高(雙空間擴張)",
   "高(5-way 平行)"],
];

const cmpTable = [
  cmpHeaders.map((h, i) => ({
    text: h, options: {
      bold: true, color: "FFFFFF",
      fill: { color: i === 0 ? COLORS.navy : (i === 1 ? COLORS.graphrag : (i === 2 ? COLORS.kge : COLORS.kag)) },
      align: i === 0 ? "left" : "center",
      fontSize: 14,
    },
  })),
  ...cmpRows.map(row => row.map((cell, i) => ({
    text: cell, options: {
      align: i === 0 ? "left" : "center",
      bold: i === 0,
      color: i === 0 ? COLORS.navy : COLORS.text,
      fontFace: i === 0 ? FONTS.body : FONTS.mono,
      fontSize: i === 0 ? 12 : 11,
    },
  }))),
];

s.addTable(cmpTable, {
  x: 0.6, y: 1.7, w: 12.2,
  colW: [3.0, 3.067, 3.067, 3.066],
  rowH: 0.95,
  fontFace: FONTS.body, color: COLORS.text,
  border: { type: "solid", color: COLORS.border, pt: 1 },
  fill: { color: COLORS.cardBg },
  margin: 8,
  valign: "middle",
});

s.addText("一句話:三條都送給同一顆 gpt-5.4,但 LLM 看到的 context 形狀差異很大 — 這是 retrieval 精度與覆蓋率取捨的直接結果。", {
  x: 0.6, y: 6.95, w: 12.2, h: 0.4,
  fontSize: 12, fontFace: FONTS.body, italic: true, color: COLORS.muted, align: "center", margin: 0,
});

footer(s, 15, total);

// ====================================================================
// Slide 16: Conclusion / Takeaway
// ====================================================================
s = pres.addSlide();
s.background = { color: COLORS.navy };

s.addShape(pres.shapes.RECTANGLE, {
  x: 1.0, y: 1.3, w: 0.15, h: 1.5,
  fill: { color: COLORS.gold }, line: { color: COLORS.gold, width: 0 },
});
s.addText("Takeaway", {
  x: 1.4, y: 1.2, w: 11, h: 0.8,
  fontSize: 36, fontFace: FONTS.header, bold: true, color: "FFFFFF", margin: 0,
});
s.addText("三條 pipeline 做同一件事,差別在 retrieval 的「精度 × 召回 × 工程複雜度」取捨", {
  x: 1.4, y: 2.05, w: 11, h: 0.7,
  fontSize: 18, fontFace: FONTS.body, italic: true, color: COLORS.navyLight, margin: 0,
});

const concl = [
  { color: COLORS.graphrag, name: "GraphRAG", line: "直接吃 ontology 結構,精度高、雜訊少,目前最平衡。" },
  { color: COLORS.kge,      name: "KGE",      line: "多吃一層向量空間,召回最廣,但 prompt 容易冗、verbosity 全敗。" },
  { color: COLORS.kag,      name: "KAG",      line: "基礎設施最重(Docker + Neo4j + 5 extractor),corpus 是自然語言時 ontology 命中率反而被拖累。" },
];

const startY = 3.4;
concl.forEach((p, i) => {
  const cy = startY + i * 0.9;
  // colored circle "bullet"
  s.addShape(pres.shapes.OVAL, {
    x: 1.0, y: cy + 0.1, w: 0.4, h: 0.4,
    fill: { color: p.color }, line: { color: p.color, width: 0 },
  });
  s.addText(p.name, {
    x: 1.55, y: cy, w: 2.2, h: 0.6,
    fontSize: 20, fontFace: FONTS.header, bold: true, color: "FFFFFF", margin: 0, valign: "middle",
  });
  s.addText(p.line, {
    x: 3.85, y: cy, w: 8.5, h: 0.6,
    fontSize: 15, fontFace: FONTS.body, color: COLORS.navyLight, margin: 0, valign: "middle",
  });
});

s.addText("下一步:壓 KGE 的 verbosity / 同條件四方重跑 / 進 Phase 2", {
  x: 1.0, y: 6.6, w: 11, h: 0.4,
  fontSize: 13, fontFace: FONTS.body, italic: true, color: "94A3B8", margin: 0,
});

// ----- Write -----
pres.writeFile({ fileName: path.join(ROOT, "mechanism_deck.pptx") }).then((fn) => {
  console.log("Wrote:", fn);
});
