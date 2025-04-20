def bar_range(df):
    return df["High"].astype(float) - df["Low"].astype(float)
