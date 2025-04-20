from pathlib import Path
import datetime as dt

AZ_CONTAINER = "gold"

TIMEFRAME_FILES = {
    "m":  "M.csv",
    "d":  "D.csv",
    "h1": "1h.csv"
}

PROFILE_SOURCE = {
    "decennial":     "m",
    "presidential":  "m",
    "quarter":       "m",
    "month":         "m",
    "week_of_year":  "d",
    "week_of_month": "d",
    "day_of_week":   "d",
    "session":       "h1",
}

CACHE_DIR = Path.home() / ".gold_cache"
CACHE_DIR.mkdir(exist_ok=True)

PRESETS = {
    "1Y":  (dt.date.today()-dt.timedelta(days=365),     dt.date.today()),
    "5Y":  (dt.date.today()-dt.timedelta(days=365*5),   dt.date.today()),
    "15Y": (dt.date.today()-dt.timedelta(days=365*15),  dt.date.today()),
    "Full":(dt.date(1974,12,1), dt.date.today())
}
