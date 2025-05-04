# Gold Cyclical Profiles – Calculation Logic

This document explains **exactly** how every metric in the dashboard is computed.
Share it with stakeholders so they can audit, replicate, or extend the
calculations.

---

## 1  Input Data

All profiles are derived from continuous‐contract futures data
(`M.csv`, `D.csv`, `1h.csv`) downloaded from Azure Blob Storage.  
Columns used:

| Column | Purpose |
|--------|---------|
| `Date` | Timestamp in UTC (no timezone offset is applied **except** for the *Session* profile) |
| `Open`, `High`, `Low`, `Close` | Price series used for ranges and returns |

> **Note** Thousands separators are stripped and values are coerced to `float`
before any calculation.

## 2  Core Helpers

| Helper | Location | Formula |
|--------|----------|---------|
| `bar_range(df)` | `gold/metrics/range.py` | `High − Low` per bar |
| `pct(df)` | `gold/metrics/ret.py` | `(Close − Open) ÷ Open` |
| `flag(df)` | `gold/metrics/color.py` | `True` if `Close ≥ Open`, else `False` |
| `probs(series)` | `gold/metrics/color.py` | Share of green / red bars (`mean`, `1 − mean`) |

Every profile uses these helpers, so behaviour is **identical** across
timeframes.

## 3  Profiles & Bucketing Rules

| Profile | File | Bucket expression | Buckets |
|---------|------|-------------------|---------|
| **Decennial** | `gold/profiles/decennial.py` | `year % 10` | 0‑9 |
| **Presidential** | `gold/profiles/presidential.py` | `(year % 4) + 1` | 1‑4 = Year 1…4 of US presidential cycle |
| **Quarter** | `gold/profiles/quarter.py` | `quarter` | 1‑4 |
| **Month** | `gold/profiles/month.py` | `month` | 1‑12 |
| **Week of Year** | `gold/profiles/week_of_year.py` | `isocalendar().week` | 1‑53 |
| **Week of Month** | `gold/profiles/week_of_month.py` | `(((day − 1) // 7) + 1)` | 1‑5 |
| **Day of Week** | `gold/profiles/day_of_week.py` | `weekday + 1` | 1=Mon…5=Fri |
| **Session** | `gold/profiles/session.py` | NYSE *open day* `weekday + 1` (UTC→America/New_York) | 1‑5 |

Each profile’s `build()` function:

1. Filters the input dataframe to the selected *Start/End* range.
2. Computes the **Bucket** as described above.
3. Adds `Range`, `Ret`, and `Flag`.
4. Aggregates by bucket:
   * `ProbGreen`, `ProbRed` – proportion of green/red bars.
   * `AvgReturn` – mean of `Ret`.
   * `AvgRange` – mean of `Range`.
5. Fills missing buckets with zeros (via `gold.utils.ensure`).

## 4  Dashboard Metrics

| Metric | Chart | Computation |
|--------|-------|-------------|
| *Average Return* | Bar height = `AvgReturn`; bar colour = green if `>0` else red |
| *ATR points* | Bar height = `AvgRange`; colour banding based on tertiles |
| *ATR level* | Bar height = categorical 1 (Low), 2 (Avg), 3 (High) derived from tertiles |
| *Probability* | Stacked bars showing `ProbGreen` vs. `ProbRed` |

## 5  Barcode Cycle

Beneath the main chart a one‑pixel‑high “barcode” is rendered:

* Each column corresponds to a bucket (month, week, etc.).
* Green = positive `AvgReturn`, red = negative.
* Useful for a **quick glance** alignment check.  
  (e.g. April 2025 → month 4 = green if the average return is positive.)

## 6  Date Handling

* The date picker enforces US format **MM/DD/YYYY** to avoid confusion
  (`st.date_input(format="MM/DD/YYYY")`).
* Internally everything is converted to `pd.Timestamp` **without**
  timezone offsets – except the *Session* profile which is explicitly
  converted to **America/New_York** to obtain the correct trading day.

## 7  Caching & Performance

* CSVs are cached locally as Parquet files in `~/.gold_cache`.
* Streamlit’s `@st.cache_data` memoises the cleaned dataframe.
* Plotly figures are lightweight (<1 k points) and render instantly.

---
© Market Algo 2025
