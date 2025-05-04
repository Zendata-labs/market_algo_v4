def flag(df):
    return (df["Close"].astype(float) - df["Open"].astype(float)).gt(0).astype(float)

def probs(flags):
    tot = flags.count()
    return (flags.sum()/tot if tot else 0,
            1 - (flags.sum()/tot) if tot else 0)
