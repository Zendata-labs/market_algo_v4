import streamlit as st, pandas as pd, plotly.express as px, plotly.graph_objects as go
from plotly.subplots import make_subplots
import pathlib, sys, datetime as dt, pytz
sys.path.append(str(pathlib.Path(__file__).parent))

from gold import config
from gold.azure import load_csv
from gold.seasonality import calculate_seasonality, generate_cumulative_returns, plot_seasonality
from gold.profiles import BUILDERS
from gold.date_ui import get_date_range_for_profile

st.set_page_config(page_title="Gold Profiles", layout="wide")
st.title("🥇 Gold Cyclical Profiles")

# Top-level tab organization
tab1, tab2, tab3, tab4 = st.tabs(["Current Market Position", "Cyclical Profiles", "Seasonality", "Candle Charts"])

# --- Sidebar controls ----------------------------------------------------
# Profile selection dropdown with display names
profile_options = list(config.PROFILE_DISPLAY_NAMES.keys())
profile_display_names = [config.PROFILE_DISPLAY_NAMES[k] for k in profile_options]
default_index = 3  # Default to 'month' profile

profile_display = st.sidebar.selectbox("Profile", profile_display_names, default_index)
profile_key = profile_options[profile_display_names.index(profile_display)]

# Metrics selection
metric = st.sidebar.radio("Metric", 
               ["Average Return", "ATR points", "ATR level", "Probability"], 0)

# Session profile specific options
session_view_mode = "daily"
session_filter = "All"

if profile_key == "session":
    # Add session-specific controls
    session_view_options = ["5-Bar (Weekdays)", "1-Bar (Combined)"]
    session_view_selection = st.sidebar.selectbox("View Mode", session_view_options, 0)
    session_view_mode = "daily" if session_view_selection == session_view_options[0] else "combined"
    
    # For the 1-bar view, add filter for red/green days
    if session_view_mode == "combined":
        session_filter = st.sidebar.radio("Filter by Day Type", ["All", "Green Days", "Red Days"], 0)

# Use the specialized date UI for this profile
start, end = get_date_range_for_profile(profile_key)

# Error handling for invalid dates
if start > end:
    st.error("Start date after End"); st.stop()
    
# --- Candle Charts Tab ------------------------------------------------------
with tab4:
    st.markdown("## Gold Candle Charts Analysis")
    
    # Create a more trading view like layout
    col1, col2 = st.columns([4, 1])
    
    with col2:
        st.markdown("### Chart Settings")
        
        # Timeframe buttons in a row for quick switching (TradingView style)
        st.markdown("**Timeframe:**")
        timeframe_cols = st.columns(5)
        
        timeframe_options = {
            "Monthly": "m",
            "Weekly": "W",
            "Daily": "d",
            "1h": "h1",
            "4h": "4h"
        }
        
        # Store the selected timeframe in session state if not already there
        if 'selected_timeframe_key' not in st.session_state:
            st.session_state['selected_timeframe_key'] = "d"  # Default to daily
            st.session_state['selected_timeframe_name'] = "Daily"
        
        # Create timeframe buttons
        if timeframe_cols[0].button("Monthly", use_container_width=True):
            st.session_state['selected_timeframe_key'] = "m"
            st.session_state['selected_timeframe_name'] = "Monthly"
        
        if timeframe_cols[1].button("Weekly", use_container_width=True):
            st.session_state['selected_timeframe_key'] = "W"
            st.session_state['selected_timeframe_name'] = "Weekly"
            
        if timeframe_cols[2].button("Daily", use_container_width=True):
            st.session_state['selected_timeframe_key'] = "d"
            st.session_state['selected_timeframe_name'] = "Daily"
            
        if timeframe_cols[3].button("1h", use_container_width=True):
            st.session_state['selected_timeframe_key'] = "h1"
            st.session_state['selected_timeframe_name'] = "1-Hour"
            
        if timeframe_cols[4].button("4h", use_container_width=True):
            st.session_state['selected_timeframe_key'] = "4h"
            st.session_state['selected_timeframe_name'] = "4-Hour"
        
        # Chart type selection (FORCED to standard candlestick)
        selected_chart_type = "Standard Candlestick"
        # Technical indicators
        st.markdown("**Indicators:**")
        show_ma = st.checkbox("Moving Averages", value=True)
        if show_ma:
            ma_periods = st.multiselect(
                "MA Periods",
                [20, 50, 100, 200],
                default=[50, 200]
            )
        
        show_bollinger = st.checkbox("Bollinger Bands", value=False)
        if show_bollinger:
            bollinger_period = st.slider("Period", 10, 50, 20)
            bollinger_std = st.slider("Std Dev", 1.0, 3.0, 2.0, 0.1)
        
        # Date ranges - more compact layout
        st.markdown("**Date Range:**")
        date_ranges = list(config.STANDARD_PRESETS.keys())
        date_range = st.selectbox(
            "Time Period",
            date_ranges,
            index=1,  # Default to 3Y
            label_visibility="collapsed"
        )
        
        # Get date range from presets
        start_date, end_date = config.STANDARD_PRESETS[date_range]
        
        # Show currently selected settings
        st.markdown("---")
        st.markdown(f"**Current View:**")
        st.markdown(f"📊 **{st.session_state['selected_timeframe_name']}** candlesticks")
        st.markdown(f"📅 **{date_range}** time period")
        
        # Generate chart button
        generate_button = st.button("Update Chart", type="primary", use_container_width=True)
    
    # Use timeframe key from session state
    timeframe_key = st.session_state['selected_timeframe_key']
    
    # Move chart info to the left column
    with col1:
        # Chart title displays the current timeframe
        st.subheader(f"{selected_chart_type} - {st.session_state['selected_timeframe_name']}")
        
        # Description appears below chart once generated
        chart_description = """
        Candlestick charts display the high, low, open, and close prices for each period.\n- **Green candles**: Close price higher than open price (bullish)\n- **Red candles**: Close price lower than open price (bearish)\nThis chart is styled for a TradingView-like appearance."""
    
    # Generate and display the chart - always show in col1
    if generate_button or 'candle_chart' in st.session_state:
        with col1:
            with st.spinner(f"Generating Candlestick Chart for {st.session_state['selected_timeframe_name']} data..."):
                # Load data file
                try:
                    data_file = config.TIMEFRAME_FILES[timeframe_key]
                except KeyError:
                    st.error(f"No data file available for timeframe {timeframe_key}")
                    st.stop()
                
                # Load data with caching
                @st.cache_data(show_spinner=False)
                def load_chart_data(file_key):
                    df = load_csv(file_key)
                    return df
                
                # Load and prepare data
                data = load_chart_data(data_file)
            
                # Ensure datetime format and numeric columns
                data["Date"] = pd.to_datetime(data["Date"])
                
                # Filter by date range
                data = data[(data["Date"] >= pd.Timestamp(start_date)) & 
                           (data["Date"] <= pd.Timestamp(end_date))]
                
                # Convert price columns to numeric if needed
                for col in ["Open", "High", "Low", "Close", "Volume"]:
                    if col in data.columns and data[col].dtype == object:
                        data[col] = data[col].astype(str).str.replace(',', '').astype(float)
            
                # Candlestick chart only
                increasing_color = '#26a69a'  # Green
                decreasing_color = '#ef5350'  # Red
                line_increasing = '#26a69a'
                line_decreasing = '#ef5350'
            
                # Adjust candle width based on timeframe for better visibility
                if len(data) > 1:
                    time_delta = (data['Date'].iloc[1] - data['Date'].iloc[0]).total_seconds()
                    if time_delta >= 86400 * 30:  # Monthly
                        candle_width = 20
                    elif time_delta >= 86400 * 7:  # Weekly
                        candle_width = 12  
                    elif time_delta >= 86400:  # Daily
                        candle_width = 8
                    elif time_delta >= 3600:  # Hourly
                        candle_width = 4
                    else:  # Any other timeframe
                        candle_width = 6
                else:
                    candle_width = 8  # Default width
                
                fig = go.Figure()
                fig.add_trace(
                    go.Candlestick(
                        x=data["Date"],
                        open=data["Open"],
                        high=data["High"],
                        low=data["Low"],
                        close=data["Close"],
                        increasing_line_color=line_increasing,
                        decreasing_line_color=line_decreasing,
                        increasing_fillcolor=increasing_color,
                        decreasing_fillcolor=decreasing_color,
                        name="Price",
                        whiskerwidth=0.5,
                        line=dict(width=2),
                        xperiodalignment="middle",
                        xperiod=time_delta if len(data) > 1 else 86400,
                        xperiod0=data['Date'].iloc[0] if len(data) > 0 else None
                    )
                )
            
                # Add Moving Averages if selected
                if show_ma and len(data) > 0:
                    for period in ma_periods:
                        if len(data) >= period:
                            ma = data["Close"].rolling(window=period).mean()
                            # Check if this is a subplot figure (for volume charts)
                            if selected_chart_type == "Candlestick with Volume" and "Volume" in data.columns:
                                # This is a subplot figure
                                fig.add_trace(
                                    go.Scatter(
                                        x=data["Date"],
                                        y=ma,
                                        line=dict(width=1.5),
                                        name=f"MA{period}"
                                    ),
                                    row=1, col=1
                                )
                            else:
                                # This is a regular figure without subplots
                                fig.add_trace(
                                    go.Scatter(
                                        x=data["Date"],
                                        y=ma,
                                        line=dict(width=1.5),
                                        name=f"MA{period}"
                                    )
                                )
            
                # Add Bollinger Bands if selected
                if show_bollinger and len(data) >= bollinger_period:
                    mid_band = data["Close"].rolling(window=bollinger_period).mean()
                    std_dev = data["Close"].rolling(window=bollinger_period).std()
                
                    upper_band = mid_band + (std_dev * bollinger_std)
                    lower_band = mid_band - (std_dev * bollinger_std)
                    
                    # Add mid band
                    # Check if this is a subplot figure (for volume charts)
                    if selected_chart_type == "Candlestick with Volume" and "Volume" in data.columns:
                        # This is a subplot figure
                        fig.add_trace(
                            go.Scatter(
                                x=data["Date"],
                                y=mid_band,
                                line=dict(width=1, color='rgba(200, 200, 200, 0.8)'),
                                name=f"BB Mid ({bollinger_period})"
                            ),
                            row=1, col=1
                        )
                    else:
                        # This is a regular figure without subplots
                        fig.add_trace(
                            go.Scatter(
                                x=data["Date"],
                                y=mid_band,
                                line=dict(width=1, color='rgba(200, 200, 200, 0.8)'),
                                name=f"BB Mid ({bollinger_period})"
                            )
                        )
                    
                    # Add upper band
                    if selected_chart_type == "Candlestick with Volume" and "Volume" in data.columns:
                        # This is a subplot figure
                        fig.add_trace(
                            go.Scatter(
                                x=data["Date"],
                                y=upper_band,
                                line=dict(width=1, color='rgba(200, 200, 200, 0.6)'),
                                fill=None,
                                name=f"BB Upper ({bollinger_std}σ)"
                            ),
                            row=1, col=1
                        )
                        
                        # Add lower band with fill
                        fig.add_trace(
                            go.Scatter(
                                x=data["Date"],
                                y=lower_band,
                                line=dict(width=1, color='rgba(200, 200, 200, 0.6)'),
                                fill='tonexty',  # Fill area between upper and lower bands
                                fillcolor='rgba(200, 200, 200, 0.2)',
                                name=f"BB Lower ({bollinger_std}σ)"
                            ),
                            row=1, col=1
                        )
                    else:
                        # This is a regular figure without subplots
                        fig.add_trace(
                            go.Scatter(
                                x=data["Date"],
                                y=upper_band,
                                line=dict(width=1, color='rgba(200, 200, 200, 0.6)'),
                                fill=None,
                                name=f"BB Upper ({bollinger_std}σ)"
                            )
                        )
                        
                        # Add lower band with fill
                        fig.add_trace(
                            go.Scatter(
                                x=data["Date"],
                                y=lower_band,
                                line=dict(width=1, color='rgba(200, 200, 200, 0.6)'),
                                fill='tonexty',  # Fill area between upper and lower bands
                                fillcolor='rgba(200, 200, 200, 0.2)',
                                name=f"BB Lower ({bollinger_std}σ)"
                            )
                        )
            
                # Update layout
                title = f"{selected_chart_type} - {st.session_state['selected_timeframe_name']} ({date_range})"
                
                fig.update_layout(
                    title=title,
                    xaxis_title="",
                    yaxis_title="Price",
                    xaxis_rangeslider_visible=False,  # Hide range slider for cleaner look
                    template="plotly_dark",
                    legend=dict(
                        orientation="h",
                        yanchor="bottom",
                        y=1.02,
                        xanchor="right",
                        x=1
                    ),
                    height=700,
                    margin=dict(l=20, r=20, t=50, b=20),
                    showlegend=True,
                    paper_bgcolor='#1c1c1c',  # Darker background like TradingView
                    plot_bgcolor='#1c1c1c',   # Darker plot area
                    hovermode='x unified',    # Better hover behavior
                    # Better grid styling
                    xaxis=dict(
                        showgrid=True,
                        gridcolor='rgba(80, 80, 80, 0.3)',
                        gridwidth=0.5,
                        showspikes=True,  # Add price spikes on hover
                        spikethickness=1,
                        spikecolor="#999999",
                        spikedash="solid"
                    ),
                    yaxis=dict(
                        showgrid=True,
                        gridcolor='rgba(80, 80, 80, 0.3)',
                        gridwidth=0.5,
                        showspikes=True,  # Add price spikes on hover
                        spikethickness=1,
                        spikecolor="#999999",
                        spikedash="solid"
                    )
                )
            
                # Set the y-axis to logarithmic scale for long-term charts
                if date_range in ["5Y", "10Y", "Full"]:
                    fig.update_yaxes(type="log")
                
                # Save to session state
                st.session_state['candle_chart'] = fig
            
                # Display the chart with full width and proper height
                st.plotly_chart(st.session_state['candle_chart'], use_container_width=True)
                
                # Show the chart description
                if selected_chart_type in chart_descriptions:
                    st.markdown(chart_descriptions[selected_chart_type])
                
                # Show chart patterns in an expander for clean UI
                with st.expander("View Chart Patterns & Interpretation"):
                    st.markdown("### Common Candlestick Patterns")
                    st.markdown("""
**Bullish Patterns:**
- **Hammer**: Small body at the top with a long lower wick. Suggests potential reversal after downtrend.
- **Engulfing Bullish**: Bearish candle followed by a larger bullish candle that 'engulfs' the previous one.
- **Morning Star**: Three-candle pattern with a bearish candle, small-bodied middle candle, and bullish candle.

**Bearish Patterns:**
- **Shooting Star**: Small body at the bottom with a long upper wick. Suggests potential reversal after uptrend.
- **Engulfing Bearish**: Bullish candle followed by a larger bearish candle that 'engulfs' the previous one.
- **Evening Star**: Three-candle pattern with a bullish candle, small-bodied middle candle, and bearish candle.
""")
                    st.image("https://a.c-dn.net/c/content/dam/publicsites/igcom/uk/images/ContentImage/How-to-read-candlestick-charts.png", 
                        caption="Common Candlestick Patterns",
                        width=400)
    else:
        # Default chart preview in the main column
        with col1:
            st.info("Use the controls on the right to configure your chart, then click 'Update Chart' to generate the candle chart.")
            
            # Show an example TradingView-like chart as a placeholder
            st.image("https://d2.alternativeto.net/dist/s/tradingview_912128_full.jpg?format=jpg&width=1600&height=1600&mode=min&upscale=false", 
                    caption="Sample Gold Chart - Click 'Update Chart' to view live data",
                    use_column_width=True)
            
            # Add quick guide to chart types
            st.markdown("### Chart Types Available")
            st.markdown("""
            - **Standard Candlestick**: Traditional OHLC display
            - **Candlestick with Volume**: Adds volume bars below the main chart
            - **Hollow Candlestick**: Hollow bodies for bullish candles
            - **Heiken Ashi**: Smoothed price action for trend identification
            - **Line Chart**: Simple line chart showing closing prices
            """)
            
            # Add note about timeframes
            st.markdown("### Available Timeframes")
            st.markdown("""
            Switch between timeframes using the buttons at the top right:
            - **Monthly**: Long-term analysis (each candle is one month)
            - **Weekly**: Medium-term analysis (each candle is one week)
            - **Daily**: Standard analysis (each candle is one day)
            - **1h**: Short-term analysis (each candle is one hour)
            - **4h**: Intraday analysis (each candle is four hours)
            """)
            
            # Add instruction about technical indicators
            st.markdown("### Technical Indicators")
            st.markdown("""
            Add technical indicators using the checkboxes:
            - **Moving Averages**: Add multiple MAs with different periods
            - **Bollinger Bands**: Add standard deviation bands around price
            """)
            
            # Add some space
            st.write("")

# --- Seasonality Tab ----------------------------------------------------
with tab3:
    st.markdown("## Gold Seasonality Analysis")
    
    # Create sidebar for seasonality controls
    st.sidebar.markdown("---")
    st.sidebar.markdown("### Seasonality Options")
    
    # Data source selection (timeframe)
    timeframe_options = {
        "Daily": "d",
        "Weekly": "W",
        "Monthly": "m",
        "1-Hour": "h1"
    }
    selected_timeframe = st.sidebar.selectbox(
        "Data Timeframe",
        list(timeframe_options.keys()),
        index=0  # Default to daily
    )
    timeframe_key = timeframe_options[selected_timeframe]
    
    # Return calculation method
    return_methods = {
        "Open to Close (Intraday)": "open-close",
        "Close to Close (Daily)": "close-close"
    }
    selected_return_method = st.sidebar.radio(
        "Return Calculation",
        list(return_methods.keys())
    )
    return_method = return_methods[selected_return_method]
    
    # Year ranges to show
    show_ytd = st.sidebar.checkbox("Show Year-to-Date", value=True)
    show_5yr = st.sidebar.checkbox("Show 5-Year Average", value=True)
    show_10yr = st.sidebar.checkbox("Show 10-Year Average", value=True)
    show_15yr = st.sidebar.checkbox("Show 15-Year Average", value=True)
    
    # Calculate button
    calculate_button = st.sidebar.button("Calculate Seasonality", type="primary")
    clear_button = st.sidebar.button("Clear Filters")
    
    if clear_button:
        # Reset to defaults
        show_ytd = True
        show_5yr = True
        show_10yr = True
        show_15yr = True
        selected_timeframe = list(timeframe_options.keys())[0]
        selected_return_method = list(return_methods.keys())[0]
    
    # Main content area for the seasonality tab
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.subheader(f"Gold Seasonality ({selected_timeframe} Data)")
    
    with col2:
        st.caption(f"Return Method: {selected_return_method}")
    
    # Calculate and display seasonality if button is clicked
    if calculate_button or 'seasonality_figure' in st.session_state:
        # Show a spinner while calculating
        with st.spinner(f"Calculating seasonality patterns using {selected_timeframe} data..."):
            # Get the data file
            data_file = config.TIMEFRAME_FILES[timeframe_key]
            
            # Load data
            @st.cache_data(show_spinner=False)
            def load_seasonality_data(file_key):
                df = load_csv(file_key)
                return df
            
            data = load_seasonality_data(data_file)
            
            # Calculate years to include
            years_to_include = []
            if show_5yr:
                years_to_include.append(5)
            if show_10yr:
                years_to_include.append(10)
            if show_15yr:
                years_to_include.append(15)
            
            # Calculate seasonality using the same cutoff date as other profiles
            seasonality_data = calculate_seasonality(
                data, 
                years_back=max(years_to_include), 
                return_type=return_method,
                cutoff_date=config.cutoff_date
            )
            
            # Generate return data
            return_data = generate_cumulative_returns(seasonality_data, years_list=years_to_include)
            
            # Filter based on selected options
            if not show_ytd and "YTD" in return_data:
                del return_data["YTD"]
            if not show_5yr and "5YR" in return_data:
                del return_data["5YR"]
            if not show_10yr and "10YR" in return_data:
                del return_data["10YR"]
            if not show_15yr and "15YR" in return_data:
                del return_data["15YR"]
            
            # Create figure
            title = f"Gold Seasonality - {selected_timeframe} ({selected_return_method})"
            seasonality_figure = plot_seasonality(return_data, title=title)
            
            # Save to session state
            st.session_state['seasonality_figure'] = seasonality_figure
    
        # Display the figure
        st.plotly_chart(st.session_state['seasonality_figure'], use_container_width=True)
        
        # Additional metrics table
        st.subheader("Monthly Performance Summary")
        
        # Create monthly summary if we have data
        if 'seasonality_figure' in st.session_state and return_data:
            # Create summary table
            summary_data = []
            
            for key, data in return_data.items():
                if key == "YTD":
                    name = "Year to Date"
                else:
                    name = f"{key[:-2]} Year Average"
                
                # Calculate monthly performance - handle different day of year calculations
                try:
                    # More accurate month calculation - convert day of year to date
                    if "DayOfYear" in data.columns:
                        # Make sure DayOfYear is integer
                        data["DayOfYear"] = data["DayOfYear"].astype(int)
                        
                        # Generate month from day of year (more accurate than division)
                        def day_to_month(day, year=2020):  # Using leap year for safety
                            date = dt.datetime(year, 1, 1) + dt.timedelta(days=int(day)-1)
                            return date.month
                        
                        data["Month"] = data["DayOfYear"].apply(day_to_month)
                    else:  # Handle case where DayOfYear is missing
                        data["Month"] = (data.index % 365 // 30) + 1
                    
                    # Group by month
                    monthly_returns = data.groupby("Month")["Return"].sum().reset_index()
                except Exception as e:
                    st.warning(f"Could not calculate monthly returns accurately: {e}")
                    # Fallback to approximate months
                    month_data = {"Timeframe": name}
                    for m in range(1, 13):
                        month_name = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"][m-1]
                        month_data[month_name] = "N/A"
                    summary_data.append(month_data)
                    continue
                
                # Format data for the table
                month_data = {"Timeframe": name}
                
                for _, row in monthly_returns.iterrows():
                    month = int(row["Month"])  # Convert to integer explicitly
                    if 1 <= month <= 12:
                        month_name = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"][month-1]
                        month_data[month_name] = f"{row['Return']:.2f}%"
                
                summary_data.append(month_data)
            
            # Convert to DataFrame and display
            if summary_data:
                summary_df = pd.DataFrame(summary_data)
                st.dataframe(summary_df, use_container_width=True)
    else:
        # Show placeholder before calculation
        st.info("Select your parameters and click 'Calculate Seasonality' to view seasonal patterns.")



# ------------------------------------------------------------------------
blob_key = config.PROFILE_SOURCE[profile_key]
blob     = config.TIMEFRAME_FILES[blob_key]

@st.cache_data(show_spinner=f"Loading {blob} …")
def fetch(b):
    df = load_csv(b)[["Date","Open","High","Low","Close"]].copy()
    # strip thousands separator before numeric cast
    for col in ["Open","High","Low","Close"]:
        df[col] = df[col].astype(str).str.replace(",", "").astype(float)
    
    # First try to parse date with common formats to avoid warning
    try:
        # Try M/D/YYYY format (e.g., 3/19/2025)
        df["Date"] = pd.to_datetime(df["Date"], format="%m/%d/%Y", errors="raise")
    except ValueError:
        try:
            # Try YYYY-MM-DD format
            df["Date"] = pd.to_datetime(df["Date"], format="%Y-%m-%d", errors="raise")
        except ValueError:
            # As a fallback, let pandas infer the format
            df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    
    return df.dropna()

raw = fetch(blob)
build = BUILDERS[profile_key]

# Special handling for session profile
if profile_key == "session":
    # Call build with view mode parameter
    df = build(raw, pd.Timestamp(start), pd.Timestamp(end), view=session_view_mode)
    
    # Apply filter for combined view if needed
    if session_view_mode == "combined" and session_filter != "All":
        if session_filter == "Green Days":
            # Filter to only include data from days with positive returns
            green_days = raw[raw["Close"] > raw["Open"]].copy()
            if not green_days.empty:
                df = build(green_days, pd.Timestamp(start), pd.Timestamp(end), view=session_view_mode)
        elif session_filter == "Red Days":
            # Filter to only include data from days with negative returns
            red_days = raw[raw["Close"] < raw["Open"]].copy()
            if not red_days.empty:
                df = build(red_days, pd.Timestamp(start), pd.Timestamp(end), view=session_view_mode)
else:
    # Standard build for other profiles
    df = build(raw, pd.Timestamp(start), pd.Timestamp(end))

if df.empty:
    st.info("No data in range"); st.stop()

# --- Current Market Position Tab -------------------------------------------------------
with tab1:
    # Get current Eastern Time
    eastern = pytz.timezone('US/Eastern')
    current_time = dt.datetime.now(eastern)
    st.markdown(f"### Current Eastern Time: {current_time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    
    # Create the Current Market Position table
    st.markdown("## Current Market Position 🔄")
    
    # Calculate current positions for all profiles
    positions_data = []
    
    for i, prof_key in enumerate(BUILDERS.keys()):
        # Get data for this profile using default presets
        blob_key = config.PROFILE_SOURCE[prof_key]
        blob_data = config.TIMEFRAME_FILES[blob_key]
        raw_data = fetch(blob_data)
        build_func = BUILDERS[prof_key]
        
        # Get default dates from profile presets
        default_preset = config.PROFILE_DEFAULT_PRESET[prof_key]
        preset_dict = config.PROFILE_PRESETS.get(prof_key, config.STANDARD_PRESETS)
        default_start, default_end = preset_dict.get(default_preset, (None, None))
        
        # Fall back to 1-year range if needed
        if default_start is None or default_end is None:
            default_start = dt.date.today() - dt.timedelta(days=365)
            default_end = dt.date.today()
        
        profile_df = build_func(raw_data, pd.Timestamp(default_start), pd.Timestamp(default_end))
        
        # Determine current position based on today's date
        if prof_key == 'decennial':
            current_position = current_time.year % 10
            max_position = 10
        elif prof_key == 'presidential':
            current_position = (current_time.year % 4) + 1
            max_position = 4
        elif prof_key == 'quarter':
            current_position = (current_time.month - 1) // 3 + 1
            max_position = 4
        elif prof_key == 'month':
            current_position = current_time.month
            max_position = 12
        elif prof_key == 'week_of_year':
            current_position = current_time.isocalendar()[1]
            max_position = 52
        elif prof_key == 'week_of_month':
            current_position = ((current_time.day - 1) // 7) + 1
            max_position = 4 if current_position <= 4 else 5
        elif prof_key == 'day_of_week':
            current_position = current_time.weekday() + 1
            max_position = 5
        elif prof_key == 'session':
            current_position = current_time.weekday() + 1
            max_position = 5
        
        # Format the profile name for better display
        formatted_profile = prof_key.replace('_', ' ').title()
        
        positions_data.append({
            'Profile': formatted_profile,
            'Position': f"{current_position} of {max_position}"
        })
    
    # Create and display the position table
    position_df = pd.DataFrame(positions_data)
    st.dataframe(position_df, use_container_width=True, hide_index=False)
    
    # Add some contextual explanation
    st.markdown("""
The table above shows the current market position for each cyclical profile based on Eastern Time.
These positions can help you align your trading strategies with historical seasonal patterns.
Switch to the 'Cyclical Profiles' tab to explore detailed historical performance for each profile.
""")

# --- Cyclical Profiles Tab -------------------------------------------------------
with tab2:
    st.markdown("""
    Explore **gold's seasonality** across multiple time‑based profiles (month, week of year, day of week, session, etc.).
    The coloured **barcode** underneath the main chart gives you a quick visual of the cycle:
    <span style='background:#2e7d32;color:white;padding:2px 6px;border-radius:4px'>green</span>
    bars = average up months, <span style='background:#c62828;color:white;padding:2px 6px;border-radius:4px'>red</span>
    bars = average down months.
    """, unsafe_allow_html=True)
    
    # Original view - sorted by returns (reds/greens grouped together)
    st.subheader("Chart 1 - Grouped by Returns (Red/Green)")
    
    # Sort by returns (reds on one side, greens on the other)
    returns_df = df.copy().sort_values("AvgReturn", ascending=False)
    
    # Use Label for x-axis
    x = "Label"
    
    # Create visualization based on selected metric
    if metric == "Average Return":
        returns_df["col"] = returns_df["AvgReturn"].gt(0).map({True:"green", False:"red"})
        fig = px.bar(returns_df, x=x, y="AvgReturn", color="col",
                    color_discrete_map="identity", height=400)
    elif metric == "ATR points":
        q = returns_df["AvgRange"].quantile([0, .33, .66, 1]).values
        returns_df["band"] = returns_df["AvgRange"].apply(
            lambda v: "Low" if v<=q[1] else "Avg" if v<=q[2] else "High")
        fig = px.bar(returns_df, x=x, y="AvgRange", color="band",
                    color_discrete_map={"Low":"green","Avg":"orange","High":"red"}, height=400)
    elif metric == "ATR level":
        q = returns_df["AvgRange"].quantile([0, .33, .66, 1]).values
        returns_df["lvl"] = returns_df["AvgRange"].apply(lambda v: 1 if v<=q[1] else 2 if v<=q[2] else 3)
        fig = px.bar(returns_df, x=x, y="lvl", color="lvl",
                    color_discrete_map={1:"green",2:"orange",3:"red"}, height=400)
    else:
        fig = px.bar(returns_df, x=x, y=["ProbGreen","ProbRed"], barmode="group",
                    color_discrete_map={"ProbGreen":"green","ProbRed":"red"}, height=400)
    
    fig.update_layout(xaxis_title="", yaxis_title="")
    st.plotly_chart(fig, use_container_width=True)
    
    # Removed barcode visualization as requested
    
    # Add separator
    st.markdown("---")
    
    # Natural profile order view (Jan-Dec, Mon-Fri, etc.)
    st.subheader("Chart 2 - Natural Profile Order")
    
    # Sort by Bucket (natural profile order)
    # Create hardcoded calendar ordering for each profile type
    if profile_key == "month":
        # For monthly profile, explicitly create a new dataframe in Jan-Dec order
        month_order = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        profile_df = pd.DataFrame()
        
        # Build dataframe in explicit month order
        for month in month_order:
            month_data = df[df["Label"] == month]
            if not month_data.empty:
                profile_df = pd.concat([profile_df, month_data])
    elif profile_key == "day_of_week":
        # For day of week, explicitly order Mon-Fri
        dow_order = ["Mon", "Tue", "Wed", "Thu", "Fri"]
        profile_df = pd.DataFrame()
        
        for day in dow_order:
            day_data = df[df["Label"] == day]
            if not day_data.empty:
                profile_df = pd.concat([profile_df, day_data])
    elif profile_key == "session":
        # For session profile, special handling based on view mode
        if session_view_mode == "daily":
            # Order by weekday, then by session within each day
            profile_df = df.copy().sort_values(["Bucket", "Session"])
        else:
            # For combined view, order by session (Asia, London, NY)
            profile_df = df.copy().sort_values(["Session"])
    else:
        # For other profiles, sort by Bucket which should represent the natural profile order
        profile_df = df.copy().sort_values("Bucket")
    
    # Create visualization based on selected metric and profile type
    if profile_key == "session":
        # Special visualization for sessions profile
        if session_view_mode == "daily":
            # For daily view with 5 bars, each split into 3 sessions as stacked segments
            # Create a pivot table to get sessions as columns
            if "DayLabel" in profile_df.columns and "SessionLabel" in profile_df.columns:
                # Create a vibrant color palette for the three sessions (good for dark mode)
                session_colors = {
                    "Asia": "#FF3333",    # Bright red
                    "London": "#FFCC00",  # Golden yellow
                    "NY": "#33CC33"       # Bright green
                }
                
                # Create a stacked bar chart with one bar per day, colored by session
                fig2 = px.bar(profile_df,
                              x="DayLabel",
                              y="AvgReturn",
                              color="SessionLabel",
                              color_discrete_map=session_colors,
                              barmode="stack",
                              height=500)
                
                # Customize layout
                fig2.update_layout(
                    title="Daily Performance by Trading Session",
                    xaxis_title="Day of Week",
                    yaxis_title="Average Return",
                    legend_title="Trading Session"
                )
                
                # Add annotations to explain the segments
                fig2.add_annotation(
                    x=0.02, y=0.98,
                    xref="paper", yref="paper",
                    text="Each bar shows a day split into three sessions:",
                    showarrow=False,
                    font=dict(size=12), align="left"
                )
                
                y_pos = 0.93
                for session, color in session_colors.items():
                    fig2.add_annotation(
                        x=0.02, y=y_pos,
                        xref="paper", yref="paper",
                        text=f"• {session}",
                        showarrow=False,
                        font=dict(size=12, color="black"),
                        bgcolor=color,
                        borderpad=4,
                        align="left"
                    )
                    y_pos -= 0.05
            else:
                # Fallback if the data structure is not as expected
                fig2 = px.bar(profile_df, x="Label", y="AvgReturn", color="col",
                              color_discrete_map="identity", height=400)
        else:
            # For combined view (1 bar with 3 sessions)
            # Create a vibrant color palette for the three sessions (good for dark mode)
            session_colors = {
                "Asia": "#FF3333",    # Bright red
                "London": "#FFCC00",  # Golden yellow
                "NY": "#33CC33"       # Bright green
            }
            
            # Use a constant value for x-axis to create a single bar
            profile_df["Segment"] = "Combined Sessions"
            
            # Create a stacked bar chart
            fig2 = px.bar(profile_df,
                          x="Segment",
                          y="AvgReturn",
                          color="SessionLabel",
                          color_discrete_map=session_colors,
                          barmode="stack",
                          height=500)
            
            # Add title based on filter
            filter_title = ""
            if session_filter != "All":
                filter_title = f" ({session_filter})"
                
            # Customize layout
            fig2.update_layout(
                title=f"Trading Sessions Performance{filter_title}",
                xaxis_title="",
                yaxis_title="Average Return",
                legend_title="Trading Session"
            )
            
            # Add annotations to explain the segments
            fig2.add_annotation(
                x=0.02, y=0.98,
                xref="paper", yref="paper",
                text="Single bar split into three trading sessions:",
                showarrow=False,
                font=dict(size=12), align="left"
            )
            
            y_pos = 0.93
            for session, color in session_colors.items():
                fig2.add_annotation(
                    x=0.02, y=y_pos,
                    xref="paper", yref="paper",
                    text=f"• {session}",
                    showarrow=False,
                    font=dict(size=12, color="black"),
                    bgcolor=color,
                    borderpad=4,
                    align="left"
                )
                y_pos -= 0.05
    else:
        # Standard visualization for other profiles
        if metric == "Average Return":
            profile_df["col"] = profile_df["AvgReturn"].gt(0).map({True:"green", False:"red"})
            fig2 = px.bar(profile_df, x=x, y="AvgReturn", color="col",
                         color_discrete_map="identity", height=400)
        elif metric == "ATR points":
            q = profile_df["AvgRange"].quantile([0, .33, .66, 1]).values
            profile_df["band"] = profile_df["AvgRange"].apply(
                lambda v: "Low" if v<=q[1] else "Avg" if v<=q[2] else "High")
            fig2 = px.bar(profile_df, x=x, y="AvgRange", color="band",
                         color_discrete_map={"Low":"green","Avg":"orange","High":"red"}, height=400)
        elif metric == "ATR level":
            q = profile_df["AvgRange"].quantile([0, .33, .66, 1]).values
            profile_df["lvl"] = profile_df["AvgRange"].apply(lambda v: 1 if v<=q[1] else 2 if v<=q[2] else 3)
            fig2 = px.bar(profile_df, x=x, y="lvl", color="lvl",
                         color_discrete_map={1:"green",2:"orange",3:"red"}, height=400)
        else:
            fig2 = px.bar(profile_df, x=x, y=["ProbGreen","ProbRed"], barmode="group",
                         color_discrete_map={"ProbGreen":"green","ProbRed":"red"}, height=400)
    
    fig2.update_layout(xaxis_title="", yaxis_title="")
    st.plotly_chart(fig2, use_container_width=True)
