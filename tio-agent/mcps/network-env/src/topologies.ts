// Fake Enterprise VPN SLA environment for hub-and-spoke intent grounding.
// Replace the static cases with real inventory/telemetry adapters later while
// keeping the MCP tool surface stable.

export interface Link {
  from: string;
  to: string;
  bandwidth_mbps: number;
  latency_ms: number;
}

export interface Service {
  id: string;
  name: string;
  type: string;
  attrs: {
    tenant: string;
    topology: "hub-and-spoke";
    hub: string;
    spokes: string[];
    supported_metrics: string[];
    preferred_measurement_method: string;
    monitoring_window: string;
  };
}

export interface Topology {
  name: string;
  description: string;
  nodes: string[];
  links: Link[];
  services: Service[];
  live_hints?: Record<string, unknown>;
}

type EnterpriseVpnCase = {
  tenant: string;
  hub: string;
  spokes: string[];
  metrics: string[];
};

const enterpriseVpnCases: EnterpriseVpnCase[] = [
  { tenant: "星河銀行", hub: "台北總部", spokes: ["新竹分行", "台中分行", "高雄分行"], metrics: ["evsla:latency"] },
  { tenant: "遠東製造", hub: "桃園總廠", spokes: ["新竹廠", "台中廠", "台南廠"], metrics: ["evsla:packetLoss"] },
  { tenant: "宏海物流", hub: "台北營運中心", spokes: ["高雄倉儲中心"], metrics: ["evsla:guaranteedBandwidth"] },
  { tenant: "康健醫療", hub: "台北醫療雲中心", spokes: ["林口院區", "台中院區", "高雄院區"], metrics: ["evsla:latency"] },
  {
    tenant: "晨星零售",
    hub: "台北資料中心",
    spokes: ["板橋旗艦店", "台中公益店", "台南西門店", "高雄夢時代店"],
    metrics: ["evsla:packetLoss"],
  },
  { tenant: "北辰證券", hub: "信義交易中心", spokes: ["台中交易室"], metrics: ["evsla:guaranteedBandwidth"] },
  { tenant: "海港航運", hub: "高雄港營運中心", spokes: ["基隆港站", "台中港站", "花蓮港站"], metrics: ["evsla:latency"] },
  {
    tenant: "晶耀半導體",
    hub: "新竹研發總部",
    spokes: ["竹南封測廠", "台中晶圓廠", "台南先進製程廠"],
    metrics: ["evsla:packetLoss"],
  },
  { tenant: "綠能電力", hub: "台北調度中心", spokes: ["彰濱風場"], metrics: ["evsla:guaranteedBandwidth"] },
  { tenant: "迅捷遊戲", hub: "台北遊戲雲中心", spokes: ["板橋節點", "台中節點", "高雄節點"], metrics: ["evsla:latency"] },
  {
    tenant: "城市交通局",
    hub: "台北交通控制中心",
    spokes: ["信義監控站", "南港監控站", "北投監控站"],
    metrics: ["evsla:packetLoss"],
  },
  { tenant: "藍海保險", hub: "台北總公司", spokes: ["花蓮服務中心"], metrics: ["evsla:guaranteedBandwidth"] },
  {
    tenant: "雲端教育",
    hub: "台北教學平台中心",
    spokes: ["新竹校區", "台中校區", "嘉義校區", "高雄校區"],
    metrics: ["evsla:latency"],
  },
  { tenant: "聯合媒體", hub: "內湖製播中心", spokes: ["台中攝影棚", "高雄攝影棚", "宜蘭外景站"], metrics: ["evsla:packetLoss"] },
  { tenant: "亞洲航空維修", hub: "桃園維修總部", spokes: ["小港機棚"], metrics: ["evsla:guaranteedBandwidth"] },
  { tenant: "智慧農業", hub: "雲林農業資料中心", spokes: ["斗六農場", "虎尾農場", "西螺農場"], metrics: ["evsla:latency"] },
  { tenant: "國際會展", hub: "南港會展網管中心", spokes: ["台北館", "台中館", "高雄館"], metrics: ["evsla:packetLoss"] },
  { tenant: "東岸觀光", hub: "台東營運總部", spokes: ["綠島服務站"], metrics: ["evsla:guaranteedBandwidth"] },
  { tenant: "安全監控", hub: "台北監控中心", spokes: ["士林站", "文山站", "大安站", "松山站"], metrics: ["evsla:latency"] },
  {
    tenant: "精準醫材",
    hub: "台北研發總部",
    spokes: ["竹北實驗室", "台南製造廠"],
    metrics: ["evsla:latency", "evsla:packetLoss"],
  },
];

const serviceFor = (item: EnterpriseVpnCase): Service => ({
  id: `svc:${item.tenant}-enterprise-vpn`,
  name: `${item.tenant} Enterprise VPN Service`,
  type: "enterprise-vpn",
  attrs: {
    tenant: item.tenant,
    topology: "hub-and-spoke",
    hub: item.hub,
    spokes: item.spokes,
    supported_metrics: item.metrics,
    preferred_measurement_method: "evsla:twamp",
    monitoring_window: "evsla:fiveMinuteWindow",
  },
});

const services = enterpriseVpnCases.map(serviceFor);
const nodes = [...new Set(enterpriseVpnCases.flatMap((item) => [item.hub, ...item.spokes]))];
const links = enterpriseVpnCases.flatMap((item) =>
  item.spokes.map((spoke) => ({
    from: item.hub,
    to: spoke,
    bandwidth_mbps: item.metrics.includes("evsla:guaranteedBandwidth") ? 1000 : 500,
    latency_ms: item.metrics.includes("evsla:latency") ? 20 : 35,
  }))
);

export const topologies: Record<string, Topology> = {
  "enterprise-vpn-sla-hub-spoke": {
    name: "enterprise-vpn-sla-hub-spoke",
    description:
      "Enterprise VPN SLA hub-and-spoke environment for tenant services, hub/spoke sites, SLA metrics, and fake live telemetry.",
    nodes,
    links,
    services,
    live_hints: {
      supported_ontology: "evsla:EnterpriseVpnSlaOntology",
      topology_type: "evsla:HubAndSpokeTopology",
      measurement_method: "evsla:twamp",
      monitoring_window: "evsla:fiveMinuteWindow",
    },
  },
};

const METRIC_SYNONYMS: Array<[string[], string]> = [
  [["latency", "延遲", "低延遲"], "evsla:latency"],
  [["packet loss", "packet_loss", "封包遺失", "封包遺失率", "丟包"], "evsla:packetLoss"],
  [["guaranteed bandwidth", "guaranteed_bandwidth", "保證頻寬", "頻寬", "Mbps"], "evsla:guaranteedBandwidth"],
];

const SCOPE_SYNONYMS: Array<[string[], string]> = [
  [["所有分點", "各spoke", "各 spoke", "所有spoke", "所有 spoke", "hub與各spoke", "總部至所有分點"], "evsla:hubToAllSpokes"],
  [["specific spoke", "指定", "單一分點", "至高雄", "倉儲中心", "交易室", "風場", "服務中心", "機棚", "服務站"], "evsla:specificSpoke"],
];

const GENERIC_SYNONYMS: Record<string, string[]> = {
  hub: ["總部", "中心", "hub", "Hub"],
  spoke: ["分點", "分行", "分廠", "廠", "院區", "倉儲中心", "交易室", "節點", "監控站", "校區", "攝影棚", "Spoke", "spoke"],
  vpn: ["enterprise vpn", "企業 vpn", "企業VPN", "l3vpn", "專線"],
  sla: ["sla", "SLA", "服務水準", "保證"],
};

export interface ResolveResult {
  matches: Service[];
  tried: string[];
  reason?: string;
}

function addIfIncluded(tokens: Set<string>, lowerHint: string, candidates: string[]) {
  for (const candidate of candidates) {
    if (lowerHint.includes(candidate.toLowerCase())) tokens.add(candidate);
  }
}

export function resolveTarget(topologyName: string, hint: string): ResolveResult {
  const t = topologies[topologyName];
  if (!t) return { matches: [], tried: [], reason: `unknown topology: ${topologyName}` };

  const lower = hint.toLowerCase();
  const tokens = new Set<string>([hint]);

  for (const service of t.services) {
    addIfIncluded(tokens, lower, [service.attrs.tenant, service.attrs.hub, ...service.attrs.spokes]);
  }
  for (const [synonyms, metric] of METRIC_SYNONYMS) {
    if (synonyms.some((s) => lower.includes(s.toLowerCase()))) tokens.add(metric);
  }
  for (const [synonyms, scope] of SCOPE_SYNONYMS) {
    if (synonyms.some((s) => lower.includes(s.toLowerCase()))) tokens.add(scope);
  }
  for (const values of Object.values(GENERIC_SYNONYMS)) addIfIncluded(tokens, lower, values);

  const matches = t.services
    .map((service) => {
      let score = 0;
      if (lower.includes(service.attrs.tenant.toLowerCase())) score += 100;
      if (lower.includes(service.attrs.hub.toLowerCase())) score += 20;
      score += service.attrs.spokes.filter((spoke) => lower.includes(spoke.toLowerCase())).length * 20;
      score += service.attrs.supported_metrics.filter((metric) => tokens.has(metric)).length * 5;
      return { service, score };
    })
    .filter(({ score }) => score > 0)
    .sort((a, b) => b.score - a.score);

  const bestScore = matches[0]?.score ?? 0;
  const best = matches.filter(({ score }) => score === bestScore).map(({ service }) => service);

  return { matches: best, tried: [...tokens] };
}

// Deterministic-ish fake live metrics keyed on topology+target.
export function fakeMetrics(key: string) {
  let h = 2166136261;
  for (let i = 0; i < key.length; i++) {
    h ^= key.charCodeAt(i);
    h = (h * 16777619) >>> 0;
  }
  const r = (mod: number) => {
    h = (h * 1103515245 + 12345) & 0x7fffffff;
    return h % mod;
  };
  const jitter = () => (Math.random() - 0.5) * 4;
  const baseLat = 10 + r(45);
  const baseTput = 100 + r(1200);
  return {
    latency_ms: +(Math.max(0.5, baseLat + jitter())).toFixed(2),
    throughput_mbps: +(Math.max(10, baseTput + jitter() * 20)).toFixed(1),
    packet_loss_pct: +(Math.random() * 0.25).toFixed(3),
    sla_compliance_pct: +(95 + Math.random() * 4.99).toFixed(2),
    timestamp: new Date().toISOString(),
    status: "healthy" as const,
  };
}
