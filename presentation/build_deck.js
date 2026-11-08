// Council deck: editable titles, narrative and sources; charts as images from assets/bare.
// Usage: NODE_PATH=<dir with pptxgenjs> node presentation/build_deck.js
//   run after: make_assets.py assets/bare --bare   (writes the bare charts and slides.json with their titles)
const fs = require("fs");
const path = require("path");
const pptxgen = require("pptxgenjs");
const JSZip = require("jszip");

const ROOT = path.resolve(__dirname, "..");
const BARE = path.join(ROOT, "assets", "bare");
const META = JSON.parse(fs.readFileSync(path.join(BARE, "slides.json"), "utf8"));
const OUT = path.join(__dirname, "two-jobs-council.pptx");

const PAPER = "F2EEE4", INK = "12171D", INK2 = "47515C", MUTED = "6E7884", TEAL = "0E8083", ORANGE = "EB6834", CARD = "FFFDF8", WHITE = "FFFFFF";
const FONT = "Barlow Condensed";
const SOURCE = "Source: Calgary Transit GTFS, fall schedules, weekday service. Analysis: Willem Klumpenhouwer. Supply, not ridership.";
const W = 10, M = 0.5, CW = W - 2 * M;
const AREA = { y: 1.6, h: 3.35 };  // chart area between the subtitle and the source line

const pres = new pptxgen();
pres.layout = "LAYOUT_16x9";
pres.author = "Willem Klumpenhouwer";
pres.title = "Transit does two jobs";
pres.theme = { headFontFace: FONT, bodyFontFace: FONT };

const ph = (name, type, x, y, w, h, o) => ({ placeholder: { options: { name, type, x, y, w, h, margin: 0, fontFace: FONT, ...o }, text: "" } });
// pptxgenjs mutates option objects, so every layout gets fresh placeholder objects
const TITLE = () => ph("title", "title", M, 0.35, CW, 0.6, { fontSize: 32, bold: true, color: INK, valign: "top" });
const SRC = () => ph("source", "body", M, 5.12, CW, 0.3, { fontSize: 10, color: MUTED, valign: "top" });
pres.defineSlideMaster({ title: "CHART", background: { color: PAPER },
  objects: [TITLE(), ph("subtitle", "body", M, 0.98, CW, 0.55, { fontSize: 15, color: INK2, valign: "top" }), SRC()] });
pres.defineSlideMaster({ title: "TEXT", background: { color: PAPER }, objects: [TITLE(), SRC()] });
pres.defineSlideMaster({ title: "BLANK", background: { color: PAPER }, objects: [] });

function pngSize(file) {
  const b = fs.readFileSync(file);
  return [b.readUInt32BE(16), b.readUInt32BE(20)];
}

const text = (s, t, o) => s.addText(t, { isTextBox: true, margin: 0, fontFace: FONT, color: INK, valign: "top", ...o });

// Chart slide: title, subtitle and source from slides.json; the chart fits the area, centred. Returns the image box.
function chart(section, name, notes) {
  const m = META[name];
  const s = pres.addSlide({ masterName: "CHART", sectionTitle: section });
  s.addText(m.title, { placeholder: "title" });
  s.addText(m.subtitle, { placeholder: "subtitle" });
  if (m.source) s.addText(m.source, { placeholder: "source" });
  const file = path.join(BARE, `${name}.png`);
  const [pw, phh] = pngSize(file);
  const w = Math.min(CW, AREA.h * pw / phh), h = w * phh / pw;
  const box = { x: (W - w) / 2, y: AREA.y + (AREA.h - h) / 2, w, h };
  s.addImage({ path: file, ...box, altText: m.title });
  s.addNotes(notes);
  return { s, box };
}

function textSlide(section, title, source, notes) {
  const s = pres.addSlide({ masterName: "TEXT", sectionTitle: section });
  s.addText(title, { placeholder: "title" });
  if (source) s.addText(source, { placeholder: "source" });
  s.addNotes(notes);
  return s;
}

function arrow(s, x1, y1, x2, y2, color) {
  s.addShape(pres.shapes.LINE, { x: x1, y: Math.min(y1, y2), w: x2 - x1, h: Math.abs(y2 - y1), flipV: y2 < y1,
    line: { color, width: 2.5, endArrowType: "triangle" } });
}

// ---------- talk ----------
pres.addSection({ title: "Talk" });

chart("Talk", "s1_cold_open_bar",
  "[0:00–0:30] Transit does two jobs. Frequency: buses often enough that you just show up. Coverage: some service close to everyone. Every hour in the transit budget goes to one or the other.");

{
  const { s, box } = chart("Talk", "s2_ten_vs_thirty_minutes",
    "[0:30–1:00] Same three hours at one stop. Every 10 minutes is 18 buses: you just show up. Every half hour is 6 buses: you check the schedule and plan your day around it. (Arithmetic, not a real stop.)");
  // dot rows sit at 27% and 68% of the bare chart's height; the first departure at 24.5% of its width
  const x = box.x + 0.245 * box.w;
  text(s, "18 buses. Just show up.", { x, y: box.y + 0.27 * box.h - 0.5, w: 4, h: 0.32, fontSize: 18, bold: true, color: TEAL });
  text(s, "6 buses. Check the schedule.", { x, y: box.y + 0.68 * box.h - 0.5, w: 4, h: 0.32, fontSize: 18, bold: true, color: ORANGE });
}

{
  const s = textSlide("Talk", "Council already chose frequency",
    "RouteAhead, Calgary Transit’s 30-Year Strategic Plan. Approved by Council July 2023. Pages 5 and 40.",
    "[1:00–1:30] Council has already chosen. RouteAhead, approved in July 2023, says Calgary will shift towards frequency to build ridership, and defines the Primary Transit Network as every 10 minutes or better, 15 hours a day, seven days a week. It also says today's network leans toward coverage (p. 40).");
  text(s, "“By implementing RouteAhead, Calgary will shift more towards frequency to build ridership…”",
    { x: M, y: 1.45, w: CW, h: 1.9, fontSize: 34, bold: true, color: TEAL, lineSpacingMultiple: 0.95 });
  text(s, "The Primary Transit Network: “service running every 10 minutes or better, at least 15 hours a day, seven days a week.”",
    { x: M, y: 3.6, w: 8.2, h: 0.9, fontSize: 20 });
}

chart("Talk", "s4_split_ctrain_10min",
  "[1:30–1:55] Where are we today? Of every weekly service hour in the fall 2026 schedule, 18% runs every 10 minutes or better. 82% runs less often.");
chart("Talk", "06_map_2026_noon",
  "[1:55–2:15] On a weekday at noon, almost all of the teal is CTrain. Everything in orange is coverage.");
chart("Talk", "02_split_by_year",
  "[2:15–2:40] The balance has drifted. 25% in 2016, 15% in 2019, 18% today. Most of the loss came between 2016 and 2019, before the pandemic. RouteAhead itself notes that cuts after the economic downturn reversed earlier progress.");
chart("Talk", "s5_covered_vs_frequent_area",
  "[2:40–3:00] Meanwhile the area with any service grew 10%, and the area with 10-minute service shrank 3%. Service has spread further and thinner.");

{
  const s = textSlide("Talk", "Land use sets the split", SOURCE,
    "[3:00–3:35] Nobody decided this. New communities, rezoning, corridor growth and budget decisions each move the balance, and none of them reports its effect on it.");
  text(s, "Decisions made one at a time add up to the balance between the two jobs", { x: M, y: 0.98, w: CW, h: 0.4, fontSize: 15, color: INK2 });
  const ins = [["New communities on the edge", ORANGE], ["Rezoning, and rezoning that doesn’t happen", ORANGE], ["Dense growth along corridors", TEAL], ["Transit budget decisions", INK]];
  const LX = M, LW = 3.6, LH = 0.55, RX = 6.3, RW = 3.2, RH = 1.0, COV = 1.85, FRQ = 3.45;
  ins.forEach(([t, c], i) => text(s, t, { x: LX, y: 1.65 + i * 0.8, w: LW, h: LH, fontSize: 16, bold: true, align: "center", valign: "middle",
    fill: { color: CARD }, line: { color: c, width: 2 } }));
  for (const [y, t, c] of [[COV, "Coverage line", ORANGE], [FRQ, "Frequency line", TEAL]]) {
    s.addText([{ text: t, options: { fontSize: 26, bold: true, breakLine: true } }, { text: "not visible in the budget today", options: { fontSize: 14 } }],
      { isTextBox: true, x: RX, y, w: RW, h: RH, margin: 0, fontFace: FONT, color: WHITE, align: "center", valign: "middle", fill: { color: c } });
  }
  const mid = (i) => 1.65 + i * 0.8 + LH / 2, x1 = LX + LW, x2 = RX;
  arrow(s, x1, mid(0), x2, COV + 0.35, ORANGE);
  arrow(s, x1, mid(1), x2, COV + 0.6, ORANGE);
  arrow(s, x1, mid(2), x2, FRQ + 0.4, TEAL);
  arrow(s, x1, mid(3), x2, COV + 0.85, INK);
  arrow(s, x1, mid(3), x2, FRQ + 0.75, INK);
}

{
  const s = textSlide("Talk", "Three requests for Council", "",
    "[3:35–4:30] Three requests. One: budget the two services separately, and set the balance on purpose. Two: show the impact on both before major land use and service decisions are made. Three: ask Calgarians to help decide. This is a question about balance, not a call to cut coverage.");
  const asks = [
    ["Budget the two services separately.", "In the 2027–2030 budget, show a coverage line and a frequency line, and have Council set the balance between them on purpose.", ORANGE],
    ["Show the impact to both services.", "New community decisions, other major land use changes, and major service adjustments and network reconfiguration should report their effect on the coverage and frequency lines before a decision is made.", TEAL],
    ["Ask Calgarians to help decide the balance.", "Put the trade-off to the public directly.", INK],
  ];
  asks.forEach(([head, body, c], i) => {
    const y = 1.25 + i * 1.18;
    text(s, String(i + 1), { x: M, y, w: 0.45, h: 0.6, fontSize: 30, bold: true, color: c });
    text(s, head, { x: 1.05, y, w: 8.45, h: 0.45, fontSize: 24, bold: true });
    text(s, body, { x: 1.05, y: y + 0.47, w: 8.0, h: 0.6, fontSize: 15, color: INK2 });
  });
  text(s, "This is a question about balance, not a call to cut coverage.", { x: M, y: 4.85, w: CW, h: 0.4, fontSize: 18 });
}

{
  const s = pres.addSlide({ masterName: "BLANK", sectionTitle: "Talk" });
  s.addShape(pres.shapes.RECTANGLE, { x: M, y: 1.55, w: 0.7, h: 0.09, fill: { color: ORANGE }, line: { type: "none" } });
  s.addShape(pres.shapes.RECTANGLE, { x: M + 0.7, y: 1.55, w: 0.7, h: 0.09, fill: { color: TEAL }, line: { type: "none" } });
  text(s, "Which balance do Calgarians want?", { x: M, y: 2.0, w: 7.5, h: 2.2, fontSize: 60, bold: true, lineSpacingMultiple: 0.95 });
  s.addNotes("[4:30–5:00] So the question for this budget is: which balance do Calgarians want? Thank you. I'm happy to take questions.");
}

// ---------- backup ----------
pres.addSection({ title: "Backup" });
chart("Backup", "05_threshold_sensitivity", "If asked why 10 minutes: this is the share at every threshold from 10 to 30 minutes. 2026 is below 2016 wherever you draw the line.");
chart("Backup", "s4_split_ctrain_15min", "At 15 minutes, 30% of weekly hours count as frequency (27% to 32% with CTrain at 2× to 3×).");
chart("Backup", "09_map_2026_noon_15min", "The noon network at the 15-minute line.");
chart("Backup", "04_time_of_day_2026", "Service by hour of the weekday, frequency against coverage.");
chart("Backup", "07_map_years_noon", "The noon network in 2016, 2019 and 2026.");
chart("Backup", "08_map_2026_noon_vs_9pm", "The same network at noon and at 9 pm.");

{
  const s = textSlide("Backup", "Method", "",
    "Method. Schedules, not observed service. CTrain weighting holds between 2× and 3×. Supply, not ridership: the City does not publish ridership by route.");
  const rows = [
    ["Source", "Calgary Transit GTFS schedules, fall 2016, 2019 and 2026. Scheduled service, not observed."],
    ["Week", "One reference Tue, Fri, Sat and Sun per year. Week = 4 × Mon–Thu + Fri + Sat + Sun."],
    ["Hours", "First to last stop of each trip, apportioned to clock hours. 10% deadhead on all service."],
    ["Frequency", "A route-hour counts if it averages 6+ trips per hour per direction (3-hour smoothing)."],
    ["CTrain", "Counted at 2.5× bus hours. The result holds between 2× and 3×."],
    ["Excluded", "School specials (routes 600–899). This measures supply, not ridership."],
  ];
  rows.forEach(([k, v], i) => {
    const y = 1.3 + i * 0.6;
    text(s, k, { x: M, y, w: 1.5, h: 0.4, fontSize: 20, bold: true, color: TEAL });
    text(s, v, { x: 2.1, y: y + 0.03, w: 7.4, h: 0.4, fontSize: 16 });
  });
}

{
  const s = textSlide("Backup", "Either direction is a choice", "",
    "Either direction is legitimate. Leaning coverage, ridership will likely shrink. Leaning frequency, ridership will likely grow, with a plan for edge areas.");
  const cards = [[M, ORANGE, "Lean toward coverage", "Service near more people, less often.\nRidership will likely shrink."],
                 [5.15, TEAL, "Lean toward frequency", "Service more often on fewer corridors.\nRidership will likely grow, with a plan for edge areas."]];
  for (const [x, c, head, body] of cards) {
    s.addShape(pres.shapes.RECTANGLE, { x, y: 1.3, w: 4.35, h: 3.3, fill: { color: c }, line: { type: "none" } });
    text(s, head, { x: x + 0.3, y: 1.55, w: 3.75, h: 0.5, fontSize: 26, bold: true, color: WHITE });
    text(s, body, { x: x + 0.3, y: 2.25, w: 3.75, h: 2.1, fontSize: 20, color: WHITE, paraSpaceAfter: 8 });
  }
  text(s, "The point is to choose it on purpose, in the open.", { x: M, y: 4.85, w: CW, h: 0.4, fontSize: 18 });
}

// Folder entries in the zip break Drive import and co-editing. JSZip's remove() on a folder also removes
// its contents, so copy the file entries into a fresh zip instead.
pres.write({ outputType: "nodebuffer" })
  .then((buf) => JSZip.loadAsync(buf))
  .then(async (z) => {
    const out = new JSZip();
    for (const f of Object.values(z.files).filter((f) => !f.dir)) out.file(f.name, await f.async("nodebuffer"), { createFolders: false });
    return out.generateAsync({ type: "nodebuffer", compression: "DEFLATE" });
  })
  .then((buf) => { fs.writeFileSync(OUT, buf); console.log("wrote", OUT); });
