import pandas as pd
import numpy as np
from gold.metrics.range import bar_range
from gold.metrics.ret import pct
from gold.metrics.color import flag, probs
from gold.utils.ensure import ensure
from gold.utils import labels as L
from datetime import time

# Session buckets: 1-5 for weekdays, with sub-buckets for sessions
# 0.1 = Asia session, 0.2 = London session, 0.3 = NY session
BUCKETS = list(range(1, 6))  # Weekdays
SESSION_BUCKETS = [1, 2, 3]  # Session numbers (Asia, London, NY)
ALL_SESSIONS_BUCKET = 0      # Special bucket for combined view

# Session time ranges in ET (24-hour format)
# Asia: 4PM-12AM ET
# London: 12AM-8AM ET
# NY: 8AM-4PM ET
SESSION_TIMES = {
    1: (time(16, 0), time(23, 59)),   # Asia: 4PM-12AM
    2: (time(0, 0), time(7, 59)),      # London: 12AM-8AM
    3: (time(8, 0), time(15, 59))      # NY: 8AM-4PM
}

def session_label(session_num):
    """Return label for session number"""
    sessions = {1: "Asia", 2: "London", 3: "NY"}
    return sessions.get(session_num, str(session_num))

def dow_session_label(day, session):
    """Return label for day and session combination"""
    day_label = L.dow(day)
    session_label_str = session_label(session)
    return f"{day_label}-{session_label_str}"

def determine_session(hour):
    """Determine which session a given hour belongs to"""
    t = time(hour, 0)
    for session, (start, end) in SESSION_TIMES.items():
        # Handle sessions that cross midnight
        if start <= end:  # Normal case
            if start <= t <= end:
                return session
        else:  # Session crosses midnight
            if t >= start or t <= end:
                return session
    return None  # Should never happen if sessions cover 24 hours

def build(df, start, end, view="daily"):
    """Build session profile data
    
    Args:
        df: Dataframe with price data
        start: Start date
        end: End date
        view: 'daily' for 5-bar view (weekdays), 'combined' for 1-bar view
    """
    df = df.copy()
    df["Date"] = pd.to_datetime(df["Date"])
    df = df[(df["Date"] >= start) & (df["Date"] <= end)]
    
    if df.empty:
        return pd.DataFrame()
    
    # Convert to Eastern Time for session analysis
    local = df["Date"].dt.tz_localize("UTC").dt.tz_convert("America/New_York")
    df["Weekday"] = local.dt.weekday + 1  # 1-5 for Mon-Fri
    df["Hour"] = local.dt.hour
    
    # Assign session to each row
    df["Session"] = df["Hour"].apply(determine_session)
    
    # Calculate metrics for each row
    df["Range"] = bar_range(df)
    df["Ret"] = pct(df)
    df["Flag"] = flag(df)
    
    # Filter out weekends
    df = df[df["Weekday"] <= 5]
    
    rows = []
    
    if view == "daily":
        # For daily view, create entries for each day-session combination
        for (day, session), g in df.groupby(["Weekday", "Session"]):
            pg, pr = probs(g["Flag"])
            rows.append({
                "Bucket": day,
                "Session": session,
                "Label": dow_session_label(day, session),
                "DayLabel": L.dow(day),
                "SessionLabel": session_label(session),
                "ProbGreen": pg * 100,
                "ProbRed": pr * 100,
                "AvgReturn": g["Ret"].mean(),
                "AvgRange": g["Range"].mean()
            })
    else:  # combined view
        # For combined view, just create entries for each session
        for session, g in df.groupby("Session"):
            pg, pr = probs(g["Flag"])
            rows.append({
                "Bucket": ALL_SESSIONS_BUCKET,
                "Session": session,
                "Label": session_label(session),
                "SessionLabel": session_label(session),
                "ProbGreen": pg * 100,
                "ProbRed": pr * 100,
                "AvgReturn": g["Ret"].mean(),
                "AvgRange": g["Range"].mean()
            })
    
    # Create DataFrame and handle empty results
    out = pd.DataFrame(rows)
    
    if out.empty:
        # Create empty dataframe with expected columns
        cols = ["Bucket", "Session", "Label", "SessionLabel", 
                "ProbGreen", "ProbRed", "AvgReturn", "AvgRange"]
        if view == "daily":
            cols.append("DayLabel")
        return pd.DataFrame(columns=cols)
            
    return out