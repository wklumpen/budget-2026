"""Stop-level and area trend by frequency threshold, for the page's trend panel.

Usage: python3 -I trend_json.py <out.json> <year> <feed_dir> <YYYYMMDD ref Tuesday> [<year> <feed_dir> <date> ...]
For each threshold (minutes between buses, 5 to 30) and year:
  visits = share of midday (10:00-15:00) weekday stop-visits at stops with trips/hr >= 60/threshold
  area   = km^2 within the hybrid buffer (800 m of CTrain stops, 400 m of bus stops) of those stops
covered = same buffer around every stop with weekday service. School specials (600-899) are excluded.
"""
import json
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import shapely

THRS = [5, 10, 15, 20, 25, 30]
MIDDAY = range(10, 15)


def active(feed, date):
    wd = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"][datetime.strptime(date, "%Y%m%d").weekday()]
    a = set()
    p = feed / "calendar.txt"
    if p.exists():
        c = pd.read_csv(p, dtype=str)
        a |= set(c[(c.start_date <= date) & (c.end_date >= date) & (c[wd] == "1")].service_id)
    cd = pd.read_csv(feed / "calendar_dates.txt", dtype=str)
    cd = cd[cd.date == date]
    a |= set(cd[cd.exception_type == "1"].service_id)
    a -= set(cd[cd.exception_type == "2"].service_id)
    return a


def run(feed, date):
    feed = Path(feed)
    t = pd.read_csv(feed / "trips.txt", dtype=str, usecols=["route_id", "service_id", "trip_id"])
    r = pd.read_csv(feed / "routes.txt", dtype=str)
    n = pd.to_numeric(r.route_short_name, errors="coerce")
    keep = r[~((r.route_type == "3") & n.between(600, 899))].route_id
    t = t[t.service_id.isin(active(feed, date)) & t.route_id.isin(keep)]
    st = pd.read_csv(feed / "stop_times.txt", usecols=["trip_id", "stop_id", "departure_time"], dtype=str)
    st = st[st.trip_id.isin(set(t.trip_id))]
    hr = st.departure_time.str.split(":").str[0].astype(int)
    per = st[hr.isin(list(MIDDAY))].groupby("stop_id").size() / len(MIDDAY)
    stops = pd.read_csv(feed / "stops.txt", dtype=str)
    stops["lat"] = pd.to_numeric(stops.stop_lat.str.strip())
    stops["lon"] = pd.to_numeric(stops.stop_lon.str.strip())
    stops = stops[stops.stop_id.isin(set(st.stop_id))].copy()
    stops["tph"] = stops.stop_id.map(per).fillna(0.0)
    rail_trips = set(t[t.route_id.isin(set(r[r.route_type == "0"].route_id))].trip_id)
    is_rail = stops.stop_id.isin(set(st[st.trip_id.isin(rail_trips)].stop_id)).values
    x = (stops.lon - -114.07) * 111320 * np.cos(np.radians(51.05))
    y = (stops.lat - 51.05) * 110574
    pts = shapely.points(np.column_stack([x, y]))
    rad = np.where(is_rail, 800.0, 400.0)
    area = lambda m: shapely.union_all(shapely.buffer(pts[m], rad[m], quad_segs=8)).area / 1e6
    out = {"covered": round(area(np.ones(len(stops), bool)), 1)}
    for thr in THRS:
        ok = (stops.tph >= 60 / thr - 1e-9).values
        visits = stops.tph[ok].sum() / stops.tph.sum()
        out[thr] = {"visits": round(visits * 100, 1), "area": round(area(ok), 1)}
    return out


out = Path(sys.argv[1])
args = sys.argv[2:]
res = {}
for y, feed, date in zip(args[0::3], args[1::3], args[2::3]):
    res[y] = run(feed, date)
    print(y, res[y])
trend = {"covered": {y: res[y]["covered"] for y in res}}
for thr in THRS:
    trend[str(thr)] = {y: res[y][thr] for y in res}
out.write_text(json.dumps(trend, separators=(",", ":")))
