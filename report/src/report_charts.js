// Small SVG chart helpers. Every colour comes from CSS tokens; text uses ink tokens, never series colours.
const NS = 'http://www.w3.org/2000/svg';
const css = (v) => getComputedStyle(document.documentElement).getPropertyValue(v).trim();
const fmt = (v, d = 1) => (v > 0 ? '+' : v < 0 ? '−' : '') + Math.abs(v).toFixed(d);
const fmtPlain = (v, d = 1) => (v < 0 ? '−' : '') + Math.abs(v).toFixed(d);

function el(tag, attrs = {}, parent) {
  const e = document.createElementNS(NS, tag);
  for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, v);
  if (parent) parent.appendChild(e);
  return e;
}

const tip = document.createElement('div');
tip.className = 'tip';
tip.hidden = true;
document.body.appendChild(tip);
function showTip(evt, html) {
  tip.innerHTML = html;
  tip.hidden = false;
  const pad = 14, w = tip.offsetWidth, h = tip.offsetHeight;
  let x = evt.clientX + pad, y = evt.clientY + pad;
  if (x + w > window.innerWidth - 8) x = evt.clientX - w - pad;
  if (y + h > window.innerHeight - 8) y = evt.clientY - h - pad;
  tip.style.left = Math.max(8, x) + 'px';
  tip.style.top = Math.max(8, y) + 'px';
}
const hideTip = () => { tip.hidden = true; };
function hover(node, html) {
  node.addEventListener('pointermove', (e) => showTip(e, html));
  node.addEventListener('pointerleave', hideTip);
  node.setAttribute('tabindex', '0');
  node.addEventListener('focus', (e) => {
    const r = node.getBoundingClientRect();
    showTip({ clientX: r.right, clientY: r.top }, html);
  });
  node.addEventListener('blur', hideTip);
}

function niceTicks(lo, hi, n = 5) {
  const span = hi - lo, step0 = span / n;
  const mag = Math.pow(10, Math.floor(Math.log10(step0)));
  const step = [1, 2, 2.5, 5, 10].map((m) => m * mag).find((s) => span / s <= n) || 10 * mag;
  const ticks = [];
  for (let t = Math.ceil(lo / step) * step; t <= hi + 1e-9; t += step) ticks.push(+t.toFixed(10));
  return ticks;
}

// Horizontal bars (optionally with an interval) on a shared zero baseline.
// rows: [{label, value, lo?, hi?, color, note?}]
function hbars(container, rows, { unit = '', domain, labelW = 190, rowH = 30, decimals = 1, signed = true } = {}) {
  const W = Math.max(container.clientWidth, 300), lw = Math.min(labelW, W * 0.42);
  const H = rows.length * rowH + 34;
  const vals = rows.flatMap((r) => [r.value, r.lo ?? r.value, r.hi ?? r.value, 0]);
  let [lo, hi] = domain || [Math.min(...vals), Math.max(...vals)];
  const padv = (hi - lo) * 0.08; if (!domain) { lo -= padv; hi += padv; }
  const x0 = lw + 8, x1 = W - 62;
  const sx = (v) => x0 + ((v - lo) / (hi - lo)) * (x1 - x0);
  const svg = el('svg', { viewBox: `0 0 ${W} ${H}`, width: '100%', role: 'img' });
  for (const t of niceTicks(lo, hi)) {
    el('line', { x1: sx(t), x2: sx(t), y1: 4, y2: H - 26, stroke: css('--grid'), 'stroke-width': 1 }, svg);
    el('text', { x: sx(t), y: H - 10, 'text-anchor': 'middle', class: 'tick' }, svg).textContent =
      (signed && t > 0 ? '+' : '') + fmtPlain(t, Math.abs(t) < 1 && t !== 0 ? 1 : 0) + unit;
  }
  el('line', { x1: sx(0), x2: sx(0), y1: 2, y2: H - 26, stroke: css('--axis'), 'stroke-width': 1.5 }, svg);
  rows.forEach((r, i) => {
    const y = i * rowH + 6, bh = Math.min(16, rowH - 10), cy = y + rowH / 2 - 3;
    const g = el('g', { class: 'mark' }, svg);
    el('text', { x: lw, y: cy + 4, 'text-anchor': 'end', class: 'rowlabel' }, g).textContent = r.label;
    if (r.lo !== undefined) {
      el('line', { x1: sx(r.lo), x2: sx(r.hi), y1: cy, y2: cy, stroke: css('--ink-3'), 'stroke-width': 1.5 }, g);
      el('circle', { cx: sx(r.value), cy, r: 5, fill: r.color, stroke: css('--surface'), 'stroke-width': 2 }, g);
    } else {
      const a = sx(Math.min(0, r.value)), b = sx(Math.max(0, r.value));
      el('rect', { x: a, y: cy - bh / 2, width: Math.max(1.5, b - a), height: bh, rx: 3, fill: r.color }, g);
    }
    // Interval rows always label to the right of the whisker, clear of the row labels
    const end = r.hi !== undefined ? sx(r.hi) : sx(r.value);
    const right = r.hi !== undefined || r.value >= 0;
    el('text', { x: end + (right ? 6 : -6), y: cy + 4, 'text-anchor': right ? 'start' : 'end', class: 'vallabel' }, g)
      .textContent = (signed ? fmt(r.value, decimals) : fmtPlain(r.value, decimals)) + unit;
    el('rect', { x: 0, y, width: W, height: rowH, fill: 'transparent' }, g);
    hover(g, `<b>${r.label}</b><br>${(signed ? fmt(r.value, decimals) : fmtPlain(r.value, decimals)) + unit}` +
      (r.lo !== undefined ? `<br>95% interval ${fmtPlain(r.lo, decimals)} to ${fmtPlain(r.hi, decimals)}${unit}` : '') +
      (r.note ? `<br><span class="tipnote">${r.note}</span>` : ''));
  });
  container.replaceChildren(svg);
}

// Scatter: [{x, y, color, label, tip}] with a y = x reference line
function scatter(container, pts, { xlab, ylab, domain, labels = [] }) {
  const W = Math.max(container.clientWidth, 300), H = Math.min(440, W * 0.8);
  const m = { l: 46, r: 14, t: 12, b: 42 };
  const [lo, hi] = domain;
  const sx = (v) => m.l + ((v - lo) / (hi - lo)) * (W - m.l - m.r);
  const sy = (v) => H - m.b - ((v - lo) / (hi - lo)) * (H - m.t - m.b);
  const svg = el('svg', { viewBox: `0 0 ${W} ${H}`, width: '100%', role: 'img' });
  for (const t of niceTicks(lo, hi, 5)) {
    el('line', { x1: sx(t), x2: sx(t), y1: m.t, y2: H - m.b, stroke: css('--grid') }, svg);
    el('line', { x1: m.l, x2: W - m.r, y1: sy(t), y2: sy(t), stroke: css('--grid') }, svg);
    el('text', { x: sx(t), y: H - m.b + 16, 'text-anchor': 'middle', class: 'tick' }, svg).textContent = t;
    el('text', { x: m.l - 8, y: sy(t) + 4, 'text-anchor': 'end', class: 'tick' }, svg).textContent = t;
  }
  el('line', { x1: sx(lo), y1: sy(lo), x2: sx(hi), y2: sy(hi), stroke: css('--axis'), 'stroke-width': 1.5 }, svg);
  el('text', { x: (m.l + W - m.r) / 2, y: H - 6, 'text-anchor': 'middle', class: 'axislabel' }, svg).textContent = xlab;
  const yl = el('text', { x: 14, y: (m.t + H - m.b) / 2, 'text-anchor': 'middle', class: 'axislabel',
    transform: `rotate(-90 14 ${(m.t + H - m.b) / 2})` }, svg);
  yl.textContent = ylab;
  for (const p of pts) {
    const g = el('g', { class: 'mark' }, svg);
    el('circle', { cx: sx(p.x), cy: sy(p.y), r: 11, fill: 'transparent' }, g);
    el('circle', { cx: sx(p.x), cy: sy(p.y), r: 4.5, fill: p.color, stroke: css('--surface'), 'stroke-width': 2 }, g);
    hover(g, p.tip);
    if (labels.includes(p.label)) {
      el('text', { x: sx(p.x) + 8, y: sy(p.y) + 4, class: 'pointlabel' }, svg).textContent = p.label;
    }
  }
  container.replaceChildren(svg);
}

// Waterfall from the type baseline to the actual average, one step per part
function waterfall(container, steps, { start, startLabel, endLabel }) {
  const W = Math.max(container.clientWidth, 300), rowH = 28, lw = Math.min(180, W * 0.4);
  const H = (steps.length + 2) * rowH + 34;
  let run = start; const bars = [{ label: startLabel, a: 0, b: start, total: true }];
  for (const s of steps) { bars.push({ ...s, a: run, b: run + s.value }); run += s.value; }
  bars.push({ label: endLabel, a: 0, b: run, total: true });
  const vals = bars.flatMap((b) => [b.a, b.b]);
  const lo = 0, hi = Math.max(...vals) * 1.08;
  const x0 = lw + 8, x1 = W - 56, sx = (v) => x0 + ((v - lo) / (hi - lo)) * (x1 - x0);
  const svg = el('svg', { viewBox: `0 0 ${W} ${H}`, width: '100%', role: 'img' });
  for (const t of niceTicks(lo, hi, 5)) {
    el('line', { x1: sx(t), x2: sx(t), y1: 4, y2: H - 26, stroke: css('--grid') }, svg);
    el('text', { x: sx(t), y: H - 10, 'text-anchor': 'middle', class: 'tick' }, svg).textContent = t;
  }
  bars.forEach((b, i) => {
    const y = i * rowH + 6, cy = y + rowH / 2 - 3, g = el('g', { class: 'mark' }, svg);
    const a = sx(Math.min(b.a, b.b)), w = Math.max(2, Math.abs(sx(b.b) - sx(b.a)));
    const color = b.total ? css('--ink-3') : b.value < 0 ? css('--better') : css('--worse');
    el('text', { x: lw, y: cy + 4, 'text-anchor': 'end', class: b.total ? 'rowlabel strong' : 'rowlabel' }, g).textContent = b.label;
    el('rect', { x: a, y: cy - 7, width: w, height: 14, rx: 3, fill: color }, g);
    const txt = b.total ? b.b.toFixed(1) : fmt(b.value, 1);
    el('text', { x: sx(Math.max(b.a, b.b)) + 6, y: cy + 4, class: 'vallabel' }, g).textContent = txt;
    el('rect', { x: 0, y, width: W, height: rowH, fill: 'transparent' }, g);
    hover(g, `<b>${b.label}</b><br>${b.total ? b.b.toFixed(2) + ' runs per wicket' : fmt(b.value, 2) + ' runs per wicket'}` +
      (b.ci ? `<br>95% interval ${fmtPlain(b.ci[0], 1)} to ${fmtPlain(b.ci[1], 1)}` : ''));
  });
  container.replaceChildren(svg);
}
