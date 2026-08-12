# utils/data_fetcher.py
import pandas as pd
import numpy as np
import requests
from datetime import datetime, timedelta
import time
import logging
import os
from typing import Optional, Dict, List

logger = logging.getLogger(__name__)

# ==================== কনফিগ ====================

SUPPORTED_PAIRS = [
    'EURUSD', 'GBPUSD', 'USDJPY', 'AUDUSD', 'USDCAD', 'NZDUSD',
    'EURGBP', 'EURJPY', 'GBPJPY', 'XAUUSD', 'XAGUSD',
    'BTCUSD', 'ETHUSD', 'BNBUSD', 'SOLUSD', 'XRPUSD'
]

TIMEFRAME_MAP = {
    '1m': 60,
    '5m': 300,
    '15m': 900,
    '30m': 1800,
    '1h': 3600,
    '4h': 14400,
    '1d': 86400
}

# ==================== ডাটা ফেচ ফাংশন ====================

def get_dhaka_time() -> str:
    """ঢাকা সময় ফেরত দিন (GMT+6)"""
    dhaka_time = datetime.utcnow() + timedelta(hours=6)
    return dhaka_time.strftime("%Y-%m-%d %H:%M:%S GMT+6")

def fetch_data(pair: str, timeframe: str = "5m", limit: int = 150) -> pd.DataFrame:
    """
    OANDA API থেকে ডাটা ফেচ করুন
    
    Args:
        pair: কারেন্সি পেয়ার (যেমন: EURUSD)
        timeframe: টাইমফ্রেম (1m, 5m, 15m, 30m, 1h, 4h, 1d)
        limit: কতটি ক্যান্ডেল
    Returns:
        pd.DataFrame: OHLCV ডাটা
    """
    
    # OANDA API (ফ্রি টিয়ার)
    api_key = os.getenv('OANDA_API_KEY', '')
    account_id = os.getenv('OANDA_ACCOUNT_ID', '')
    
    # ডেমো অ্যাকাউন্ট
    base_url = "https://api-fxpractice.oanda.com/v3"
    
    if api_key and account_id:
        try:
            return _fetch_oanda(pair, timeframe, limit, api_key, account_id, base_url)
        except Exception as e:
            logger.warning(f"OANDA API failed: {e}, trying backup...")
    
    # ব্যাকআপ: Yahoo Finance
    try:
        return _fetch_yahoo(pair, timeframe, limit)
    except Exception as e:
        logger.warning(f"Yahoo Finance failed: {e}, trying mock...")
    
    # ফাইনাল ব্যাকআপ: Mock Data
    return _generate_mock_data(pair, limit)

def _fetch_oanda(pair: str, timeframe: str, limit: int, api_key: str, account_id: str, base_url: str) -> pd.DataFrame:
    """OANDA API থেকে ডাটা ফেচ"""
    
    # পেয়ার ফরম্যাট
    if pair == 'XAUUSD':
        instrument = 'XAU_USD'
    elif pair == 'XAGUSD':
        instrument = 'XAG_USD'
    else:
        instrument = pair
    
    # টাইমফ্রেম
    granularity = timeframe.upper()
    if granularity == '1M':
        granularity = 'M1'
    elif granularity == '5M':
        granularity = 'M5'
    elif granularity == '15M':
        granularity = 'M15'
    elif granularity == '30M':
        granularity = 'M30'
    elif granularity == '1H':
        granularity = 'H1'
    elif granularity == '4H':
        granularity = 'H4'
    elif granularity == '1D':
        granularity = 'D'
    
    # API কল
    url = f"{base_url}/instruments/{instrument}/candles"
    params = {
        'granularity': granularity,
        'count': limit,
        'price': 'M'
    }
    
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
    
    response = requests.get(url, params=params, headers=headers, timeout=10)
    response.raise_for_status()
    data = response.json()
    
    # ডাটা পার্স
    candles = []
    for candle in data['candles']:
        if 'mid' in candle:
            mid = candle['mid']
            candles.append({
                'Open': float(mid['o']),
                'High': float(mid['h']),
                'Low': float(mid['l']),
                'Close': float(mid['c']),
                'Volume': 0  # OANDA ফ্রি ভার্সনে ভলিউম নেই
            })
    
    df = pd.DataFrame(candles)
    df = df.iloc[::-1].reset_index(drop=True)  # উল্টো করে দিন
    
    logger.info(f"Fetched {len(df)} candles from OANDA for {pair}")
    return df

def _fetch_yahoo(pair: str, timeframe: str, limit: int) -> pd.DataFrame:
    """Yahoo Finance থেকে ডাটা ফেচ"""
    try:
        import yfinance as yf
        
        # পেয়ার ম্যাপিং
        yahoo_map = {
            'EURUSD': 'EURUSD=X',
            'GBPUSD': 'GBPUSD=X',
            'USDJPY': 'USDJPY=X',
            'AUDUSD': 'AUDUSD=X',
            'USDCAD': 'USDCAD=X',
            'NZDUSD': 'NZDUSD=X',
            'XAUUSD': 'GC=F',
            'XAGUSD': 'SI=F',
            'BTCUSD': 'BTC-USD',
            'ETHUSD': 'ETH-USD'
        }
        
        symbol = yahoo_map.get(pair, pair)
        
        # টাইমফ্রেম ম্যাপিং
        period_map = {
            '1m': '7d',
            '5m': '7d',
            '15m': '7d',
            '30m': '7d',
            '1h': '30d',
            '4h': '60d',
            '1d': '1y'
        }
        
        interval_map = {
            '1m': '1m',
            '5m': '5m',
            '15m': '15m',
            '30m': '30m',
            '1h': '60m',
            '4h': '60m',
            '1d': '1d'
        }
        
        period = period_map.get(timeframe, '7d')
        interval = interval_map.get(timeframe, '5m')
        
        # ডাউনলোড
        df = yf.download(
            symbol,
            period=period,
            interval=interval,
            progress=False
        )
        
        if df.empty:
            raise ValueError("No data from Yahoo Finance")
        
        # রিস্যাম্পল (যদি দরকার হয়)
        if timeframe == '4h' and interval == '60m':
            df = df.resample('4H').agg({
                'Open': 'first',
                'High': 'max',
                'Low': 'min',
                'Close': 'last',
                'Volume': 'sum'
            }).dropna()
        
        # লিমিট
        df = df.tail(limit)
        
        logger.info(f"Fetched {len(df)} candles from Yahoo for {pair}")
        return df
        
    except ImportError:
        logger.warning("yfinance not installed")
        raise
    except Exception as e:
        logger.error(f"Yahoo Finance error: {e}")
        raise

def _generate_mock_data(pair: str, limit: int) -> pd.DataFrame:
    """মক ডাটা জেনারেট (যখন কোনো API কাজ করে না)"""
    logger.warning(f"Generating mock data for {pair}")
    
    np.random.seed(42)
    
    # বেস প্রাইস
    base_prices = {
        'EURUSD': 1.10, 'GBPUSD': 1.27, 'USDJPY': 145,
        'AUDUSD': 0.65, 'USDCAD': 1.35, 'NZDUSD': 0.60,
        'XAUUSD': 2400, 'XAGUSD': 28, 'BTCUSD': 60000
    }
    base = base_prices.get(pair, 100)
    
    # রেটার্ন জেনারেট
    returns = np.random.normal(0, 0.0005, limit)
    price = base * np.exp(np.cumsum(returns))
    
    # OHLC তৈরি
    df = pd.DataFrame({
        'Open': price * (1 + np.random.normal(0, 0.0001, limit)),
        'High': price * (1 + np.random.normal(0.0002, 0.0002, limit)),
        'Low': price * (1 - np.random.normal(0.0002, 0.0002, limit)),
        'Close': price,
        'Volume': np.random.randint(100, 1000, limit)
    })
    
    df['High'] = df[['Open', 'High', 'Close']].max(axis=1)
    df['Low'] = df[['Open', 'Low', 'Close']].min(axis=1)
    
    logger.info(f"Generated {len(df)} mock candles for {pair}")
    return df

def fetch_multiple_pairs(pairs: List[str], timeframe: str = "5m", limit: int = 100) -> Dict[str, pd.DataFrame]:
    """একাধিক পেয়ারের ডাটা ফেচ"""
    data = {}
    for pair in pairs:
        try:
            df = fetch_data(pair, timeframe, limit)
            if not df.empty:
                data[pair] = df
        except Exception as e:
            logger.error(f"Failed to fetch {pair}: {e}")
    return data

# ==================== ডাটা ভ্যালিডেশন ====================

def validate_data(df: pd.DataFrame) -> bool:
    """ডাটা ভ্যালিডেট করুন"""
    if df.empty:
        return False
    
    required_cols = ['Open', 'High', 'Low', 'Close']
    if not all(col in df.columns for col in required_cols):
        return False
    
    if df.isnull().any().any():
        return False
    
    # প্রাইস > 0
    if (df[['Open', 'High', 'Low', 'Close']] <= 0).any().any():
        return False
    
    # High >= Low
    if (df['High'] < df['Low']).any():
        return False
    
    return True

# ==================== ক্যাশিং ====================

_cache = {}
_cache_time = {}

def fetch_data_cached(pair: str, timeframe: str = "5m", limit: int = 150, ttl: int = 60) -> pd.DataFrame:
    """ক্যাশ সহ ডাটা ফেচ"""
    key = f"{pair}_{timeframe}_{limit}"
    
    # ক্যাশ চেক
    if key in _cache and (time.time() - _cache_time.get(key, 0)) < ttl:
        return _cache[key].copy()
    
    # ফেচ
    df = fetch_data(pair, timeframe, limit)
    
    # ক্যাশ আপডেট
    if not df.empty:
        _cache[key] = df.copy()
        _cache_time[key] = time.time()
    
    return df

def clear_cache():
    """ক্যাশ ক্লিয়ার"""
    global _cache, _cache_time
    _cache = {}
    _cache_time = {}
