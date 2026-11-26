import React from "react";
import { interpolate, useCurrentFrame } from "remotion";
import rough from "roughjs";

// Hand-drawn shapes with Rough.js. A fixed `seed` keeps the wobble identical on every frame,
// so the drawing does not flicker; the line is revealed with a stroke-dash animation.
const gen = rough.generator();

type Props = { x: number; y: number; w: number; h: number; start: number; color?: string };

export const SketchBox: React.FC<Props> = ({ x, y, w, h, start, color = "#ffcd78" }) => {
  const frame = useCurrentFrame();
  const shape = gen.rectangle(x, y, w, h, { seed: 7, roughness: 2.4, bowing: 2.2, stroke: color, strokeWidth: 4 });
  const paths = gen.toPaths(shape);
  const k = interpolate(frame, [start, start + 24], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return (
    <g>
      {paths.map((p, i) => (
        <path
          key={i}
          d={p.d}
          stroke={p.stroke}
          strokeWidth={p.strokeWidth}
          fill="none"
          strokeLinecap="round"
          pathLength={1}
          strokeDasharray={1}
          strokeDashoffset={1 - k}
        />
      ))}
    </g>
  );
};

export const SketchDemo: React.FC = () => (
  <svg width={1080} height={1920} style={{ position: "absolute", background: "#0e0c30" }}>
    <SketchBox x={190} y={760} w={700} h={400} start={0} />
  </svg>
);
