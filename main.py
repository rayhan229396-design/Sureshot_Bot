# main.py
from flask import Flask, render_template, jsonify, request, send_from_directory
from flask_cors import CORS
from datetime import datetime
import logging
import os
from dotenv import load_dotenv

from analysis import ProSignalAnalyzer, generate_signal
from utils.data_fetcher import fetch_data, get_dhaka_time, SUPPORTED_PAIRS

# লোড env
load_dotenv()

# লগিং সেটআপ
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')
CORS(app)

# অ্যানালাইজার ইন্সট্যান্স
analyzer = ProSignalAnalyzer()

# ==================== রাউটস ====================

@app.route('/')
def index():
    """হোম পেজ"""
    return render_template('index.html', 
                         pairs=SUPPORTED_PAIRS,
                         timeframes=['1m', '5m', '15m', '30m', '1h', '4h'])

@app.route('/api/signal', methods=['GET'])
def get_signal():
    """সিগন্যাল এপিআই"""
    try:
        pair = request.args.get('pair', 'EURUSD')
        timeframe = request.args.get('timeframe', '5m')
        
        # ডাটা ফেচ
        df = fetch_data(pair, timeframe=timeframe, limit=150)
        
        if df.empty:
            return jsonify({
                'success': False,
                'error': 'No data available for this pair',
                'signal': 'WAIT',
                'confidence': 0
            })
        
        # সিগন্যাল জেনারেট
        signal = generate_signal(df, pair, timeframe)
        
        # হিস্ট্রি সেভ
        if signal['signal'] != 'WAIT':
            analyzer.signal_history.append({
                'time': signal['time'],
                'pair': pair,
                'signal': signal['signal'],
                'confidence': signal['confidence'],
                'price': signal['price']
            })
            # শুধু শেষ ১০০টি রাখি
            if len(analyzer.signal_history) > 100:
                analyzer.signal_history = analyzer.signal_history[-100:]
        
        return jsonify({
            'success': True,
            'data': signal,
            'history': analyzer.signal_history[-10:]  # শেষ ১০টি সিগন্যাল
        })
        
    except Exception as e:
        logger.error(f"Signal API error: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'signal': 'WAIT',
            'confidence': 0
        })

@app.route('/api/mtf', methods=['GET'])
def get_mtf():
    """মাল্টি-টাইমফ্রেম এপিআই"""
    try:
        pair = request.args.get('pair', 'EURUSD')
        mtf_data = analyzer.check_mtf(pair)
        return jsonify({
            'success': True,
            'data': mtf_data
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/history', methods=['GET'])
def get_history():
    """সিগন্যাল হিস্ট্রি"""
    return jsonify({
        'success': True,
        'history': analyzer.signal_history[-20:]
    })

@app.route('/api/pairs', methods=['GET'])
def get_pairs():
    """সাপোর্টেড পেয়ার লিস্ট"""
    return jsonify({
        'success': True,
        'pairs': SUPPORTED_PAIRS
    })

# ==================== স্ট্যাটিক ফাইল ====================

@app.route('/static/<path:path>')
def serve_static(path):
    return send_from_directory('static', path)

# ==================== হেলথ চেক ====================

@app.route('/health')
def health():
    return jsonify({
        'status': 'healthy',
        'time': get_dhaka_time(),
        'version': analyzer.version
    })

# ==================== মেইন ====================

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('DEBUG', 'False').lower() == 'true'
    
    logger.info(f"Starting Pro Market Signal AI on port {port}")
    logger.info(f"Debug mode: {debug}")
    
    app.run(host='0.0.0.0', port=port, debug=debug)
