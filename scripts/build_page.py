"""Assemble the explorer page: replace __DATA__ in the template with {year: prep_ref.py JSON}.

Usage: python3 -I build_page.py <template.html> <out.html> <year=data.json> [<year=data.json> ...] [trend=trend.json]
"""
import json
import sys
from pathlib import Path

tpl, out = Path(sys.argv[1]), Path(sys.argv[2])
years, trend = {}, {}
for a in sys.argv[3:]:
    y, f = a.split("=", 1)
    if y == "trend":
        trend = json.loads(Path(f).read_text())
    else:
        years[y] = json.loads(Path(f).read_text())
blob = json.dumps(years, separators=(",", ":"))
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(tpl.read_text().replace("__DATA__", blob).replace("__TREND__", json.dumps(trend, separators=(",", ":"))))
print("wrote", out, out.stat().st_size, "bytes")
