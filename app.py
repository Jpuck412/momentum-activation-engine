import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import yfinance as yf
import talib
import plotly.graph_objects as go
import plotly.express as px
import logging
from functools import lru_cache
import time
import requests
from typing import Dict, List, Tuple, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Page configuration
st.set_page_config(
    page_title="Momentum Activation Engine",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main {
        padding-top: 1rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 10px;
        color: white;
        text-align: center;
    }
    .active-badge {
        background-color: #d4edda;
        color: #155724;
        padding: 10px;
        border-radius: 5px;
        font-weight: bold;
        display: inline-block;
    }
    .watch-badge {
        background-color: #fff3cd;
        color: #856404;
        padding: 10px;
        border-radius: 5px;
        font-weight: bold;
        display: inline-block;
    }
    .noise-badge {
        background-color: #f8d7da;
        color: #721c24;
        padding: 10px;
        border-radius: 5px;
        font-weight: bold;
        display: inline-block;
    }
    .stTabs [data-baseweb="tab-list"] button {
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# TECHNICAL ANALYSIS FUNCTIONS
# ============================================================================

@st.cache_data(ttl=600)
def fetch_stock_data(ticker: str, period: str = "3mo") -> Optional[pd.DataFrame]:
    """Fetch historical stock data with error handling"""
    try:
        data = yf.download(ticker, period=period, progress=False, threads=False)
        if len(data) == 0:
            return None
        return data
    except Exception as e:
        logger.error(f"Error fetching data for {ticker}: {e}")
        return None

def calculate_indicators(df: pd.DataFrame) -> Optional[Dict]:
    """Calculate comprehensive technical indicators"""
    if df is None or len(df) < 30:
        return None
    
    try:
        close = df['Close'].values
        high = df['High'].values
        low = df['Low'].values
        volume = df['Volume'].values
        
        # RSI (Relative Strength Index)
        rsi = talib.RSI(close, timeperiod=14)[-1]
        
        # MACD (Moving Average Convergence Divergence)
        macd, signal, hist = talib.MACD(close, fastperiod=12, slowperiod=26, signalperiod=9)
        macd_val = macd[-1]
        macd_signal = signal[-1]
        macd_hist = hist[-1]
        
        # Bollinger Bands
        bb_high, bb_mid, bb_low = talib.BBANDS(close, timeperiod=20, nbdevup=2, nbdevdn=2, matype=0)
        current_price = close[-1]
        bb_high_val = bb_high[-1]
        bb_low_val = bb_low[-1]
        bb_position = (current_price - bb_low_val) / (bb_high_val - bb_low_val) if (bb_high_val - bb_low_val) != 0 else 0.5
        
        # ADX (Average Directional Index)
        adx = talib.ADX(high, low, close, timeperiod=14)[-1]
        
        # Stochastic RSI
        stoch_rsi = talib.STOCHRSI(close, timeperiod=14, fastk_period=3, fastd_period=3, fastd_matype=0)
        stoch_k = stoch_rsi[2][-1] * 100  # FastK
        stoch_d = stoch_rsi[3][-1] * 100  # FastD
        
        # CCI (Commodity Channel Index)
        cci = talib.CCI(high, low, close, timeperiod=20)[-1]
        
        # Volume analysis
        avg_volume = np.mean(volume[-20:])
        current_volume = volume[-1]
        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1
        
        # Volume SMA
        volume_sma = talib.SMA(volume, timeperiod=20)[-1]
        volume_trend = (current_volume - volume_sma) / volume_sma * 100 if volume_sma > 0 else 0
        
        # Price momentum
        price_change_5d = ((close[-1] - close[-5]) / close[-5] * 100) if len(close) >= 5 else 0
        price_change_1d = ((close[-1] - close[-2]) / close[-2] * 100) if len(close) >= 2 else 0
        
        # Moving averages
        ma_20 = talib.SMA(close, timeperiod=20)[-1]
        ma_50 = talib.SMA(close, timeperiod=50)[-1]
        ma_200 = talib.SMA(close, timeperiod=200)[-1] if len(close) >= 200 else ma_50
        
        # 52-week high/low
        high_52w = np.max(high[-252:]) if len(high) >= 252 else np.max(high)
        low_52w = np.min(low[-252:]) if len(low) >= 252 else np.min(low)
        high_low_position = (current_price - low_52w) / (high_52w - low_52w) * 100 if (high_52w - low_52w) != 0 else 50
        
        # ATR (Average True Range)
        atr = talib.ATR(high, low, close, timeperiod=14)[-1]
        atr_percent = (atr / current_price) * 100
        
        return {
            'rsi': rsi,
            'macd': macd_val,
            'macd_signal': macd_signal,
            'macd_hist': macd_hist,
            'bb_position': bb_position,
            'bb_high': bb_high_val,
            'bb_low': bb_low_val,
            'adx': adx,
            'stoch_k': stoch_k,
            'stoch_d': stoch_d,
            'cci': cci,
            'volume_ratio': volume_ratio,
            'volume_trend': volume_trend,
            'price_change_5d': price_change_5d,
            'price_change_1d': price_change_1d,
            'ma_20': ma_20,
            'ma_50': ma_50,
            'ma_200': ma_200,
            'high_52w': high_52w,
            'low_52w': low_52w,
            'high_low_position': high_low_position,
            'current_price': current_price,
            'avg_volume': avg_volume,
            'current_volume': current_volume,
            'atr': atr,
            'atr_percent': atr_percent
        }
    except Exception as e:
        logger.error(f"Error calculating indicators: {e}")
        return None

def determine_state(indicators: Dict, rsi_low: int, rsi_high: int, vol_mult: float) -> Tuple[str, int, List[str]]:
    """Determine momentum state based on technical indicators"""
    if indicators is None:
        return "ERROR", 0, []
    
    score = 0
    reasons = []
    
    # RSI signals (range: -30 to +30)
    rsi = indicators['rsi']
    if rsi < rsi_low:
        score += 25
        reasons.append(f"RSI Oversold ({rsi:.1f})")
    elif rsi > rsi_high:
        score += 15
        reasons.append(f"RSI Overbought ({rsi:.1f})")
    else:
        score += 5
    
    # MACD signals (range: -15 to +15)
    if indicators['macd_hist'] > 0 and indicators['macd'] > indicators['macd_signal']:
        score += 15
        reasons.append("MACD Bullish")
    elif indicators['macd_hist'] < 0 and indicators['macd'] < indicators['macd_signal']:
        score -= 10
        reasons.append("MACD Bearish")
    
    # Bollinger Bands signals (range: -20 to +20)
    bb_pos = indicators['bb_position']
    if bb_pos > 0.8:
        score += 10
        reasons.append("Upper BB (Overextended)")
    elif bb_pos < 0.2:
        score += 15
        reasons.append("Lower BB (Reversal Setup)")
    
    # Volume signals (range: -10 to +20)
    vol_ratio = indicators['volume_ratio']
    if vol_ratio > vol_mult:
        score += 20
        reasons.append(f"Volume Spike ({vol_ratio:.1f}x)")
    elif vol_ratio > 1.5:
        score += 10
        reasons.append(f"High Volume ({vol_ratio:.1f}x)")
    
    # Trend strength (ADX) - range: -5 to +10
    adx = indicators['adx']
    if adx > 25:
        score += 10
        reasons.append(f"Strong Trend (ADX: {adx:.1f})")
    
    # Price momentum (range: -10 to +15)
    price_change = indicators['price_change_5d']
    if price_change > 5:
        score += 15
        reasons.append(f"Strong Momentum (+{price_change:.1f}%)")
    elif price_change < -5:
        score -= 5
        reasons.append(f"Negative Momentum ({price_change:.1f}%)")
    
    # 52-week position (range: -5 to +10)
    hl_pos = indicators['high_low_position']
    if hl_pos > 75:
        score += 10
        reasons.append(f"Near 52w High ({hl_pos:.1f}%)")
    elif hl_pos < 25:
        score += 5
        reasons.append(f"Near 52w Low ({hl_pos:.1f}%)")
    
    # Stochastic RSI signals (range: -5 to +10)
    stoch_k = indicators['stoch_k']
    if stoch_k < 20:
        score += 10
        reasons.append(f"Stoch Oversold ({stoch_k:.1f})")
    elif stoch_k > 80:
        score += 5
    
    # Determine state
    if score >= 80:
        state = "🔥 ACTIVE"
    elif score >= 50:
        state = "👀 WATCH"
    else:
        state = "⚠️ NOISE"
    
    return state, score, reasons

def create_price_chart(df: pd.DataFrame, ticker: str) -> Optional[go.Figure]:
    """Create candlestick chart with moving averages"""
    if df is None or len(df) < 20:
        return None
    
    try:
        df_copy = df.copy()
        df_copy['MA20'] = df_copy['Close'].rolling(window=20).mean()
        df_copy['MA50'] = df_copy['Close'].rolling(window=50).mean()
        
        fig = go.Figure()
        
        # Candlestick
        fig.add_trace(go.Candlestick(
            x=df_copy.index,
            open=df_copy['Open'],
            high=df_copy['High'],
            low=df_copy['Low'],
            close=df_copy['Close'],
            name=ticker,
        ))
        
        # Moving averages
        fig.add_trace(go.Scatter(
            x=df_copy.index, y=df_copy['MA20'],
            name='MA20', line=dict(color='orange', width=1),
            hovertemplate='<b>MA20</b><br>%{y:.2f}<extra></extra>'
        ))
        
        fig.add_trace(go.Scatter(
            x=df_copy.index, y=df_copy['MA50'],
            name='MA50', line=dict(color='blue', width=1),
            hovertemplate='<b>MA50</b><br>%{y:.2f}<extra></extra>'
        ))
        
        fig.update_layout(
            title=f"{ticker} - Price Action",
            yaxis_title="Price ($)",
            xaxis_title="Date",
            template="plotly_dark",
            height=500,
            hovermode='x unified',
            xaxis_rangeslider_visible=False
        )
        
        return fig
    except Exception as e:
        logger.error(f"Error creating chart: {e}")
        return None

def create_rsi_chart(df: pd.DataFrame, ticker: str) -> Optional[go.Figure]:
    """Create RSI indicator chart"""
    if df is None or len(df) < 14:
        return None
    
    try:
        close = df['Close'].values
        rsi = talib.RSI(close, timeperiod=14)
        
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=df.index, y=rsi,
            name='RSI(14)', line=dict(color='purple', width=2),
            fill='tozeroy'
        ))
        
        # Overbought/Oversold lines
        fig.add_hline(y=70, line_dash="dash", line_color="red", annotation_text="Overbought (70)")
        fig.add_hline(y=30, line_dash="dash", line_color="green", annotation_text="Oversold (30)")
        
        fig.update_layout(
            title=f"{ticker} - RSI(14)",
            yaxis_title="RSI",
            xaxis_title="Date",
            template="plotly_dark",
            height=350,
            hovermode='x unified',
            yaxis=dict(range=[0, 100])
        )
        
        return fig
    except Exception as e:
        logger.error(f"Error creating RSI chart: {e}")
        return None

def create_volume_chart(df: pd.DataFrame, ticker: str) -> Optional[go.Figure]:
    """Create volume chart"""
    if df is None:
        return None
    
    try:
        df_copy = df.copy()
        df_copy['MA_Vol'] = df_copy['Volume'].rolling(window=20).mean()
        
        colors = ['green' if row['Close'] >= row['Open'] else 'red' for idx, row in df_copy.iterrows()]
        
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            x=df_copy.index, y=df_copy['Volume'],
            name='Volume', marker_color=colors,
            hovertemplate='<b>Volume</b><br>%{y:.0f}<extra></extra>'
        ))
        
        fig.add_trace(go.Scatter(
            x=df_copy.index, y=df_copy['MA_Vol'],
            name='MA20', line=dict(color='yellow', width=2),
            hovertemplate='<b>MA20 Vol</b><br>%{y:.0f}<extra></extra>'
        ))
        
        fig.update_layout(
            title=f"{ticker} - Volume",
            yaxis_title="Volume",
            xaxis_title="Date",
            template="plotly_dark",
            height=350,
            hovermode='x unified',
            showlegend=True
        )
        
        return fig
    except Exception as e:
        logger.error(f"Error creating volume chart: {e}")
        return None

# ============================================================================
# APP HEADER
# ============================================================================

col1, col2 = st.columns([3, 1])
with col1:
    st.title("🚀 Momentum Activation Engine")
    st.subheader("Real-Time Small-Cap Runner Detector")
with col2:
    st.metric("Last Scan", datetime.now().strftime("%H:%M:%S"))

# ============================================================================
# SIDEBAR CONFIGURATION
# ============================================================================

with st.sidebar:
    st.header("⚙️ Configuration")
    
    scan_type = st.radio(
        "Scan Type",
        ["Manual Tickers", "Top Gainers", "Top Losers", "Most Active"],
        help="Choose how to populate ticker list"
    )
    
    timeframe = st.selectbox(
        "Analysis Timeframe",
        ["1d", "5d", "1mo", "3mo", "6mo", "1y"],
        help="Historical period for technical analysis",
        index=2
    )
    
    st.markdown("### Technical Thresholds")
    rsi_threshold_low = st.slider("RSI Oversold", 0, 50, 30, help="Lower = more oversold signals")
    rsi_threshold_high = st.slider("RSI Overbought", 50, 100, 70, help="Higher = more overbought signals")
    volume_multiplier = st.slider("Volume Spike", 1.0, 5.0, 2.0, 0.1, help="Volume multiple above average")
    
    st.markdown("### Display Options")
    show_charts = st.checkbox("Show Technical Charts", value=True)
    show_details = st.checkbox("Show Detailed Analysis", value=True)
    show_alerts = st.checkbox("Show Trade Alerts", value=True)

# ============================================================================
# TICKER INPUT
# ============================================================================

st.divider()

if scan_type == "Manual Tickers":
    tickers_input = st.text_input(
        "Enter tickers (comma separated)",
        value="PLTR,MSTR,COIN,MARA,RIOT,SOFI,HYLN,RGTI,NVTS",
        placeholder="E.g., AAPL,MSFT,TSLA"
    )
    tickers = [t.strip().upper() for t in tickers_input.split(",") if t.strip()]
else:
    # Default top movers for demo
    if scan_type == "Top Gainers":
        tickers = ["NVDA", "MSTR", "PLTR", "MARA", "RIOT", "COIN", "SOFI", "GME"]
    elif scan_type == "Top Losers":
        tickers = ["F", "BAC", "WFC", "GE", "X", "AA", "PBR", "VALE"]
    else:  # Most Active
        tickers = ["SPY", "QQQ", "IWM", "XLF", "XLE", "GLD", "TLT", "VIX"]
    
    st.info(f"📊 Scanning {len(tickers)} {scan_type.lower()}")

# ============================================================================
# SCAN BUTTON & RESULTS
# ============================================================================

if st.button("🔍 SCAN MOMENTUM", use_container_width=True, type="primary"):
    if not tickers:
        st.error("Please enter at least one ticker")
    else:
        results = []
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for idx, ticker in enumerate(tickers):
            status_text.text(f"📡 Scanning {ticker}... ({idx+1}/{len(tickers)})")
            
            try:
                # Fetch data
                df = fetch_stock_data(ticker, period=timeframe)
                if df is None:
                    continue
                
                # Calculate indicators
                indicators = calculate_indicators(df)
                if indicators is None:
                    continue
                
                # Determine state
                state, score, reasons = determine_state(
                    indicators, 
                    rsi_threshold_low, 
                    rsi_threshold_high,
                    volume_multiplier
                )
                
                results.append({
                    'Ticker': ticker,
                    'State': state,
                    'Score': score,
                    'Price': indicators['current_price'],
                    'Change 1D': indicators['price_change_1d'],
                    'Change 5D': indicators['price_change_5d'],
                    'RSI': indicators['rsi'],
                    'Volume Ratio': indicators['volume_ratio'],
                    'ADX': indicators['adx'],
                    'MACD': indicators['macd_hist'],
                    'Reasons': reasons,
                    'Chart': df,
                    'Indicators': indicators,
                })
                
            except Exception as e:
                logger.error(f"Error processing {ticker}: {e}")
            
            progress_bar.progress((idx + 1) / len(tickers))
        
        status_text.empty()
        progress_bar.empty()
        
        if results:
            # Sort by score
            results_sorted = sorted(results, key=lambda x: x['Score'], reverse=True)
            
            # ====== RESULTS TABLE ======
            st.subheader("📊 Scan Results")
            
            display_df = pd.DataFrame([
                {
                    'Ticker': r['Ticker'],
                    'State': r['State'],
                    'Score': r['Score'],
                    'Price': f"${r['Price']:.2f}",
                    'Change 1D': f"{r['Change 1D']:+.1f}%",
                    'Change 5D': f"{r['Change 5D']:+.1f}%",
                    'RSI': f"{r['RSI']:.0f}",
                    'Vol': f"{r['Volume Ratio']:.1f}x",
                    'ADX': f"{r['ADX']:.0f}",
                }
                for r in results_sorted
            ])
            
            def style_state(val):
                if '🔥' in str(val):
                    return 'background-color: #d4edda; color: #155724; font-weight: bold'
                elif '👀' in str(val):
                    return 'background-color: #fff3cd; color: #856404; font-weight: bold'
                else:
                    return 'background-color: #f8d7da; color: #721c24; font-weight: bold'
            
            styled_df = display_df.style.applymap(style_state, subset=['State'])
            st.dataframe(styled_df, use_container_width=True, hide_index=True)
            
            # ====== SUMMARY METRICS ======
            col1, col2, col3, col4 = st.columns(4)
            active_count = sum(1 for r in results if '🔥' in r['State'])
            watch_count = sum(1 for r in results if '👀' in r['State'])
            noise_count = sum(1 for r in results if '⚠️' in r['State'])
            avg_score = np.mean([r['Score'] for r in results])
            
            with col1:
                st.metric("🔥 Active", active_count, delta=f"{(active_count/len(results)*100):.0f}%")
            with col2:
                st.metric("👀 Watch", watch_count, delta=f"{(watch_count/len(results)*100):.0f}%")
            with col3:
                st.metric("⚠️ Noise", noise_count, delta=f"{(noise_count/len(results)*100):.0f}%")
            with col4:
                st.metric("📈 Avg Score", f"{avg_score:.0f}", delta="Overall")
            
            # ====== DETAILED ANALYSIS ======
            if show_details:
                st.subheader("🔬 Detailed Analysis")
                
                for result in results_sorted:
                    with st.expander(f"{result['Ticker']} - {result['State']} (Score: {result['Score']})", expanded=False):
                        tab1, tab2, tab3, tab4 = st.tabs(["Overview", "Charts", "Indicators", "Analysis"])
                        
                        with tab1:
                            col1, col2, col3 = st.columns(3)
                            
                            with col1:
                                st.metric("Price", f"${result['Price']:.2f}")
                                st.metric("RSI(14)", f"{result['RSI']:.1f}")
                                st.metric("Score", result['Score'])
                            
                            with col2:
                                st.metric("1D Change", f"{result['Change 1D']:+.1f}%")
                                st.metric("5D Change", f"{result['Change 5D']:+.1f}%")
                                st.metric("Volume", f"{result['Volume Ratio']:.1f}x")
                            
                            with col3:
                                ind = result['Indicators']
                                st.metric("ADX", f"{ind['adx']:.1f}")
                                st.metric("MACD", f"{ind['macd_hist']:.4f}")
                                st.metric("BB Pos", f"{ind['bb_position']:.0%}")
                        
                        with tab2:
                            if show_charts:
                                chart1 = create_price_chart(result['Chart'], result['Ticker'])
                                if chart1:
                                    st.plotly_chart(chart1, use_container_width=True)
                                
                                col1, col2 = st.columns(2)
                                with col1:
                                    chart2 = create_rsi_chart(result['Chart'], result['Ticker'])
                                    if chart2:
                                        st.plotly_chart(chart2, use_container_width=True)
                                with col2:
                                    chart3 = create_volume_chart(result['Chart'], result['Ticker'])
                                    if chart3:
                                        st.plotly_chart(chart3, use_container_width=True)
                        
                        with tab3:
                            ind = result['Indicators']
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                st.write("**Momentum Indicators**")
                                st.write(f"RSI: {ind['rsi']:.2f}")
                                st.write(f"Stoch RSI K: {ind['stoch_k']:.2f}")
                                st.write(f"CCI: {ind['cci']:.2f}")
                                st.write(f"MACD Histogram: {ind['macd_hist']:.4f}")
                            
                            with col2:
                                st.write("**Volatility & Trend**")
                                st.write(f"ADX: {ind['adx']:.2f}")
                                st.write(f"ATR: ${ind['atr']:.2f} ({ind['atr_percent']:.2f}%)")
                                st.write(f"BB Position: {ind['bb_position']:.0%}")
                                st.write(f"52w Position: {ind['high_low_position']:.1f}%")
                        
                        with tab4:
                            st.write("**Analysis Signals:**")
                            for reason in result['Reasons']:
                                st.write(f"• {reason}")
            
            # ====== TRADE ALERTS ======
            if show_alerts:
                st.subheader("🚨 Trade Alerts")
                
                active_tickers = [r for r in results_sorted if '🔥' in r['State']]
                
                if active_tickers:
                    for ticker_result in active_tickers[:3]:  # Top 3 active
                        with st.container():
                            ind = ticker_result['Indicators']
                            col1, col2 = st.columns([3, 1])
                            
                            with col1:
                                st.write(f"### {ticker_result['Ticker']}")
                                
                                # Entry signals
                                entry_signals = []
                                if ind['rsi'] < rsi_threshold_low:
                                    entry_signals.append("✅ RSI Oversold - Buy Signal")
                                if ind['volume_ratio'] > volume_multiplier:
                                    entry_signals.append(f"✅ Volume Spike - {ind['volume_ratio']:.1f}x")
                                if ind['macd_hist'] > 0:
                                    entry_signals.append("✅ MACD Bullish Crossover")
                                
                                for signal in entry_signals:
                                    st.success(signal)
                                
                                # Risk management
                                st.write(f"**Support:** ${ind['bb_low']:.2f}")
                                st.write(f"**Resistance:** ${ind['bb_high']:.2f}")
                                st.write(f"**Risk/Reward:** {abs(ind['current_price'] - ind['bb_low']) / abs(ind['bb_high'] - ind['current_price']):.2f}")
                            
                            with col2:
                                st.metric("Score", ticker_result['Score'], delta="High Priority")
                            
                            st.divider()
                else:
                    st.info("No active trade signals at this time.")
        else:
            st.error("❌ No valid data retrieved for the given tickers")

# ============================================================================
# FOOTER
# ============================================================================

st.divider()
col1, col2, col3 = st.columns(3)
with col1:
    st.caption(f"📡 Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")
with col2:
    st.caption("🔄 Real-time market data via Yahoo Finance")
with col3:
    st.caption("⚠️ Disclaimer: Not financial advice - Educational use only")
