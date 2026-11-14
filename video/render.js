#!/usr/bin/env node
// Render a coded animation to video, frame by frame.
//
//   node video/render.js video/m1_break_the_agent.html out.mp4 [--fps 60] [--from 0] [--to 30]
//   node video/render.js video/m1_break_the_agent.html stills/ --stills 0.5,3,8,...   (PNG stills)
//
// The page must define window.DURATION (seconds) and window.render(t), a pure function of the time t
// in seconds that draws the frame. Every frame is computed, so the result is identical on every run
// and independent of the machine's speed.
const { chromium } = require('playwright');
const { spawn } = require('child_process');
const fs = require('fs');
const path = require('path');

(async () => {
  const args = process.argv.slice(2);
  const opt = (name, dflt) => { const i = args.indexOf('--' + name); return i >= 0 ? args[i + 1] : dflt; };
  const [html, out] = args;
  const fps = +opt('fps', 60);
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });
  await page.goto('file://' + path.resolve(html));
  await page.evaluate(() => document.fonts.ready);
  await page.evaluate(() => (window.ready || Promise.resolve()));
  const duration = await page.evaluate(() => window.DURATION);
  const stills = opt('stills', null);

  if (stills) {
    fs.mkdirSync(out, { recursive: true });
    for (const t of stills.split(',').map(Number)) {
      await page.evaluate((t) => window.render(t), t);
      await page.screenshot({ path: path.join(out, `t${t.toFixed(2).padStart(6, '0')}.png`) });
    }
    console.log(`${stills.split(',').length} stills in ${out}`);
    await browser.close();
    return;
  }

  const from = +opt('from', 0), to = +opt('to', duration);
  const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(fps), '-c:v', 'mjpeg',
    '-i', '-', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '17', '-preset', 'slow', '-movflags', '+faststart', out]);
  const n = Math.round((to - from) * fps), t0 = Date.now();
  for (let i = 0; i < n; i++) {
    await page.evaluate((t) => window.render(t), from + i / fps);
    const buf = await page.screenshot({ type: 'jpeg', quality: 94 });
    if (!ff.stdin.write(buf)) await new Promise((r) => ff.stdin.once('drain', r));
    if (i % (fps * 5) === 0) process.stdout.write(`\r${(i / fps).toFixed(0)} s / ${(n / fps).toFixed(0)} s`);
  }
  ff.stdin.end();
  await new Promise((r) => ff.on('close', r));
  console.log(`\r${n} frames rendered in ${((Date.now() - t0) / 1000).toFixed(0)} s -> ${out}`);
  await browser.close();
})();
