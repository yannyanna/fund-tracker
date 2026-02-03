import streamlit as st
from datetime import datetime
import json
import os
import urllib.request
import ssl
import re
import pytz

# --- 基础配置 ---
TZ = pytz.timezone('Asia/Shanghai')
DATA_FILE = "fund_tracker.json"
BACKUP_FILE = "fund_tracker.json.bak"
ssl_ctx = ssl._create_unverified_context()

st.set_page_config(page_title="资产追踪", layout="wide", initial_sidebar_state="collapsed")

# --- 样式优化 ---
st.markdown("""
<style>
    .main { padding: 0.3rem !important; }
    .block-container { padding-top: 0.3rem !important; padding-bottom: 0.5rem !important; }
    
    /* 灵动岛避让 - 增加顶部空行 */
    .spacer-top { height: 45px; }
    
    /* 刷新栏 - 按钮和时间严格同行 */
    .refresh-row {
        display: flex;
        align-items: center;
        gap: 12px;
        margin: 0 0 12px 0;
        padding: 0 5px;
    }
    .refresh-btn button {
        font-size: 0.8rem !important;
        padding: 0.25rem 1rem !important;
        height: 34px !important;
        border-radius: 17px !important;
        margin: 0 !important;
    }
    .update-time-inline {
        font-size: 0.75rem;
        color: #6c757d;
        line-height: 34px;
    }
    
    /* 黄金区域 - 三列一行，超紧凑 */
    .gold-section { margin-bottom: 10px; }
    .gold-row {
        display: flex;
        gap: 6px;
    }
    .gold-box {
        flex: 1;
        background: linear-gradient(135deg, #fffdf2 0%, #fff9e6 100%);
        padding: 8px 4px;
        border-radius: 8px;
        text-align: center;
        border: 1px solid #f0e6cc;
    }
    .gold-title {
        font-size: 0.65rem;
        color: #856404;
        margin-bottom: 2px;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    .gold-price {
        font-size: 1.1rem;
        font-weight: bold;
        color: #b8860b;
        line-height: 1.1;
    }
    .gold-sub {
        font-size: 0.6rem;
        color: #997;
        margin-top: 1px;
    }
    
    /* 汇总区域 */
    .summary-section { margin-bottom: 12px; }
    .summary-box {
        display: flex;
        justify-content: space-around;
        padding: 10px 5px;
        background: #f8f9fa;
        border-radius: 8px;
        border: 1px solid #e9ecef;
    }
    .summary-item {
        text-align: center;
        flex: 1;
        padding: 0 2px;
    }
    .summary-label {
        font-size: 0.65rem;
        color: #6c757d;
        margin-bottom: 2px;
    }
    .summary-value {
        font-size: 1rem;
        font-weight: bold;
    }
    
    /* 基金卡片 */
    .fund-card {
        background: white;
        padding: 10px 12px;
        margin-bottom: 8px;
        border-radius: 8px;
        border: 1px solid #e9ecef;
    }
    .fund-header {
        display: flex;
        justify-content: space-between;
        align-items: baseline;
        margin-bottom: 6px;
    }
    .fund-name {
        font-size: 0.95rem;
        font-weight: 600;
        color: #212529;
    }
    .fund-code {
        font-size: 0.7rem;
        color: #6c757d;
        background: #f1f3f5;
        padding: 1px 6px;
        border-radius: 10px;
        margin-left: 6px;
    }
    .fund-time {
        font-size: 0.7rem;
        color: #adb5bd;
    }
    
    /* 基金数据网格 */
    .fund-grid {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 8px;
        text-align: center;
        margin-bottom: 8px;
    }
    .fund-item {
        padding: 6px 2px;
        background: #f8f9fa;
        border-radius: 6px;
    }
    .fund-label {
        font-size: 0.65rem;
        color: #868e96;
        margin-bottom: 1px;
    }
    .fund-value-num {
        font-size: 0.9rem;
        font-weight: 600;
    }
    
    /* 基金底部信息行 */
    .fund-footer {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding-top: 6px;
        border-top: 1px solid #f1f3f5;
    }
    .fund-detail-left {
        font-size: 0.7rem;
        color: #868e96;
    }
    .fund-detail-right {
        font-size: 0.7rem;
        color: #868e96;
        text-align: right;
    }
    .del-btn-inline button {
        font-size: 0.65rem !important;
        padding: 0.1rem 0.4rem !important;
        height: 22px !important;
        line-height: 1 !important;
        min-height: 22px !important;
    }
    
    /* 添加区域 - 左右布局 */
    .add-section {
        margin-top: 12px;
        padding-top: 12px;
        border-top: 2px solid #e9ecef;
    }
    .input-row {
        display: flex;
        align-items: center;
        margin-bottom: 8px;
        gap: 10px;
    }
    .input-label {
        font-size: 0.8rem;
        color: #495057;
        min-width: 70px;
        white-space: nowrap;
    }
    .input-field {
        flex: 1;
    }
    .input-field input {
        font-size: 0.85rem !important;
        padding: 0.4rem 0.6rem !important;
    }
    .add-section .stButton button {
        font-size: 0.8rem !important;
        padding: 0.25rem 1rem !important;
        height: 32px !important;
    }
    .add-section .stExpander {
        font-size: 0.85rem !important;
    }
    
    /* 颜色 */
    .up { color: #e03131; }
    .down { color: #2f9e44; }
    
    /* 空状态 */
    .empty-state {
        text-align: center;
        padding: 20px;
        color: #adb5bd;
        font-size: 0.85rem;
    }
    
    /* 隐藏默认元素 */
    .stDeployButton { display: none !important; }
    div[data-testid="stToolbar"] { display: none !important; }
</style>
""", unsafe_allow_html=True)

# --- 数据持久化 ---
def load_db():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"holdings": []}

def save_db(data):
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            with open(BACKUP_FILE, 'w', encoding='utf-8') as bf:
                bf.write(f.read())
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# --- 数据获取 ---
def fetch_data():
    result = {
        "au9999": 0.0,
        "xau_usd": 0.0,
        "usdcny": 0.0,
        "xau_cny": 0.0,
        "update_time": datetime.now(TZ).strftime("%m-%d %H:%M"),
        "error": None
    }
    
    try:
        codes = "gds_AU9999,hf_XAU,fx_susdcnh"
        url = f"http://hq.sinajs.cn/list={codes}"
        req = urllib.request.Request(url, headers={'Referer': 'http://finance.sina.com.cn'})
        
        with urllib.request.urlopen(req, timeout=5, context=ssl_ctx) as res:
            data = res.read().decode('gbk')
            
            if 'gds_AU9999' in data:
                match = re.search(r'gds_AU9999="([^"]+)"', data)
                if match:
                    result["au9999"] = float(match.group(1).split(',')[0])
            
            if 'hf_XAU' in data:
                match = re.search(r'hf_XAU="([^"]+)"', data)
                if match:
                    parts = match.group(1).split(',')
                    result["xau_usd"] = float(parts[0])
            
            if 'fx_susdcnh' in data:
                match = re.search(r'fx_susdcnh="([^"]+)"', data)
                if match:
                    parts = match.group(1).split(',')
                    result["usdcny"] = float(parts[1])
            
            if result["xau_usd"] > 0 and result["usdcny"] > 0:
                result["xau_cny"] = (result["xau_usd"] * result["usdcny"]) / 31.1034768
                
    except Exception as e:
        result["error"] = str(e)
    
    return result

def fetch_fund_data(code):
    try:
        url = f"http://fundgz.1234567.com.cn/js/{code}.js"
        req = urllib.request.Request(url, headers={'Referer': 'http://fund.eastmoney.com'})
        
        with urllib.request.urlopen(req, timeout=5, context=ssl_ctx) as res:
            content = res.read().decode('utf-8')
            json_str = content[content.find('{'):content.rfind('}')+1]
            data = json.loads(json_str)
            
            return {
                "name": data.get("name", "未知"),
                "code": data.get("fundcode", code),
                "nav": float(data.get("dwjz", 0)),
                "estimate": float(data.get("gsz", 0)),
                "change_pct": float(data.get("gszzl", 0)),
                "time": data.get("gztime", "--")
            }
    except Exception:
        return None

# --- 初始化 ---
if 'db' not in st.session_state:
    st.session_state.db = load_db()
if 'gold_data' not in st.session_state:
    st.session_state.gold_data = None
if 'fund_cache' not in st.session_state:
    st.session_state.fund_cache = {}
if 'last_refresh' not in st.session_state:
    st.session_state.last_refresh = None

# 输入框状态管理（用于自动清空）
if 'code_focused' not in st.session_state:
    st.session_state.code_focused = False
if 'shares_focused' not in st.session_state:
    st.session_state.shares_focused = False
if 'cost_focused' not in st.session_state:
    st.session_state.cost_focused = False

# --- 第1行：空行避让灵动岛（增加到45px） ---
st.markdown('<div class="spacer-top"></div>', unsafe_allow_html=True)

# --- 第2行：刷新按钮 + 时间（严格同行） ---
refresh_col, time_col = st.columns([1, 3])
with refresh_col:
    if st.button("🔄 刷新", type="primary", key="refresh_btn"):
        with st.spinner("..."):
            st.session_state.gold_data = fetch_data()
            st.session_state.fund_cache = {}
            st.session_state.last_refresh = datetime.now(TZ).strftime("%m-%d %H:%M")
        st.rerun()

with time_col:
    time_text = f"更新于 {st.session_state.last_refresh}" if st.session_state.last_refresh else "点击刷新获取数据"
    st.markdown(f'<div class="update-time-inline">{time_text}</div>', unsafe_allow_html=True)

# --- 第3行：黄金数据（三列一行） ---
st.markdown('<div class="gold-section">', unsafe_allow_html=True)
gold = st.session_state.gold_data

if gold and not gold.get("error") and gold.get("au9999", 0) > 0:
    st.markdown(f"""
    <div class="gold-row">
        <div class="gold-box">
            <div class="gold-title">上海AU9999</div>
            <div class="gold-price">¥{gold['au9999']:.2f}</div>
            <div class="gold-sub">元/克</div>
        </div>
        <div class="gold-box">
            <div class="gold-title">国际现货</div>
            <div class="gold-price">${gold['xau_usd']:.2f}</div>
            <div class="gold-sub">美元/盎司</div>
        </div>
        <div class="gold-box">
            <div class="gold-title">国际(换算)</div>
            <div class="gold-price">¥{gold['xau_cny']:.2f}</div>
            <div class="gold-sub">汇率{gold['usdcny']:.2f}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
else:
    st.info("点击刷新获取黄金数据", icon="💰")
st.markdown('</div>', unsafe_allow_html=True)

# --- 第4行：基金汇总 ---
st.markdown('<div class="summary-section">', unsafe_allow_html=True)

total_market_value = 0.0
total_day_profit = 0.0
total_total_profit = 0.0
has_data = False

if st.session_state.db["holdings"] and st.session_state.last_refresh:
    for holding in st.session_state.db["holdings"]:
        code = holding["code"]
        if code not in st.session_state.fund_cache:
            st.session_state.fund_cache[code] = fetch_fund_data(code)
        
        fund_data = st.session_state.fund_cache.get(code)
        if fund_data:
            has_data = True
            total_market_value += holding["shares"] * fund_data["estimate"]
            total_day_profit += holding["shares"] * (fund_data["estimate"] - fund_data["nav"])
            total_total_profit += holding["shares"] * (fund_data["estimate"] - holding["cost"])

if has_data:
    day_color = "up" if total_day_profit >= 0 else "down"
    total_color = "up" if total_total_profit >= 0 else "down"
    
    st.markdown(f"""
    <div class="summary-box">
        <div class="summary-item">
            <div class="summary-label">总市值</div>
            <div class="summary-value">¥{total_market_value:,.1f}</div>
        </div>
        <div class="summary-item">
            <div class="summary-label">当日预估</div>
            <div class="summary-value {day_color}">{total_day_profit:+,.1f}</div>
        </div>
        <div class="summary-item">
            <div class="summary-label">累计收益</div>
            <div class="summary-value {total_color}">{total_total_profit:+,.1f}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
else:
    st.markdown("""
    <div class="summary-box">
        <div class="summary-item"><div class="summary-label">总市值</div><div class="summary-value">--</div></div>
        <div class="summary-item"><div class="summary-label">当日预估</div><div class="summary-value">--</div></div>
        <div class="summary-item"><div class="summary-label">累计收益</div><div class="summary-value">--</div></div>
    </div>
    """, unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)

st.divider()

# --- 第5行：基金持仓列表 ---
st.markdown('<div class="fund-list">', unsafe_allow_html=True)

if not st.session_state.db["holdings"]:
    st.markdown('<div class="empty-state">暂无持仓，点击下方添加</div>', unsafe_allow_html=True)
else:
    for idx, holding in enumerate(st.session_state.db["holdings"]):
        code = holding["code"]
        
        if code not in st.session_state.fund_cache:
            with st.spinner(f"获取{code}..."):
                st.session_state.fund_cache[code] = fetch_fund_data(code)
        
        fund_data = st.session_state.fund_cache.get(code)
        
        if fund_data:
            market_value = holding["shares"] * fund_data["estimate"]
            day_profit = holding["shares"] * (fund_data["estimate"] - fund_data["nav"])
            total_profit = holding["shares"] * (fund_data["estimate"] - holding["cost"])
            total_return = ((fund_data["estimate"] - holding["cost"]) / holding["cost"] * 100) if holding["cost"] > 0 else 0
            
            day_color = "up" if day_profit >= 0 else "down"
            total_color = "up" if total_profit >= 0 else "down"
            change_color = "up" if fund_data["change_pct"] >= 0 else "down"
            
            st.markdown(f"""
            <div class="fund-card">
                <div class="fund-header">
                    <div>
                        <span class="fund-name">{fund_data["name"]}</span>
                        <span class="fund-code">{code}</span>
                    </div>
                    <span class="fund-time">{fund_data["time"][-5:] if len(fund_data["time"]) > 5 else fund_data["time"]}</span>
                </div>
                <div class="fund-grid">
                    <div class="fund-item">
                        <div class="fund-label">估值</div>
                        <div class="fund-value-num">{fund_data["estimate"]:.4f}</div>
                    </div>
                    <div class="fund-item">
                        <div class="fund-label">涨跌</div>
                        <div class="fund-value-num {change_color}">{fund_data["change_pct"]:+.2f}%</div>
                    </div>
                    <div class="fund-item">
                        <div class="fund-label">当日预估</div>
                        <div class="6px;
    }
    .fund-name {
        font-size: 0.95rem;
        font-weight: 600;
        color: #212529;
    }
    .fund-code {
        font-size: 0.7rem;
        color: #6c757d;
        background: #f1f3f5;
        padding: 1px 6px;
        border-radius: 10px;
        margin-left: 6px;
    }
    .fund-time {
        font-size: 0.7rem;
        color: #adb5bd;
    }
    
    /* 基金数据网格 */
    .fund-grid {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 8px;
        text-align: center;
        margin-bottom: 8px;
    }
    .fund-item {
        padding: 6px 2px;
        background: #f8f9fa;
        border-radius: 6px;
    }
    .fund-label {
        font-size: 0.65rem;
        color: #868e96;
        margin-bottom: 1px;
    }
    .fund-value-num {
        font-size: 0.9rem;
        font-weight: 600;
    }
    
    /* 基金底部信息行 */
    .fund-footer {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding-top: 6px;
        border-top: 1px solid #f1f3f5;
    }
    .fund-detail-left {
        font-size: 0.7rem;
        color: #868e96;
    }
    .fund-detail-right {
        font-size: 0.7rem;
        color: #868e96;
        text-align: right;
    }
    .del-btn-inline button {
        font-size: 0.65rem !important;
        padding: 0.1rem 0.4rem !important;
        height: 22px !important;
        line-height: 1 !important;
        min-height: 22px !important;
    }
    
    /* 添加区域 - 左右布局 */
    .add-section {
        margin-top: 12px;
        padding-top: 12px;
        border-top: 2px solid #e9ecef;
    }
    .input-row {
        display: flex;
        align-items: center;
        margin-bottom: 8px;
        gap: 10px;
    }
    .input-label {
        font-size: 0.8rem;
        color: #495057;
        min-width: 70px;
        white-space: nowrap;
    }
    .input-field {
        flex: 1;
    }
    .input-field input {
        font-size: 0.85rem !important;
        padding: 0.4rem 0.6rem !important;
    }
    .add-section .stButton button {
        font-size: 0.8rem !important;
        padding: 0.25rem 1rem !important;
        height: 32px !important;
    }
    .add-section .stExpander {
        font-size: 0.85rem !important;
    }
    
    /* 颜色 */
    .up { color: #e03131; }
    .down { color: #2f9e44; }
    
    /* 空状态 */
    .empty-state {
        text-align: center;
        padding: 20px;
        color: #adb5bd;
        font-size: 0.85rem;
    }
    
    /* 隐藏默认元素 */
    .stDeployButton { display: none !important; }
    div[data-testid="stToolbar"] { display: none !important; }
</style>
""", unsafe_allow_html=True)

# --- 数据持久化 ---
def load_db():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"holdings": []}

def save_db(data):
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            with open(BACKUP_FILE, 'w', encoding='utf-8') as bf:
                bf.write(f.read())
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# --- 数据获取 ---
def fetch_data():
    result = {
        "au9999": 0.0,
        "xau_usd": 0.0,
        "usdcny": 0.0,
        "xau_cny": 0.0,
        "update_time": datetime.now(TZ).strftime("%m-%d %H:%M"),
        "error": None
    }
    
    try:
        codes = "gds_AU9999,hf_XAU,fx_susdcnh"
        url = f"http://hq.sinajs.cn/list={codes}"
        req = urllib.request.Request(url, headers={'Referer': 'http://finance.sina.com.cn'})
        
        with urllib.request.urlopen(req, timeout=5, context=ssl_ctx) as res:
            data = res.read().decode('gbk')
            
            if 'gds_AU9999' in data:
                match = re.search(r'gds_AU9999="([^"]+)"', data)
                if match:
                    result["au9999"] = float(match.group(1).split(',')[0])
            
            if 'hf_XAU' in data:
                match = re.search(r'hf_XAU="([^"]+)"', data)
                if match:
                    parts = match.group(1).split(',')
                    result["xau_usd"] = float(parts[0])
            
            if 'fx_susdcnh' in data:
                match = re.search(r'fx_susdcnh="([^"]+)"', data)
                if match:
                    parts = match.group(1).split(',')
                    result["usdcny"] = float(parts[1])
            
            if result["xau_usd"] > 0 and result["usdcny"] > 0:
                result["xau_cny"] = (result["xau_usd"] * result["usdcny"]) / 31.1034768
                
    except Exception as e:
        result["error"] = str(e)
    
    return result

def fetch_fund_data(code):
    try:
        url = f"http://fundgz.1234567.com.cn/js/{code}.js"
        req = urllib.request.Request(url, headers={'Referer': 'http://fund.eastmoney.com'})
        
        with urllib.request.urlopen(req, timeout=5, context=ssl_ctx) as res:
            content = res.read().decode('utf-8')
            json_str = content[content.find('{'):content.rfind('}')+1]
            data = json.loads(json_str)
            
            return {
                "name": data.get("name", "未知"),
                "code": data.get("fundcode", code),
                "nav": float(data.get("dwjz", 0)),
                "estimate": float(data.get("gsz", 0)),
                "change_pct": float(data.get("gszzl", 0)),
                "time": data.get("gztime", "--")
            }
    except Exception:
        return None

# --- 初始化 ---
if 'db' not in st.session_state:
    st.session_state.db = load_db()
if 'gold_data' not in st.session_state:
    st.session_state.gold_data = None
if 'fund_cache' not in st.session_state:
    st.session_state.fund_cache = {}
if 'last_refresh' not in st.session_state:
    st.session_state.last_refresh = None

# 输入框状态管理（用于自动清空）
if 'code_focused' not in st.session_state:
    st.session_state.code_focused = False
if 'shares_focused' not in st.session_state:
    st.session_state.shares_focused = False
if 'cost_focused' not in st.session_state:
    st.session_state.cost_focused = False

# --- 第1行：空行避让灵动岛（增加到45px） ---
st.markdown('<div class="spacer-top"></div>', unsafe_allow_html=True)

# --- 第2行：刷新按钮 + 时间（严格同行） ---
refresh_col, time_col = st.columns([1, 3])
with refresh_col:
    if st.button("🔄 刷新", type="primary", key="refresh_btn"):
        with st.spinner("..."):
            st.session_state.gold_data = fetch_data()
            st.session_state.fund_cache = {}
            st.session_state.last_refresh = datetime.now(TZ).strftime("%m-%d %H:%M")
        st.rerun()

with time_col:
    time_text = f"更新于 {st.session_state.last_refresh}" if st.session_state.last_refresh else "点击刷新获取数据"
    st.markdown(f'<div class="update-time-inline">{time_text}</div>', unsafe_allow_html=True)

# --- 第3行：黄金数据（三列一行） ---
st.markdown('<div class="gold-section">', unsafe_allow_html=True)
gold = st.session_state.gold_data

if gold and not gold.get("error") and gold.get("au9999", 0) > 0:
    st.markdown(f"""
    <div class="gold-row">
        <div class="gold-box">
            <div class="gold-title">上海AU9999</div>
            <div class="gold-price">¥{gold['au9999']:.2f}</div>
            <div class="gold-sub">元/克</div>
        </div>
        <div class="gold-box">
            <div class="gold-title">国际现货</div>
            <div class="gold-price">${gold['xau_usd']:.2f}</div>
            <div class="gold-sub">美元/盎司</div>
        </div>
        <div class="gold-box">
            <div class="gold-title">国际(换算)</div>
            <div class="gold-price">¥{gold['xau_cny']:.2f}</div>
            <div class="gold-sub">汇率{gold['usdcny']:.2f}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
else:
    st.info("点击刷新获取黄金数据", icon="💰")
st.markdown('</div>', unsafe_allow_html=True)

# --- 第4行：基金汇总 ---
st.markdown('<div class="summary-section">', unsafe_allow_html=True)

total_market_value = 0.0
total_day_profit = 0.0
total_total_profit = 0.0
has_data = False

if st.session_state.db["holdings"] and st.session_state.last_refresh:
    for holding in st.session_state.db["holdings"]:
        code = holding["code"]
        if code not in st.session_state.fund_cache:
            st.session_state.fund_cache[code] = fetch_fund_data(code)
        
        fund_data = st.session_state.fund_cache.get(code)
        if fund_data:
            has_data = True
            total_market_value += holding["shares"] * fund_data["estimate"]
            total_day_profit += holding["shares"] * (fund_data["estimate"] - fund_data["nav"])
            total_total_profit += holding["shares"] * (fund_data["estimate"] - holding["cost"])

if has_data:
    day_color = "up" if total_day_profit >= 0 else "down"
    total_color = "up" if total_total_profit >= 0 else "down"
    
    st.markdown(f"""
    <div class="summary-box">
        <div class="summary-item">
            <div class="summary-label">总市值</div>
            <div class="summary-value">¥{total_market_value:,.1f}</div>
        </div>
        <div class="summary-item">
            <div class="summary-label">当日预估</div>
            <div class="summary-value {day_color}">{total_day_profit:+,.1f}</div>
        </div>
        <div class="summary-item">
            <div class="summary-label">累计收益</div>
            <div class="summary-value {total_color}">{total_total_profit:+,.1f}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
else:
    st.markdown("""
    <div class="summary-box">
        <div class="summary-item"><div class="summary-label">总市值</div><div class="summary-value">--</div></div>
        <div class="summary-item"><div class="summary-label">当日预估</div><div class="summary-value">--</div></div>
        <div class="summary-item"><div class="summary-label">累计收益</div><div class="summary-value">--</div></div>
    </div>
    """, unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)

st.divider()

# --- 第5行：基金持仓列表 ---
st.markdown('<div class="fund-list">', unsafe_allow_html=True)

if not st.session_state.db["holdings"]:
    st.markdown('<div class="empty-state">暂无持仓，点击下方添加</div>', unsafe_allow_html=True)
else:
    for idx, holding in enumerate(st.session_state.db["holdings"]):
        code = holding["code"]
        
        if code not in st.session_state.fund_cache:
            with st.spinner(f"获取{code}..."):
                st.session_state.fund_cache[code] = fetch_fund_data(code)
        
        fund_data = st.session_state.fund_cache.get(code)
        
        if fund_data:
            market_value = holding["shares"] * fund_data["estimate"]
            day_profit = holding["shares"] * (fund_data["estimate"] - fund_data["nav"])
            total_profit = holding["shares"] * (fund_data["estimate"] - holding["cost"])
            total_return = ((fund_data["estimate"] - holding["cost"]) / holding["cost"] * 100) if holding["cost"] > 0 else 0
            
            day_color = "up" if day_profit >= 0 else "down"
            total_color = "up" if total_profit >= 0 else "down"
            change_color = "up" if fund_data["change_pct"] >= 0 else "down"
            
            st.markdown(f"""
            <div class="fund-card">
                <div class="fund-header">
                    <div>
                        <span class="fund-name">{fund_data["name"]}</span>
                        <span class="fund-code">{code}</span>
                    </div>
                    <span class="fund-time">{fund_data["time"][-5:] if len(fund_data["time"]) > 5 else fund_data["time"]}</span>
                </div>
                <div class="fund-grid">
                    <div class="fund-item">
                        <div class="fund-label">估值</div>
                        <div class="fund-value-num">{fund_data["estimate"]:.4f}</div>
                    </div>
                    <div class="fund-item">
                        <div class="fund-label">涨跌</div>
                        <div class="fund-value-num {change_color}">{fund_data["change_pct"]:+.2f}%</div>
                    </div>
                    <div class="fund-item">
                        <div class="fund-label">当日预估</div>
                        <div class="fund-value-num {day_color}">{day_profit:+.1f}</div>
                    </div>
                    <div class="fund-item">
                        <div class="fund-label">持有收益</div>
                        <div class="fund-value-num {total_color}">{total_profit:+.1f}</div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # 删除按钮左下，信息右下
            del_col, info_col = st.columns([1, 5])
            with del_col:
                if st.button("删除", key=f"del_{idx}", type="secondary"):
                    st.session_state.db["holdings"].pop(idx)
                    save_db(st.session_state.db)
                    st.rerun()
            with info_col:
                st.markdown(f'<div style="font-size:0.7rem;color:#868e96;text-align:right;padding-top:4px;">{holding["shares"]:.2f}份 · 成本¥{holding["cost"]:.4f} · 市值¥{market_value:.1f} · {total_return:+.2f}%</div>', unsafe_allow_html=True)
                
        else:
            st.error(f"无法获取 {code}", icon="⚠️")

st.markdown('</div>', unsafe_allow_html=True)

st.divider()

# --- 第6行：添加持仓（左右布局，填写即清空） ---
st.markdown('<div class="add-section">', unsafe_allow_html=True)
with st.expander("➕ 添加/修改持仓"):

    # 基金代码 - 左右布局
    code_col1, code_col2 = st.columns([1, 3])
    with code_col1:
        st.markdown('<div class="input-label">基金代码</div>', unsafe_allow_html=True)
    with code_col2:
        # 使用placeholder实现"填写即清空"效果
        new_code = st.text_input("基金代码", max_chars=6, key="new_code", 
                                placeholder="输入6位数字", label_visibility="collapsed")
    
    # 自动显示基金名称
    fund_name = ""
    if new_code and len(new_code) == 6 and new_code.isdigit():
        if new_code in st.session_state.fund_cache:
            fund_name = st.session_state.fund_cache[new_code].get("name", "")
        else:
            with st.spinner("查询中..."):
                info = fetch_fund_data(new_code)
                if info:
                    fund_name = info["name"]
                    st.session_state.fund_cache[new_code] = info
        if fund_name:
            st.caption(f"📌 {fund_name}")
    
    # 持有份额 - 左右布局
    shares_col1, shares_col2 = st.columns([1, 3])
    with shares_col1:
        st.markdown('<div class="input-label">持有份额</div>', unsafe_allow_html=True)
    with shares_col2:
        # 使用None作为默认值，placeholder提示，实现填写即清空
        new_shares = st.number_input("持有份额", min_value=0.0, format="%.2f", 
                                    key="new_shares", placeholder="输入份额", 
                                    value=None, label_visibility="collapsed")
    
    # 成本价 - 左右布局
    cost_col1, cost_col2 = st.columns([1, 3])
    with cost_col1:
        st.markdown('<div class="input-label">成本价</div>', unsafe_allow_html=True)
    with cost_col2:
        new_cost = st.number_input("成本价", min_value=0.0, format="%.4f", 
                                  key="new_cost", step=0.0001, placeholder="输入成本价", 
                                  value=None, label_visibility="collapsed")
    
    # 添加按钮
    btn_col1, btn_col2 = st.columns([1, 3])
    with btn_col1:
        st.write("")  # 占位
    with btn_col2:
        if st.button("添加", type="primary", use_container_width=True):
            # 校验
            if not new_code or len(new_code) != 6 or not new_code.isdigit():
                st.error("请输入6位数字基金代码")
            elif new_shares is None or new_shares <= 0:
                st.error("请输入有效的持有份额")
            elif new_cost is None or new_cost <= 0:
                st.error("请输入有效的成本价")
            else:
                existing = next((i for i, h in enumerate(st.session_state.db["holdings"]) 
                               if h["code"] == new_code), None)
                
                if existing is not None:
                    # 加仓 - 移动平均
                    old = st.session_state.db["holdings"][existing]
                    total_shares = old["shares"] + new_shares
                    new_avg_cost = (old["shares"] * old["cost"] + new_shares * new_cost) / total_shares
                    old["shares"] = total_shares
                    old["cost"] = new_avg_cost
                    st.success(f"已加仓 {new_code}，新成本价: ¥{new_avg_cost:.4f}")
                else:
                    # 新建持仓
                    st.session_state.db["holdings"].append({
                        "code": new_code,
                        "name": fund_name or f"基金{new_code}",
                        "shares": new_shares,
                        "cost": new_cost
                    })
                    st.success(f"已添加 {new_code}")
                
                save_db(st.session_state.db)
                st.rerun()

st.markdown('</div>', unsafe_allow_html=True)
