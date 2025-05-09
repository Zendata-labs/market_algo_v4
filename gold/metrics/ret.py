def pct(df):
    return (df["Close"].astype(float) - df["Open"].astype(float)) \
           / df["Open"].astype(float) * 100
