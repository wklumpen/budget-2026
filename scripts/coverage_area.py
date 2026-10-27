"""Coverage area: dissolved 800 m (and 400 m) buffers around stops, by service level.

Usage: python3 -I coverage_area.py <label> <feed_dir> <YYYYMMDD ref Tuesday> [<label> <feed_dir> <date> ...]
Stops are those with weekday service on the reference date (school specials excluded).
Service level at a stop = mean trips per hour over the weekday midday window (10:00-15:00).
Radius "hybrid" uses 800 m around CTrain stops and 400 m around bus stops. Areas are in km^2, from a local equirectangular projection (fine at Calgary's scale).
"""
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import shapely

MIDDAY = range(10, 15)
LEVELS = [("any weekday service", None), ("any midday service", 0.0), ("20 min or better midday", 3), ("15 min or better midday", 4), ("10 min or better midday", 6)]


def active(feed, date):
    dt = datetime.strptime(date, "%Y%m%d")
    wd = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"][dt.weekday()]
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


def run(label, feed, date):
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
    rail_ids = set(r[r.route_type == "0"].route_id)
    rail_trips = set(t[t.route_id.isin(rail_ids)].trip_id)
    rail_stops = set(st[st.trip_id.isin(rail_trips)].stop_id)
    is_rail = stops.stop_id.isin(rail_stops).values
    lat0, lon0 = 51.05, -114.07
    x = (stops.lon - lon0) * 111320 * np.cos(np.radians(lat0))
    y = (stops.lat - lat0) * 110574
    pts = shapely.points(np.column_stack([x, y]))
    print(f"== {label} (stops with weekday service: {len(stops)})")
    base = {}
    for radius in (800, 400, "hybrid"):
        rad = np.where(is_rail, 800, 400) if radius == "hybrid" else np.full(len(stops), float(radius))
        print(f"  radius {radius}" + (" (CTrain stops 800 m, bus stops 400 m)" if radius == "hybrid" else " m"))
        for name, thr in LEVELS:
            if thr is None:
                m = np.ones(len(stops), bool)
            elif thr == 0.0:
                m = (stops.tph > 0).values
            else:
                m = (stops.tph >= thr).values
            area = shapely.union_all(shapely.buffer(pts[m], rad[m], quad_segs=8)).area / 1e6
            base.setdefault(radius, area if thr is None else base[radius])
            print(f"     {name:26s} {m.sum():5d} stops  {area:7.1f} km2  ({area / base[radius] * 100:5.1f}% of any-weekday area)")


args = sys.argv[1:]
for label, feed, date in zip(args[0::3], args[1::3], args[2::3]):
    run(label, feed, date)
