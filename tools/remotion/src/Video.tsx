import React from "react";
import {AbsoluteFill, Sequence, interpolate, useCurrentFrame, useVideoConfig} from "remotion";
import {SceneView} from "./Scene";
import type {Scene, VideoProps} from "./types";

const Fade: React.FC<{children: React.ReactNode}> = ({children}) => {
  const frame = useCurrentFrame();
  const {durationInFrames} = useVideoConfig();
  const o = interpolate(frame, [0, 8, durationInFrames - 8, durationInFrames], [0, 1, 1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  return <AbsoluteFill style={{opacity: o}}>{children}</AbsoluteFill>;
};

export const FinpediaVideo: React.FC<VideoProps> = ({scenes, colors}) => {
  let from = 0;
  let page = 0;
  return (
    <AbsoluteFill style={{background: colors.background}}>
      {scenes.map((s: Scene) => {
        const start = from;
        from += s.durationInFrames;
        const idx = s.kind === "page" ? page++ : 0;
        return (
          <Sequence key={s.id} name={s.id} from={start} durationInFrames={s.durationInFrames}>
            <Fade>
              <SceneView scene={s} index={idx} />
            </Fade>
          </Sequence>
        );
      })}
    </AbsoluteFill>
  );
};
