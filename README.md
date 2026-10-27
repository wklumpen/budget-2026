# Calgary Transit's Two Jobs

An interactive explorer that sorts Calgary Transit's published bus and CTrain schedules into two jobs: a frequent network (judged on ridership) and a coverage network (judged on who it reaches). Fall 2016, 2019 and 2026 schedules.

Open `dist/two-jobs.html` in a browser. Rebuild with `./run_all.sh` (needs unzip, python3, pandas, numpy, shapely>=2).

## Data and attribution

Schedules are Calgary Transit GTFS feeds (fall 2016, fall 2019 and fall 2026, the last via MobilityDatabase `mdb-712`), published by The City of Calgary. Contains information licensed under the City of Calgary's Open Data Licence. Check the current licence terms before reuse.

This is an independent analysis. It is not an official Calgary Transit figure, and it measures scheduled service supplied, not ridership.
