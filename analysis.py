# analysis.py
import pandas as pd
import numpy as np
import ta
from datetime import datetime
import logging
from utils.data_fetcher import get_dhaka_time, fetch_data

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ProSignalAnalyzer:
    """প্রো মার্কেট সিগন্যাল অ্যানালাইজার - ৪-লেয়ার কনফ্লুয়েন্স সিস্টেম"""
    
    def __init__(self):
        self.version = "2.0"
        self.signal_history = []
        self.pattern_weights = {
            'bullish_engulfing': 25,
            'bearish_engulfing': -25,
            'hammer': 22,
            'shooting_star': -22,
            'bullish_harami': 15,
            'bearish_harami': -15,
            'doji': 0
        }
        
    def add_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """সমস্ত ইন্ডিকেটর যোগ করুন"""
        if df.empty or len(df) < 50:
            return df
        
        df = df.copy()
        
        try:
            # === ট্রেন্ড ইন্ডিকেটর ===
            for period in [9, 21, 50, 200]:
                df[f"EMA_{period}"] = ta.trend.ema_indicator(df["Close"], window=period)
            
            df["SMA_20"] = ta.trend.sma_indicator(df["Close"], window=20)
            df["ADX"] = ta.trend.adx(df["High"], df["Low"], df["Close"], window=14)
            
            # === মোমেন্টাম ===
            df["RSI"] = ta.momentum.rsi(df["Close"], window=14)
            
            macd = ta.trend.MACD(df["Close"])
            df["MACD"] = macd.macd()
            df["MACD_Signal"] = macd.macd_signal()
            df["MACD_Hist"] = macd.macd_diff()
            
            df["Stoch_K"] = ta.momentum.stoch(df["High"], df["Low"], df["Close"], window=14, smooth_window=3)
            df["Stoch_D"] = ta.momentum.stoch_signal(df["High"], df["Low"], df["Close"], window=14, smooth_window=3)
            
            # === ভোলাটিলিটি ===
            bb = ta.volatility.BollingerBands(df["Close"], window=20, window_dev=2)
            df["BB_High"] = bb.bollinger_hband()
            df["BB_Low"] = bb.bollinger_lband()
            df["BB_Mid"] = bb.bollinger_mavg()
            df["BB_Width"] = bb.bollinger_wband()
            df["BB_Position"] = (df["Close"] - df["BB_Low"]) / (df["BB_High"] - df["BB_Low"])
            
            df["ATR"] = ta.volatility.average_true_range(df["High"], df["Low"], df["Close"], window=14)
            df["ATR_Percent"] = (df["ATR"] / df["Close"]) * 100
            
            # === ভলিউম ===
            if "Volume" in df.columns:
                df["Volume_SMA"] = df["Volume"].rolling(20).mean()
                df["Volume_Ratio"] = df["Volume"] / df["Volume_SMA"]
            
            # === ক্যান্ডেল ===
            df["Body"] = df["Close"] - df["Open"]
            df["Body_Size"] = abs(df["Body"])
            df["Upper_Wick"] = df["High"] - df[["Open", "Close"]].max(axis=1)
            df["Lower_Wick"] = df[["Open", "Close"]].min(axis=1) - df["Low"]
            df["Candle_Range"] = df["High"] - df["Low"]
            
            df["Market_Regime"] = self._detect_regime(df)
            
        except Exception as e:
            logger.error(f"Indicator error: {e}")
            
        return df
    
    def _detect_regime(self, df: pd.DataFrame) -> str:
        """মার্কেট রেজিম ডিটেক্ট"""
        if "ADX" not in df.columns:
            return "Unknown"
        
        try:
            adx = df["ADX"].iloc[-1]
            bb_width = df["BB_Width"].iloc[-1]
            avg_bb = df["BB_Width"].rolling(20).mean().iloc[-1]
            
            if adx > 25 and bb_width > avg_bb:
                return "Strong_Trend"
            elif adx > 20:
                return "Weak_Trend"
            elif bb_width < avg_bb * 0.7:
                return "Ranging"
            else:
                return "Transition"
        except:
            return "Unknown"
    
    def detect_patterns(self, df: pd.DataFrame) -> list:
        """ক্যান্ডেলস্টিক প্যাটার্ন ডিটেক্ট"""
        if len(df) < 5:
            return []
        
        patterns = []
        curr = df.iloc[-1]
        prev = df.iloc[-2]
        
        try:
            body = curr["Body_Size"] if curr["Body_Size"] > 0 else 0.00001
            range_ = curr["Candle_Range"] if curr["Candle_Range"] > 0 else 0.00001
            
            # হ্যামার / শুটিং স্টার
            if curr["Lower_Wick"] >= (body * 2.0) and curr["Upper_Wick"] <= (body * 0.5):
                patterns.append(("Hammer", self.pattern_weights['hammer']))
            elif curr["Upper_Wick"] >= (body * 2.0) and curr["Lower_Wick"] <= (body * 0.5):
                patterns.append(("Shooting_Star", self.pattern_weights['shooting_star']))
            
            # ইঞ্জালফিং
            if prev["Body"] < 0 and curr["Body"] > 0 and curr["Close"] > prev["Open"]:
                patterns.append(("Bullish_Engulfing", self.pattern_weights['bullish_engulfing']))
            elif prev["Body"] > 0 and curr["Body"] < 0 and curr["Close"] < prev["Open"]:
                patterns.append(("Bearish_Engulfing", self.pattern_weights['bearish_engulfing']))
            
            # ডোজি
            if body <= (range_ * 0.1):
                patterns.append(("Doji", self.pattern_weights['doji']))
                
        except:
            pass
            
        return patterns
    
    def detect_sr(self, df: pd.DataFrame) -> dict:
        """সাপোর্ট/রেজিস্ট্যান্স লেভেল"""
        if len(df) < 30:
            return {"zone": "Neutral", "score": 0}
        
        curr_close = df["Close"].iloc[-1]
        recent_low = df["Low"].tail(30).min()
        recent_high = df["High"].tail(30).max()
        
        score = 0
        zone = "Neutral"
        
        if abs(curr_close - recent_low) / curr_close < 0.0015:
            zone = "Support"
            score = 15
        elif abs(curr_close - recent_high) / curr_close < 0.0015:
            zone = "Resistance"
            score = -15
        
        if "EMA_50" in df.columns:
            ema50 = df["EMA_50"].iloc[-1]
            if abs(curr_close - ema50) / curr_close < 0.001:
                zone += "_EMA"
                score += 8 if curr_close > ema50 else -8
        
        return {"zone": zone, "score": score}
    
    def check_mtf(self, pair: str) -> dict:
        """মাল্টি-টাইমফ্রেম অ্যানালাইসিস"""
        timeframes = ["15m", "1h", "4h"]
        trends = {}
        score = 0
        
        for tf in timeframes:
            df = fetch_data(pair, timeframe=tf, limit=30)
            if not df.empty and len(df) > 15:
                df = self.add_indicators(df)
                try:
                    ema9 = df["EMA_9"].iloc[-1]
                    ema21 = df["EMA_21"].iloc[-1]
                    
                    if ema9 > ema21:
                        trends[tf] = "Bullish"
                        score += 3
                    elif ema9 < ema21:
                        trends[tf] = "Bearish"
                        score -= 3
                except:
                    pass
        
        return {"trends": trends, "score": score}
    
    def check_confluence(self, df: pd.DataFrame) -> dict:
        """৪-লেয়ার কনফ্লুয়েন্স চেক"""
        latest = df.iloc[-1]
        confluence = {"bullish": 0, "bearish": 0, "signals": []}
        
        try:
            # RSI + MACD
            if latest["RSI"] < 40 and latest["MACD"] > latest["MACD_Signal"]:
                confluence["bullish"] += 2
                confluence["signals"].append("RSI_MACD")
            elif latest["RSI"] > 60 and latest["MACD"] < latest["MACD_Signal"]:
                confluence["bearish"] += 2
                confluence["signals"].append("RSI_MACD")
            
            # BB + EMA
            if latest["Close"] < latest["BB_Low"] and latest["Close"] > latest["EMA_21"]:
                confluence["bullish"] += 2
                confluence["signals"].append("BB_EMA")
            elif latest["Close"] > latest["BB_High"] and latest["Close"] < latest["EMA_21"]:
                confluence["bearish"] += 2
                confluence["signals"].append("BB_EMA")
            
            # Stochastic
            if latest["Stoch_K"] < 20 and latest["Stoch_D"] < 20:
                confluence["bullish"] += 1
                confluence["signals"].append("Stoch_Oversold")
            elif latest["Stoch_K"] > 80 and latest["Stoch_D"] > 80:
                confluence["bearish"] += 1
                confluence["signals"].append("Stoch_Overbought")
                
        except:
            pass
            
        return confluence
    
    def generate_signal(self, df: pd.DataFrame, pair: str = "", timeframe: str = "5m") -> dict:
        """মেইন সিগন্যাল জেনারেশন"""
        if df.empty or len(df) < 50:
            return self._default_signal("Not enough data")
        
        df = self.add_indicators(df)
        latest = df.iloc[-1]
        
        score = 50
        reasons = []
        
        try:
            # 1. MTF (30%)
            mtf = self.check_mtf(pair)
            score += mtf["score"] * 0.3
            reasons.append(f"MTF: {', '.join(mtf['trends'].values()) if mtf['trends'] else 'Neutral'}")
            
            # 2. প্যাটার্ন (25%)
            patterns = self.detect_patterns(df)
            if patterns:
                pattern_score = max(patterns, key=lambda x: abs(x[1]))[1]
                score += pattern_score * 0.25
                reasons.append(f"Pattern: {patterns[0][0]}")
            
            # 3. SR (20%)
            sr = self.detect_sr(df)
            score += sr["score"] * 0.2
            if sr["zone"] != "Neutral":
                reasons.append(f"SR: {sr['zone']}")
            
            # 4. কনফ্লুয়েন্স (25%)
            confluence = self.check_confluence(df)
            conf_score = (confluence["bullish"] - confluence["bearish"]) * 3
            score += conf_score * 0.25
            if confluence["signals"]:
                reasons.append(f"Confluence: {', '.join(confluence['signals'][:2])}")
            
            # রেজিম ফিল্টার
            regime = df["Market_Regime"].iloc[-1] if "Market_Regime" in df.columns else "Unknown"
            if regime == "Ranging" and abs(score - 50) < 15:
                score = 50
                reasons.append("Ranging Market - Wait")
            
            # ভলিউম
            if "Volume_Ratio" in df.columns:
                vol = df["Volume_Ratio"].iloc[-1]
                if vol > 1.5 and score > 55:
                    score += 3
                    reasons.append(f"High Volume ({vol:.1f}x)")
            
        except Exception as e:
            logger.error(f"Signal error: {e}")
            return self._default_signal(str(e))
        
        score = max(0, min(100, int(score)))
        
        # সিগন্যাল
        if score >= 60:
            signal = "BUY"
            confidence = score
            entry = "Long Entry"
        elif score <= 40:
            signal = "SELL"
            confidence = 100 - score
            entry = "Short Entry"
        else:
            signal = "WAIT"
            confidence = 50
            entry = "None"
        
        return {
            "signal": signal,
            "confidence": confidence,
            "trend": "Bullish" if score > 55 else "Bearish" if score < 45 else "Neutral",
            "entry": entry,
            "reasons": reasons[:5],
            "price": round(float(latest["Close"]), 5),
            "time": get_dhaka_time(),
            "score": score,
            "regime": regime if "regime" in locals() else "Unknown",
            "version": self.version
        }
    
    def _default_signal(self, error_msg: str) -> dict:
        return {
            "signal": "WAIT",
            "confidence": 0,
            "trend": "Unknown",
            "entry": "None",
            "reasons": [error_msg],
            "price": 0,
            "time": get_dhaka_time(),
            "score": 0,
            "regime": "Error",
            "version": self.version
        }

# ==================== ব্যাকওয়ার্ড কম্প্যাটিবিলিটি ====================

analyzer = ProSignalAnalyzer()

def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    return analyzer.add_indicators(df)

def detect_candlestick_pattern(df: pd.DataFrame) -> tuple:
    patterns = analyzer.detect_patterns(df)
    if patterns:
        return patterns[0]
    return None, 0

def check_support_resistance(df: pd.DataFrame) -> tuple:
    sr = analyzer.detect_sr(df)
    return sr["zone"], sr["score"]

def check_multi_timeframe(pair: str) -> dict:
    return analyzer.check_mtf(pair)

def generate_signal(df: pd.DataFrame, pair: str = "", timeframe: str = "5m") -> dict:
    return analyzer.generate_signal(df, pair, timeframe)
