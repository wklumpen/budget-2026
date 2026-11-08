// Council deck: one full-bleed asset per slide, speaker notes with timings.
// Usage: NODE_PATH=<dir with pptxgenjs> node presentation/build_deck.js   (run from the repo root after make_assets.py)
const fs = require("fs");
const path = require("path");
const pptxgen = require("pptxgenjs");

const ROOT = path.resolve(__dirname, "..");
const ASSETS = path.join(ROOT, "assets");
const OUT = path.join(__dirname, "two-jobs-council.pptx");
const W = 10, H = 5.625, PAD = 0.25;

const TALK = [
  ["s1_cold_open_bar", "[0:00–0:30] Transit does two jobs. Frequency: buses often enough that you just show up. Coverage: some service close to everyone. Every hour in the transit budget goes to one or the other."],
  ["s2_ten_vs_sixty_minutes", "[0:30–1:00] Same three hours at one stop. Every 10 minutes is 18 buses: you just show up. Every hour is 3 buses: you check the schedule and plan your day around it. (Arithmetic, not a real stop.)"],
  ["s3_routeahead_quote", "[1:00–1:30] Council has already chosen. RouteAhead, approved in July 2023, says Calgary will shift towards frequency to build ridership, and defines the Primary Transit Network as every 10 minutes or better, 15 hours a day, seven days a week. It also says today's network leans toward coverage (p. 40)."],
  ["s4_split_ctrain_10min", "[1:30–1:55] Where are we today? Of every weekly service hour in the fall 2026 schedule, 18% runs every 10 minutes or better. 82% runs less often."],
  ["06_map_2026_noon", "[1:55–2:15] On a weekday at noon, almost all of the teal is CTrain. Everything in orange is coverage."],
  ["02_split_by_year", "[2:15–2:40] The balance has drifted. 25% in 2016, 15% in 2019, 18% today. Most of the loss came between 2016 and 2019, before the pandemic. RouteAhead itself notes that cuts after the economic downturn reversed earlier progress."],
  ["s5_covered_vs_frequent_area", "[2:40–3:00] Meanwhile the area with any service grew 10%, and the area with 10-minute service shrank 3%. Service has spread further and thinner."],
  ["s6_land_use_diagram", "[3:00–3:35] Nobody decided this. New communities, rezoning, corridor growth and budget decisions each move the balance, and none of them reports its effect on it."],
  ["s7_the_ask", "[3:35–4:30] Three requests. One: budget the two services separately, and set the balance on purpose. Two: show the impact on both before major land use and service decisions are made. Three: ask Calgarians to help decide. This is a question about balance, not a call to cut coverage."],
  ["s8_close_question", "[4:30–5:00] So the question for this budget is: which balance do Calgarians want? Thank you. I'm happy to take questions."],
];

const BACKUP = [
  ["05_threshold_sensitivity", "If asked why 10 minutes: this is the share at every threshold from 10 to 30 minutes. 2026 is below 2016 wherever you draw the line."],
  ["s4_split_ctrain_15min", "At 15 minutes, 30% of weekly hours count as frequency (27% to 32% with CTrain at 2× to 3×)."],
  ["09_map_2026_noon_15min", "The noon network at the 15-minute line."],
  ["04_time_of_day_2026", "Service by hour of the weekday, frequency against coverage."],
  ["07_map_years_noon", "The noon network in 2016, 2019 and 2026."],
  ["08_map_2026_noon_vs_9pm", "The same network at noon and at 9 pm."],
  ["b_method", "Method. Schedules, not observed service. CTrain weighting holds between 2× and 3×. Supply, not ridership: the City does not publish ridership by route."],
  ["b_tradeoffs", "Either direction is legitimate. Leaning coverage, ridership will likely shrink. Leaning frequency, ridership will likely grow, with a plan for edge areas."],
];

function pngSize(file) {
  const b = fs.readFileSync(file);
  return [b.readUInt32BE(16), b.readUInt32BE(20)];
}

const pres = new pptxgen();
pres.layout = "LAYOUT_16x9";
pres.author = "Willem Klumpenhouwer";
pres.title = "Transit does two jobs";

function add(section, [name, notes]) {
  const file = path.join(ASSETS, `${name}.png`);
  const [pw, ph] = pngSize(file);
  const r = pw / ph;
  // 16:9 slides fill the frame; charts fit inside a small margin, centred on the matching paper colour
  const full = Math.abs(r - W / H) < 0.01;
  const bw = full ? W : W - 2 * PAD, bh = full ? H : H - 2 * PAD;
  const w = Math.min(bw, bh * r), h = w / r;
  const s = pres.addSlide({ sectionTitle: section });
  s.background = { color: "F2EEE4" };
  s.addImage({ path: file, x: (W - w) / 2, y: (H - h) / 2, w, h, altText: name });
  s.addNotes(notes);
}

pres.addSection({ title: "Talk" });
TALK.forEach((t) => add("Talk", t));
pres.addSection({ title: "Backup" });
BACKUP.forEach((t) => add("Backup", t));
// Folder entries in the zip break Drive import and co-editing, so drop them before writing
const JSZip = require("jszip");
pres.write({ outputType: "nodebuffer" })
  .then((buf) => JSZip.loadAsync(buf))
  .then(async (z) => {
    // JSZip's remove() on a folder also removes its contents, so copy the file entries into a fresh zip instead
    const out = new JSZip();
    for (const f of Object.values(z.files).filter((f) => !f.dir)) out.file(f.name, await f.async("nodebuffer"), { createFolders: false });
    return out.generateAsync({ type: "nodebuffer", compression: "DEFLATE" });
  })
  .then((buf) => { fs.writeFileSync(OUT, buf); console.log("wrote", OUT); });
