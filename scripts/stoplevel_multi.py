import sys, pandas as pd, numpy as np
from datetime import datetime
from pathlib import Path
def active(feed, date):
    dt = datetime.strptime(date, "%Y%m%d"); wd = ["monday","tuesday","wednesday","thursday","friday","saturday","sunday"][dt.weekday()]
    a = set(); p = feed / "calendar.txt"
    if p.exists():
        c = pd.read_csv(p, dtype=str); c = c[(c.start_date <= date) & (c.end_date >= date) & (c[wd] == "1")]; a |= set(c.service_id)
    cd = pd.read_csv(feed / "calendar_dates.txt", dtype=str); cd = cd[cd.date == date]
    a |= set(cd[cd.exception_type == "1"].service_id); a -= set(cd[cd.exception_type == "2"].service_id); return a
def run(feed, date, label):
    feed = Path(feed)
    t = pd.read_csv(feed / "trips.txt", dtype=str, usecols=["route_id", "service_id", "trip_id"])
    r = pd.read_csv(feed / "routes.txt", dtype=str)
    n = pd.to_numeric(r.route_short_name, errors="coerce")
    keep = r[~((r.route_type == "3") & n.between(600, 899))].route_id  # drop school specials
    t = t[t.service_id.isin(active(feed, date)) & t.route_id.isin(keep)]
    st = pd.read_csv(feed / "stop_times.txt", usecols=["trip_id", "stop_id", "departure_time"], dtype=str)
    st = st[st.trip_id.isin(set(t.trip_id))]
    h = st.departure_time.str.split(":").str[0].astype(int)
    out = {}
    for name, hrs in (("midday 10-15", range(10, 15)), ("evening 19-22", range(19, 22))):
        s = st[h.isin(list(hrs))]
        per = s.groupby("stop_id").size() / len(list(hrs))   # trips per hour at each stop
        allstops = st.stop_id.nunique()
        res = {}
        for thr, lab in ((6, "10min"), (4, "15min"), (3, "20min")):
            ok = per >= thr
            res[lab] = (ok.sum() / allstops, per[ok].sum() / per.sum())
        out[name] = (res, allstops, len(per))
    print(f"== {label}: {len(t)} trips, {out['midday 10-15'][1]} stops with any weekday service")
    for name, (res, _, nserved) in out.items():
        print(f"  {name}: stops served in window {nserved}")
        for lab, (sh_stops, sh_visits) in res.items():
            print(f"     >= every {lab}: {sh_stops*100:5.1f}% of stops | {sh_visits*100:5.1f}% of stop-visits")
for label, feed, date in zip(sys.argv[1::3], sys.argv[2::3], sys.argv[3::3]):
    run(feed, date, label)
