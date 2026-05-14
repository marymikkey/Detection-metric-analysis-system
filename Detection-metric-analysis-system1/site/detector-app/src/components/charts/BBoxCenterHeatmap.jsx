import { useRef, useEffect } from 'react';

const GRID = 35;
const ACCENT_RGB = '129,140,248';
const SZ = 400;      // internal canvas resolution (square)
const LABEL_H = 18;  // bottom strip for x-axis labels
const PLOT = SZ - LABEL_H; // square plot area: PLOT × PLOT

/* ── Real data ───────────────────────────────────────────────────────────── */

function drawReal(ctx, centers) {
  // Background
  ctx.fillStyle = '#080a14';
  ctx.fillRect(0, 0, SZ, SZ);

  // ── Density binning ──────────────────────────────────────────────────────
  const bins = Array.from({ length: GRID }, () => new Array(GRID).fill(0));
  centers.forEach(pt => {
    const x = Array.isArray(pt) ? pt[0] : pt.x;
    const y = Array.isArray(pt) ? pt[1] : pt.y;
    bins[Math.min(Math.floor(y * GRID), GRID - 1)]
        [Math.min(Math.floor(x * GRID), GRID - 1)]++;
  });
  const maxBin = Math.max(...bins.flat(), 1);

  // ── Draw density cells ───────────────────────────────────────────────────
  const cell = PLOT / GRID;
  for (let row = 0; row < GRID; row++) {
    for (let col = 0; col < GRID; col++) {
      const count = bins[row][col];
      if (count === 0) continue;
      const alpha = 0.05 + Math.sqrt(count / maxBin) * 0.93;
      ctx.fillStyle = `rgba(${ACCENT_RGB},${alpha.toFixed(3)})`;
      ctx.fillRect(col * cell, row * cell, cell, cell);
    }
  }

  // ── Draw individual points on top ────────────────────────────────────────
  ctx.globalAlpha = 0.42;
  ctx.fillStyle = '#ffffff';
  centers.forEach(pt => {
    const x = Array.isArray(pt) ? pt[0] : pt.x;
    const y = Array.isArray(pt) ? pt[1] : pt.y;
    ctx.beginPath();
    ctx.arc(x * PLOT, y * PLOT, 2, 0, Math.PI * 2);
    ctx.fill();
  });
  ctx.globalAlpha = 1;

  // ── Guide grid lines ─────────────────────────────────────────────────────
  ctx.strokeStyle = 'rgba(255,255,255,.08)'; ctx.lineWidth = .5;
  [.25, .5, .75].forEach(v => {
    ctx.beginPath(); ctx.moveTo(v * PLOT, 0); ctx.lineTo(v * PLOT, PLOT); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(0, v * PLOT); ctx.lineTo(PLOT, v * PLOT); ctx.stroke();
  });

  // ── Border ───────────────────────────────────────────────────────────────
  ctx.strokeStyle = 'rgba(255,255,255,.22)'; ctx.lineWidth = 1;
  ctx.strokeRect(0, 0, PLOT, PLOT);

  // ── X-axis labels ────────────────────────────────────────────────────────
  ctx.fillStyle = '#4e5270'; ctx.font = '9px IBM Plex Mono';
  ['0', '0.25', '0.5', '0.75', '1.0'].forEach((l, i) =>
    ctx.fillText(l, i * (PLOT - 16) / 4, SZ - 3));

  // ── max count badge (top-right) ──────────────────────────────────────────
  ctx.fillStyle = 'rgba(255,255,255,.28)'; ctx.font = '8px IBM Plex Mono';
  ctx.fillText(`max ${maxBin}`, PLOT - 52, 12);
}

/* ── Fake / legacy (seed-based, for COCO / VOC / KITTI) ─────────────────── */

function drawFake(ctx, seed) {
  ctx.fillStyle = '#080a14';
  ctx.fillRect(0, 0, SZ, SZ);

  [[.5,.5,1.1],[.5,.4,.7],[.3,.5,.4],[.7,.5,.38],[.5,.65,.45],[.2,.3,.2],[.8,.3,.22]]
    .forEach(([cx, cy, str]) => {
      const g = ctx.createRadialGradient(cx * SZ, cy * SZ, 0, cx * SZ, cy * SZ, SZ * .22);
      g.addColorStop(0,  `rgba(${ACCENT_RGB},${(str * .65).toFixed(2)})`);
      g.addColorStop(.5, `rgba(${ACCENT_RGB},${(str * .18).toFixed(2)})`);
      g.addColorStop(1,  'rgba(0,0,0,0)');
      ctx.fillStyle = g;
      ctx.fillRect(0, 0, SZ, SZ);
    });

  ctx.strokeStyle = 'rgba(255,255,255,.07)'; ctx.lineWidth = .5;
  [.25, .5, .75].forEach(v => {
    ctx.beginPath(); ctx.moveTo(v * SZ, 0); ctx.lineTo(v * SZ, SZ); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(0, v * SZ); ctx.lineTo(SZ, v * SZ); ctx.stroke();
  });
  ctx.strokeStyle = 'rgba(255,255,255,.18)'; ctx.lineWidth = 1;
  ctx.strokeRect(0, 0, SZ, SZ);
  ctx.fillStyle = '#4e5270'; ctx.font = '9px IBM Plex Mono';
  ['0', '0.25', '0.5', '0.75', '1.0'].forEach((l, i) =>
    ctx.fillText(l, i * (SZ - 16) / 4, SZ - 3));
}

/* ── Component ───────────────────────────────────────────────────────────── */

// `height` prop is accepted for API compatibility but ignored — the chart
// is always square so the aspect ratio is maintained regardless of container.
export default function BBoxCenterHeatmap({ seed = 1, centers }) {
  const ref = useRef(null);

  useEffect(() => {
    const c = ref.current;
    if (!c) return;
    const ctx = c.getContext('2d');
    if (centers?.length) {
      drawReal(ctx, centers);
    } else {
      drawFake(ctx, seed);
    }
  }, [seed, centers]);

  return (
    <div style={{ width: '100%', maxWidth: 380, aspectRatio: '1 / 1' }}>
      <canvas
        ref={ref}
        width={SZ}
        height={SZ}
        style={{ width: '100%', height: '100%', display: 'block', borderRadius: 5, border: '1px solid var(--border)' }}
      />
    </div>
  );
}
