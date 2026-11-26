import React from "react";
import {
  AbsoluteFill,
  Easing,
  interpolate,
  interpolateColors,
  random,
  Sequence,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { loadFont } from "@remotion/google-fonts/Outfit";

const { fontFamily } = loadFont("normal", { weights: ["500", "800"], subsets: ["latin"] });

const W = 1080;
const H = 1920;
const GOLD = "#ffcd78";
const CREAM = "#fff6e2";
const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;
const ease = Easing.bezier(0.16, 1, 0.3, 1);

// ---------------------------------------------------------------- the people
const YOU = { x: 540, y: 1300 };
const NEAR = [
  { x: 370, y: 1225, at: 1.2 },
  { x: 720, y: 1265, at: 3.0 },
  { x: 420, y: 1455, at: 3.8 },
  { x: 690, y: 1475, at: 4.6 },
];
type Node = { x: number; y: number; d: number; ph: number };
const FIELD: Node[] = (() => {
  const out: Node[] = [];
  for (let i = 0; out.length < 130 && i < 6000; i++) {
    const x = 50 + random(`x${i}`) * (W - 100);
    const y = 80 + random(`y${i}`) * (H - 160);
    if (y > 470 && y < 1060) continue; // keep the caption band clear
    if (Math.hypot(x - YOU.x, y - YOU.y) < 290) continue;
    if (out.some((p) => Math.hypot(p.x - x, p.y - y) < 76)) continue;
    out.push({ x, y, d: Math.hypot(x - YOU.x, y - YOU.y), ph: random(`p${i}`) * 6.28 });
  }
  return out;
})();
const MAXD = Math.max(...FIELD.map((p) => p.d));
const ALL: { x: number; y: number; ph?: number }[] = [
  YOU,
  ...NEAR.map((n, i) => ({ ...n, ph: 1.3 * i + 0.4 })),
  ...FIELD,
];
const EDGES: { a: number; b: number; at: number }[] = (() => {
  const set = new Set<string>();
  const out: { a: number; b: number; at: number }[] = [];
  const dist = (i: number) => Math.hypot(ALL[i].x - YOU.x, ALL[i].y - YOU.y);
  const add = (i: number, j: number) => {
    const [a, b] = dist(i) <= dist(j) ? [i, j] : [j, i];
    const k = `${a}-${b}`;
    if (set.has(k)) return;
    set.add(k);
    out.push({ a, b, at: 14.6 + (dist(a) / MAXD) * 2.6 });
  };
  for (let i = 1; i <= 4; i++) add(0, i);
  for (let i = 1; i < ALL.length; i++) {
    const near = ALL.map((p, j) => ({ j, d: Math.hypot(p.x - ALL[i].x, p.y - ALL[i].y) }))
      .filter((o) => o.j !== i && o.j !== 0)
      .sort((p, q) => p.d - q.d)
      .slice(0, 2);
    near.forEach((o) => add(i, o.j));
  }
  return out;
})();

const Sky: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;
  const k = interpolate(t, [13.5, 20.5], [0, 1], { ...clamp, easing: Easing.inOut(Easing.cubic) });
  const top = interpolateColors(k, [0, 1], ["#06081a", "#1a2266"]);
  const mid = interpolateColors(k, [0, 1], ["#0e0c30", "#7a3a8e"]);
  const bot = interpolateColors(k, [0, 1], ["#18103c", "#ff9a5c"]);
  return <AbsoluteFill style={{ background: `linear-gradient(180deg, ${top} 0%, ${mid} 58%, ${bot} 100%)` }} />;
};

const Constellation: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;
  const drift = (i: number, ax: "x" | "y") =>
    i === 0 ? 0 : 7 * Math.sin(t * 0.5 + (ALL[i].ph ?? 0) * (ax === "x" ? 1 : 1.7) + i);
  const pos = (i: number) => ({ x: ALL[i].x + drift(i, "x"), y: ALL[i].y + drift(i, "y") });
  const lit = interpolate(t, [14.6, 17.6], [0, 1], clamp);

  const nodeAlpha = (i: number) => {
    if (i === 0) return 1;
    const tw = 0.8 + 0.2 * Math.sin(t * 2 + i);
    if (i <= 4) {
      const on = interpolate(t, [NEAR[i - 1].at, NEAR[i - 1].at + 0.5], [0, 1], { ...clamp, easing: ease });
      const gone = interpolate(t, [6.0, 7.2], [1, 0.1], clamp); // the setup beat: connections fade
      const back = interpolate(t, [8.5, 9.3], [0, 1], clamp);
      const v = on * gone;
      return (v + (1 - v) * back) * tw;
    }
    const at = 8.6 + (FIELD[i - 5].d / MAXD) * 2.6;
    return interpolate(t, [at, at + 0.6], [0, 1], { ...clamp, easing: ease }) * tw;
  };

  const ring = interpolate(t, [7.0, 8.5], [1, 0], clamp);
  const youLabel = interpolate(t, [0.15, 0.6], [0, 1], clamp) * interpolate(t, [7.4, 8.4], [1, 0], clamp);
  const pulse = 17 + 2.5 * Math.sin(t * 2.6);

  return (
    <svg width={W} height={H} style={{ position: "absolute" }}>
      <defs>
        <filter id="glow" x="-50%" y="-50%" width="200%" height="200%">
          <feGaussianBlur stdDeviation="9" result="b" />
          <feMerge>
            <feMergeNode in="b" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
      </defs>
      <g filter="url(#glow)">
        {EDGES.map(({ a, b, at }) => {
          const g = interpolate(t, [at, at + 0.55], [0, 1], { ...clamp, easing: ease });
          if (g <= 0) return null;
          const p = pos(a);
          const q = pos(b);
          return (
            <line
              key={`${a}-${b}`}
              x1={p.x}
              y1={p.y}
              x2={p.x + (q.x - p.x) * g}
              y2={p.y + (q.y - p.y) * g}
              stroke={GOLD}
              strokeOpacity={0.55}
              strokeWidth={3}
              strokeLinecap="round"
            />
          );
        })}
        {ALL.map((_, i) => {
          if (i === 0) return null;
          const a = nodeAlpha(i);
          if (a < 0.01) return null;
          const p = pos(i);
          const r = (i <= 4 ? 9 : 6.5) * (1 + 0.25 * lit);
          return <circle key={i} cx={p.x} cy={p.y} r={r} fill="#ffd696" opacity={a} />;
        })}
        {[0, 0.5].map((off) => {
          const ph = (t / 1.8 + off) % 1;
          return (
            <circle
              key={off}
              cx={YOU.x}
              cy={YOU.y}
              r={22 + ph * 190}
              fill="none"
              stroke={CREAM}
              strokeWidth={3}
              opacity={0.42 * (1 - ph) * ring}
            />
          );
        })}
        <circle cx={YOU.x} cy={YOU.y} r={pulse} fill={CREAM} />
      </g>
      <text
        x={YOU.x}
        y={YOU.y + 62}
        textAnchor="middle"
        fill={CREAM}
        opacity={youLabel}
        style={{ fontFamily, fontWeight: 500, fontSize: 40 }}
      >
        you
      </text>
    </svg>
  );
};

// ---------------------------------------------------------------- words
type Line = { text: string; size?: number; gold?: boolean; delay?: number; light?: boolean };

const Words: React.FC<{ line: Line; endAt: number }> = ({ line, endAt }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const words = line.text.split(" ");
  const start = (line.delay ?? 0) * fps;
  const out = interpolate(frame, [endAt - 9, endAt], [1, 0], clamp);
  return (
    <div
      style={{
        display: "flex",
        flexWrap: "wrap",
        justifyContent: "center",
        columnGap: "0.28em",
        fontSize: line.size ?? 84,
        fontWeight: line.light ? 500 : 800,
        lineHeight: 1.12,
        color: line.gold ? GOLD : "#fffaf0",
        textShadow: "0 4px 28px rgba(4,4,20,0.75)",
        opacity: out,
      }}
    >
      {words.map((w, i) => {
        const f0 = start + i * 2.2;
        const k = interpolate(frame, [f0, f0 + 0.45 * fps], [0, 1], {
          ...clamp,
          easing: Easing.spring({ damping: 200 }),
        });
        return (
          <span
            key={i}
            style={{
              opacity: k,
              translate: `0px ${(1 - k) * 36}px`,
              filter: `blur(${(1 - k) * 8}px)`,
            }}
          >
            {w}
          </span>
        );
      })}
    </div>
  );
};

const Block: React.FC<{ lines: Line[]; dur: number }> = ({ lines, dur }) => (
  <AbsoluteFill style={{ justifyContent: "center", alignItems: "center", top: -220, padding: "0 64px", fontFamily }}>
    <div style={{ display: "flex", flexDirection: "column", gap: 6, alignItems: "center", textAlign: "center" }}>
      {lines.map((l, i) =>
        l.text ? <Words key={i} line={l} endAt={dur} /> : <div key={i} style={{ height: l.size ?? 30 }} />,
      )}
    </div>
  </AbsoluteFill>
);

// The script: one block per beat, timed in seconds. Edit the words and timings; keep each
// block to a few short lines. `gold` marks the words that carry the idea, `delay` staggers lines.
const BLOCKS: { from: number; to: number; lines: Line[] }[] = [
  { from: 0, to: 3, lines: [{ text: "Hook line one," }, { text: "said in the" }, { text: "first second.", gold: true }] },
  {
    from: 3,
    to: 6,
    lines: [
      { text: "Example one." },
      { text: "Example two.", delay: 0.8 },
      { text: "Example three.", gold: true, size: 80, delay: 1.6 },
    ],
  },
  { from: 6, to: 8.5, lines: [{ text: "The problem,", size: 86 }, { text: "in one breath.", size: 86 }] },
  {
    from: 8.5,
    to: 12,
    lines: [
      { text: "The bigger", size: 86 },
      { text: "picture, built", size: 86, delay: 0.5 },
      { text: "line by line.", size: 104, gold: true, delay: 1.0 },
    ],
  },
  { from: 12, to: 14.5, lines: [{ text: "What has been" }, { text: "missing until now." }] },
  { from: 14.5, to: 17.5, lines: [{ text: "What if", size: 132 }, { text: "it could?", size: 132, gold: true, delay: 0.3 }] },
  {
    from: 17.5,
    to: 21,
    lines: [
      { text: "this is", size: 46, light: true },
      { text: "The Big Idea", size: 116, delay: 0.15 },
      { text: "", size: 24 },
      { text: "One sentence that names it.", size: 50, light: true, delay: 0.9 },
    ],
  },
  {
    from: 21,
    to: 24.5,
    lines: [
      { text: "A question that" },
      { text: "invites comments.", gold: true, delay: 0.4 },
      { text: "", size: 40 },
      { text: "yoursite.org", size: 46, light: true, delay: 0.9 },
    ],
  },
];

export const ConstellationShort: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  return (
    <AbsoluteFill style={{ backgroundColor: "#06081a" }}>
      <Sky />
      <AbsoluteFill
        style={{
          scale: interpolate(frame, [0, durationInFrames], [1, 1.07], clamp),
          translate: interpolate(frame, [0, durationInFrames], ["0px 0px", "0px -40px"], clamp),
        }}
      >
        <Constellation />
      </AbsoluteFill>
      {BLOCKS.map((b) => (
        <Sequence key={b.from} from={Math.round(b.from * fps)} durationInFrames={Math.round((b.to - b.from) * fps)}>
          <Block lines={b.lines} dur={Math.round((b.to - b.from) * fps)} />
        </Sequence>
      ))}
    </AbsoluteFill>
  );
};
