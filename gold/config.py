from pathlib import Path
import datetime as dt
import calendar

AZ_CONTAINER = "gold"

TIMEFRAME_FILES = {
    "m":  "M.csv",
    "d":  "D.csv",
    "h1": "1h.csv",
    "4h": "4h.csv",
    "W":  "W.csv"  # Adding weekly timeframe as well
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

# Current date information for calculations
today = dt.date.today()
current_year = today.year
current_month = today.month
current_day = today.day

# Set cutoff date - use data only through February 2025 (exclude March 2025)
cutoff_month = 2  # February
cutoff_year = 2025

# Define the cutoff date (last day with available data)
# Using February 28, 2025 as the cutoff - excluding March 2025
cutoff_date = dt.date(cutoff_year, cutoff_month, 28)

# Calculate complete year based on cutoff date
complete_year = cutoff_year if cutoff_month == 12 else cutoff_year - 1
current_decade_start = current_year - (current_year % 10)

# Standard presets (used as fallback) - use complete periods through February 2025
STANDARD_PRESETS = {
    "1Y": (cutoff_date - dt.timedelta(days=365), cutoff_date),  # Full year ending at cutoff date
    "3Y": (cutoff_date - dt.timedelta(days=365*3), cutoff_date),  # 3 years ending at cutoff date
    "5Y": (cutoff_date - dt.timedelta(days=365*5), cutoff_date),  # 5 years ending at cutoff date
    "10Y": (cutoff_date - dt.timedelta(days=365*10), cutoff_date),  # 10 years ending at cutoff date
    "Full":(dt.date(1974,12,1), cutoff_date)  # All data up to cutoff date
}

# Calculate presidential cycle - find most recent completed cycle
# Only consider complete years (up to 2024 if current is 2025)
last_election_year = complete_year
while (last_election_year % 4) != 0 or last_election_year > complete_year:
    last_election_year -= 1

prev_election_year = last_election_year - 4
prev_prev_election_year = prev_election_year - 4

# Presidential cycle presets (4-year cycles)
# Don't create cycles with just 1 year (e.g., 2024-2024)
PRESIDENTIAL_PRESETS = {}

# Only add the current cycle if we have at least 2 years of data
if complete_year - last_election_year >= 1:
    PRESIDENTIAL_PRESETS[f"Current Cycle ({last_election_year}-{complete_year})"] = \
        (dt.date(last_election_year, 1, 1), cutoff_date)

# Always add the previous complete cycle
PRESIDENTIAL_PRESETS[f"Previous Cycle ({prev_election_year}-{last_election_year})"] = \
    (dt.date(prev_election_year, 1, 1), dt.date(last_election_year, 12, 31))

# Add multi-cycle options
PRESIDENTIAL_PRESETS[f"Two Cycles ({prev_election_year}-{complete_year})"] = \
    (dt.date(prev_election_year, 1, 1), cutoff_date)

PRESIDENTIAL_PRESETS[f"Three Cycles ({prev_prev_election_year}-{complete_year})"] = \
    (dt.date(prev_prev_election_year, 1, 1), cutoff_date)

PRESIDENTIAL_PRESETS["Full Presidential History"] = \
    (dt.date(1974,12,1), cutoff_date)

# Function to get start of quarter
def quarter_start(year, quarter):
    return dt.date(year, 3*quarter-2, 1)

# Function to get end of quarter
def quarter_end(year, quarter):
    next_q_month = 3*quarter+1 if quarter < 4 else 1
    next_q_year = year if quarter < 4 else year+1
    end = dt.date(next_q_year, next_q_month, 1) - dt.timedelta(days=1)
    return end

# Use complete year for quarters (not the partial current year)
# For 2025, this would use 2024 Q1-Q4 data instead of partial 2025 data
last_complete_year = complete_year 

# Find the most recent complete quarter based on cutoff date (Feb 2025)
if cutoff_month <= 3:
    # If cutoff is in Q1, use Q4 of previous year
    last_complete_q = 4
    last_complete_q_year = cutoff_year - 1
elif cutoff_month <= 6:
    # If cutoff is in Q2, use Q1 of cutoff year
    last_complete_q = 1
    last_complete_q_year = cutoff_year
elif cutoff_month <= 9:
    # If cutoff is in Q3, use Q2 of cutoff year
    last_complete_q = 2
    last_complete_q_year = cutoff_year
else:
    # If cutoff is in Q4, use Q3 of cutoff year
    last_complete_q = 3
    last_complete_q_year = cutoff_year

# Since our cutoff is Feb 2025 (Q1), last complete quarter is Q4 2024

# Previous complete quarter
prev_complete_q = last_complete_q - 1 if last_complete_q > 1 else 4
prev_complete_q_year = last_complete_q_year if last_complete_q > 1 else last_complete_q_year - 1

# Quarter presets (3-month periods) - use complete quarters only
QUARTER_PRESETS = {
    f"Recent Q{last_complete_q} {last_complete_q_year}": 
        (quarter_start(last_complete_q_year, last_complete_q), 
         quarter_end(last_complete_q_year, last_complete_q)),
    f"Previous Q{prev_complete_q} {prev_complete_q_year}": 
        (quarter_start(prev_complete_q_year, prev_complete_q),
         quarter_end(prev_complete_q_year, prev_complete_q)),
    f"Year {last_complete_year} Q{last_complete_q}": 
        (quarter_start(last_complete_year, last_complete_q), 
         quarter_end(last_complete_year, last_complete_q)),
    f"Full Year {last_complete_year}": 
        (dt.date(last_complete_year, 1, 1), dt.date(last_complete_year, 12, 31)),
    f"Full Year {last_complete_year-1}": 
        (dt.date(last_complete_year-1, 1, 1), dt.date(last_complete_year-1, 12, 31)),
    "Last 5 Complete Years": 
        (dt.date(last_complete_year-4, 1, 1), dt.date(last_complete_year, 12, 31))
}

# Month presets (ensure at least 1 year of data) - use data through February 2025
MONTH_PRESETS = {
    f"Last Complete Year {last_complete_year}": 
        (dt.date(last_complete_year, 1, 1), dt.date(last_complete_year, 12, 31)),
    f"Previous Year {last_complete_year-1}": 
        (dt.date(last_complete_year-1, 1, 1), dt.date(last_complete_year-1, 12, 31)),
    "Last 12 Complete Months": 
        (cutoff_date - dt.timedelta(days=365), cutoff_date),
    "Last 5 Complete Years": 
        (dt.date(cutoff_year-5, 1, 1), cutoff_date),
    "Full History": 
        (dt.date(1974, 1, 1), cutoff_date),
}

# Week of Year presets (ensure at least 1 year of data) - use complete years only
WEEK_OF_YEAR_PRESETS = {
    f"Complete Year {last_complete_year}": 
        (dt.date(last_complete_year, 1, 1), dt.date(last_complete_year, 12, 31)),
    f"Previous Year {last_complete_year-1}": 
        (dt.date(last_complete_year-1, 1, 1), dt.date(last_complete_year-1, 12, 31)),
    "Last 12 Complete Weeks": 
        (cutoff_date - dt.timedelta(weeks=12), cutoff_date),
    "Last 52 Complete Weeks": 
        (cutoff_date - dt.timedelta(weeks=52), cutoff_date),
}

# Week of Month presets (ensure at least 1 month of data) - use complete weeks and months
WEEK_OF_MONTH_PRESETS = {
    "Last 12 Complete Months": 
        (cutoff_date - dt.timedelta(days=365), cutoff_date),
    "Last 6 Complete Months": 
        (cutoff_date - dt.timedelta(days=180), cutoff_date),
    "Last 3 Complete Months": 
        (cutoff_date - dt.timedelta(days=90), cutoff_date),
    "Last 2 Complete Months": 
        (cutoff_date - dt.timedelta(days=60), cutoff_date),
}

# Day of week presets - use data through February 2025
DAY_OF_WEEK_PRESETS = {
    "Last 4 Complete Weeks": 
        (cutoff_date - dt.timedelta(days=28), cutoff_date),
    "Last 12 Complete Weeks": 
        (cutoff_date - dt.timedelta(weeks=12), cutoff_date),
    "Last 26 Complete Weeks": 
        (cutoff_date - dt.timedelta(weeks=26), cutoff_date),
    "Last 52 Complete Weeks": 
        (cutoff_date - dt.timedelta(weeks=52), cutoff_date),
}

# Decade-based presets for decennial profile - use data through February 2025
DECENNIAL_PRESETS = {
    f"{current_year-10}-{current_year}": (dt.date(current_year-10, 1, 1), cutoff_date),
    f"{current_year-20}-{current_year-10}": (dt.date(current_year-20, 1, 1), dt.date(current_year-10, 12, 31)),
    f"{current_year-30}-{current_year-20}": (dt.date(current_year-30, 1, 1), dt.date(current_year-20, 12, 31)),
    f"{current_year-40}-{current_year-30}": (dt.date(current_year-40, 1, 1), dt.date(current_year-30, 12, 31)),
    f"{current_year-50}-{current_year-40}": (dt.date(current_year-50, 1, 1), dt.date(current_year-40, 12, 31)),
    "Full Decennial History": (dt.date(1974,12,1), cutoff_date)
}

# Default presets for session profile (standard presets)
SESSION_PRESETS = STANDARD_PRESETS

# Combined presets dictionary (for backward compatibility)
PRESETS = {**STANDARD_PRESETS}

# Profile-specific presets mapping
PROFILE_PRESETS = {
    "decennial": DECENNIAL_PRESETS,
    "presidential": PRESIDENTIAL_PRESETS,
    "quarter": QUARTER_PRESETS,
    "month": MONTH_PRESETS,
    "week_of_year": WEEK_OF_YEAR_PRESETS,
    "week_of_month": WEEK_OF_MONTH_PRESETS,
    "day_of_week": DAY_OF_WEEK_PRESETS,
    "session": SESSION_PRESETS,
}

# Define profile-specific defaults
PROFILE_DEFAULT_PRESET = {
    "decennial":     f"{current_year-10}-{current_year}",
    "presidential":  f"Current Cycle ({last_election_year}-{complete_year})",
    "quarter":       f"Recent Q{last_complete_q} {last_complete_q_year}",
    "month":         f"Full Year {last_complete_year}",  # Use complete year
    "week_of_year":  f"Full Year {last_complete_year}",  # Use complete year
    "week_of_month": f"Last 12 Months",
    "day_of_week":   "Last 4 Weeks",
    "session":       "1Y",
}

# Profile minimum required time periods
PROFILE_MIN_PERIODS = {
    "decennial": 10*365,      # 10 years in days
    "presidential": 4*365,   # 4 years in days
    "quarter": 3*30,         # 3 months in days
    "month": 365,            # 1 year in days
    "week_of_year": 365,     # 1 year in days
    "week_of_month": 30,     # 1 month in days
    "day_of_week": 7,        # 1 week in days
    "session": 7,            # 1 week in days
}

# Create a mapping of readable profile names
PROFILE_DISPLAY_NAMES = {
    "decennial": "Decennial Profile",
    "presidential": "Presidential Profile",
    "quarter": "Annual Quarter Profile",
    "month": "Monthly Profile",
    "week_of_year": "Weekly Profiles (Year)",
    "week_of_month": "Weekly Profiles (Month)",
    "day_of_week": "Daily Profiles",
    "session": "Session Profiles",
}

# Cache directory setup
CACHE_DIR = Path.home() / ".gold_cache"
CACHE_DIR.mkdir(exist_ok=True)
