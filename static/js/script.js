// static/js/script.js

// ==================== স্টেট ====================
const state = {
    currentPair: 'EURUSD',
    currentTimeframe: '5m',
    isAnalyzing: false,
    signalHistory: [],
    autoRefreshInterval: null
};

// ==================== DOM রেফারেন্স ====================
const elements = {
    pairSelect: document.getElementById('pairSelect'),
    timeframeSelect: document.getElementById('timeframeSelect'),
    analyzeBtn: document.getElementById('analyzeBtn'),
    refreshBtn: document.getElementById('refreshBtn'),
    signalValue: document.getElementById('signalValue'),
    priceValue: document.getElementById('priceValue'),
    confidenceText: document.getElementById('confidenceText'),
    confidenceFill: document.getElementById('confidenceFill'),
    scoreValue: document.getElementById('scoreValue'),
    trendValue: document.getElementById('trendValue'),
    regimeValue: document.getElementById('regimeValue'),
    reasonsList: document.getElementById('reasonsList'),
    signalTime: document.getElementById('signalTime'),
    mtf15m: document.getElementById('mtf15m'),
    mtf1h: document.getElementById('mtf1h'),
    mtf4h: document.getElementById('mtf4h'),
    historyList: document.getElementById('historyList'),
    historyCount: document.getElementById('historyCount'),
    currentTime: document.getElementById('currentTime'),
    signalCard: document.getElementById('signalCard')
};

// ==================== ইউটিলিটি ফাংশন ====================
function formatTime(date) {
    return date.toLocaleTimeString('en-US', { 
        hour12: false,
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    });
}

function formatDate(date) {
    return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
    });
}

function formatPrice(price) {
    if (price === 0 || price === undefined) return '0.0000';
    if (price > 1000) return price.toFixed(2);
    if (price > 100) return price.toFixed(3);
    if (price > 1) return price.toFixed(4);
    return price.toFixed(5);
}

function getSignalClass(signal) {
    if (!signal) return 'wait';
    const s = signal.toLowerCase();
    if (s === 'buy') return 'buy';
    if (s === 'sell') return 'sell';
    return 'wait';
}

function getTrendClass(trend) {
    if (!trend) return 'neutral';
    const t = trend.toLowerCase();
    if (t.includes('bullish')) return 'bullish';
    if (t.includes('bearish')) return 'bearish';
    return 'neutral';
}

// ==================== টাইম আপডেট ====================
function updateClock() {
    const now = new Date();
    const dhakaTime = new Date(now.getTime() + (6 * 60 * 60 * 1000));
    elements.currentTime.querySelector('span').textContent = 
        formatDate(dhakaTime) + ' ' + formatTime(dhakaTime) + ' GMT+6';
}

// ==================== সিগন্যাল ফেচ ====================
async function fetchSignal(pair, timeframe) {
    if (state.isAnalyzing) return;
    
    state.isAnalyzing = true;
    elements.analyzeBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Analyzing...';
    elements.analyzeBtn.disabled = true;
    elements.signalCard.classList.add('loading');
    
    try {
        const url = `/api/signal?pair=${encodeURIComponent(pair)}&timeframe=${encodeURIComponent(timeframe)}`;
        const response = await fetch(url);
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        if (data.success) {
            updateSignalUI(data.data);
            if (data.history) {
                updateHistoryUI(data.history);
            }
        } else {
            showError(data.error || 'Unknown error occurred');
        }
        
    } catch (error) {
        console.error('Fetch error:', error);
        showError('Failed to fetch signal. Please try again.');
    } finally {
        state.isAnalyzing = false;
        elements.analyzeBtn.innerHTML = '<i class="fas fa-play"></i> Analyze';
        elements.analyzeBtn.disabled = false;
        elements.signalCard.classList.remove('loading');
    }
}

// ==================== সিগন্যাল UI আপডেট ====================
function updateSignalUI(data) {
    const signal = data.signal || 'WAIT';
    const signalClass = getSignalClass(signal);
    
    // সিগন্যাল
    elements.signalValue.textContent = signal;
    elements.signalValue.className = 'signal-value ' + signalClass;
    
    // প্রাইস
    elements.priceValue.textContent = formatPrice(data.price);
    
    // কনফিডেন্স
    const confidence = data.confidence || 0;
    elements.confidenceText.textContent = confidence + '%';
    elements.confidenceFill.style.width = confidence + '%';
    
    // স্কোর
    elements.scoreValue.textContent = data.score || 0;
    
    // ট্রেন্ড
    const trend = data.trend || 'Neutral';
    elements.trendValue.textContent = trend;
    elements.trendValue.className = 'metric-value ' + getTrendClass(trend);
    
    // রেজিম
    elements.regimeValue.textContent = data.regime || 'Unknown';
    
    // রিজনস
    elements.reasonsList.innerHTML = '';
    if (data.reasons && data.reasons.length > 0) {
        data.reasons.forEach(reason => {
            const tag = document.createElement('span');
            tag.className = 'reason-tag fade-in';
            tag.textContent = reason;
            elements.reasonsList.appendChild(tag);
        });
    } else {
        elements.reasonsList.innerHTML = '<span class="no-reasons">No signals detected</span>';
    }
    
    // টাইম
    const timeSpan = elements.signalTime.querySelector('span');
    timeSpan.textContent = data.time || '--:--:--';
    
    // MTF আপডেট (যদি থাকে)
    if (data.mtf) {
        updateMTFUI(data.mtf);
    }
}

// ==================== MTF UI আপডেট ====================
function updateMTFUI(mtfData) {
    const timeframes = ['15m', '1h', '4h'];
    const elements_map = {
        '15m': elements.mtf15m,
        '1h': elements.mtf1h,
        '4h': elements.mtf4h
    };
    
    timeframes.forEach(tf => {
        const el = elements_map[tf];
        const value = mtfData[tf] || 'Neutral';
        const cls = getTrendClass(value);
        el.textContent = value;
        el.className = 'mtf-value ' + cls;
    });
}

// ==================== হিস্ট্রি UI আপডেট ====================
function updateHistoryUI(history) {
    if (!history || history.length === 0) {
        elements.historyList.innerHTML = `
            <div class="history-empty">
                <i class="fas fa-inbox"></i>
                <span>No signals yet</span>
            </div>
        `;
        elements.historyCount.textContent = '0 signals';
        return;
    }
    
    // রিভার্স করুন (লেটেস্ট উপরে)
    const reversed = [...history].reverse();
    
    let html = '';
    reversed.forEach(item => {
        const signalClass = getSignalClass(item.signal);
        const confidence = item.confidence || 0;
        const price = formatPrice(item.price);
        const time = item.time ? item.time.split(' ')[1] : '--:--';
        
        html += `
            <div class="history-item fade-in">
                <span class="h-signal ${signalClass}">${item.signal}</span>
                <div class="h-details">
                    <span class="h-price">${price}</span>
                    <span class="h-confidence">${confidence}%</span>
                    <span class="h-time">${time}</span>
                </div>
            </div>
        `;
    });
    
    elements.historyList.innerHTML = html;
    elements.historyCount.textContent = history.length + ' signals';
}

// ==================== এরর হ্যান্ডলিং ====================
function showError(message) {
    elements.reasonsList.innerHTML = `<span class="no-reasons" style="color: var(--accent-red);">⚠️ ${message}</span>`;
    elements.signalValue.textContent = 'ERROR';
    elements.signalValue.className = 'signal-value wait';
}

// ==================== ইভেন্ট লিসেনার ====================

// পেয়ার চেঞ্জ
elements.pairSelect.addEventListener('change', () => {
    state.currentPair = elements.pairSelect.value;
});

// টাইমফ্রেম চেঞ্জ
elements.timeframeSelect.addEventListener('change', () => {
    state.currentTimeframe = elements.timeframeSelect.value;
});

// অ্যানালাইজ বাটন
elements.analyzeBtn.addEventListener('click', () => {
    fetchSignal(state.currentPair, state.currentTimeframe);
});

// রিফ্রেশ বাটন
elements.refreshBtn.addEventListener('click', () => {
    elements.refreshBtn.classList.add('spinning');
    fetchSignal(state.currentPair, state.currentTimeframe);
    setTimeout(() => {
        elements.refreshBtn.classList.remove('spinning');
    }, 1000);
});

// ==================== অটো রিফ্রেশ ====================
function startAutoRefresh(interval = 60000) { // ১ মিনিট
    if (state.autoRefreshInterval) {
        clearInterval(state.autoRefreshInterval);
    }
    
    state.autoRefreshInterval = setInterval(() => {
        fetchSignal(state.currentPair, state.currentTimeframe);
    }, interval);
}

function stopAutoRefresh() {
    if (state.autoRefreshInterval) {
        clearInterval(state.autoRefreshInterval);
        state.autoRefreshInterval = null;
    }
}

// ==================== কীবোর্ড শর্টকাট ====================
document.addEventListener('keydown', (e) => {
    // Ctrl+Enter = Analyze
    if (e.ctrlKey && e.key === 'Enter') {
        e.preventDefault();
        elements.analyzeBtn.click();
    }
    // Ctrl+R = Refresh
    if (e.ctrlKey && e.key === 'r') {
        e.preventDefault();
        elements.refreshBtn.click();
    }
});

// ==================== ইনিশিয়ালাইজ ====================
function init() {
    // ঘড়ি আপডেট
    updateClock();
    setInterval(updateClock, 1000);
    
    // প্রথম সিগন্যাল
    setTimeout(() => {
        fetchSignal(state.currentPair, state.currentTimeframe);
    }, 500);
    
    // অটো রিফ্রেশ (৫ মিনিট পর পর)
    startAutoRefresh(300000);
    
    console.log('🚀 Pro Market Signal AI initialized');
    console.log(`📊 Pair: ${state.currentPair}, Timeframe: ${state.currentTimeframe}`);
    console.log(`🔄 Auto-refresh: Every 5 minutes`);
}

// DOM লোড হলে ইনিশিয়ালাইজ
document.addEventListener('DOMContentLoaded', init);

// ==================== ক্লিনআপ ====================
window.addEventListener('beforeunload', () => {
    stopAutoRefresh();
});
