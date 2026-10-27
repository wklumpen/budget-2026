"""Preprocess a GTFS feed for the frequent/coverage split, using reference dates.

The same method is applied to every feed: pick one representative date per day
type, take the services active on that date (calendar.txt plus calendar_dates.txt),
and measure trips started per direction per clock hour plus revenue minutes per
clock hour. A typical week is 4 x Mon-Thu, 1 x Fri, 1 x Sat, 1 x Sun.

Usage: python3 -I prep_ref.py <feed_dir> <out_json> <tue> <fri> <sat> <sun> [--geom] [--label TEXT] [--period TEXT]
Dates are YYYYMMDD. --geom adds simplified route shapes (needed for the map).
--label / --period fill the page footer (meta.feed, meta.period).
"""
import json
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

feed = Path(sys.argv[1])
out = Path(sys.argv[2])
refs = dict(zip(["mt", "fr", "sa", "su"], sys.argv[3:7]))
with_geom = "--geom" in sys.argv


def opt(flag, default):
    return sys.argv[sys.argv.index(flag) + 1] if flag in sys.argv else default


DAYS_PER_WEEK = {"mt": 4, "fr": 1, "sa": 1, "su": 1}
NH = 28

routes = pd.read_csv(feed / "routes.txt", dtype=str)
trips = pd.read_csv(feed / "trips.txt", dtype=str)
st = pd.read_csv(
    feed / "stop_times.txt",
    usecols=["trip_id", "arrival_time", "departure_time", "stop_sequence"],
    dtype={"trip_id": str, "arrival_time": str, "departure_time": str, "stop_sequence": int},
)


def active_services(date):
    dt = datetime.strptime(date, "%Y%m%d")
    wd = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"][dt.weekday()]
    active = set()
    cal = feed / "calendar.txt"
    if cal.exists():
        c = pd.read_csv(cal, dtype=str)
        c = c[(c.start_date <= date) & (c.end_date >= date) & (c[wd] == "1")]
        active |= set(c.service_id)
    cdp = feed / "calendar_dates.txt"
    if cdp.exists():
        cd = pd.read_csv(cdp, dtype=str)
        cd = cd[cd.date == date]
        active |= set(cd[cd.exception_type == "1"].service_id)
        active -= set(cd[cd.exception_type == "2"].service_id)
    return active


def to_sec(s):
    h, m, x = s.strip().split(":")
    return int(h) * 3600 + int(m) * 60 + int(x)


st = st.sort_values(["trip_id", "stop_sequence"])
first = st.groupby("trip_id").first()
last = st.groupby("trip_id").last()
span = pd.DataFrame({"start": first["departure_time"].map(to_sec), "end": last["arrival_time"].map(to_sec)})
trips = trips.join(span, on="trip_id")
trips = trips[trips.start.notna()]
trips["direction_id"] = trips["direction_id"].fillna("0")


def mode_of(r):
    if r.route_type == "0":
        return "ctrain"
    try:
        n = int(r.route_short_name)
    except ValueError:
        return "bus"
    return "school" if 600 <= n <= 899 else "bus"


routes["mode"] = routes.apply(mode_of, axis=1)


def apportion(start, end):
    mins = np.zeros(NH)
    t = start
    while t < end:
        h = int(t // 3600)
        nxt = min(end, (h + 1) * 3600)
        if h < NH:
            mins[h] += (nxt - t) / 60
        t = nxt
    return mins


svc = {dt: active_services(d) for dt, d in refs.items()}
for dt, s in svc.items():
    print(dt, refs[dt], sorted(s))

shapes = pd.read_csv(feed / "shapes.txt", dtype={"shape_id": str}) if with_geom else None
by_route = {rid: g for rid, g in trips.groupby("route_id")}
out_routes = []
for r in routes.itertuples():
    rt = by_route.get(r.route_id)
    if rt is None:
        continue
    rec = {"id": r.route_id, "n": r.route_short_name, "name": str(r.route_long_name).strip(),
           "mode": r.mode, "dirs": sorted(rt.direction_id.unique().tolist()), "d": {}}
    wk = 0.0
    for dt in refs:
        sub = rt[rt.service_id.isin(svc[dt])]
        starts = {d: [0] * NH for d in ("0", "1")}
        mins = np.zeros(NH)
        for tr in sub.itertuples():
            h = int(tr.start // 3600)
            if h < NH:
                starts[tr.direction_id][h] += 1
            mins += apportion(tr.start, tr.end)
        rec["d"][dt] = {"s0": starts["0"], "s1": starts["1"], "m": [round(x, 1) for x in mins]}
        wk += mins.sum() * DAYS_PER_WEEK[dt]
    rec["wkh"] = round(wk / 60, 1)
    if with_geom:
        geoms = []
        from shapely.geometry import LineString
        for d in rec["dirs"]:
            sid = rt[rt.direction_id == d].shape_id.value_counts()
            if sid.empty:
                continue
            pts = shapes[shapes.shape_id == sid.index[0]].sort_values("shape_pt_sequence")
            if len(pts) < 2:
                continue
            line = LineString(zip(pts.shape_pt_lon, pts.shape_pt_lat)).simplify(0.00025)
            geoms.append([[round(x, 4), round(y, 4)] for x, y in line.coords])
        rec["g"] = geoms
    out_routes.append(rec)

meta = {"feed": opt("--label", str(feed.name)), "period": opt("--period", "Reference dates " + ", ".join(refs.values())), "refs": refs, "days": DAYS_PER_WEEK}
out.write_text(json.dumps({"meta": meta, "routes": out_routes}, separators=(",", ":")))
tot = pd.DataFrame([(r["mode"], r["wkh"]) for r in out_routes], columns=["mode", "wkh"])
print(tot.groupby("mode").wkh.agg(["count", "sum"]).round(1))
