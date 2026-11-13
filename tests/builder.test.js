// Run: node tests/builder.test.js <path-to-second-movement>
// Loads index.html in Chromium and checks config generation, import and the MODE simulator.
const { chromium } = require("playwright");
const fs = require("fs"), path = require("path"), assert = require("assert");
const { execFileSync } = require("child_process");

const UP = process.argv[2];
if (!UP) { console.error("usage: node tests/builder.test.js <second-movement>"); process.exit(2); }
const upstreamCfg = fs.readFileSync(path.join(UP, "movement_config.h"), "utf8");

const defines = t => Object.fromEntries([...t.matchAll(/^#define\s+(MOVEMENT_\w+|SIGNAL_TUNE_\w+)\s*(.*)$/gm)].map(m => [m[1], m[2].trim()]));
const faces = t => t.match(/watch_faces\[\]\s*=\s*\{([\s\S]*?)\};/)[1].replace(/\/\/.*$/gm, "").split(",").map(s => s.trim()).filter(Boolean);
const secIdx = (t, n) => Function(`return ${defines(t).MOVEMENT_SECONDARY_FACE_INDEX.replace(/MOVEMENT_NUM_FACES/g, n)}`)();

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage();
  const errors = []; page.on("pageerror", e => errors.push(e.message));
  await page.goto("file://" + path.resolve(__dirname, "../index.html"));
  let pass = 0; const ok = (c, m) => { assert(c, m); pass++; };

  // 1. upstream default preset reproduces upstream movement_config.h semantically
  const gen = await page.evaluate(() => { localStorage.clear(); SWPB.presetDefault(); SWPB.render(); return SWPB.buildConfig(); });
  ok(JSON.stringify(faces(gen)) === JSON.stringify(faces(upstreamCfg)), "face list matches upstream");
  ok(secIdx(gen, faces(gen).length) === secIdx(upstreamCfg, faces(upstreamCfg).length), "secondary index matches upstream");
  const du = defines(upstreamCfg), dg = defines(gen);
  for (const k of Object.keys(du)) if (k !== "MOVEMENT_SECONDARY_FACE_INDEX") ok(du[k] === dg[k], `${k}: upstream ${du[k]} vs generated ${dg[k]}`);
  ok(Object.keys(dg).length === Object.keys(du).length, "same set of defines");

  // 2. config_meta.py accepts the generated config
  const tmp = fs.mkdtempSync(path.join(require("os").tmpdir(), "swpb-")), f = path.join(tmp, "t.h");
  fs.writeFileSync(f, gen);
  const chk = execFileSync("python3", ["-I", path.resolve(__dirname, "../tools/config_meta.py"), "check", f, UP]).toString();
  ok(chk.includes(`${faces(gen).length} faces OK`), "config_meta sees all faces: " + chk.trim());
  const meta = JSON.parse(execFileSync("python3", ["-I", path.resolve(__dirname, "../tools/config_meta.py"), "matrix", f]).toString()).include[0];
  ok(meta.board === "sensorwatch_pro" && meta.display === "classic" && /^[0-9a-f]{40}$/.test(meta.upstream), "metadata parsed");
  pass++;

  // 3. import round-trip of a custom config
  const rt = await page.evaluate(() => {
    const s = SWPB.state;
    s.main = []; s.sec = [];
    SWPB.parseConfig(`const watch_faces[] = { clock_face, totp_face, world_clock_face, world_clock_face, settings_face, set_time_face };
      #define MOVEMENT_SECONDARY_FACE_INDEX (MOVEMENT_NUM_FACES - 2)
      #define SIGNAL_TUNE_MARIO_THEME
      #define MOVEMENT_DEFAULT_RED_COLOR 0xA
      #define MOVEMENT_DEFAULT_24H_MODE true
      #define MOVEMENT_DEFAULT_LOW_ENERGY_INTERVAL 6
      * builder:display=custom`);
    const a = SWPB.buildConfig(); SWPB.parseConfig(a); const b = SWPB.buildConfig();
    return { a, b, main: s.main.map(x => x.id), sec: s.sec.map(x => x.id), s: { ...s.s } };
  });
  ok(rt.a === rt.b, "generate -> import -> generate is stable");
  ok(rt.main.join() === "clock_face,totp_face,world_clock_face,world_clock_face" && rt.sec.join() === "settings_face,set_time_face", "lists imported");
  ok(rt.s.tune === "SIGNAL_TUNE_MARIO_THEME" && rt.s.r === 10 && rt.s.h24 === true && rt.s.le === 6 && rt.s.display === "custom", "settings imported");

  // 4. no long-press faces -> index 0
  const zero = await page.evaluate(() => { SWPB.state.sec = []; return SWPB.buildConfig(); });
  ok(/MOVEMENT_SECONDARY_FACE_INDEX 0\b/.test(zero), "index 0 without long-press faces");

  // 5. simulator follows movement.c: MODE wraps in group; long press home<->secondary; end of secondary -> home
  const seq = await page.evaluate(() => {
    SWPB.presetDefault(); SWPB.render(); const out = [];
    const at = () => { const s = SWPB.sim(); return s.list + s.i; };
    for (let i = 0; i < 6; i++) { SWPB.modePress(); out.push(at()); }   // 6 rotation faces -> wraps to main0
    SWPB.modeLong(); out.push(at());                                     // sec0
    for (let i = 0; i < 5; i++) { SWPB.modePress(); out.push(at()); }    // sec1..4 then main0
    SWPB.modePress(); SWPB.modeLong(); out.push(at());                   // long press away from home -> home
    return out.join(" ");
  });
  ok(seq === "main1 main2 main3 main4 main5 main0 sec0 sec1 sec2 sec3 sec4 main0 main0", "simulator sequence: " + seq);

  // 6. UI: add a face via the catalog button
  await page.evaluate(() => { SWPB.presetDefault(); SWPB.render(); });
  await page.fill("#q", "tarot");
  await page.click('[data-add="main"][data-face="tarot_face"]');
  ok((await page.textContent("#out")).includes("tarot_face,"), "catalog add updates config");
  ok((await page.getAttribute("#gh-commit", "href")).startsWith("https://github.com/4fxtwin/SensorWatchPro/new/main?filename=configs%2Fmy-watch.h&value="), "commit link");

  ok(errors.length === 0, "no page errors: " + errors.join("; "));
  await browser.close();
  console.log(`${pass} checks passed`);
})().catch(e => { console.error("FAIL:", e.message); process.exit(1); });
