import json, sys
import numpy as np
W = {"mt": 4, "fr": 1, "sa": 1, "su": 1}; DH = 0.10
def load(p):
    D = json.load(open(p))
    for r in D["routes"]:
        r["tph"] = {}
        for dt, d in r["d"].items():
            s = [np.convolve(np.array(d[k], float), np.ones(3) / 3, "same") for k in ("s0", "s1")]
            r["tph"][dt] = (s[0] + s[1]) / 2 if len(r["dirs"]) == 2 else s[int(r["dirs"][0])]
    return D
def split(D, thr, f):
    o = dict(Rb=0, Rl=0, Cb=0, Cl=0)
    for r in D["routes"]:
        if r["mode"] == "school": continue
        k = "l" if r["mode"] == "ctrain" else "b"; w = (1 + DH) * (f if k == "l" else 1)
        for dt in W:
            m = np.array(r["d"][dt]["m"]); fr = r["tph"][dt] >= 60 / thr - 1e-9
            o["R" + k] += m[fr].sum() * W[dt] * w / 60; o["C" + k] += m[~fr].sum() * W[dt] * w / 60
    o["R"] = o["Rb"] + o["Rl"]; o["C"] = o["Cb"] + o["Cl"]; o["T"] = o["R"] + o["C"]; return o
runs = [(a, load(b)) for a, b in zip(sys.argv[1::2], sys.argv[2::2])]
print("year thr | bus-only freq share | combined share @ CTrain 2.0 / 2.5 / 3.0")
for thr in (10, 15, 20):
    for name, D in runs:
        b = split(D, thr, 1.0)
        c = [split(D, thr, f) for f in (2.0, 2.5, 3.0)]
        print(name, thr, f"{b['Rb']/(b['Rb']+b['Cb'])*100:5.1f}%", " / ".join(f"{x['R']/x['T']*100:5.1f}%" for x in c))
print()
for name, D in runs:
    bus = sum(r["wkh"] for r in D["routes"] if r["mode"] == "bus"); rail = sum(r["wkh"] for r in D["routes"] if r["mode"] == "ctrain")
    b10 = split(D, 10, 1.0)["Rb"] / (1 + DH); b15 = split(D, 15, 1.0)["Rb"] / (1 + DH)
    print(name, "bus rev hrs", round(bus), "| CTrain train-hrs", round(rail), "| bus hrs at <=10min", round(b10), "| <=15min", round(b15))
