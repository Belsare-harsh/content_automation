// Props written by tools/animate.py from the approved step 5 design (05_design/design.json).
// Every word on screen comes from these layers; this code never adds or changes text.

export type Layer = {
  id: string;
  role: string; // background | logo_slot | progress | disclosure_bg | disclosure | script | highlight | rule | panel
  kind: "rect" | "text";
  x: number;
  y: number;
  w: number;
  h: number;
  fill?: string;
  stroke?: string;
  radius?: number;
  text?: string;
  lines?: string[];
  font_family?: string;
  font_weight?: number;
  font_size?: number;
  line_height?: number;
  color?: string;
  align?: "left" | "center";
};

export type Scene = {
  id: string;
  kind: "slate" | "page";
  durationInFrames: number;
  layers: Layer[];
};

export type VideoProps = {
  width: number;
  height: number;
  fps: number;
  colors: Record<string, string>;
  scenes: Scene[];
};
