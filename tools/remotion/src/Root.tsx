import React from "react";
import {Composition, staticFile} from "remotion";
import {loadFont} from "@remotion/fonts";
import {FinpediaVideo} from "./Video";
import type {VideoProps} from "./types";
import {RisoReel} from "./riso/RisoReel";
import reel from "./riso/reel-rmwdezgf7.json";
import {SilentReel} from "./silent/SilentReel";
import silent from "./silent/silent-rmwdezgf7.json";
import type {SilentProps} from "./silent/SilentReel";

// Brand fonts are local files (public/fonts). Swap them when the real brand assets arrive.
loadFont({family: "Inter", url: staticFile("fonts/Inter-Regular.otf"), weight: "400"});
loadFont({family: "Inter", url: staticFile("fonts/Inter-Medium.otf"), weight: "500"});
loadFont({family: "Inter", url: staticFile("fonts/Inter-Bold.otf"), weight: "700"});
// Bricolage Grotesque (OFL) for the risograph style; latin-ext carries the rupee sign
const LATIN = "U+0000-00FF,U+0131,U+0152-0153,U+02BB-02BC,U+02C6,U+02DA,U+02DC,U+2000-206F,U+2074,U+20AC,U+2122,U+2191,U+2193,U+2212,U+2215,U+FEFF,U+FFFD";
const LATIN_EXT = "U+0100-02AF,U+0304,U+0308,U+0329,U+1E00-1E9F,U+1EF2-1EFF,U+2020,U+20A0-20AB,U+20AD-20C0,U+2113,U+2C60-2C7F,U+A720-A7FF";
// Playfair Display (OFL) for the silent-film intertitles; latin-ext carries the rupee sign
for (const [fam, file, w, style] of [["Playfair Display SC", "playfair-display-sc", "700", "normal"], ["Playfair Display", "playfair-display", "700", "normal"], ["Playfair Display", "playfair-display", "400", "italic"]] as const) {
  const suf = `${w}-${style}`;
  loadFont({family: fam, url: staticFile(`silent/${file}-latin-${suf}.woff2`), weight: w, style, unicodeRange: LATIN});
  loadFont({family: fam, url: staticFile(`silent/${file}-latin-ext-${suf}.woff2`), weight: w, style, unicodeRange: LATIN_EXT});
}
for (const w of ["500", "600", "700", "800"]) {
  loadFont({family: "Bricolage", url: staticFile("riso/bricolage-grotesque-latin-wght-normal.woff2"), weight: w, unicodeRange: LATIN});
  loadFont({family: "Bricolage", url: staticFile("riso/bricolage-grotesque-latin-ext-wght-normal.woff2"), weight: w, unicodeRange: LATIN_EXT});
}

const sample: VideoProps = {
  width: 1080,
  height: 1920,
  fps: 30,
  colors: {background: "#F6F1E7"},
  scenes: [
    {
      id: "S01",
      kind: "page",
      durationInFrames: 90,
      layers: [
        {id: "bg", role: "background", kind: "rect", x: 0, y: 0, w: 1080, h: 1920, fill: "#F6F1E7"},
        {id: "t", role: "script", kind: "text", x: 86, y: 800, w: 908, h: 200, text: "Sample only. Real scenes come from props.json.",
          lines: ["Sample only. Real scenes", "come from props.json."], font_size: 64, font_weight: 700, line_height: 1.25, color: "#14213D"},
      ],
    },
  ],
};

export const RemotionRoot: React.FC = () => (
  <>
  <Composition
    id="SilentReel"
    component={SilentReel}
    defaultProps={silent as unknown as SilentProps}
    width={1080}
    height={1920}
    fps={30}
    durationInFrames={silent.frames}
  />
  <Composition
    id="RisoReel"
    component={RisoReel}
    defaultProps={reel}
    width={1080}
    height={1920}
    fps={30}
    durationInFrames={reel.frames}
  />
  <Composition
    id="FinpediaVideo"
    component={FinpediaVideo}
    defaultProps={sample}
    width={1080}
    height={1920}
    fps={30}
    durationInFrames={90}
    calculateMetadata={({props}) => ({
      width: props.width,
      height: props.height,
      fps: props.fps,
      durationInFrames: props.scenes.reduce((n, s) => n + s.durationInFrames, 0),
    })}
  />
  </>
);
