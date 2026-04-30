// Fake PoC topologies. Replace with real telemetry adapters later;
// keep the shape stable so the MCP surface doesn't have to change.

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
  attrs: Record<string, unknown>;
}

export interface Topology {
  name: string;
  description: string;
  nodes: string[];
  links: Link[];
  services: Service[];
  live_hints?: Record<string, unknown>;
}

export const topologies: Record<string, Topology> = {
  "campus-5g-south": {
    name: "campus-5g-south",
    description:
      "5G campus network spanning Kaohsiung (KHH) and Pingtung (PTG), serving enterprise eMBB and IoT URLLC slices.",
    nodes: ["gNB-KHH-01", "gNB-KHH-02", "gNB-PTG-01", "UPF-KHH", "AMF-TPE"],
    links: [
      { from: "gNB-KHH-01", to: "UPF-KHH", bandwidth_mbps: 10000, latency_ms: 2 },
      { from: "gNB-KHH-02", to: "UPF-KHH", bandwidth_mbps: 10000, latency_ms: 2 },
      { from: "gNB-PTG-01", to: "UPF-KHH", bandwidth_mbps: 5000, latency_ms: 4 },
      { from: "UPF-KHH", to: "AMF-TPE", bandwidth_mbps: 20000, latency_ms: 8 },
    ],
    services: [
      {
        id: "svc:slice-eMBB-enterprise-01",
        name: "Enterprise eMBB 5G slice (KHH-PTG)",
        type: "5G-slice",
        attrs: { sst: "eMBB", coverage: ["KHH", "PTG"], bandwidth_target_mbps: 1000 },
      },
      {
        id: "svc:slice-URLLC-iot-01",
        name: "IoT URLLC slice (KHH)",
        type: "5G-slice",
        attrs: { sst: "URLLC", coverage: ["KHH"], latency_target_ms: 5 },
      },
      {
        id: "svc:conn-khh-ptg",
        name: "Kaohsiung-Pingtung enterprise connectivity",
        type: "backhaul-link",
        attrs: { endpoints: ["KHH", "PTG"] },
      },
    ],
    live_hints: { peak_hours: "weekday 09-18", known_issues: [] },
  },

  "enterprise-backup-taipei": {
    name: "enterprise-backup-taipei",
    description:
      "Enterprise L3VPN with primary/secondary paths for a Taipei customer; carries video-conferencing and backup-sync traffic classes.",
    nodes: ["CE-TPE-01", "PE-TPE-A", "PE-TPE-B", "P-HQ"],
    links: [
      { from: "CE-TPE-01", to: "PE-TPE-A", bandwidth_mbps: 1000, latency_ms: 1 },
      { from: "CE-TPE-01", to: "PE-TPE-B", bandwidth_mbps: 500, latency_ms: 2 },
      { from: "PE-TPE-A", to: "P-HQ", bandwidth_mbps: 10000, latency_ms: 5 },
      { from: "PE-TPE-B", to: "P-HQ", bandwidth_mbps: 10000, latency_ms: 6 },
    ],
    services: [
      {
        id: "svc:enterprise-backup-link",
        name: "Enterprise backup L3VPN link",
        type: "l3vpn",
        attrs: { primary: "PE-TPE-A", backup: "PE-TPE-B", sla: "99.99%" },
      },
      {
        id: "svc:video-conf-traffic",
        name: "Video conferencing traffic class",
        type: "traffic-class",
        attrs: { dscp: "EF", priority: "high" },
      },
      {
        id: "svc:bg-sync-traffic",
        name: "Background synchronization traffic",
        type: "traffic-class",
        attrs: { dscp: "AF11", priority: "low" },
      },
    ],
  },

  "dc-fabric-tp1": {
    name: "dc-fabric-tp1",
    description: "Datacenter spine-leaf fabric at the TP1 site, 100GbE between spines and leaves.",
    nodes: ["spine-01", "spine-02", "leaf-01", "leaf-02", "leaf-03"],
    links: [
      { from: "leaf-01", to: "spine-01", bandwidth_mbps: 100000, latency_ms: 0.5 },
      { from: "leaf-01", to: "spine-02", bandwidth_mbps: 100000, latency_ms: 0.5 },
      { from: "leaf-02", to: "spine-01", bandwidth_mbps: 100000, latency_ms: 0.5 },
      { from: "leaf-02", to: "spine-02", bandwidth_mbps: 100000, latency_ms: 0.5 },
      { from: "leaf-03", to: "spine-01", bandwidth_mbps: 100000, latency_ms: 0.5 },
      { from: "leaf-03", to: "spine-02", bandwidth_mbps: 100000, latency_ms: 0.5 },
    ],
    services: [
      {
        id: "svc:east-west-fabric",
        name: "East-west fabric connectivity",
        type: "fabric",
        attrs: { topology: "spine-leaf" },
      },
      {
        id: "svc:campus-backup-traffic",
        name: "Campus backup traffic class",
        type: "traffic-class",
        attrs: { off_hours_throttle: true, default_limit_mbps: 500 },
      },
    ],
  },
};

// Cheap synonym resolver for NL → service candidates
const SYNONYMS: Record<string, string[]> = {
  備份: ["backup", "備援", "bg-sync"],
  備援: ["backup", "備份"],
  視訊: ["video", "conf"],
  視訊會議: ["video", "conf"],
  視訊流量: ["video", "conf"],
  "5g": ["slice", "embb", "urllc"],
  切片: ["slice"],
  高雄: ["khh", "kaohsiung"],
  屏東: ["ptg", "pingtung"],
  園區: ["campus"],
  iot: ["urllc", "iot"],
  東西向: ["east-west", "fabric"],
  企業: ["enterprise", "embb"],
  同步: ["sync", "bg-sync"],
  低延遲: ["urllc", "latency"],
};

export interface ResolveResult {
  matches: Service[];
  tried: string[];
  reason?: string;
}

export function resolveTarget(topologyName: string, hint: string): ResolveResult {
  const t = topologies[topologyName];
  if (!t) return { matches: [], tried: [], reason: `unknown topology: ${topologyName}` };

  const lower = hint.toLowerCase();
  const tokens = new Set<string>([lower]);
  for (const [key, vs] of Object.entries(SYNONYMS)) {
    if (lower.includes(key.toLowerCase())) for (const v of vs) tokens.add(v.toLowerCase());
  }

  const matches = t.services.filter((s) => {
    const hay = `${s.id} ${s.name} ${s.type} ${JSON.stringify(s.attrs)}`.toLowerCase();
    return [...tokens].some((tk) => tk.length > 1 && hay.includes(tk));
  });
  return { matches, tried: [...tokens] };
}

// Deterministic-ish fake live metrics keyed on topology+target
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
  const baseLat = 2 + r(18);
  const baseTput = 200 + r(1500);
  const jitter = () => (Math.random() - 0.5) * 4;
  return {
    latency_ms: +(Math.max(0.5, baseLat + jitter())).toFixed(2),
    throughput_mbps: +(Math.max(10, baseTput + jitter() * 20)).toFixed(1),
    packet_loss_pct: +(Math.random() * 0.5).toFixed(3),
    timestamp: new Date().toISOString(),
    status: "healthy" as const,
  };
}
