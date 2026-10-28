"""Presentation assets (PNG + SVG) built with Altair from the same data as the explorer page.

Usage: python3 -I make_assets.py <out_dir>        (needs altair>=5, vl-convert-python, pandas, numpy)
Reads data/data{2016,2019,2026}.json and data/trend.json relative to this script's parent folder.
Method matches page/template.html: smoothed trips/hr per direction averaged across directions, frequent if
>= 60/threshold, 10% deadhead, CTrain at 2.5x bus hours, school specials excluded.
"""
import json
import math
import sys
from pathlib import Path

import altair as alt
import pandas as pd
import vl_convert as vlc

ROOT = Path(__file__).resolve().parent.parent
OUT = Path(sys.argv[1])
OUT.mkdir(parents=True, exist_ok=True)
vlc.register_font_directory(str(Path(__file__).resolve().parent / "fonts"))

YEARS = ["2016", "2019", "2026"]
DATA = {y: json.loads((ROOT / f"data/data{y}.json").read_text()) for y in YEARS}
TREND = json.loads((ROOT / "data/trend.json").read_text())
DH, LRT = 0.10, 2.5

PAPER, INK, INK2, MUTED, LINE = "#f2eee4", "#12171d", "#47515c", "#6e7884", "#d6cfbf"
TEAL, TEAL_D, ORANGE, ORANGE_D, IDLE = "#0e8083", "#095457", "#eb6834", "#a8401a", "#cbc4b3"
DISPLAY, BODY = "Barlow Condensed", "Barlow Condensed"  # plain zeros; Atkinson Hyperlegible slashes them
SOURCE = "Source: Calgary Transit GTFS, fall schedules, weekday service. Analysis: Willem Klumpenhouwer. Supply, not ridership."
W16 = 1600


# ---------- numbers (mirror of the page's JavaScript) ----------
def smooth(a):
    return [((a[h - 1] if h else 0) + a[h] + (a[h + 1] if h + 1 < len(a) else 0)) / 3 for h in range(len(a))]


def tph(r, dt):
    d = r["d"][dt]
    s0, s1 = smooth(d["s0"]), smooth(d["s1"])
    if len(r["dirs"]) == 2:
        return [(a + b) / 2 for a, b in zip(s0, s1)]
    return s1 if r["dirs"][0] == "1" else s0


for y in YEARS:
    for r in DATA[y]["routes"]:
        r["tph"] = {dt: tph(r, dt) for dt in r["d"]}


def counted(y):
    return [r for r in DATA[y]["routes"] if r["mode"] != "school"]


def split_for(y, thr, lrt=LRT):
    o = dict(Rb=0.0, Rl=0.0, Cb=0.0, Cl=0.0)
    days = DATA[y]["meta"]["days"]
    for r in counted(y):
        k = "l" if r["mode"] == "ctrain" else "b"
        f = (1 + DH) * (lrt if k == "l" else 1)
        for dt, n in days.items():
            for h, m in enumerate(r["d"][dt]["m"]):
                if m:
                    o[("R" if r["tph"][dt][h] >= 60 / thr - 1e-9 else "C") + k] += m * n * f / 60
    o["R"], o["C"] = o["Rb"] + o["Rl"], o["Cb"] + o["Cl"]
    o["T"] = o["R"] + o["C"]
    return o


def by_hour(y, thr, dt="mt"):
    rows = []
    for h in range(4, 26):
        o = dict(Rb=0.0, Rl=0.0, Cb=0.0, Cl=0.0)
        for r in counted(y):
            m = r["d"][dt]["m"][h]
            if m:
                k = "l" if r["mode"] == "ctrain" else "b"
                f = (1 + DH) * (LRT if k == "l" else 1)
                o[("R" if r["tph"][dt][h] >= 60 / thr - 1e-9 else "C") + k] += m * f / 60
        rows.append(dict(hour=h, **o))
    return pd.DataFrame(rows)


def pct(x):
    return f"{round(x * 100)}%"


# ---------- shared look ----------
def finish(chart, title, subtitle, width=W16, source=True):
    """Title block plus a source line, then page-wide config."""
    parts = [chart]
    if source:
        parts.append(alt.Chart(pd.DataFrame({"t": [SOURCE]})).mark_text(align="left", x=0, baseline="top", font=BODY, fontSize=20, color=MUTED)
                     .encode(text="t:N").properties(width=width, height=24))
    out = alt.vconcat(*parts, spacing=12).properties(
        title=alt.TitleParams(text=title, subtitle=subtitle, anchor="start", font=DISPLAY, fontSize=64, fontWeight=700, color=INK,
                              subtitleFont=BODY, subtitleFontSize=30, subtitleColor=INK2, subtitlePadding=8, offset=26)
    )
    return (out.configure(background=PAPER, padding={"left": 40, "right": 40, "top": 34, "bottom": 28})
            .configure_view(stroke=None)
            .configure_axis(labelFont=BODY, titleFont=BODY, labelColor=INK2, titleColor=INK2, labelFontSize=26, titleFontSize=26,
                            domainColor=INK, tickColor=INK, gridColor=LINE)
            .configure_legend(labelFont=BODY, titleFont=BODY, labelFontSize=26, titleFontSize=26))


def save(chart, name):
    chart.save(str(OUT / f"{name}.png"), scale_factor=1.2)
    chart.save(str(OUT / f"{name}.svg"))
    print("wrote", name)


def big_text(df, **kw):
    return alt.Chart(df).mark_text(**{"font": DISPLAY, "fontWeight": 700, **kw})


# ---------- 1. headline split ----------
def chart_headline(y="2026", thr=10):
    s = split_for(y, thr)
    sc = alt.Scale(domain=["Frequency", "Coverage"], range=[TEAL, ORANGE])
    color = alt.Color("job:N", scale=sc, legend=None)
    xs = alt.Scale(domain=[0, s["T"]], nice=False)
    df = pd.DataFrame({"job": ["Frequency", "Coverage"], "x0": [0, s["R"]], "x1": [s["R"], s["T"]], "xt": [s["R"] / 2, s["R"] + s["C"] / 2],
                       "p": [pct(s["R"] / s["T"]), pct(s["C"] / s["T"])], "lbl": ["FREQUENCY", "COVERAGE"],
                       "hrs": [f"{round(s['R']):,} hrs / week", f"{round(s['C']):,} hrs / week"]})
    xt = alt.X("xt:Q", scale=xs, axis=None)
    bar = alt.Chart(df).mark_bar(height=200, stroke=PAPER, strokeWidth=3).encode(x=alt.X("x0:Q", axis=None, scale=xs), x2="x1:Q", color=color)
    nums = big_text(df, fontSize=170, baseline="bottom", dy=-110).encode(x=xt, text="p:N", color=color)
    lbls = big_text(df, fontSize=44, fontWeight=600, baseline="bottom", dy=-285).encode(x=xt, text="lbl:N", color=color)
    hrs = alt.Chart(df).mark_text(font=BODY, fontSize=26, baseline="top", dy=120, color=INK2).encode(x=xt, text="hrs:N")
    ch = alt.layer(bar, nums, lbls, hrs).properties(width=W16, height=200)
    return finish(ch, "Transit's conflicting priorities", f"Share of weekly service hours (bus and CTrain) running every {thr} minutes or better, fall {y}")


# ---------- 2. split by year ----------
def chart_years(thr=10):
    rows = []
    for y in YEARS:
        s = split_for(y, thr)
        rows.append(dict(year=y, **s))
    d = pd.DataFrame(rows)
    mx = d["T"].max()
    d["fx1"] = d["R"]
    d["cx0"] = mx - d["C"]
    d["cx1"] = mx
    d["fp"] = d["R"] / d["T"]
    d["cp"] = d["C"] / d["T"]
    d["fl"] = d["fp"].map(pct)
    d["cl"] = d["cp"].map(pct)
    d["fh"] = d["R"].map(lambda v: f"{round(v):,} hrs")
    d["ch"] = d["C"].map(lambda v: f"{round(v):,} hrs")
    xs = alt.Scale(domain=[0, mx], nice=False)
    y_enc = alt.Y("year:N", title=None, axis=alt.Axis(labelFont=DISPLAY, labelFontSize=46, labelFontWeight=700, labelColor=INK, ticks=False, domain=False, labelPadding=14), sort=YEARS)
    f = alt.Chart(d).mark_bar(color=TEAL, size=84).encode(y=y_enc, x=alt.X("zero:Q", scale=xs, axis=None), x2="fx1:Q").transform_calculate(zero="0")
    c = alt.Chart(d).mark_bar(color=ORANGE, size=84).encode(y=y_enc, x=alt.X("cx0:Q", scale=xs, axis=None), x2="cx1:Q")
    ft = alt.Chart(d).mark_text(font=DISPLAY, fontWeight=700, fontSize=58, color="#ffffff", align="left", dx=14).encode(y=y_enc, x=alt.value(0), text="fl:N")
    ct = alt.Chart(d).mark_text(font=DISPLAY, fontWeight=700, fontSize=58, color="#12171d", align="right", dx=-14).encode(y=y_enc, x=alt.value(W16 - 150), text="cl:N")
    fh = alt.Chart(d).mark_text(font=BODY, fontSize=22, color=INK2, align="left", baseline="top", dy=48).encode(y=y_enc, x=alt.value(0), text="fh:N")
    ch = alt.Chart(d).mark_text(font=BODY, fontSize=22, color=INK2, align="right", baseline="top", dy=48).encode(y=y_enc, x=alt.value(W16 - 150), text="ch:N")
    chart = alt.layer(f, c, ft, ct, fh, ch).properties(width=W16 - 150, height=430)
    a, b = d.iloc[0], d.iloc[-1]
    sub = (f"Every {thr} min or better. Frequency hours {round((b.R / a.R - 1) * 100):+d}%, coverage hours {round((b.C / a.C - 1) * 100):+d}%, "
           f"total {round((b['T'] / a['T'] - 1) * 100):+d}%, 2016 to 2026")
    return finish(chart, "The balance has drifted toward coverage", sub, width=W16 - 150)


# ---------- 3. trend panels ----------
def chart_trend(kind, thr=10):
    T = TREND[str(thr)]
    if kind == "visits":
        d = pd.DataFrame({"year": YEARS, "v": [T[y]["visits"] for y in YEARS]})
        d["label"] = d["v"].map(lambda v: f"{v:.0f}%")
        title, sub, mx = f"Midday stop-visits every {thr} min or better", "Share of all stop-visits, weekdays 10:00 to 15:00", 100
    elif kind == "area":
        d = pd.DataFrame({"year": YEARS, "v": [T[y]["area"] for y in YEARS], "ref": [TREND["covered"][y] for y in YEARS]})
        d["label"] = d["v"].map(lambda v: f"{v:.0f} km²")
        title, sub = f"Area with {thr}-minute midday service", "km² within 800 m of CTrain / 400 m of a bus stop; the pale bar is the whole covered area"
        mx = d["ref"].max()
    else:
        d = pd.DataFrame({"year": YEARS, "v": [split_for(y, thr)["Rb"] / (1 + DH) for y in YEARS]})
        d["label"] = d["v"].map(lambda v: f"{round(v):,} hrs")
        title, sub, mx = f"Bus hours on routes every {thr} min or better", "Weekly bus revenue hours when the route meets the threshold", d["v"].max()
    xs = alt.Scale(domain=[0, mx * 1.18], nice=False)
    y_enc = alt.Y("year:N", title=None, sort=YEARS, axis=alt.Axis(labelFont=DISPLAY, labelFontSize=40, labelFontWeight=700, labelColor=INK, ticks=False, domain=False))
    layers = []
    if kind == "area":
        layers.append(alt.Chart(d).mark_bar(color=IDLE, size=70).encode(y=y_enc, x=alt.X("ref:Q", scale=xs, axis=None)))
    layers.append(alt.Chart(d).mark_bar(color=TEAL, size=70).encode(y=y_enc, x=alt.X("v:Q", scale=xs, axis=None)))
    layers.append(alt.Chart(d).mark_text(font=DISPLAY, fontWeight=700, fontSize=48, color=INK, align="left", dx=10).encode(y=y_enc, x=alt.X("ref:Q" if kind == "area" else "v:Q", scale=xs), text="label:N"))
    ch = alt.layer(*layers).properties(width=W16 - 150, height=380)
    return finish(ch, title, sub, width=W16 - 150)


# ---------- 4. time of day ----------
def chart_tod(y="2026", thr=10):
    d = by_hour(y, thr)
    names = {"Rl": "Frequency, CTrain", "Rb": "Frequency, bus", "Cb": "Coverage, bus", "Cl": "Coverage, CTrain"}
    long = d.melt("hour", ["Rl", "Rb", "Cb", "Cl"], var_name="k", value_name="hrs")
    long["series"] = long["k"].map(names)
    order = [names[k] for k in ["Rl", "Rb", "Cb", "Cl"]]
    long["o"] = long["series"].map(order.index)
    chart = alt.Chart(long).mark_area(interpolate="step-after").encode(
        x=alt.X("hour:Q", title=None, scale=alt.Scale(domain=[4, 26], nice=False),
                axis=alt.Axis(values=[6, 9, 12, 15, 18, 21, 24], labelExpr="datum.value % 24 < 10 ? '0' + datum.value % 24 + ':00' : datum.value % 24 + ':00'", grid=False)),
        y=alt.Y("hrs:Q", title="Bus-equivalent hours", stack=True, axis=alt.Axis(titlePadding=18)),
        color=alt.Color("series:N", sort=order, scale=alt.Scale(domain=order, range=[TEAL_D, TEAL, ORANGE, ORANGE_D]), legend=alt.Legend(title=None, orient="top", symbolSize=300, columns=4, labelLimit=0, columnPadding=24)),
        order=alt.Order("o:Q"),
    ).properties(width=W16 - 40, height=520)
    return finish(chart, "Frequency is a daytime service", f"Weekday service hours by clock hour, fall {y}, frequent = every {thr} minutes or better", width=W16 - 40)


# ---------- 5. sensitivity ----------
def chart_sens():
    rows = [dict(year=y, thr=t, share=split_for(y, t)["R"] / split_for(y, t)["T"]) for y in YEARS for t in range(10, 31)]
    d = pd.DataFrame(rows)
    d["label"] = d["share"].map(pct)
    color = alt.Color("year:N", scale=alt.Scale(domain=YEARS, range=["#9aa3ad", "#5f6a76", TEAL]), legend=None)
    line = alt.Chart(d).mark_line(strokeWidth=5).encode(x=alt.X("thr:Q", title="Counts as frequent: every ___ minutes or better", scale=alt.Scale(domain=[10, 30], nice=False), axis=alt.Axis(values=[10, 15, 20, 25, 30], format="d", grid=False)),
                                                        y=alt.Y("share:Q", title="Share of weekly service hours", axis=alt.Axis(format="%"), scale=alt.Scale(domain=[0, 0.7])), color=color)
    end = d[d.thr == 30]
    end = end.assign(dy=end["year"].map({"2016": -14, "2019": -3, "2026": 18}))
    lab = alt.Chart(end).mark_text(font=DISPLAY, fontWeight=700, fontSize=30, align="left", dx=12).encode(x="thr:Q", y="share:Q", text="year:N", color=color, yOffset="dy:Q")
    chart = alt.layer(line, lab).properties(width=W16 - 220, height=520)
    return finish(chart, "Wherever you draw the line, frequency lost ground", "Frequency share of weekly service hours by threshold. 2026 sits below 2016 at every threshold", width=W16 - 220)


# ---------- 6. maps ----------
LON = [p[0] for y in YEARS for r in counted(y) for ln in r.get("g", []) for p in ln]
LAT = [p[1] for y in YEARS for r in counted(y) for ln in r.get("g", []) for p in ln]
LON0, LON1, LAT0, LAT1 = min(LON), max(LON), min(LAT), max(LAT)


def mercy(lat):
    return math.log(math.tan(math.pi / 4 + math.radians(lat) / 2))


def proj_for(w, h):
    s = min(w * 0.96 / math.radians(LON1 - LON0), h * 0.96 / (mercy(LAT1) - mercy(LAT0)))
    return alt.Projection(type="mercator", scale=s, center=[(LON0 + LON1) / 2, math.degrees(2 * math.atan(math.exp((mercy(LAT0) + mercy(LAT1)) / 2)) - math.pi / 2)], translate=[w / 2, h / 2])


def features(y, hour, thr, dt="mt"):
    out = {"idle": [], "C": [], "R": [], "RL": [], "CL": []}
    for r in counted(y):
        rail = r["mode"] == "ctrain"
        if not r["d"][dt]["m"][hour]:
            cls = "idle"
        else:
            cls = ("R" if r["tph"][dt][hour] >= 60 / thr - 1e-9 else "C") + ("L" if rail else "")
        for ln in r.get("g", []):
            out[cls].append({"type": "Feature", "properties": {}, "geometry": {"type": "LineString", "coordinates": ln}})
    return out


def map_chart(y, hour, thr, w=760, h=800, title=None):
    f = features(y, hour, thr)
    proj = proj_for(w, h)
    style = [("idle", IDLE, 1.0), ("C", ORANGE, 1.6), ("CL", ORANGE_D, 5.5), ("R", TEAL, 3.4), ("RL", TEAL_D, 5.5)]
    layers = []
    for k, col, sw in style:
        if f[k]:
            layers.append(alt.Chart(alt.Data(values=f[k])).mark_geoshape(filled=False, stroke=col, strokeWidth=sw, strokeCap="round", strokeJoin="round").project(**proj.to_dict()))
    ch = alt.layer(*layers).properties(width=w, height=h)
    if title:
        ch = ch.properties(title=alt.TitleParams(title, font=DISPLAY, fontSize=54, fontWeight=700, color=INK, anchor="start", offset=6))
    return ch


def map_legend(width, thr=10):
    items = [("Frequency, every %d min or better" % thr, TEAL, 8, 0), ("Coverage", ORANGE, 8, 560), ("Not running", IDLE, 4, 760), ("Heavy line: CTrain", INK, 12, 960)]
    d = pd.DataFrame([dict(t=t, c=c, w=w, x0=x, x1=x + 46) for t, c, w, x in items])
    rule = alt.Chart(d).mark_rule(strokeCap="round").encode(x=alt.X("x0:Q", scale=alt.Scale(domain=[0, width], nice=False), axis=None), x2="x1:Q",
                                                            y=alt.value(16), color=alt.Color("c:N", scale=None), strokeWidth=alt.StrokeWidth("w:Q", scale=None))
    txt = alt.Chart(d).mark_text(font=BODY, fontSize=28, align="left", baseline="middle", dx=56, color=INK).encode(x=alt.X("x0:Q", scale=alt.Scale(domain=[0, width], nice=False), axis=None), y=alt.value(16), text="t:N")
    return alt.layer(rule, txt).properties(width=width, height=32)


def chart_map_single(y="2026", hour=12, thr=10):
    m = map_chart(y, hour, thr, w=1000, h=900)
    lg = map_legend(1000, thr)
    sub = f"Bus routes and CTrain (heavy lines) at {hour}:00 on a weekday, fall {y}, coloured by how often they run"
    return finish(alt.vconcat(m, lg, spacing=6), f"The network at {'noon' if hour == 12 else str(hour) + ':00'}", sub, width=1000)


def chart_map_years(hour=12, thr=10):
    ms = [map_chart(y, hour, thr, w=520, h=640, title=y) for y in YEARS]
    lg = map_legend(1560, thr)
    return finish(alt.vconcat(alt.hconcat(*ms, spacing=20), lg, spacing=6), "The frequent network, 2016 to 2026",
                  f"Weekday at {hour}:00. Teal runs every {thr} minutes or better; orange is coverage service", width=1560)


def chart_map_times(y="2026", thr=10):
    ms = [map_chart(y, 12, thr, w=760, h=800, title="Noon"), map_chart(y, 21, thr, w=760, h=800, title="9 pm")]
    lg = map_legend(1560, thr)
    return finish(alt.vconcat(alt.hconcat(*ms, spacing=30), lg, spacing=6), "The same network, two times of day",
                  f"Weekday, fall {y}. After the day peak, almost all of it is coverage service", width=1560)


# ---------- per-slide assets for the 5-minute talk ----------
def chart_s1(y="2026", thr=10):
    """Cold open: the split bar with names and no numbers."""
    s = split_for(y, thr)
    sc = alt.Scale(domain=["Frequency", "Coverage"], range=[TEAL, ORANGE])
    xs = alt.Scale(domain=[0, s["T"]], nice=False)
    df = pd.DataFrame({"job": ["Frequency", "Coverage"], "x0": [0, s["R"]], "x1": [s["R"], s["T"]], "xt": [s["R"] / 2, s["R"] + s["C"] / 2], "lbl": ["FREQUENCY", "COVERAGE"]})
    bar = alt.Chart(df).mark_bar(height=260, stroke=PAPER, strokeWidth=3).encode(x=alt.X("x0:Q", axis=None, scale=xs), x2="x1:Q", color=alt.Color("job:N", scale=sc, legend=None))
    txt = big_text(df, fontSize=64, baseline="middle", color="#ffffff").encode(x=alt.X("xt:Q", scale=xs, axis=None), text="lbl:N")
    ch = alt.layer(bar, txt).properties(width=W16, height=260)
    return finish(ch, "Transit has two jobs", "Every hour of service goes to one or the other", source=False)


def chart_s2():
    """What each job needs: the same three hours at a stop with 10-minute and 60-minute service."""
    rows = []
    for lab, gap in (("Every 10 minutes", 10), ("Every 60 minutes", 60)):
        rows += [dict(row=lab, t=t, gap=gap) for t in range(0, 180, gap)]
    d = pd.DataFrame(rows)
    order = ["Every 10 minutes", "Every 60 minutes"]
    y_enc = alt.Y("row:N", sort=order, title=None, axis=alt.Axis(labelFont=DISPLAY, labelFontSize=44, labelFontWeight=700, labelColor=INK, ticks=False, domain=False, labelPadding=18, labelLimit=0))
    col = alt.Color("row:N", scale=alt.Scale(domain=order, range=[TEAL, ORANGE]), legend=None)
    x_enc = alt.X("t:Q", scale=alt.Scale(domain=[-4, 184], nice=False), title=None,
                  axis=alt.Axis(values=[0, 60, 120, 180], labelExpr="['12:00','13:00','14:00','15:00'][datum.value / 60]", grid=False, tickSize=0))
    rule = alt.Chart(pd.DataFrame({"row": order})).mark_rule(color=LINE, strokeWidth=3).encode(y=y_enc, x=alt.value(0), x2=alt.value(W16 - 520))
    dots = alt.Chart(d).mark_circle(size=900, opacity=1).encode(y=y_enc, x=x_enc, color=col)
    note = pd.DataFrame({"row": order, "t": [90, 90], "n": ["18 buses. Just show up.", "3 buses. Check the schedule."]})
    txt = alt.Chart(note).mark_text(font=DISPLAY, fontWeight=600, fontSize=40, dy=-64, color=INK).encode(y=y_enc, x=alt.X("t:Q", scale=alt.Scale(domain=[-4, 184], nice=False)), text="n:N")
    ch = alt.layer(rule, dots, txt).properties(width=W16 - 520, height=420)
    return finish(ch, "Same three hours, two kinds of service", "Departures from one stop between noon and 3 pm", width=W16 - 520)


def chart_s4_split(thr=10):
    """Where Calgary sits: split bar with CTrain as the darker shade, plus the 2x to 3x range."""
    s = split_for("2026", thr)
    lo, hi = (split_for("2026", thr, l) for l in (2.0, 3.0))
    rs = sorted([lo["R"] / lo["T"], hi["R"] / hi["T"]])
    xs = alt.Scale(domain=[0, s["T"]], nice=False)
    segs = [("Frequency, CTrain", 0, s["Rl"], TEAL_D), ("Frequency, bus", s["Rl"], s["R"], TEAL), ("Coverage, bus", s["R"], s["R"] + s["Cb"], ORANGE), ("Coverage, CTrain", s["R"] + s["Cb"], s["T"], ORANGE_D)]
    d = pd.DataFrame([dict(k=k, x0=a, x1=b, c=c) for k, a, b, c in segs])
    bar = alt.Chart(d).mark_bar(height=200, stroke=PAPER, strokeWidth=3).encode(x=alt.X("x0:Q", axis=None, scale=xs), x2="x1:Q", color=alt.Color("c:N", scale=None))
    j = pd.DataFrame({"xt": [s["R"] / 2, s["R"] + s["C"] / 2], "p": [pct(s["R"] / s["T"]), pct(s["C"] / s["T"])], "l": ["FREQUENCY", "COVERAGE"], "c": [TEAL, ORANGE]})
    xt = alt.X("xt:Q", scale=xs, axis=None)
    nums = big_text(j, fontSize=170, baseline="bottom", dy=-110).encode(x=xt, text="p:N", color=alt.Color("c:N", scale=None))
    lbls = big_text(j, fontSize=44, fontWeight=600, baseline="bottom", dy=-285).encode(x=xt, text="l:N", color=alt.Color("c:N", scale=None))
    ct = pd.DataFrame({"xt": [s["Rl"] / 2], "t": ["CTrain"]})
    ctt = alt.Chart(ct).mark_text(font=BODY, fontSize=28, color="#ffffff", baseline="middle").encode(x=alt.X("xt:Q", scale=xs, axis=None), text="t:N")
    ch = alt.layer(bar, nums, lbls, ctt).properties(width=W16, height=200)
    sub = f"Weekly service hours, fall 2026, every {thr} minutes or better. CTrain (darker) at 2.5× bus hours; at 2× to 3× the frequency share is {pct(rs[0])} to {pct(rs[1])}"
    return finish(ch, "Where Calgary sits today", sub)


def chart_s5_index():
    """The decade: covered area grew, the 10-minute footprint did not. Index 2016 = 100."""
    T = TREND["10"]
    rows = []
    for y in YEARS:
        rows.append(dict(year=int(y), series="Area covered by any service", v=TREND["covered"][y] / TREND["covered"]["2016"] * 100))
        rows.append(dict(year=int(y), series="Area with 10-minute midday service", v=T[y]["area"] / T["2016"]["area"] * 100))
    d = pd.DataFrame(rows)
    d["label"] = d["v"].map(lambda v: f"{v:.0f}")
    names = ["Area covered by any service", "Area with 10-minute midday service"]
    ys = alt.Scale(domain=[85, 115], nice=False)
    col = alt.Color("series:N", scale=alt.Scale(domain=names, range=[ORANGE, TEAL]), legend=alt.Legend(title=None, orient="top", labelLimit=0, symbolSize=500, symbolStrokeWidth=8, symbolType="stroke", columnPadding=40))
    x = alt.X("year:Q", scale=alt.Scale(domain=[2015, 2027], nice=False), title=None, axis=alt.Axis(values=[2016, 2019, 2026], format="d", grid=False))
    line = alt.Chart(d).mark_line(strokeWidth=7, point=alt.OverlayMarkDef(size=260, filled=True)).encode(x=x, y=alt.Y("v:Q", scale=ys, title="Index, 2016 = 100"), color=col)
    lab = alt.Chart(d).mark_text(font=DISPLAY, fontWeight=700, fontSize=42, dy=-26).encode(x=x, y=alt.Y("v:Q", scale=ys), text="label:N", color=col)
    ref = alt.Chart(pd.DataFrame({"y": [100]})).mark_rule(color=INK, strokeDash=[5, 5]).encode(y=alt.Y("y:Q", scale=ys))
    ch = alt.layer(ref, line, lab).properties(width=W16 - 80, height=520)
    return finish(ch, "The covered area grew. The frequent area didn't.", "Weekday service area within walking distance (800 m of CTrain, 400 m of a bus stop), fall 2016, 2019 and 2026", width=W16 - 80)


# ---------- SVG text and diagram slides ----------
def svg_slide(name, body, w=1600, h=900):
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">'
           f'<style>text{{font-family:"{DISPLAY}";fill:{INK}}} .b{{font-weight:700}} .m{{font-weight:500}}</style>'
           f'<rect width="{w}" height="{h}" fill="{PAPER}"/>{body}</svg>')
    (OUT / f"{name}.svg").write_text(svg)
    (OUT / f"{name}.png").write_bytes(vlc.svg_to_png(svg, scale=1.2))
    print("wrote", name)


def box(x, y, w, h, label, fill, fg="#ffffff", size=44, sub=None):
    t = f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}"/>'
    if sub:
        t += f'<text x="{x + w / 2}" y="{y + h / 2 - 6}" text-anchor="middle" class="b" font-size="{size}" style="fill:{fg}">{label}</text>'
        t += f'<text x="{x + w / 2}" y="{y + h / 2 + 34}" text-anchor="middle" class="m" font-size="{size * 0.6}" style="fill:{fg}">{sub}</text>'
    else:
        t += f'<text x="{x + w / 2}" y="{y + h / 2 + size / 3}" text-anchor="middle" class="b" font-size="{size}" style="fill:{fg}">{label}</text>'
    return t


def arrow(x1, y1, x2, y2, color):
    return (f'<defs><marker id="a{color[1:]}" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="3.2" markerHeight="3.2" orient="auto"><path d="M0,0L10,5L0,10z" fill="{color}"/></marker></defs>'
            f'<path d="M{x1},{y1} C{x1 + 140},{y1} {x2 - 140},{y2} {x2},{y2}" fill="none" stroke="{color}" stroke-width="6" marker-end="url(#a{color[1:]})"/>')


def slide_s6():
    b = '<text x="60" y="110" class="b" font-size="84">Land use sets the split</text>'
    b += f'<text x="60" y="162" font-size="34" style="fill:{INK2}">Decisions made one at a time add up to the balance between the two jobs</text>'
    ins = [(250, "New communities on the edge", ORANGE), (400, "Rezoning, and rezoning that doesn't happen", ORANGE), (550, "Dense growth along corridors", TEAL), (700, "Transit budget decisions", INK)]
    for y, lab, c in ins:
        b += box(60, y, 620, 100, lab, "#fffdf8", fg=INK, size=36).replace("<rect ", f'<rect stroke="{c}" stroke-width="6" ', 1)
    b += box(1040, 300, 500, 180, "Coverage line", ORANGE, size=60, sub="not visible in the budget today")
    b += box(1040, 560, 500, 180, "Frequency line", TEAL, size=60, sub="not visible in the budget today")
    b += arrow(680, 300, 1040, 370, ORANGE) + arrow(680, 450, 1040, 405, ORANGE) + arrow(680, 600, 1040, 645, TEAL)
    b += arrow(680, 750, 1040, 450, INK) + arrow(680, 750, 1040, 690, INK)
    b += f'<text x="60" y="860" font-size="24" style="fill:{MUTED}">{SOURCE}</text>'
    svg_slide("s6_land_use_diagram", b)


def slide_s7():
    b = '<text x="60" y="130" class="b" font-size="110">The ask</text>'
    b += f'<rect x="60" y="190" width="120" height="14" fill="{ORANGE}"/><rect x="180" y="190" width="120" height="14" fill="{TEAL}"/>'
    b += f'<text x="60" y="400" class="b" font-size="82" style="fill:{ORANGE}">1</text><text x="150" y="400" class="b" font-size="74">Show the frequency and coverage split</text><text x="150" y="480" class="b" font-size="74">as a visible budget line.</text>'
    b += f'<text x="60" y="690" class="b" font-size="82" style="fill:{TEAL}">2</text><text x="150" y="690" class="b" font-size="74">Have land use decisions report their</text><text x="150" y="770" class="b" font-size="74">effect on each line.</text>'
    svg_slide("s7_the_ask", b)


def slide_s8():
    b = f'<rect x="60" y="150" width="120" height="14" fill="{ORANGE}"/><rect x="180" y="150" width="120" height="14" fill="{TEAL}"/>'
    b += '<text x="60" y="440" class="b" font-size="130">Which balance do</text><text x="60" y="590" class="b" font-size="130">Calgarians want?</text>'
    svg_slide("s8_close_question", b)


if __name__ == "__main__":
    for t in (10, 15):
        for k in ("visits", "area", "hours"):
            save(chart_trend(k, t), f"03_trend_{k}_{t}min")
    save(chart_headline(), "01_headline_split_2026")
    save(chart_years(), "02_split_by_year")
    save(chart_tod(), "04_time_of_day_2026")
    save(chart_sens(), "05_threshold_sensitivity")
    save(chart_map_single(), "06_map_2026_noon")
    save(chart_map_years(), "07_map_years_noon")
    save(chart_map_times(), "08_map_2026_noon_vs_9pm")
    save(chart_map_single(thr=15), "09_map_2026_noon_15min")
    save(chart_s1(), "s1_cold_open_bar")
    save(chart_s2(), "s2_ten_vs_sixty_minutes")
    save(chart_s4_split(10), "s4_split_ctrain_10min")
    save(chart_s4_split(15), "s4_split_ctrain_15min")
    save(chart_s5_index(), "s5_covered_vs_frequent_area")
    slide_s6()
    slide_s7()
    slide_s8()
