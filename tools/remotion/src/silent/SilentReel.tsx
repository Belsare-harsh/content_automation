// Silent-film reel (Lemo-Opuscar "1920s Silent Film" style, adapted to a 9:16 reel and to regulated MF content).
// A portrait film gate between velvet curtains; intertitle cards carry every number; one drawn scene is the turn.
// Each frame: paint the gate in grey values -> FilmPost print pass (flicker, weave, scratches, grain, sepia) -> dust -> iris -> theatre.
import React, {useEffect, useLayoutEffect, useRef, useState} from 'react';
import {AbsoluteFill, Audio, staticFile, useCurrentFrame, interpolate, Easing, delayRender, continueRender} from 'remotion';
import {FilmPost, damage} from './film';
import {intertitle, iris, theatre, FONT_BODY, FONT_TITLE} from './cards';

type Line = {text: string; size: number; italic?: boolean; title?: boolean; weight?: number};
export type Shot = {kind: 'card' | 'scene'; from: number; to: number; text?: string; lines?: Line[]; level?: number; shake?: number; fact_ids?: string[]; print: {strength: number; sepia: number; scratches?: number}};
export type SilentProps = {shots: Shot[]; slot: string; frames: number; audio?: string};

const W = 1080, H = 1920;
const GATE = {x: 112, y: 300, w: 856, h: 1140};      // 3:4 portrait gate, inside the reel safe zones
const PLAQUE = {y: 1456, h: 64};                      // SEBI disclosure plaque, above the bottom 20 % UI zone

let gateC: HTMLCanvasElement | null = null, film: any = null;

// ---- the turn: one frame of film, then the camera travels back along the strip a whole year ----
function filmStrip(g: CanvasRenderingContext2D, lt: number) {
  const w = GATE.w, h = GATE.h;
  const ls = Math.floor(lt * 16 / 30) * 30 / 16;                 // hand-cranked: motion sampled at 16 fps
  const bg = g.createRadialGradient(w / 2, h / 2, 50, w / 2, h / 2, h * .8);
  bg.addColorStop(0, '#d8d8d8'); bg.addColorStop(1, '#7a7a7a');   // a light table
  g.fillStyle = bg; g.fillRect(0, 0, w, h);
  const FW = 600, FH = 450, STEP = 500, N = 13;
  const k = interpolate(ls, [6, 32], [1.32, .74], {easing: Easing.inOut(Easing.cubic), extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const cy = interpolate(ls, [32, 84], [(N - 1) * STEP, 0], {easing: Easing.inOut(Easing.cubic), extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  g.save(); g.translate(w / 2, h / 2); g.scale(k, k); g.translate(0, -cy);
  // the strip
  g.fillStyle = '#1b1b1b'; g.fillRect(-380, -400, 760, N * STEP + 300);
  for (let y = -380; y < N * STEP - 100; y += 62) {                // sprocket holes
    g.fillStyle = '#cfcfcf'; g.beginPath(); g.roundRect(-362, y, 40, 30, 6); g.fill(); g.beginPath(); g.roundRect(322, y, 40, 30, 6); g.fill();
  }
  for (let i = 0; i < N; i++) {
    const lit = i === 0 || i === N - 1, y = i * STEP - FH / 2;
    g.fillStyle = lit ? '#f2f2f2' : '#9a9a9a'; g.fillRect(-FW / 2, y, FW, FH);
    // the same little scene in every frame: a horizon, a house, its window (lit in the first and last frame)
    g.fillStyle = lit ? '#c9c9c9' : '#7f7f7f'; g.fillRect(-FW / 2, y + FH * .68, FW, FH * .32);
    g.fillStyle = lit ? '#2a2a2a' : '#4a4a4a';
    g.beginPath(); g.moveTo(-120, y + FH * .68); g.lineTo(-120, y + FH * .38); g.lineTo(-20, y + FH * .2); g.lineTo(80, y + FH * .38); g.lineTo(80, y + FH * .68); g.closePath(); g.fill();
    g.fillStyle = lit ? '#fbfbfb' : '#6a6a6a'; g.fillRect(-48, y + FH * .44, 56, 64);
    // ink hatching in the shadow side, period engraving feel
    g.strokeStyle = lit ? 'rgba(20,20,20,.55)' : 'rgba(20,20,20,.35)'; g.lineWidth = 2;
    for (let j = 0; j < 9; j++) { g.beginPath(); g.moveTo(40 + j * 4, y + FH * .4 + j * 2); g.lineTo(80, y + FH * .4 + 30 + j * 10); g.stroke(); }
  }
  g.restore();
}

function drawFrame(frame: number, p: SilentProps, out: HTMLCanvasElement) {
  if (!gateC) { gateC = document.createElement('canvas'); gateC.width = GATE.w; gateC.height = GATE.h; film = new FilmPost(GATE.w, GATE.h); }
  const shot = p.shots.find((s) => frame >= s.from && frame < s.to) ?? p.shots[p.shots.length - 1];
  const lt = frame - shot.from;
  const g = gateC.getContext('2d')!;
  g.setTransform(1, 0, 0, 1, 0, 0);
  if (shot.kind === 'card') {
    const lines = (shot.lines ?? []).map((l) => ({text: l.text, size: l.size, italic: l.italic, weight: l.weight ?? (l.title ? 700 : 400), font: l.title ? FONT_TITLE : FONT_BODY}));
    intertitle(g, GATE.w, GATE.h, {lines, level: shot.level ?? 1, seed: shot.from, shake: shot.shake, gap: 1.22}, lt / 30);
  } else filmStrip(g, lt);
  const pr = film.render(gateC, {frame, strength: shot.print.strength, sepia: shot.print.sepia, scratches: shot.print.scratches ?? 1, seed: 3.1 + shot.from * .01});
  const o = out.getContext('2d')!;
  o.setTransform(1, 0, 0, 1, 0, 0);
  // the picture house
  theatre(o, W, H, GATE, film.mean * .9, 1);
  // valance above the screen, footlights below
  const val = o.createLinearGradient(0, 0, 0, GATE.y); val.addColorStop(0, '#080404'); val.addColorStop(1, '#3a1612');
  o.fillStyle = val; o.fillRect(0, 0, W, GATE.y - 8);
  for (let x = 0; x < W; x += 36) { o.fillStyle = '#5a2a20'; o.beginPath(); o.moveTo(x, GATE.y - 8); o.lineTo(x + 18, GATE.y + 14); o.lineTo(x + 36, GATE.y - 8); o.fill(); }
  const foot = o.createRadialGradient(W / 2, GATE.y + GATE.h + 40, 20, W / 2, GATE.y + GATE.h + 40, 700);
  foot.addColorStop(0, `rgba(255,214,150,${.18 + film.mean * .12})`); foot.addColorStop(1, 'rgba(255,214,150,0)');
  o.fillStyle = foot; o.fillRect(0, GATE.y + GATE.h, W, H - GATE.y - GATE.h);
  // the projected print, its dust, and the iris
  o.drawImage(pr, GATE.x, GATE.y);
  damage(o, GATE.x, GATE.y, GATE.w, GATE.h, frame, shot.print.strength * (shot.kind === 'card' ? .5 : 1));
  if (shot.kind === 'scene') {
    const r = interpolate(lt, [0, 10], [0, 900], {extrapolateRight: 'clamp', easing: Easing.out(Easing.quad)});
    o.save(); o.beginPath(); o.rect(GATE.x, GATE.y, GATE.w, GATE.h); o.clip(); iris(o, W, H, GATE.x + GATE.w / 2, GATE.y + GATE.h / 2, r, 4); o.restore();
  }
  if (frame >= p.frames - 18) {
    const r = interpolate(frame, [p.frames - 18, p.frames - 1], [900, 0], {easing: Easing.in(Easing.quad), extrapolateRight: 'clamp'});
    o.save(); o.beginPath(); o.rect(GATE.x, GATE.y, GATE.w, GATE.h); o.clip(); iris(o, W, H, GATE.x + GATE.w / 2, GATE.y + GATE.h / 2, r, 4); o.restore();
  }
  // empty logo slot on the valance (filled per distributor at co-branding)
  o.setLineDash([12, 9]); o.strokeStyle = 'rgba(236,229,213,.7)'; o.lineWidth = 3; o.strokeRect(808, 196, 160, 64); o.setLineDash([]);
  // SEBI disclosure plaque (brass), on every frame
  const br = o.createLinearGradient(0, PLAQUE.y, 0, PLAQUE.y + PLAQUE.h);
  br.addColorStop(0, '#b8955a'); br.addColorStop(.5, '#e2c486'); br.addColorStop(1, '#9c7a44');
  o.fillStyle = br; o.beginPath(); o.roundRect(36, PLAQUE.y, W - 72, PLAQUE.h, 8); o.fill();
  o.strokeStyle = '#5e4522'; o.lineWidth = 2; o.strokeRect(44, PLAQUE.y + 8, W - 88, PLAQUE.h - 16);
  // fit the placeholder line inside the plaque
  let fs = 22; do { o.font = `700 ${fs}px "${FONT_BODY}"`; fs -= 1; } while (o.measureText(p.slot).width > W - 130 && fs > 12); o.fillStyle = '#2a1d0c'; o.textAlign = 'center'; o.textBaseline = 'middle';
  o.fillText(p.slot, W / 2, PLAQUE.y + PLAQUE.h / 2 + 1);
}

export const SilentReel: React.FC<SilentProps> = (p) => {
  const frame = useCurrentFrame();
  const ref = useRef<HTMLCanvasElement>(null);
  const [ready, setReady] = useState(false);
  const [h] = useState(() => delayRender('Playfair for canvas text'));
  useEffect(() => {
    Promise.all([`700 60px "${FONT_TITLE}"`, `italic 400 60px "${FONT_BODY}"`, `700 60px "${FONT_BODY}"`].map((f) => document.fonts.load(f, '₹ Aa 0123')))
      .then(() => { if (!document.fonts.check(`700 60px "${FONT_TITLE}"`, '₹')) throw new Error('Playfair Display SC (with ₹) did not load'); setReady(true); continueRender(h); });
  }, [h]);
  useLayoutEffect(() => { if (ready && ref.current) drawFrame(frame, p, ref.current); }, [frame, p, ready]);
  return (
    <AbsoluteFill style={{backgroundColor: '#050404'}}>
      <canvas ref={ref} width={W} height={H} style={{width: '100%', height: '100%'}} />
      {p.audio ? <Audio src={staticFile(p.audio)} /> : null}
    </AbsoluteFill>
  );
};
