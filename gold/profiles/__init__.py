from importlib import import_module
BUILDERS = {}

for name in [
    "decennial", "presidential", "quarter", "month",
    "week_of_year", "week_of_month", "day_of_week", "session"
]:
    BUILDERS[name] = import_module(f"gold.profiles.{name}").build