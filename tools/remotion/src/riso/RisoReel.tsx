// Risograph reel (Lemo-Opuscar "Risograph Print" style, adapted for regulated MF content).
// Two plates: R = Federal Blue (all words, numbers, silhouettes), G = Sunflower (sun, lit windows, warmth).
// Art and type print in two WebGL passes; the type pass has no pinholes and 1 px registration so every word stays legible,
// and is multiplied over the art with CSS (mix-blend-mode: multiply).
import React, {useEffect, useLayoutEffect, useRef, useState} from 'react';
import {AbsoluteFill, Audio, staticFile, useCurrentFrame, interpolate, Easing, delayRender, continueRender} from 'remotion';
import {makeRiso} from './riso';

export type Card = {big?: string; line: string; small?: string};
export type ReelProps = {cards: Card[]; slot: string; cuts: number[]; hits: number[]; audio?: string};

const W = 1080, H = 1920, M = 86;
const BLUE = [61, 85, 136], SUN = [255, 181, 17], PAPER = [244, 238, 226], WHITE = [255, 255, 255], NONE = [255, 255, 255];
const ART = {x: 0, y: 900, w: W, h: 520};          // art window (inside the safe zone)
const STRIP_Y = 1440, STRIP_H = 64;                 // disclosure strip, above the bottom 20 % UI zone
const TEXT_Y = 420;                                 // text starts below the top 15 % UI zone and the logo slot
const ink = (b = 0, y = 0) => `rgb(${Math.round(b * 255)},${Math.round(y * 255)},0)`;
const KO = ink(0, 0);
const ease = Easing.bezier(0.45, 0, 0.2, 1);
const rnd = (i: number) => { const x = Math.sin(i * 127.1 + 311.7) * 43758.5453; return x - Math.floor(x); };

let artPlate: HTMLCanvasElement | null = null, typePlate: HTMLCanvasElement | null = null;
const mk = () => { const c = document.createElement('canvas'); c.width = W; c.height = H; return c; };

function wrap(g: CanvasRenderingContext2D, s: string, max: number) {
  const w = s.split(' '), L: string[] = []; let c = '';
  for (const x of w) { const t = c ? c + ' ' + x : x; if (g.measureText(t).width <= max || !c) c = t; else { L.push(c); c = x; } }
  if (c) L.push(c); return L;
}
function textBlock(g: CanvasRenderingContext2D, s: string, x: number, y: number, size: number, weight: number, maxW = W - 2 * M, align: CanvasTextAlign = 'left') {
  g.font = `${weight} ${size}px Bricolage`; g.fillStyle = ink(1); g.textBaseline = 'top'; g.textAlign = align;
  const lines = wrap(g, s, maxW), lh = Math.round(size * 1.14);
  lines.forEach((l, i) => g.fillText(l, align === 'center' ? x + maxW / 2 : x, y + i * lh));
  return y + lines.length * lh;
}

// ---------- the world: one phone, held at one window, in one building, in a city ----------
function world(a: CanvasRenderingContext2D, k: number, lit: number, f: number) {
  // buildings of the city (world units; phone is 34 x 52 at the origin)
  const blocks: [number, number, number][] = [[-1600, 420, 900], [-1150, 380, 1300], [-740, 420, 1050], [-300, 640, 1500], [360, 380, 1150], [760, 460, 1350], [1240, 420, 950]];
  let wi = 0;
  for (const [x, w, h] of blocks) {
    a.fillStyle = ink(1); a.fillRect(x, 420 - h, w, 2400);
    for (let yy = 440 - h; yy < 1200; yy += 150) for (let xx = x + 50; xx < x + w - 90; xx += 130) {
      wi++;
      const on = rnd(wi) < lit;
      a.fillStyle = on ? ink(0, 1) : ink(.55); a.fillRect(xx, yy, 60, 84);
    }
  }
  // our window (the one the story starts in): paper, frame, the person and the phone
  a.fillStyle = ink(1); a.fillRect(-150, -150, 260, 300);
  a.fillStyle = KO; a.fillRect(-138, -138, 236, 276);
  a.fillStyle = ink(1); a.fillRect(-24, -138, 10, 276); a.fillRect(-138, -10, 236, 8);
  // person
  a.beginPath(); a.arc(-58, -54, 22, 0, Math.PI * 2); a.fill();
  a.beginPath(); a.roundRect(-92, -26, 70, 170, 26); a.fill();
  a.lineCap = 'round'; a.strokeStyle = ink(1); a.lineWidth = 16; a.beginPath(); a.moveTo(-34, 6); a.quadraticCurveTo(-8, 28, -10, 14); a.stroke();
  // phone (origin), screen lit sunflower once the message has arrived
  a.beginPath(); a.roundRect(-17, -26, 34, 52, 5); a.fillStyle = ink(1); a.fill();
  a.beginPath(); a.roundRect(-13, -21, 26, 40, 3); a.fillStyle = ink(0, 1); a.fill();
}

function phoneCloseUp(a: CanvasRenderingContext2D, lt: number, t: CanvasRenderingContext2D) {
  // the phone fills the art window; the debit bubble pops at lt = 21
  a.save(); a.beginPath(); a.rect(ART.x, ART.y, ART.w, ART.h); a.clip();
  a.fillStyle = ink(.3); a.fillRect(0, ART.y, W, ART.h);                       // warm table tint
  a.fillStyle = ink(1); a.beginPath(); a.roundRect(330, 930, 420, 700, 46); a.fill();
  a.fillStyle = KO; a.beginPath(); a.roundRect(352, 960, 376, 640, 26); a.fill();
  a.fillStyle = ink(1); a.beginPath(); a.ellipse(300, 1380, 120, 170, -.4, 0, Math.PI * 2); a.fill();   // thumb and hand
  const s = interpolate(lt, [19, 25, 29], [0, 1.12, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  if (s > 0) {
    a.save(); a.translate(540, 1080); a.scale(s, s);
    a.fillStyle = ink(0, 1); a.beginPath(); a.roundRect(-160, -54, 320, 108, 30); a.fill();
    a.restore();
    if (s > .9) { t.font = '700 46px Bricolage'; t.fillStyle = ink(1); t.textAlign = 'center'; t.textBaseline = 'middle'; t.fillText('SIP debited', 540, 1082); }
  }
  a.restore();
}

function tower(a: CanvasRenderingContext2D, lt: number) {
  // tilt up a tall residential tower: the camera moves, the building does not grow
  const pan = interpolate(lt, [0, 93], [0, 520], {easing: ease, extrapolateRight: 'clamp'});
  a.save(); a.beginPath(); a.rect(ART.x, ART.y, ART.w, ART.h); a.clip();
  a.fillStyle = ink(0, .35); a.fillRect(0, ART.y, W, ART.h);
  a.translate(0, pan);
  for (let i = 0, y = 1360; y > 200; i++, y -= 72) {
    a.fillStyle = ink(i % 2 ? .45 : 1); a.fillRect(280, y, 520, 72);
    for (let x = 320; x < 760; x += 80) { a.fillStyle = ink(0, 1); a.fillRect(x, y + 20, 38, 32); }
  }
  a.restore();
}

function draw(frame: number, p: ReelProps) {
  if (!artPlate) { artPlate = mk(); typePlate = mk(); }
  const a = artPlate.getContext('2d')!, t = typePlate!.getContext('2d')!;
  a.setTransform(1, 0, 0, 1, 0, 0); a.globalCompositeOperation = 'source-over'; a.fillStyle = KO; a.fillRect(0, 0, W, H);
  t.setTransform(1, 0, 0, 1, 0, 0); t.fillStyle = KO; t.fillRect(0, 0, W, H);
  const cuts = [0, ...p.cuts, 9999];
  const si = cuts.findIndex((c, i) => frame >= c && frame < cuts[i + 1]);
  const lt = frame - cuts[si];
  const card = p.cards[si];
  const AX = 540, AY = 1160;      // camera anchor (the phone) inside the art window

  // ---------- art ----------
  if (si === 0) phoneCloseUp(a, lt, t);
  else if (si === 1 || si === 2 || si === 3 || si === 5) {
    a.save(); a.beginPath(); a.rect(ART.x, ART.y, ART.w, ART.h); a.clip();
    if (si === 5) { a.fillStyle = ink(0, .3); a.fillRect(0, ART.y, W, ART.h); }          // dusk tint
    if (si === 3 || si === 5) {                                                              // the sun: rising at S4, setting at S6
      const sy = si === 3 ? interpolate(lt, [0, 60], [1500, 1130], {easing: ease, extrapolateRight: 'clamp'}) : interpolate(lt, [0, 110], [1060, 1240]);
      a.fillStyle = ink(0, 1); a.beginPath(); a.arc(si === 3 ? 760 : 820, sy, 230, 0, Math.PI * 2); a.fill();
    }
    let k = 0.42, lit = 0.08;
    if (si === 1) { k = interpolate(lt, [0, 79], [9, 1.6], {easing: ease}); lit = .05; }
    if (si === 2) { k = interpolate(lt, [0, 50], [1.6, .42], {easing: ease, extrapolateRight: 'clamp'}); lit = interpolate(lt, [8, 80], [.05, .92], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}); }
    if (si === 3) { k = .42; lit = .92; }
    if (si === 5) { k = interpolate(lt, [0, 113], [1.5, 7], {easing: Easing.in(Easing.quad)}); lit = .9; }
    const drop = si === 3 ? interpolate(lt, [0, 45], [0, 300], {easing: ease, extrapolateRight: 'clamp'}) : 0;
    a.translate(AX, AY + drop); a.scale(k, k); world(a, k, Math.floor(lit * 24) / 24, frame); a.restore();
  } else if (si === 4) tower(a, lt);

  // ---------- type ----------
  // logo slot (filled at co-branding) and progress dots
  t.strokeStyle = ink(1); t.lineWidth = 3; t.setLineDash([14, 10]); t.strokeRect(800, 300, 194, 76); t.setLineDash([]);
  for (let k = 0; k < p.cards.length; k++) { t.fillStyle = ink(1); t.beginPath(); t.arc(M + 12 + k * 30, 338, k === si ? 10 : 5, 0, Math.PI * 2); t.fill(); }
  let y = TEXT_Y;
  if (card.big) y = textBlock(t, card.big, M, y, card.big.length > 14 ? 112 : card.big.length > 12 ? 128 : 150, 800) + 26;
  y = textBlock(t, card.line, M, y, card.big ? 62 : (si === 0 ? 150 : 92), card.big ? 600 : 800) + 22;
  if (card.small) textBlock(t, card.small, M, y, 40, 500);
  // disclosure strip, on every frame
  a.setTransform(1, 0, 0, 1, 0, 0); a.fillStyle = KO; a.fillRect(0, STRIP_Y, W, STRIP_H);
  t.setTransform(1, 0, 0, 1, 0, 0);
  t.font = '500 24px Bricolage'; t.fillStyle = ink(1); t.textAlign = 'center'; t.textBaseline = 'middle'; t.fillText(p.slot, W / 2, STRIP_Y + STRIP_H / 2);
  t.strokeStyle = ink(1); t.lineWidth = 2; t.beginPath(); t.moveTo(M, STRIP_Y); t.lineTo(W - M, STRIP_Y); t.moveTo(M, STRIP_Y + STRIP_H); t.lineTo(W - M, STRIP_Y + STRIP_H); t.stroke();
  return {si, lt};
}

export const RisoReel: React.FC<ReelProps> = (p) => {
  const frame = useCurrentFrame();
  const artRef = useRef<HTMLCanvasElement>(null), typeRef = useRef<HTMLCanvasElement>(null);
  const pr = useRef<{art: any; type: any} | null>(null);
  // canvas text needs the font loaded first (the rupee sign lives in the latin-ext file)
  const [ready, setReady] = useState(false);
  const [fontHandle] = useState(() => delayRender('Bricolage for canvas text'));
  useEffect(() => {
    Promise.all(['500', '600', '700', '800'].map((w) => document.fonts.load(`${w} 60px Bricolage`, '₹ Aa 0123')))
      .then(() => { if (!document.fonts.check('800 60px Bricolage', '₹')) throw new Error('Bricolage (with ₹) did not load'); setReady(true); continueRender(fontHandle); });
  }, [fontHandle]);
  useLayoutEffect(() => {
    if (!ready) return;
    if (!pr.current) pr.current = {art: makeRiso(artRef.current, W, H), type: makeRiso(typeRef.current, W, H)};
    const {si, lt} = draw(frame, p);
    // registration: fixed per shot, a decaying kick when a number or the bubble lands
    const base: number[][] = [[2, -1], [-2, 2], [0, 0]];
    let kick = 0; for (const h of p.hits) { const d = frame - h; if (d >= 0 && d < 10) kick += Math.exp(-d / 2.6) * Math.cos(d * 1.9) * 11; }
    const off = [[base[0][0] + kick * .6, base[0][1] - kick * .3], [base[1][0] - kick, base[1][1] + kick * .5], [0, 0]];
    const seed = Math.floor(frame / 2);                               // grain boils on twos (12 fps)
    pr.current.art(artPlate, {inks: [BLUE, SUN, NONE], paper: PAPER, off, rot: [.0006, -.0005, 0], ang: [0.2618, 1.309, 0], period: 7, seed, sheet: 1 + si * .7, gate: [1, 1, 0], boil: .35});
    // type prints with a roller sweep over the first 8 frames of each card
    const sweep = interpolate(lt, [0, 8], [-40, W + 260], {extrapolateRight: 'clamp'});
    pr.current.type(typePlate, {inks: [BLUE, SUN, NONE], paper: WHITE, off: [[1, 0], [0, 0], [0, 0]], period: 7, grain: .35, pin: 0, gate: [1, 0, 0], sheet: 2 + si, seed, sweep: [si === 0 && frame < 8 ? sweep : (lt < 8 ? sweep : 1e5), 1e5, 1e5]});
  }, [frame, p, ready]);
  return (
    <AbsoluteFill style={{backgroundColor: `rgb(${PAPER.join(',')})`}}>
      <canvas ref={artRef} width={W} height={H} style={{position: 'absolute', inset: 0, width: '100%', height: '100%'}} />
      <canvas ref={typeRef} width={W} height={H} style={{position: 'absolute', inset: 0, width: '100%', height: '100%', mixBlendMode: 'multiply'}} />
      {p.audio ? <Audio src={staticFile(p.audio)} /> : null}
    </AbsoluteFill>
  );
};
