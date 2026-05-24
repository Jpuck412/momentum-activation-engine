import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, time
import yfinance as yf
import talib
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import logging
from functools import lru_cache
import pytz

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Page configuration
st.set_page_config(
    page_title="Day Trader Engine - 4AM-8PM",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for day trader
st.markdown("""
<style>
    .main {
        padding-top: 0.5rem;
    }
    .speed-badge-hot {
        background-color: #ff4444;
        color: white;
        padding: 8px 12px;
        border-radius: 4px;
        font-weight: bold;
        font-size: 14px;
        display: inline-block;
    }
    .speed-badge-warm {
        background-color: #ffaa00;
        color: black;
        padding: 8px 12px;
        border-radius: 4px;
        font-weight: bold;
        font-size: 14px;
        display: inline-block;
    }
    .speed-badge-cool {
        background-color: #00aa00;
        color: white;
        padding: 8px 12px;
        border-radius: 4px;
        font-weight: bold;
        font-size: 14px;
        display: inline-block;
    }
    .metric-big {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 8px;
        color: white;
        font-size: 18px;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# MARKET HOURS CHECK
# ============================================================================

def get_market_status():
    """Check if market is within trading hours (4AM - 8PM ET)"""
    now = datetime.now(pytz.timezone('US/Eastern'))
    current_time = now.time()
    
    market_open = time(4, 0)  # 4AM ET
    market_close = time(20, 0)  # 8PM ET
    
    if market_open <= current_time <= market_close:
        return "OPEN", now
    else:
        return "CLOSED", now

# ============================================================================
# FAST DATA FETCHING - 1min, 5min, 15min
# ============================================================================

@st.cache_data(ttl=60)  # Refresh every 60 seconds for day trading
def fetch_intraday_data(ticker: str, interval: str = "1m", period: str = "1d") -> pd.DataFrame:
    """Fetch ultra-fast intraday data (1m, 5m, 15m candles)"""
    try:
        data = yf.download(
            ticker, 
            interval=interval, 
            period=period,
            progress=False,
            threads=False,
            prepost=True  # Include pre-market and after-hours
        )
        if len(data) == 0:
            return None
        
        # Add timestamp
        data['Timestamp'] = data.index
        return data
    except Exception as e:
        logger.error(f"Error fetching {interval} data for {ticker}: {e}")
        return None

# ============================================================================
# SPEED ANALYSIS - Check Price Action First
# ============================================================================

def analyze_speed_and_price(df: pd.DataFrame) -> dict:
    """Analyze speed (volatility/momentum) and price action FIRST"""
    if df is None or len(df) < 3:
        return None
    
    try:
        close = df['Close'].values
        high = df['High'].values
        low = df['Low'].values
        volume = df['Volume'].values
        
        # SPEED: Recent price momentum (last 5 candles)
        price_range_5 = np.max(high[-5:]) - np.min(low[-5:])
        price_change_5 = ((close[-1] - close[-5]) / close[-5] * 100) if len(close) >= 5 else 0
        current_price = close[-1]
        
        # SPREAD: Bid-Ask equivalent (current candle)
        current_candle_spread = (high[-1] - low[-1]) / close[-1] * 100
        avg_spread = np.mean([(high[i] - low[i]) / close[i] * 100 for i in range(len(close))])
        
        # VOLUME: Current vs Average
        avg_volume_20 = np.mean(volume[-20:]) if len(volume) >= 20 else np.mean(volume)
        current_volume = volume[-1]
        volume_ratio = current_volume / avg_volume_20 if avg_volume_20 > 0 else 1
        
        # VOLATILITY (Speed indicator)
        atr = talib.ATR(high, low, close, timeperiod=14)[-1] if len(close) >= 14 else 0
        atr_percent = (atr / current_price) * 100 if current_price > 0 else 0
        
        # Recent volatility (last 10 candles)
        recent_volatility = np.std(close[-10:]) / np.mean(close[-10:]) * 100
        
        # Determine SPEED category
        if atr_percent > 2.5 or recent_volatility > 3:
            speed = "🔥 HOT"
            speed_score = 90
        elif atr_percent > 1.5 or recent_volatility > 2:
            speed = "⚠️ WARM"
            speed_score = 60
        else:
            speed = "❄️ COOL"
            speed_score = 30
        
        # Price momentum direction
        if price_change_5 > 2:
            momentum = "📈 UP"
        elif price_change_5 < -2:
            momentum = "📉 DOWN"
        else:
            momentum = "↔️ FLAT"
        
        return {
            'current_price': current_price,
            'price_change_5': price_change_5,
            'speed': speed,
            'speed_score': speed_score,
            'atr': atr,
            'atr_percent': atr_percent,
            'volatility': recent_volatility,
            'current_spread': current_candle_spread,
            'avg_spread': avg_spread,
            'volume_ratio': volume_ratio,
            'current_volume': current_volume,
            'avg_volume': avg_volume_20,
            'momentum': momentum,
            'price_range_5': price_range_5
        }
    except Exception as e:
        logger.error(f"Error analyzing speed: {e}")
        return None

# ============================================================================
# VOLUME ANALYSIS - Before Indicators
# ============================================================================

def analyze_volume_profile(df: pd.DataFrame, speed_data: dict) -> dict:
    """Analyze volume profile and accumulation/distribution"""
    if df is None or speed_data is None:
        return None
    
    try:
        close = df['Close'].values
        high = df['High'].values
        low = df['Low'].values
        volume = df['Volume'].values
        
        # On-Balance Volume (OBV)
        obv = talib.OBV(close, volume)
        obv_current = obv[-1]
        obv_prev = obv[-2] if len(obv) > 1 else obv[-1]
        obv_direction = "UP" if obv_current > obv_prev else "DOWN"
        
        # Accumulation/Distribution Line
        ad_line = talib.AD(high, low, close, volume)
        ad_current = ad_line[-1]
        ad_prev = ad_line[-2] if len(ad_line) > 1 else ad_line[-1]
        ad_direction = "ACCUM" if ad_current > ad_prev else "DISTRIB"
        
        # Volume trend (increasing or decreasing)
        vol_trend = np.mean(volume[-5:]) / np.mean(volume[-10:-5]) if len(volume) >= 10 else 1
        vol_trend_direction = "INCREASING" if vol_trend > 1.2 else "DECREASING" if vol_trend < 0.8 else "STABLE"
        
        # VWAP-like calculation (Volume Weighted)
        typical_price = (high + low + close) / 3
        vwap = np.sum(typical_price[-20:] * volume[-20:]) / np.sum(volume[-20:]) if len(volume) >= 20 else close[-1]
        price_vs_vwap = "ABOVE" if close[-1] > vwap else "BELOW"
        
        # Volume spike detection
        max_vol_20 = np.max(volume[-20:]) if len(volume) >= 20 else np.max(volume)
        vol_spike = current_vol / max_vol_20 if (current_vol := volume[-1]) < max_vol_20 else volume[-1] / max_vol_20
        spike_strength = "EXTREME" if vol_spike > 2.0 else "STRONG" if vol_spike > 1.5 else "NORMAL"
        
        return {
            'obv': obv_current,
            'obv_direction': obv_direction,
            'ad_line': ad_current,
            'ad_direction': ad_direction,
            'vol_trend': vol_trend,
            'vol_trend_direction': vol_trend_direction,
            'vwap': vwap,
            'price_vs_vwap': price_vs_vwap,
            'vol_spike_ratio': vol_spike,
            'spike_strength': spike_strength
        }
    except Exception as e:
        logger.error(f"Error analyzing volume: {e}")
        return None

# ============================================================================
# TECHNICAL INDICATORS - After Speed and Volume
# ============================================================================

def calculate_trading_indicators(df: pd.DataFrame) -> dict:
    """Calculate focused trading indicators (RSI, MACD, Bollinger Bands)"""
    if df is None or len(df) < 20:
        return None
    
    try:
        close = df['Close'].values
        high = df['High'].values
        low = df['Low'].values
        
        # RSI (Relative Strength Index)
        rsi = talib.RSI(close, timeperiod=14)[-1]
        rsi_signal = "OVERSOLD" if rsi < 30 else "OVERBOUGHT" if rsi > 70 else "NEUTRAL"
        
        # MACD (Moving Average Convergence Divergence)
        macd, signal, hist = talib.MACD(close, fastperiod=12, slowperiod=26, signalperiod=9)
        macd_current = macd[-1]
        macd_signal_val = signal[-1]
        macd_hist = hist[-1]
        
        if len(macd) > 1:
            macd_prev = macd[-2]
            macd_crossover = "BULLISH" if macd_current > macd_signal_val and macd_prev <= signal[-2] else "BEARISH" if macd_current < macd_signal_val and macd_prev >= signal[-2] else "NEUTRAL"
        else:
            macd_crossover = "NEUTRAL"
        
        # Bollinger Bands
        bb_high, bb_mid, bb_low = talib.BBANDS(close, timeperiod=20, nbdevup=2, nbdevdn=2, matype=0)
        bb_high_val = bb_high[-1]
        bb_mid_val = bb_mid[-1]
        bb_low_val = bb_low[-1]
        bb_position = (close[-1] - bb_low_val) / (bb_high_val - bb_low_val) if (bb_high_val - bb_low_val) != 0 else 0.5
        
        if bb_position > 0.8:
            bb_signal = "OVERBOUGHT (Upper Band)"
        elif bb_position < 0.2:
            bb_signal = "OVERSOLD (Lower Band)"
        else:
            bb_signal = "NEUTRAL (Middle)"
        
        # Moving Averages (Fast & Slow)
        ema_9 = talib.EMA(close, timeperiod=9)[-1]
        ema_21 = talib.EMA(close, timeperiod=21)[-1]
        ma_cross = "BULLISH" if ema_9 > ema_21 else "BEARISH"
        
        # Stochastic RSI (for fast confirmation)
        stoch_rsi = talib.STOCHRSI(close, timeperiod=14, fastk_period=3, fastd_period=3, fastd_matype=0)
        stoch_k = stoch_rsi[2][-1] * 100 if len(stoch_rsi[2]) > 0 else 50
        stoch_d = stoch_rsi[3][-1] * 100 if len(stoch_rsi[3]) > 0 else 50
        stoch_signal = "OVERSOLD" if stoch_k < 20 else "OVERBOUGHT" if stoch_k > 80 else "NEUTRAL"
        
        return {
            'rsi': rsi,
            'rsi_signal': rsi_signal,
            'macd': macd_current,
            'macd_signal': macd_signal_val,
            'macd_hist': macd_hist,
            'macd_crossover': macd_crossover,
            'bb_high': bb_high_val,
            'bb_mid': bb_mid_val,
            'bb_low': bb_low_val,
            'bb_position': bb_position,
            'bb_signal': bb_signal,
            'ema_9': ema_9,
            'ema_21': ema_21,
            'ma_cross': ma_cross,
            'stoch_k': stoch_k,
            'stoch_d': stoch_d,
            'stoch_signal': stoch_signal
        }
    except Exception as e:
        logger.error(f"Error calculating indicators: {e}")
        return None

# ============================================================================
# TRADE SIGNAL GENERATION
# ============================================================================

def generate_trade_signal(speed_data: dict, volume_data: dict, indicators: dict) -> tuple:
    """Generate trade signals: BUY or SELL with confidence"""
    if not all([speed_data, volume_data, indicators]):
        return "WAIT", 0, []
    
    signals = []
    score = 0
    
    # SPEED CHECK (Primary)
    if speed_data['speed'] == "🔥 HOT":
        score += 30
        signals.append(f"🔥 SPEED: {speed_data['speed']} (ATR: {speed_data['atr_percent']:.2f}%)")
    elif speed_data['speed'] == "⚠️ WARM":
        score += 15
        signals.append(f"⚠️ SPEED: {speed_data['speed']} (ATR: {speed_data['atr_percent']:.2f}%)")
    
    # VOLUME CHECK (Primary)
    if volume_data['spike_strength'] == "EXTREME":
        score += 35
        signals.append(f"📊 VOLUME: {volume_data['spike_strength']} SPIKE ({volume_data['vol_spike_ratio']:.1f}x)")
    elif volume_data['spike_strength'] == "STRONG":
        score += 20
        signals.append(f"📊 VOLUME: {volume_data['spike_strength']} ({volume_data['vol_spike_ratio']:.1f}x)")
    
    # VOLUME DIRECTION
    if volume_data['obv_direction'] == "UP":
        score += 15
        signals.append(f"📈 OBV: Accumulation")
    elif volume_data['ad_direction'] == "ACCUM":
        score += 10
        signals.append(f"💰 A/D: Accumulation")
    
    # PRICE vs VWAP
    if speed_data['momentum'] == "📈 UP" and volume_data['price_vs_vwap'] == "ABOVE":
        score += 20
        signals.append(f"⬆️ PRICE ABOVE VWAP + UPTREND")
    elif speed_data['momentum'] == "📉 DOWN" and volume_data['price_vs_vwap'] == "BELOW":
        score += 20
        signals.append(f"⬇️ PRICE BELOW VWAP + DOWNTREND")
    
    # INDICATOR CONFIRMATION (Secondary)
    if indicators['macd_crossover'] == "BULLISH":
        score += 15
        signals.append(f"✅ MACD: Bullish Crossover")
    elif indicators['macd_crossover'] == "BEARISH":
        score -= 10
        signals.append(f"❌ MACD: Bearish Crossover")
    
    if indicators['ma_cross'] == "BULLISH":
        score += 10
        signals.append(f"✅ EMA: 9 > 21 (Bullish)")
    elif indicators['ma_cross'] == "BEARISH":
        score -= 5
        signals.append(f"❌ EMA: 9 < 21 (Bearish)")
    
    # RSI Confirmation
    if indicators['rsi_signal'] == "OVERSOLD":
        score += 20
        signals.append(f"🔽 RSI: Oversold ({indicators['rsi']:.0f})")
    elif indicators['rsi_signal'] == "OVERBOUGHT":
        score -= 15
        signals.append(f"🔼 RSI: Overbought ({indicators['rsi']:.0f})")
    
    # Bollinger Bands
    if indicators['bb_signal'] == "OVERSOLD (Lower Band)":
        score += 15
        signals.append(f"📌 BB: At Lower Band (Reversal)")
    elif indicators['bb_signal'] == "OVERBOUGHT (Upper Band)":
        score -= 10
        signals.append(f"📌 BB: At Upper Band")
    
    # Determine Signal
    if score >= 70:
        signal = "🟢 BUY"
    elif score <= -30:
        signal = "🔴 SELL"
    else:
        signal = "⚪ HOLD"
    
    return signal, score, signals

# ============================================================================
# APP HEADER
# ============================================================================

market_status, now = get_market_status()

col1, col2, col3 = st.columns([2, 2, 1])
with col1:
    st.title("⚡ DAY TRADER ENGINE")
    st.subheader("Pre-Market to 8PM • 1min | 5min | 15min")
with col2:
    status_color = "🟢" if market_status == "OPEN" else "🔴"
    st.write(f"### {status_color} {market_status}")
    st.write(f"{now.strftime('%I:%M %p ET')}")
with col3:
    st.metric("Last Update", now.strftime("%H:%M:%S"))

st.divider()

# ============================================================================
# SIDEBAR CONFIGURATION
# ============================================================================

with st.sidebar:
    st.header("⚡ FAST EXECUTION SETUP")
    
    st.markdown("### 📊 TIMEFRAMES (Pick 1+)")
    timeframes = st.multiselect(
        "Select candle timeframes",
        ["1m", "5m", "15m"],
        default=["1m", "5m"],
        help="1m = Ultra-fast, 5m = Standard, 15m = Confirmation"
    )
    
    if not timeframes:
        timeframes = ["1m"]
    
    st.markdown("### ⚙️ SPEED THRESHOLDS")
    atr_threshold = st.slider("ATR% Minimum for 🔥 HOT", 0.5, 5.0, 2.0, 0.1)
    vol_multiple = st.slider("Volume Spike Multiple", 1.0, 5.0, 1.5, 0.1)
    
    st.markdown("### 🎯 SIGNAL SETTINGS")
    min_signal_score = st.slider("Min Signal Score", 30, 100, 60, 10)
    
    st.markdown("### 📈 ANALYSIS ORDER")
    st.write("1️⃣ **SPEED** (ATR, Volatility)")
    st.write("2️⃣ **SPREAD** (Bid-Ask width)")
    st.write("3️⃣ **VOLUME** (Spikes, OBV, A/D)")
    st.write("4️⃣ **INDICATORS** (RSI, MACD, BB)")

# ============================================================================
# TICKER INPUT
# ============================================================================

st.divider()

col1, col2 = st.columns([3, 1])
with col1:
    tickers_input = st.text_input(
        "Enter Tickers (comma-separated) - DAY TRADING STOCKS",
        value="PLTR,MSTR,NVDA,AMD,SOFI,F,GME,AMC,TSLA",
        placeholder="E.g., PLTR,MSTR,AMD"
    )
with col2:
    scan_button = st.button("⚡ EXECUTE SCAN", use_container_width=True, type="primary")

tickers = [t.strip().upper() for t in tickers_input.split(",") if t.strip()]

# ============================================================================
# MAIN SCAN & ANALYSIS
# ============================================================================

if scan_button:
    if not tickers:
        st.error("❌ Enter at least one ticker")
    else:
        st.subheader("⚡ SCANNING...")
        
        results = []
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        total_items = len(tickers) * len(timeframes)
        current = 0
        
        for ticker_idx, ticker in enumerate(tickers):
            for tf_idx, timeframe in enumerate(timeframes):
                current += 1
                status_text.text(f"🔍 {ticker} ({timeframe}) - {current}/{total_items}")
                
                try:
                    # Fetch data
                    df = fetch_intraday_data(ticker, interval=timeframe, period="1d")
                    if df is None or len(df) < 20:
                        continue
                    
                    # Analyze in order: SPEED → SPREAD → VOLUME → INDICATORS
                    speed_data = analyze_speed_and_price(df)
                    volume_data = analyze_volume_profile(df, speed_data)
                    indicators = calculate_trading_indicators(df)
                    
                    if not all([speed_data, volume_data, indicators]):
                        continue
                    
                    # Generate signal
                    signal, score, signal_reasons = generate_trade_signal(speed_data, volume_data, indicators)
                    
                    # Only show qualified signals
                    if score >= min_signal_score or signal != "⚪ HOLD":
                        results.append({
                            'Ticker': ticker,
                            'Timeframe': timeframe,
                            'Signal': signal,
                            'Score': score,
                            'Price': f"${speed_data['current_price']:.2f}",
                            'Speed': speed_data['speed'],
                            'ATR%': f"{speed_data['atr_percent']:.2f}%",
                            'Spread': f"{speed_data['current_spread']:.3f}%",
                            'Volume': f"{speed_data['volume_ratio']:.1f}x",
                            'RSI': f"{indicators['rsi']:.0f}",
                            'MACD': indicators['macd_crossover'],
                            'BB': indicators['bb_signal'],
                            'Reasons': signal_reasons,
                            'Data': df,
                            'Speed': speed_data,
                            'Volume': volume_data,
                            'Indicators': indicators
                        })
                    
                except Exception as e:
                    logger.error(f"Error processing {ticker} {timeframe}: {e}")
                
                progress_bar.progress(current / total_items)
        
        status_text.empty()
        progress_bar.empty()
        
        if results:
            # Sort by score (highest first)
            results_sorted = sorted(results, key=lambda x: x['Score'], reverse=True)
            
            # ====== QUICK SCAN TABLE ======
            st.subheader("⚡ LIVE SCAN RESULTS")
            
            display_data = []
            for r in results_sorted:
                signal_color = "🟢" if "BUY" in r['Signal'] else "🔴" if "SELL" in r['Signal'] else "⚪"
                display_data.append({
                    'Signal': f"{signal_color} {r['Signal']}",
                    'Ticker': r['Ticker'],
                    'TF': r['Timeframe'],
                    'Score': r['Score'],
                    'Price': r['Price'],
                    'Speed': r['Speed'],
                    'ATR%': r['ATR%'],
                    'Spread': r['Spread'],
                    'Volume': r['Volume'],
                    'RSI': r['RSI'],
                    'MACD': r['MACD'],
                })
            
            display_df = pd.DataFrame(display_data)
            st.dataframe(display_df, use_container_width=True, hide_index=True)
            
            # ====== STATISTICS ======
            col1, col2, col3, col4, col5 = st.columns(5)
            buy_count = sum(1 for r in results if "BUY" in r['Signal'])
            sell_count = sum(1 for r in results if "SELL" in r['Signal'])
            hold_count = sum(1 for r in results if "HOLD" in r['Signal'])
            avg_score = np.mean([r['Score'] for r in results])
            avg_volume = np.mean([float(r['Volume'].split('x')[0]) for r in results])
            
            with col1:
                st.metric("🟢 BUY Signals", buy_count)
            with col2:
                st.metric("🔴 SELL Signals", sell_count)
            with col3:
                st.metric("⚪ HOLD", hold_count)
            with col4:
                st.metric("📊 Avg Score", f"{avg_score:.0f}")
            with col5:
                st.metric("📈 Avg Vol", f"{avg_volume:.1f}x")
            
            # ====== DETAILED TRADE ANALYSIS ======
            st.subheader("📊 DETAILED TRADE SETUPS")
            
            for result in results_sorted[:10]:  # Top 10 setups
                with st.expander(
                    f"{result['Signal']} {result['Ticker']} ({result['Timeframe']}) - Score: {result['Score']} - ${result['Price']}",
                    expanded=False
                ):
                    # Create columns for analysis
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.write("**⚡ SPEED**")
                        st.write(f"Status: {result['Speed']['speed']}")
                        st.write(f"ATR: {result['Speed']['atr_percent']:.2f}%")
                        st.write(f"Volatility: {result['Speed']['volatility']:.2f}%")
                        st.write(f"Momentum: {result['Speed']['momentum']}")
                    
                    with col2:
                        st.write("**📊 VOLUME & SPREAD**")
                        st.write(f"Volume Ratio: {result['Speed']['volume_ratio']:.2f}x")
                        st.write(f"Spread: {result['Speed']['current_spread']:.3f}%")
                        st.write(f"OBV: {result['Volume']['obv_direction']}")
                        st.write(f"A/D: {result['Volume']['ad_direction']}")
                        st.write(f"Spike: {result['Volume']['spike_strength']}")
                    
                    with col3:
                        st.write("**📈 INDICATORS**")
                        st.write(f"RSI: {result['Indicators']['rsi']:.0f} ({result['Indicators']['rsi_signal']})")
                        st.write(f"MACD: {result['Indicators']['macd_crossover']}")
                        st.write(f"EMA: {result['Indicators']['ma_cross']}")
                        st.write(f"Stoch: {result['Indicators']['stoch_k']:.0f} ({result['Indicators']['stoch_signal']})")
                    
                    st.divider()
                    
                    # Trade setup and reasons
                    st.write("**🎯 TRADE SETUP REASONS:**")
                    for reason in result['Reasons']:
                        st.write(f"✓ {reason}")
                    
                    # Entry/Exit levels
                    speed = result['Speed']
                    indicators = result['Indicators']
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.write("**ENTRY:**")
                        st.write(f"Price: ${speed['current_price']:.2f}")
                    with col2:
                        st.write("**SUPPORT:**")
                        st.write(f"${indicators['bb_low']:.2f}")
                    with col3:
                        st.write("**RESISTANCE:**")
                        st.write(f"${indicators['bb_high']:.2f}")
        
        else:
            st.warning("⏳ No strong signals found. Adjust thresholds or wait for better setup.")

st.divider()

# Footer
col1, col2, col3 = st.columns(3)
with col1:
    st.caption(f"⏰ {now.strftime('%I:%M:%S %p ET')} | Market: {market_status}")
with col2:
    st.caption("🔄 Refresh: 60s | Real-time Yahoo Finance")
with col3:
    st.caption("⚠️ Not financial advice - Day trading risk")
