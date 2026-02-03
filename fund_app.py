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
USER_CONFIG_FILE = "user_config.json"
ssl_ctx = ssl._create_unverified_context()

st.set_page_config(page_title="资产管理 Pro", layout="wide", initial_sidebar_state="expanded")

# --- 增强样式 ---
st.markdown("""
<style>
    .main { padding: 0.1rem !important; }
    .spacer-top { height: 45px; } 
    
    /* 总计看板 */
    .summary-card {
        background: #212529; color: white; padding: 15px; border-radius: 12px;
        margin-bottom: 12px; text-align: center;
    }
    .summary-grid { display: flex; justify-content: space-around; margin-top: 10px; }
    .summary-val { font-size: 1.2rem; font-weight: bold; }
    .summary-lab { font-size: 0.7rem; color: #adb5bd; }

    /* 黄金看板 */
    .gold-row { display: flex; gap: 6px; margin-bottom: 12px; }
    .gold-box {
        flex: 1; background: linear-gradient(135deg, #fffdf2 0%, #fff9e6 100%);
        padding: 8px 4px; border-radius: 8px; text-align: center; border: 1px solid #f0e6cc;
    }
    .gold-price { font-size: 1.1rem; font-weight: bold; color: #b8860b; }

    /* 基金卡片 */
    .fund-card {
        background: white; padding: 12px; margin-bottom: 10px;
        border-radius: 10px; border: 1px solid #eee;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .fund-header { display: flex; justify-content: space-between; border-bottom: 1px solid #f0f0f0; padding-bottom: 5px; }
    .fund-name { font-size: 0.95rem; font-weight: bold; color: #333; }
    .fund-grid { display: flex; justify-content: space-between; text-align: center; margin-top: 8px; }
    .fund-item { flex: 1; }
    .fund-label { font-size: 0.65rem; color: #999; }
    .fund-value { font-size: 0.9rem; font-weight: 600; }
    
    .up { color: #e03131 !important; } .down { color: #2f9e44 !important; }
    
    /* 底部管理区 */
    .admin-section {
        margin-top: 20px; padding: 15px; background: #f8f9fa;
        border-top: 2px solid #ddd; border-radius: 15px 15px 0 0;
    }
    div[data-testid="column"] { display: flex; align-items: center; } 
    .input-label { width: 100%; text-align: right; padding-right: 10px; font-weight: bold; font-size: 0.9rem; color: #333; }
</style>
""", unsafe_allow_html=True)

# --- 核心函数 ---
def load_config():
    if os.path.exists(USER_CONFIG_FILE):
        try:
            with open(USER_CONFIG_FILE, 'r') as f: return json.load(f)
        except: pass
    return {"users": ["Default"], "current": "Default"}

def save_config(cfg):
    with open(USER_CONFIG_FILE, 'w') as f: json.dump(cfg, f)

def get_db(username):
    path = f"db_{username}.json"
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f: return json.load(f)
        except: pass
    return {"holdings": []}

def save_db(username, data):
    with open(f"db_{username}.json", 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def fetch_gold():
    d = {"au": 0.0, "xau": 0.0, "cny": 0.0}
    try:
        url = "http://hq.sinajs.cn/list=gds_AU9999,hf_XAU,fx_susdcnh"
        req = urllib.request.Request(url, headers={'Referer': 'http://finance.sina.com.cn'})
        with urllib.request.urlopen(req, timeout=3, context=ssl_ctx) as res:
            raw = res.read().decode('gbk')
            m1 = re.search(r'gds_AU9999="([^"]+)"', raw)
            m2 = re.search(r'hf_XAU="([^"]+)"', raw)
            m3 = re.search(r'fx_susdcnh="([^"]+)"', raw)
            if m1: d["au"] = float(m1.group(1).split(',')[0])
            if m2: d["xau"] = float(m2.group(1).split(',')[0])
            fx = float(m3.group(1).split(',')[1]) if m3 else 0
            if d["xau"] > 0 and fx > 0: d["cny"] = (d["xau"] * fx) / 31.1035
    except: pass
    return d

def fetch_fund_realtime(code):
    try:
        url = f"http://fundgz.1234567.com.cn/js/{code}.js?rt={int(datetime.now().timestamp())}"
        req = urllib.request.Request(url, headers={'Referer': 'http://fund.eastmoney.com'})
        with urllib.request.urlopen(req, timeout=3, context=ssl_ctx) as res:
            content = res.read().decode('utf-8')
            data = json.loads(content[content.find('{'):content.rfind('}')+1])
            return {"name": data['name'], "nav": float(data['dwjz']), "est": float(data['gsz']), "rate": float(data['gszzl']), "time": data['gztime']}
    except: return None

# --- 侧边栏 ---
config = load_config()
with st.sidebar:
    st.subheader("👤 用户系统")
    cur_u = st.selectbox("当前登录", config["users"], index=config["users"].index(config["current"]) if config["current"] in config["users"] else 0)
    if cur_u != config["current"]:
        config["current"] = cur_u
        save_config(config)
        st.rerun()
    with st.expander("管理用户"):
        new_u = st.text_input("新增")
        if st.button("添加") and new_u:
            config["users"].append(new_u); save_config(config); st.rerun()
    st.divider()
    st.caption("🥛 睡前一小时记得喝杯热牛奶")

# --- 主页面 ---
st.markdown('<div class="spacer-top"></div>', unsafe_allow_html=True)
db = get_db(cur_u)

# 1. 刷新
if st.button("🔄 实时刷新", type="primary", use_container_width=True):
    st.cache_data.clear(); st.rerun()

# 2. 黄金行情
g = fetch_gold()
st.markdown(f"""
<div class="gold-row">
    <div class="gold-box"><div style="font-size:0.6rem">上海金</div><div class="gold-price">¥{g['au']:.2f}</div></div>
    <div class="gold-box"><div style="font-size:0.6rem">国际现货</div><div class="gold-price">${g['xau']:.2f}</div></div>
    <div class="gold-box"><div style="font-size:0.6rem">折合汇率</div><div class="gold-price">¥{g['cny']:.2f}</div></div>
</div>
""", unsafe_allow_html=True)

# 3. 核心计算与数据处理
fund_results = []
total_market_val = 0.0
total_day_profit = 0.0

for h in db["holdings"]:
    rt = fetch_fund_realtime(h['code'])
    if rt:
        shares = float(h['shares'])
        cost = float(h['cost'])
        m_val = shares * rt['est']
        d_profit = shares * rt['est'] * rt['rate'] / 100
        h_profit = (rt['est'] - cost) * shares
        total_market_val += m_val
        total_day_profit += d_profit
        fund_results.append({**h, **rt, "m_val": m_val, "d_profit": d_profit, "h_profit": h_profit})

# 4. 资产汇总面板
profit_color = "up" if total_day_profit >= 0 else "down"
st.markdown(f"""
<div class="summary-card">
    <div style="font-size:0.8rem; color:#adb5bd">账户预估总市值 (CNY)</div>
    <div style="font-size:1.8rem; font-weight:bold">¥{total_market_val:,.2f}</div>
    <div class="summary-grid">
        <div><div class="summary-lab">今日盈亏</div><div class="summary-val {profit_color}">{total_day_profit:+.2f}</div></div>
        <div><div class="summary-lab">持仓基金</div><div class="summary-val">{len(fund_results)} 支</div></div>
    </div>
</div>
""", unsafe_allow_html=True)

# 5. 基金卡片列表
for f in fund_results:
    c_cls = "up" if f['rate'] >= 0 else "down"
    t_cls = "up" if f['h_profit'] >= 0 else "down"
    st.markdown(f"""
    <div class="fund-card">
        <div class="fund-header">
            <div><span class="fund-name">{f['name']}</span> <span style="color:#888;font-size:0.7rem">{f['code']}</span></div>
            <div style="font-size:0.7rem;color:#999">{f['time'][-5:]}</div>
        </div>
        <div class="fund-grid">
            <div class="fund-item"><div class="fund-label">实时估值</div><div class="fund-value {c_cls}">{f['est']:.4f}</div><div style="font-size:0.65rem" class="{c_cls}">{f['rate']:+.2f}%</div></div>
            <div class="fund-item"><div class="fund-label">今日收益</div><div class="fund-value {c_cls}">{f['d_profit']:+.0f}</div></div>
            <div class="fund-item"><div class="fund-label">持有收益</div><div class="fund-value {t_cls}">{f['h_profit']:+.0f}</div></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# 6. 底部管理区 (表单)
st.markdown('<div class="admin-section">', unsafe_allow_html=True)
with st.expander("⚙️ 持仓管理 (增/删/改)", expanded=st.session_state.get('admin_expanded', True)):
    with st.form("fund_form", clear_on_submit=False):
        r1_c1, r1_c2 = st.columns([1, 4])
        with r1_c1: st.markdown('<div class="input-label">代码</div>', unsafe_allow_html=True)
        with r1_c2: m_code = st.text_input("c", max_chars=6, label_visibility="collapsed")
        
        r2_c1, r2_c2 = st.columns([1, 4])
        with r2_c1: st.markdown('<div class="input-label">份额</div>', unsafe_allow_html=True)
        with r2_c2: m_shares = st.number_input("s", value=None, step=100.0, label_visibility="collapsed")
        
        r3_c1, r3_c2 = st.columns([1, 4])
        with r3_c1: st.markdown('<div class="input-label">成本</div>', unsafe_allow_html=True)
        with r3_c2: m_cost = st.number_input("p", value=None, format="%.4f", label_visibility="collapsed")
        
        b1, b2 = st.columns(2)
        if b1.form_submit_button("💾 保存/更新", type="primary", use_container_width=True):
            if m_code and m_shares is not None:
                info = fetch_fund_realtime(m_code)
                idx = next((i for i, x in enumerate(db["holdings"]) if x["code"] == m_code), None)
                item = {"code": m_code, "name": info['name'] if info else "未知", "shares": m_shares, "cost": m_cost if m_cost else 0.0}
                if idx is not None: db["holdings"][idx] = item
                else: db["holdings"].append(item)
                save_db(cur_u, db); st.session_state.admin_expanded = False; st.rerun()
        
        if b2.form_submit_button("🗑️ 删除", use_container_width=True):
            db["holdings"] = [x for x in db["holdings"] if x["code"] != m_code]
            save_db(cur_u, db); st.session_state.admin_expanded = False; st.rerun()

st.markdown('</div>', unsafe_allow_html=True)
