"""
Candle Charts tab implementation.
This module contains the UI and logic for the Candle Charts tab.
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import datetime as dt

from gold import config

def render_candle_charts_sidebar_controls():
    """Render the sidebar controls for candle chart settings"""
    st.sidebar.markdown("---")
    st.sidebar.markdown("### Chart Settings")
    
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
    ma_periods = []
    if show_ma:
        ma_periods = st.multiselect(
            "MA Periods",
            [20, 50, 100, 200],
            default=[50, 200]
        )
    
    show_bollinger = st.checkbox("Bollinger Bands", value=False)
    bollinger_period = 20
    bollinger_std = 2.0
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
    st.markdown("**Current View:**")
    st.markdown(f"📊 **{st.session_state['selected_timeframe_name']}** candlesticks")
    st.markdown(f"📅 **{date_range}** time period")
    
    # Generate chart button
    generate_button = st.button("Update Chart", type="primary", use_container_width=True)
    
    return {
        'selected_chart_type': selected_chart_type,
        'timeframe_key': st.session_state['selected_timeframe_key'],
        'date_range': date_range,
        'start_date': start_date,
        'end_date': end_date,
        'show_ma': show_ma,
        'ma_periods': ma_periods,
        'show_bollinger': show_bollinger,
        'bollinger_period': bollinger_period,
        'bollinger_std': bollinger_std,
        'generate_button': generate_button
    }

def load_chart_data(file_key, load_function):
    """Load data for chart with caching"""
    df = load_function(file_key)
    return df

def render_candle_charts_tab(tab, load_csv_function):
    """Render the Candle Charts tab content"""
    with tab:
        st.markdown("## Gold Candle Charts Analysis")
        
        # Create a more trading view like layout
        col1, col2 = st.columns([4, 1])
        
        with col2:
            controls = render_candle_charts_sidebar_controls()
        
        # Move chart info to the left column
        with col1:
            # Chart title displays the current timeframe
            st.subheader(f"{controls['selected_chart_type']} - {st.session_state['selected_timeframe_name']}")
            
            # Description appears below chart once generated
            chart_description = """
            Candlestick charts display the high, low, open, and close prices for each period.\n- **Green candles**: Close price higher than open price (bullish)\n- **Red candles**: Close price lower than open price (bearish)\nThis chart is styled for a TradingView-like appearance."""
        
        # Generate and display the chart - always show in col1
        if controls['generate_button'] or 'candle_chart' in st.session_state:
            with col1:
                with st.spinner(f"Generating Candlestick Chart for {st.session_state['selected_timeframe_name']} data..."):
                    # Load data file
                    try:
                        data_file = config.TIMEFRAME_FILES[controls['timeframe_key']]
                    except KeyError:
                        st.error(f"No data file available for timeframe {controls['timeframe_key']}")
                        st.stop()
                    
                    # Load data with caching
                    data = load_chart_data(data_file, load_csv_function)
                
                    # Ensure datetime format and numeric columns
                    data["Date"] = pd.to_datetime(data["Date"])
                    
                    # Filter by date range
                    data = data[(data["Date"] >= pd.Timestamp(controls['start_date'])) & 
                               (data["Date"] <= pd.Timestamp(controls['end_date']))]
                    
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
                    if controls['show_ma'] and len(data) > 0:
                        for period in controls['ma_periods']:
                            if len(data) >= period:
                                ma = data["Close"].rolling(window=period).mean()
                                # Check if this is a subplot figure (for volume charts)
                                if controls['selected_chart_type'] == "Candlestick with Volume" and "Volume" in data.columns:
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
                    if controls['show_bollinger'] and len(data) >= controls['bollinger_period']:
                        mid_band = data["Close"].rolling(window=controls['bollinger_period']).mean()
                        std_dev = data["Close"].rolling(window=controls['bollinger_period']).std()
                    
                        upper_band = mid_band + (std_dev * controls['bollinger_std'])
                        lower_band = mid_band - (std_dev * controls['bollinger_std'])
                        
                        # Add mid band
                        # Check if this is a subplot figure (for volume charts)
                        if controls['selected_chart_type'] == "Candlestick with Volume" and "Volume" in data.columns:
                            # This is a subplot figure
                            fig.add_trace(
                                go.Scatter(
                                    x=data["Date"],
                                    y=mid_band,
                                    line=dict(width=1, color='rgba(200, 200, 200, 0.8)'),
                                    name=f"BB Mid ({controls['bollinger_period']})"
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
                                    name=f"BB Mid ({controls['bollinger_period']})"
                                )
                            )
                        
                        # Add upper band
                        if controls['selected_chart_type'] == "Candlestick with Volume" and "Volume" in data.columns:
                            # This is a subplot figure
                            fig.add_trace(
                                go.Scatter(
                                    x=data["Date"],
                                    y=upper_band,
                                    line=dict(width=1, color='rgba(200, 200, 200, 0.6)'),
                                    fill=None,
                                    name=f"BB Upper ({controls['bollinger_std']}σ)"
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
                                    name=f"BB Lower ({controls['bollinger_std']}σ)"
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
                                    name=f"BB Upper ({controls['bollinger_std']}σ)"
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
                                    name=f"BB Lower ({controls['bollinger_std']}σ)"
                                )
                            )
                
                    # Update layout
                    title = f"{controls['selected_chart_type']} - {st.session_state['selected_timeframe_name']} ({controls['date_range']})"
                    
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
                    if controls['date_range'] in ["5Y", "10Y", "Full"]:
                        fig.update_yaxes(type="log")
                    
                    # Save to session state
                    st.session_state['candle_chart'] = fig
                
                    # Display the chart with full width and proper height
                    st.plotly_chart(st.session_state['candle_chart'], use_container_width=True)
                    
                    # Show the chart description
                    st.markdown(chart_description)
                    
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
