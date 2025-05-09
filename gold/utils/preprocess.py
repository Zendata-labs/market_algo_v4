
import pandas as pd

def trim_extremes(df, date_col='Date'):
    """Remove rows that belong to the first or last *calendar day* available in the DataFrame.

    Also removes any rows whose date is in March 2025, as requested.

    Parameters
    ----------
    df : pd.DataFrame
    date_col : str

    Returns
    -------
    pd.DataFrame
    """
    if date_col not in df.columns:
        return df

    ser = pd.to_datetime(df[date_col], errors='coerce')
    if ser.isnull().all():
        return df

    first_day = ser.min().date()
    last_day  = ser.max().date()

    mask = ~ser.dt.date.isin([first_day, last_day])
    # drop March 2025 rows
    march25 = (ser.dt.year == 2025) & (ser.dt.month == 3)
    mask &= ~march25

    return df.loc[mask].copy()
