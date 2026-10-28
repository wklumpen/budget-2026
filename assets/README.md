# Presentation assets

PNG (1.2x) and SVG of each chart and map, built by `scripts/make_assets.py` (Altair, fonts in `scripts/fonts`, both OFL). Regenerate with `./run_all.sh` or `python3 -I scripts/make_assets.py assets`.

Same method as the explorer page: frequent = every 10 minutes or better (15 for the second set of trend charts), CTrain at 2.5x bus hours, 10% deadhead, school specials excluded. Supply, not ridership.

| File | Shows |
| --- | --- |
| 01_headline_split_2026 | Frequency vs coverage share of weekly hours, fall 2026 |
| 02_split_by_year | The same split for 2016, 2019 and 2026, left/right aligned |
| 03_trend_{visits,area,hours}_{10,15}min | Stop-visits, footprint and bus hours at 10 and 15 minutes |
| 04_time_of_day_2026 | Weekday hours by clock hour, frequency vs coverage |
| 05_threshold_sensitivity | Frequency share by threshold (10 to 30 min), three years |
| 06_map_2026_noon | Network at noon, coloured by job |
| 07_map_years_noon | The network at noon in 2016, 2019 and 2026 |
| 08_map_2026_noon_vs_9pm | Same network at noon and 9 pm |
