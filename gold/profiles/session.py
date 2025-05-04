import pandas as pd
from gold.metrics.range import bar_range
from gold.metrics.ret   import pct
from gold.metrics.color import flag, probs
from gold.utils.ensure  import ensure
from gold.utils import labels as L

BUCKETS = list(range(1,6))
def lab(v): return L.dow(v)

def build(df, start, end):
    df = df.copy()
    df["Date"] = pd.to_datetime(df["Date"])
    df = df[(df["Date"]>=start) & (df["Date"]<=end)]

    local = df["Date"].dt.tz_localize("UTC").dt.tz_convert("America/New_York")
    df["Bucket"] = local.dt.weekday + 1
    df = df[df["Bucket"]<=5]

    df["Range"] = bar_range(df)
    df["Ret"]   = pct(df)
    df["Flag"]  = flag(df)

    rows = []
    for k, g in df.groupby("Bucket"):
        pg, pr = probs(g["Flag"])
        rows.append({"Bucket":k,"Label":lab(k),
                     "ProbGreen":pg*100,"ProbRed":pr*100,
                     "AvgReturn":g["Ret"].mean(),
                     "AvgRange":g["Range"].mean()})
    out = pd.DataFrame(rows)
    out = ensure(out, "Bucket", BUCKETS)
    out["Label"] = out["Bucket"].apply(lab)
    return out.sort_values("Bucket")