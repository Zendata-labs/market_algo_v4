
import pandas as pd
from datetime import datetime
from zoneinfo import ZoneInfo

def _ordinal(value, total):
    return f"{value} of {total}"

def compute_positions(now=None):
    """Return a DataFrame with current position for each profile.

    Parameters
    ----------
    now : datetime, optional
        Point in time to evaluate in America/New_York tz. Defaults to current time.

    Returns
    -------
    pd.DataFrame with columns [Profile, Position]
    """
    if now is None:
        now = datetime.now(ZoneInfo("America/New_York"))
    rows = []

    # Decennial (10‑yr cycle)
    dec_pos = (now.year % 10) + 1                           # 1‒10
    rows.append(("Decennial", _ordinal(dec_pos, 10)))

    # U.S. Presidential (4‑yr cycle starting 2021 = yr 1)
    pres_pos = ((now.year - 2021) % 4) + 1
    rows.append(("Presidential", _ordinal(pres_pos, 4)))

    # Quarter
    q_pos = ((now.month-1)//3) + 1
    rows.append(("Quarter", _ordinal(q_pos, 4)))

    # Month
    rows.append(("Month", _ordinal(now.month, 12)))

    # Week of Year
    wy_pos = now.isocalendar().week
    rows.append(("Week Of Year", _ordinal(wy_pos, 52)))

    # Week of Month (Mon‑based)
    wom_pos = ((now.day-1)//7) + 1
    rows.append(("Week Of Month", _ordinal(wom_pos, 4)))

    # Day of Week (Mon=1)
    dow_pos = now.isoweekday()
    rows.append(("Day Of Week", _ordinal(dow_pos, 5)))

    # Session (Asia, London, NY)
    hour = now.hour
    if 17 <= hour or hour < 0:        # 5pm‑midnight
        sess = 1
        tot  = 3
    elif 0 <= hour < 8:               # 12am‑8am
        sess = 2
        tot  = 3
    else:                             # 8am‑4pm
        sess = 3
        tot  = 3
    rows.append(("Session", _ordinal(sess, tot)))

    out = pd.DataFrame(rows, columns=["Profile", "Position"])
    return out
