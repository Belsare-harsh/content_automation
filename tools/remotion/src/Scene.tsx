import React from "react";
import {AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig, Easing} from "remotion";
import type {Layer, Scene} from "./types";

const ease = Easing.bezier(0.16, 1, 0.3, 1);

const Rect: React.FC<{l: Layer; progress?: number}> = ({l, progress = 1}) => {
  const dashed = l.role === "logo_slot";
  return (
    <div
      style={{
        position: "absolute",
        left: l.x,
        top: l.y,
        width: l.role === "progress" ? l.w * progress : l.w,
        height: l.h,
        background: l.fill && l.fill !== "none" ? l.fill : "transparent",
        border: dashed ? `3px dashed ${l.stroke}` : undefined,
        borderRadius: l.radius ?? 0,
        boxSizing: "border-box",
      }}
    />
  );
};

const TextLines: React.FC<{l: Layer; startFrame: number}> = ({l, startFrame}) => {
  const frame = useCurrentFrame();
  const lh = (l.font_size ?? 40) * (l.line_height ?? 1.25);
  return (
    <div style={{position: "absolute", left: l.x, top: l.y, width: l.w}}>
      {(l.lines ?? [l.text ?? ""]).map((line, i) => {
        const f0 = startFrame + i * 4;
        const t = interpolate(frame, [f0, f0 + 14], [0, 1], {extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: ease});
        return (
          <div
            key={i}
            style={{
              height: lh,
              lineHeight: `${lh}px`,
              fontFamily: "Inter",
              fontWeight: l.font_weight,
              fontSize: l.font_size,
              color: l.color,
              textAlign: l.align ?? "left",
              whiteSpace: "nowrap",
              opacity: t,
              transform: `translateY(${(1 - t) * 24}px)`,
            }}
          >
            {line}
          </div>
        );
      })}
    </div>
  );
};

const Highlight: React.FC<{l: Layer}> = ({l}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const s = spring({frame: frame - 4, fps, config: {damping: 14, stiffness: 120}});
  const lh = (l.font_size ?? 120) * (l.line_height ?? 1.25);
  return (
    <div
      style={{
        position: "absolute",
        left: l.x,
        top: l.y,
        width: l.w,
        height: lh,
        lineHeight: `${lh}px`,
        fontFamily: "Inter",
        fontWeight: l.font_weight,
        fontSize: l.font_size,
        color: l.color,
        opacity: s,
        transform: `scale(${0.85 + 0.15 * s})`,
        transformOrigin: "left center",
        whiteSpace: "nowrap",
      }}
    >
      {l.text}
    </div>
  );
};

export const SceneView: React.FC<{scene: Scene; index: number}> = ({scene, index}) => {
  const frame = useCurrentFrame();
  const {durationInFrames} = useVideoConfig();
  // the design's progress bar already has this page's final width; grow into it from the previous page's width
  const p = interpolate(frame, [0, Math.round(durationInFrames * 0.6)], [index / (index + 1), 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: ease,
  });
  const hasHighlight = scene.layers.some((l) => l.role === "highlight");
  return (
    <AbsoluteFill>
      {scene.layers.map((l) => {
        if (l.kind === "rect") return <Rect key={l.id} l={l} progress={l.role === "progress" ? p : 1} />;
        if (l.role === "highlight") return <Highlight key={l.id} l={l} />;
        if (l.role === "disclosure") return <TextLines key={l.id} l={l} startFrame={-30} />;
        return <TextLines key={l.id} l={l} startFrame={hasHighlight ? 14 : 4} />;
      })}
    </AbsoluteFill>
  );
};
