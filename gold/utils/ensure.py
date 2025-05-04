import pandas as pd

def ensure(df, col, buckets):
    if df.empty or col not in df.columns:
        base = pd.DataFrame({col: buckets})
        for c in ["ProbGreen","ProbRed","AvgReturn","AvgRange"]:
            base[c] = 0
        base["Label"] = base[col]
        return base
    full = pd.DataFrame({col: buckets})
    return full.merge(df, on=col, how="left").fillna(0)
