#!/usr/bin/env node
// Film the real results site, scene by scene, with a scripted virtual camera.
//
//   node video/screen.js s5 [--fps 30] [--from 0] [--to 60]        -> video/out/s5_*.mp4 (1920x1080, 60 fps)
//   node video/screen.js s5 --stills 2,10,30                         -> PNG stills in video/out/stills_s5/
//
// The page is the real report (results/report.html) with one hook added so the director can read its state.
// Everything that moves on screen (camera, cursor, highlights, cards) is a function of the scene time; the
// stateful steps (choosing an agent, an episode, a hotspot, opening the briefing) run once at their time, as
// a viewer would click them. Frames are captured at 2x and scaled down, so text stays sharp when zoomed.
const { chromium } = require('playwright');
const { spawn } = require('child_process');
const fs = require('fs');
const path = require('path');
const SCENES = require('./screen_scenes.js');

const ROOT = path.resolve(__dirname, '..');
const OUT = path.join(ROOT, 'video', 'out');

function sitePage() {
  // the real report, plus a hook exposing its state and drawing functions to the director
  const src = fs.readFileSync(path.join(ROOT, 'results', 'report.html'), 'utf8');
  const anchor = 'selEp.addEventListener("change", () => selectEpisode(Number(selEp.value)));';
  if (!src.includes(anchor)) throw new Error('report.html changed: hook anchor not found');
  const html = src.replace(anchor, anchor + '\n  window.__cv = { state, draw, selectAgent, selectEpisode, renderFocusButtons, renderTargets, setPresent: (on) => setPresent(on) };');
  fs.mkdirSync(OUT, { recursive: true });
  const file = path.join(OUT, 'site.html');
  fs.writeFileSync(file, html);
  return 'file://' + file;
}

// ------------------------------------------------------------------ page-side runtime
function runtime() {
  const W = 1920, H = 1080, AR = H / W;
  const ease = (k) => (k <= 0 ? 0 : k >= 1 ? 1 : k * k * k * (k * (k * 6 - 15) + 10));
  const lerp = (a, b, k) => a + (b - a) * k;
  const wrap = document.querySelector('.wrap');
  document.documentElement.style.overflow = 'hidden'; document.body.style.overflow = 'hidden'; window.scrollTo(0, 0);
  let cam = { x: 0, y: 0, w: W };
  const layer = document.createElement('div');
  layer.style.cssText = 'position:fixed;inset:0;pointer-events:none;z-index:9999';
  document.body.appendChild(layer);
  const fadeImg = document.createElement('img');
  fadeImg.style.cssText = 'position:fixed;inset:0;width:100vw;height:100vh;opacity:0;z-index:9998;pointer-events:none';
  document.body.appendChild(fadeImg);
  const cursor = document.createElement('div');
  cursor.innerHTML = '<svg width="30" height="30" viewBox="0 0 24 24"><path d="M4 2 L4 19 L8.6 14.8 L11.6 21.6 L14.6 20.3 L11.7 13.6 L18 13.6 Z" fill="#fff" stroke="#111" stroke-width="1.4" stroke-linejoin="round"/></svg>';
  cursor.style.cssText = 'position:fixed;left:0;top:0;opacity:0;z-index:10001;pointer-events:none;filter:drop-shadow(0 2px 4px rgba(0,0,0,.5))';
  document.body.appendChild(cursor);
  const ripple = document.createElement('div');
  ripple.style.cssText = 'position:fixed;width:40px;height:40px;border-radius:50%;border:2px solid var(--s1);opacity:0;z-index:10000;pointer-events:none';
  document.body.appendChild(ripple);
  const pool = {};
  const box = (key, css) => { if (!pool[key]) { const d = document.createElement('div'); d.style.cssText = 'position:fixed;pointer-events:none;' + css; layer.appendChild(d); pool[key] = d; } return pool[key]; };

  function setCam(c) {
    const z = W / c.w;
    wrap.style.transformOrigin = `${-wrap.offsetLeft}px ${-wrap.offsetTop}px`;
    wrap.style.transform = `translate(${-c.x * z}px, ${-c.y * z}px) scale(${z})`;
    cam = c;
  }
  const z = () => W / cam.w;
  function elsOf(s) {
    if (s.lines) {                       // briefing lines, from the line starting with lines[0] up to (not including) lines[1]
      const all = [...document.querySelectorAll('#brief .bl')];
      const i0 = all.findIndex((e) => e.textContent.trim().startsWith(s.lines[0]));
      let i1 = s.lines[1] ? all.findIndex((e, i) => i > i0 && e.textContent.trim().startsWith(s.lines[1])) : i0 + 1;
      if (i1 < 0) i1 = all.length;
      return all.slice(i0, i1);
    }
    const sels = Array.isArray(s.sel) ? s.sel : [s.sel];
    return sels.map((q) => (typeof q === 'number' ? null : document.querySelector(q))).filter(Boolean);
  }
  // union of elements' boxes, in page coordinates (independent of the camera)
  function pageRect(s) {
    const els = elsOf(s);
    if (!els.length) return null;
    let x0 = 1e9, y0 = 1e9, x1 = -1e9, y1 = -1e9;
    els.forEach((e) => { const r = e.getBoundingClientRect(); if (!r.width && !r.height) return; x0 = Math.min(x0, r.left); y0 = Math.min(y0, r.top); x1 = Math.max(x1, r.right); y1 = Math.max(y1, r.bottom); });
    if (x0 > x1) return null;
    return { x: x0 / z() + cam.x, y: y0 / z() + cam.y, w: (x1 - x0) / z(), h: (y1 - y0) / z() };
  }
  function screenRect(s) { const r = pageRect(s); if (!r) return null; return { x: (r.x - cam.x) * z(), y: (r.y - cam.y) * z(), w: r.w * z(), h: r.h * z() }; }
  function docH() { return wrap.offsetTop + wrap.offsetHeight + 40; }
  function resolve(s) {
    let cx, cy, w;
    if (s.full) { w = W; cx = W / 2; cy = (s.y || 0) + H / 2; }
    else {
      const r = pageRect(s);
      if (!r) return null;
      const pad = s.pad == null ? 40 : s.pad;
      if (s.at) { w = s.w; cx = r.x + r.w * s.at[0]; cy = r.y + r.h * s.at[1]; }
      else {
        w = s.w || Math.max(r.w + 2 * pad, (r.h + 2 * pad) / AR);
        w = Math.max(640, Math.min(W, w));
        cx = r.x + r.w / 2;
        cy = s.align === 'top' ? r.y - pad + w * AR / 2 : r.y + r.h / 2;
      }
      if (s.dx) cx += s.dx; if (s.dy) cy += s.dy;
    }
    const h = w * AR;
    cx = Math.max(w / 2, Math.min(W - w / 2, cx));
    cy = Math.max(h / 2, Math.min(Math.max(h / 2, docH() - h / 2), cy));
    return { cx, cy, w };
  }
  let fade = null, scrolls = {};
  function cursorPos(S, t) {
    const ks = (S.cursor || []).filter((k) => k.t <= t);
    if (!ks.length) return null;
    const pt = (k) => { if (k.hide) return null; const r = screenRect(k); return r ? [r.x + r.w * (k.at ? k.at[0] : 0.5), r.y + r.h * (k.at ? k.at[1] : 0.5)] : null; };
    const cur = ks[ks.length - 1];
    if (cur.hide) return { hide: true, at: cur.t, p: pt(ks[ks.length - 2] || cur) };
    const p1 = pt(cur), prev = ks.length > 1 && !ks[ks.length - 2].hide ? pt(ks[ks.length - 2]) : null;
    const k = ease((t - cur.t) / (cur.dur || 0.8));
    if (!p1) return null;
    const p = prev ? [lerp(prev[0], p1[0], k), lerp(prev[1], p1[1], k)] : [p1[0] + 160 * (1 - k), p1[1] + 120 * (1 - k)];
    return { p, appear: prev ? 1 : ease((t - cur.t) / 0.4) };
  }

  return {
    setCam, pageRect, screenRect, resolve,
    fadeFrom(url, t0, dur) { fadeImg.src = url; fade = { t0, dur }; },
    frame(S, t) {
      // continuous changes of the site's own state (the 3D view)
      let redraw = false;
      (S.tweens || []).forEach((tw) => {
        if (t < tw.t0) return;
        const k = ease((t - tw.t0) / (tw.t1 - tw.t0));
        window.__cv.state[tw.key] = lerp(tw.from, tw.to, k); redraw = true;
      });
      if (redraw) window.__cv.draw();
      // scrolling inside a scrollable box (the transcript)
      (S.scrolls || []).forEach((sc, i) => {
        if (t < sc.t0) return;
        const el = document.querySelector(sc.sel); if (!el) return;
        const st = scrolls[i] || (scrolls[i] = { from: el.scrollTop });
        let to = sc.top || 0;
        if (sc.to) { const tgt = document.querySelector(sc.to); if (tgt) to = tgt.offsetTop - el.offsetTop - (sc.offset || 0); }
        el.scrollTop = lerp(st.from, to, ease((t - sc.t0) / (sc.t1 - sc.t0)));
      });
      // camera
      const moves = S.cam.filter((m) => m.t0 <= t);
      const cur = moves[moves.length - 1] || S.cam[0];
      const idx = S.cam.indexOf(cur), prev = S.cam[idx - 1];
      let c = resolve(cur);
      if (prev && t < cur.t1) { const p = resolve(prev); const k = ease((t - cur.t0) / (cur.t1 - cur.t0)); if (p && c) c = { cx: lerp(p.cx, c.cx, k), cy: lerp(p.cy, c.cy, k), w: Math.exp(lerp(Math.log(p.w), Math.log(c.w), k)) }; }
      if (c && cur.drift && t > cur.t1) {           // a slow push-in while holding
        const next = S.cam[idx + 1], end = next ? next.t0 : S.duration;
        c.w *= 1 - cur.drift * ease((t - cur.t1) / Math.max(0.1, end - cur.t1));
      }
      if (c) setCam({ x: c.cx - c.w / 2, y: c.cy - c.w * AR / 2, w: c.w });
      // highlights that follow the camera
      (S.marks || []).forEach((m, i) => {
        const d = box('m' + i, 'border-radius:10px;border:2px solid var(--s1);background:color-mix(in srgb, var(--s1) 12%, transparent);box-shadow:0 0 0 6px color-mix(in srgb, var(--s1) 18%, transparent)');
        const a = Math.min(ease((t - m.t0) / 0.5), 1 - ease((t - m.t1) / 0.5));
        const r = a > 0 ? screenRect(m) : null;
        if (!r || a <= 0) { d.style.opacity = 0; return; }
        const pad = (m.pad == null ? 8 : m.pad) * z();
        Object.assign(d.style, { left: r.x - pad + 'px', top: r.y - pad + 'px', width: r.w + 2 * pad + 'px', height: r.h + 2 * pad + 'px', opacity: a });
      });
      // overlay cards, in screen space
      (S.cards || []).forEach((cd, i) => {
        const d = box('c' + i, 'background:var(--surface);color:var(--ink);border:1px solid var(--axis);border-radius:18px;padding:28px 32px;box-shadow:0 24px 60px rgba(0,0,0,.45);font-size:22px;line-height:1.45');
        if (!d.dataset.ok) { d.innerHTML = cd.html; d.dataset.ok = 1; }
        const a = Math.min(ease((t - cd.t0) / 0.6), 1 - ease((t - cd.t1) / 0.6));
        Object.assign(d.style, { left: cd.x + 'px', top: cd.y + 'px', width: cd.w + 'px', opacity: Math.max(0, a), transform: `translateY(${(1 - Math.max(0, a)) * 24}px)` });
      });
      // cursor and click ripple
      const cp = cursorPos(S, t);
      if (cp && cp.p) {
        const a = cp.hide ? 1 - ease((t - cp.at) / 0.4) : cp.appear;
        Object.assign(cursor.style, { left: cp.p[0] - 6 + 'px', top: cp.p[1] - 4 + 'px', opacity: Math.max(0, a) });
        const ck = (S.clicks || []).filter((c2) => c2 <= t).pop();
        const age = ck == null ? 9 : t - ck;
        Object.assign(ripple.style, { left: cp.p[0] - 20 + 'px', top: cp.p[1] - 20 + 'px', opacity: age < 0.5 ? 1 - age / 0.5 : 0, transform: `scale(${0.4 + age * 2.4})` });
      } else { cursor.style.opacity = 0; ripple.style.opacity = 0; }
      // cross-fade from a snapshot after a layout change
      fadeImg.style.opacity = fade ? Math.max(0, 1 - ease((t - fade.t0) / fade.dur)) : 0;
    },
  };
}

// ------------------------------------------------------------------ director
(async () => {
  const args = process.argv.slice(2);
  const opt = (n, d) => { const i = args.indexOf('--' + n); return i >= 0 ? args[i + 1] : d; };
  const name = args[0];
  const scene = SCENES[name];
  if (!scene) { console.error('scenes: ' + Object.keys(SCENES).join(', ')); process.exit(1); }
  const fps = +opt('fps', 30);
  const stills = opt('stills', null);
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 2, colorScheme: 'dark', reducedMotion: 'reduce' });
  const url = sitePage();

  const P = {
    page,
    async open(u) {
      await page.goto(u || url);
      await page.evaluate(() => document.fonts.ready);
      await page.evaluate(`window.__dir = (${runtime.toString()})()`);
    },
    ev: (fn, arg) => page.evaluate(fn, arg),
    present: (on) => page.evaluate((v) => window.__cv.setPresent(v), on),
    async episode(agentPrefix, seed, run) {
      return page.evaluate(([a, s, r]) => {
        const ag = DATA.agents.concat(DATA.legacy || []).find((x) => x.id.startsWith(a));
        const i = ag.episodes.find((k) => DATA.episodes[k].seed === s && (r == null || DATA.episodes[k].run === r));
        window.__cv.selectAgent(ag.id); window.__cv.selectEpisode(i);
        return i;
      }, [agentPrefix, seed, run]);
    },
    clickText: (sel, text) => page.evaluate(([s, tx]) => { const b = [...document.querySelectorAll(s)].find((e) => e.textContent.trim() === tx); if (b) b.click(); return !!b; }, [sel, text]),
  };
  await P.open(scene.url ? 'file://' + path.join(ROOT, scene.url) : undefined);
  if (scene.init) await scene.init(P);
  const S = { duration: scene.duration, cam: scene.cam, marks: scene.marks, cards: scene.cards, cursor: scene.cursor, clicks: scene.clicks, tweens: scene.tweens, scrolls: scene.scrolls };
  const events = (scene.events || []).slice().sort((a, b) => a.t - b.t);
  let ei = 0;
  const step = async (t) => {
    while (ei < events.length && events[ei].t <= t) {
      const e = events[ei++];
      if (e.fade) {
        // the snapshot to fade from is the previous frame, before the new camera framing applies
        await page.evaluate(([S2, tt]) => window.__dir.frame(S2, tt), [S, Math.max(0, t - 1 / fps)]);
        const shot = await page.screenshot({ type: 'jpeg', quality: 92 });
        await e.act(P);
        if (e.url) { await P.open('file://' + path.join(ROOT, e.url)); if (e.init) await e.init(P); }
        await page.evaluate(([u, t0, d]) => window.__dir.fadeFrom(u, t0, d), ['data:image/jpeg;base64,' + shot.toString('base64'), t, e.fade]);
      } else await e.act(P);
    }
    await page.evaluate(([S2, tt]) => window.__dir.frame(S2, tt), [S, t]);
  };

  if (stills) {
    const dir = path.join(OUT, 'stills_' + name); fs.mkdirSync(dir, { recursive: true });
    for (const t of stills.split(',').map(Number).sort((a, b) => a - b)) {
      while (ei < events.length && events[ei].t < t) await step(events[ei].t);   // layout changes at their own time
      await step(t);
      await page.screenshot({ path: path.join(dir, `t${t.toFixed(1).padStart(5, '0')}.png`), scale: 'css' });
    }
    console.log('stills in ' + dir); await browser.close(); return;
  }
  const from = +opt('from', 0), to = +opt('to', scene.duration);
  const out = path.join(OUT, scene.file);
  const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(fps), '-c:v', 'mjpeg', '-i', '-',
    '-vf', 'scale=1920:1080:flags=lanczos', '-r', '60', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '17', '-preset', 'medium', '-movflags', '+faststart', out]);
  const n = Math.round((to - from) * fps), t0 = Date.now();
  for (let i = 0; i < n; i++) {
    const t = from + i / fps;
    await step(t);
    const buf = await page.screenshot({ type: 'jpeg', quality: 92 });
    if (!ff.stdin.write(buf)) await new Promise((r) => ff.stdin.once('drain', r));
    if (i % (fps * 10) === 0) console.log(`${name}: ${t.toFixed(0)} s / ${to} s`);
  }
  ff.stdin.end();
  await new Promise((r) => ff.on('close', r));
  console.log(`${name}: ${n} frames in ${((Date.now() - t0) / 1000).toFixed(0)} s -> ${out}`);
  await browser.close();
})();
