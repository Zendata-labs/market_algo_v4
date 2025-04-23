import streamlit as st, pandas as pd, plotly.express as px, pathlib, sys
sys.path.append(str(pathlib.Path(__file__).parent))

from gold import config
from gold.azure import load_csv
from gold.profiles import BUILDERS

st.set_page_config(page_title="Gold Profiles", layout="wide")
st.title("🥇 Gold Cyclical Profiles")
st.markdown("""Use the selectors in the sidebar to explore **gold's seasonality** across multiple
time‑based profiles (month, week of year, day of week, session, etc.).
The coloured **barcode** underneath the main chart gives you a quick visual of the cycle:
<span style='background:#2e7d32;color:white;padding:2px 6px;border-radius:4px'>green</span>
bars = average up months, <span style='background:#c62828;color:white;padding:2px 6px;border-radius:4px'>red</span>
bars = average down months.
""", unsafe_allow_html=True)

# --- Sidebar controls ----------------------------------------------------
profile_key = st.sidebar.selectbox("Profile", list(BUILDERS.keys()), 3)
metric      = st.sidebar.radio("Metric",
               ["Average Return", "ATR points", "ATR level", "Probability"], 0)
preset      = st.sidebar.selectbox("Preset", list(config.PRESETS.keys()), 0)
s_def, e_def = config.PRESETS[preset]

# date_input: allow both typing and clicking, fixed US format mm/dd/yyyy
start = st.sidebar.date_input("Start", s_def, format="MM/DD/YYYY", key="start_date")
end   = st.sidebar.date_input("End",   e_def, format="MM/DD/YYYY", key="end_date")
if start > end:
    st.error("Start date after End"); st.stop()

# ------------------------------------------------------------------------
blob_key = config.PROFILE_SOURCE[profile_key]
blob     = config.TIMEFRAME_FILES[blob_key]

@st.cache_data(show_spinner=f"Loading {blob} …")
def fetch(b):
    df = load_csv(b)[["Date","Open","High","Low","Close"]].copy()
    # strip thousands separator before numeric cast
    for col in ["Open","High","Low","Close"]:
        df[col] = df[col].astype(str).str.replace(",", "").astype(float)
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    return df.dropna()

raw   = fetch(blob)
build = BUILDERS[profile_key]
df    = build(raw, pd.Timestamp(start), pd.Timestamp(end))
if df.empty:
    st.info("No data in range"); st.stop()

x = "Label"
if metric == "Average Return":
    df["col"] = df["AvgReturn"].gt(0).map({True:"green", False:"red"})
    fig = px.bar(df, x=x, y="AvgReturn", color="col",
                 color_discrete_map="identity", height=400)
elif metric == "ATR points":
    q = df["AvgRange"].quantile([0, .33, .66, 1]).values
    df["band"] = df["AvgRange"].apply(
        lambda v: "Low" if v<=q[1] else "Avg" if v<=q[2] else "High")
    fig = px.bar(df, x=x, y="AvgRange", color="band",
                 color_discrete_map={"Low":"green","Avg":"orange","High":"red"}, height=400)
elif metric == "ATR level":
    q = df["AvgRange"].quantile([0, .33, .66, 1]).values
    df["lvl"] = df["AvgRange"].apply(lambda v: 1 if v<=q[1] else 2 if v<=q[2] else 3)
    fig = px.bar(df, x=x, y="lvl", color="lvl",
                 color_discrete_map={1:"green",2:"orange",3:"red"}, height=400)
else:
    fig = px.bar(df, x=x, y=["ProbGreen","ProbRed"], barmode="group",
                 color_discrete_map={"ProbGreen":"green","ProbRed":"red"}, height=400)
fig.update_layout(xaxis_title="", yaxis_title="")
st.plotly_chart(fig, use_container_width=True)

# --- Barcode cycle -------------------------------------------------------
# narrow coloured bar encoding AvgReturn direction
bc = px.imshow([df["AvgReturn"].apply(lambda v: 1 if v>0 else -1)],
               color_continuous_scale=["red","white","green"],
               aspect="auto")
bc.update_layout(
    coloraxis_showscale=False,
    xaxis=dict(showticklabels=False),
    yaxis=dict(showticklabels=False),
    margin=dict(l=0,r=0,t=0,b=0),
    height=50
)
st.plotly_chart(bc, use_container_width=True)
