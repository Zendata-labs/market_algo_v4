import streamlit as st, pandas as pd, plotly.express as px, pathlib, sys
sys.path.append(str(pathlib.Path(__file__).parent))

from gold import config
from gold.azure import load_csv
from gold.profiles import BUILDERS

st.set_page_config(page_title="Gold Profiles", layout="wide")
st.title("🥇 Gold Cyclical Profiles")

profile_key = st.sidebar.selectbox("Profile", list(BUILDERS.keys()), 3)
metric      = st.sidebar.radio("Metric",
               ["Average Return", "ATR points", "ATR level", "Probability"], 0)
preset      = st.sidebar.selectbox("Preset", list(config.PRESETS.keys()), 0)
s_def, e_def = config.PRESETS[preset]
start       = st.sidebar.date_input("Start", s_def)
end         = st.sidebar.date_input("End",   e_def)
if start > end:
    st.error("Start date after End"); st.stop()

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
                 color_discrete_map="identity")
elif metric == "ATR points":
    q = df["AvgRange"].quantile([0, .33, .66, 1]).values
    df["band"] = df["AvgRange"].apply(
        lambda v: "Low" if v<=q[1] else "Avg" if v<=q[2] else "High")
    fig = px.bar(df, x=x, y="AvgRange", color="band",
                 color_discrete_map={"Low":"green","Avg":"orange","High":"red"})
elif metric == "ATR level":
    q = df["AvgRange"].quantile([0, .33, .66, 1]).values
    df["lvl"] = df["AvgRange"].apply(lambda v: 1 if v<=q[1] else 2 if v<=q[2] else 3)
    fig = px.bar(df, x=x, y="lvl", color="lvl",
                 color_discrete_map={1:"green",2:"orange",3:"red"})
else:
    fig = px.bar(df, x=x, y=["ProbGreen","ProbRed"], barmode="group",
                 color_discrete_map={"ProbGreen":"green","ProbRed":"red"})
fig.update_layout(xaxis_title="", yaxis_title="")
st.plotly_chart(fig, use_container_width=True)
