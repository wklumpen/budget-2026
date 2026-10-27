#!/usr/bin/env bash
# Rebuild every dataset, the explorer page and the comparison results from the three feeds.
# Feeds are unpacked into their own folders; scripts run with python -I so nothing in a feed folder can be imported.
set -euo pipefail
PY="${PY:-python3}"
cd "$(dirname "$0")"
for y in 2016 2019 2026; do mkdir -p "feeds/$y" && unzip -o -q "feeds/cgy-fall-$y.zip" -d "feeds/$y"; done
mkdir -p data results docs

"$PY" -I scripts/prep_ref.py feeds/2016 data/data2016.json 20161018 20161021 20161022 20161023 --geom \
  --label "Calgary Transit GTFS, fall 2016 signup"
"$PY" -I scripts/prep_ref.py feeds/2019 data/data2019.json 20191022 20191025 20191026 20191027 --geom \
  --label "Calgary Transit GTFS, fall 2019 signup"
"$PY" -I scripts/prep_ref.py feeds/2026 data/data2026.json 20261103 20261106 20261107 20261108 --geom \
  --label "Calgary Transit GTFS, MobilityDatabase mdb-712, published 2026-10-14" \
  --period "Regular service effective 2026-10-13 to 2026-12-20"

"$PY" -I scripts/trend_json.py data/trend.json 2016 feeds/2016 20161018 2019 feeds/2019 20191022 2026 feeds/2026 20261103

"$PY" -I scripts/build_page.py page/template.html docs/index.html 2016=data/data2016.json 2019=data/data2019.json 2026=data/data2026.json trend=data/trend.json

"$PY" -I scripts/compare3.py 2016 data/data2016.json 2019 data/data2019.json 2026 data/data2026.json > results/route_level.txt
"$PY" -I scripts/stoplevel_multi.py "2016 Tue 18 Oct" feeds/2016 20161018 "2019 Tue 22 Oct" feeds/2019 20191022 "2026 Tue 3 Nov" feeds/2026 20261103 > results/stop_level.txt
"$PY" -I scripts/coverage_area.py 2016 feeds/2016 20161018 2019 feeds/2019 20191022 2026 feeds/2026 20261103 > results/coverage_area.txt
echo "done: see results/ and docs/index.html"
