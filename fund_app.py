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

st.set_page_config(page_title="资产管理全功能版", layout="wide", initial_sidebar_state="expanded")

# --- 综合样式 ---
st.markdown("""
<style>
    .main { padding: 0.1rem !important; }
    .spacer-top { height: 25px; } 
    /* 总计看板 */
    .summary-card {
        background: #212529; color: white; padding: 15px; border-radius: 12px;
        margin-bottom: 12px; text-align: center;
    }
    .summary-grid { display: flex; justify-content: space-around; margin-top: 10px; }
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
    .fund-grid { display: flex; justify-content: space-between; text-align: center; margin-top: 8px; }
    .up { color: #e03131 !important; font-weight: bold; }
    .down { color: #2f9e44 !important; font-weight: bold; }
    .admin-section {
        margin-top: 20px; padding: 15px; background: #f8f9fa;
        border-top: 2px solid #ddd; border-radius: 15px 15px 0 0;
    }
    .input-label { text-align: right; padding-right: 10px; font-weight: bold; font-size: 0.9rem; color: #333; }
</style>
""", unsafe_allow_html=True)

# --- 核心函数 ---
def load_config():
    if os.path.exists(USER_CONFIG_FILE):
        try:
            with open(USER_CONFIG_FILE, 'r') as f: return json.load(f)
        except: pass
    return {"users": ["Default"], "current": "Default"}

def get_db(username):
    path = f"db_{username}.json"
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f: return json.load(f)
        except: pass
    return {"holdings": []}

def fetch_gold():
    d = {"au": 0.0, "xau": 0.0, "cny": 0.0}
    try:
        url = "http://hq.sinajs.cn/list=gds_AU9999,hf_XAU,fx_susdcnh"
        req = urllib.request.Request(url, headers={'Referer': 'http://finance.sina.com.cn'})
        with urllib.request.urlopen(req, timeout=3, context=ssl_ctx) as res:
            raw = res.read().decode('gbk')
            m1 = re.search(r'gds_AU9999="([^"]+)"', raw); m2 = re.search(r'hf_XAU="([^"]+)"', raw); m3 = re.search(r'fx_susdcnh="([^"]+)"', raw)
            if m1: d["au"] = float(m1.group(1).split(',')[0])
            if m2: d["xau"] = float(m2.group(1).split(',')[0])
            fx = float(m3.group(1).split(',')[1]) if m3 else 0
            if d["xau"] > 0 and fx > 0: d["cny"] = (d["xau"] * fx) / 31.1035
    except: pass
    return d

def fetch_fund_data(code):
    try:
        url = f"http://fundgz.1234567.com.cn/js/{code}.js?rt={int(datetime.now().timestamp())}"
        req = urllib.request.Request(url, headers={'Referer': 'http://fund.eastmoney.com'})
        with urllib.request.urlopen(req, timeout=5, context=ssl_ctx) as res:
            content = res.read().decode('utf-8')
            data = json.loads(content[content.find('{'):content.rfind('}')+1])
            curr_p = float(data['gsz'])
            rate_pct = float(data['gszzl']) / 100
            # 关键：通过涨幅倒推昨日价格，确保今日收益逻辑绝对准确
            calc_last_p = curr_p / (1 + rate_pct) if rate_pct != -1 else curr_p
            return {
                "name": data['name'], "price": curr_p, "last_p": calc_last_p,
                "rate": float(data['gszzl']), "time": data['gztime']
            }
    except: return None

# --- 侧边栏 ---
config = load_config()
with st.sidebar:
    st.subheader("👤 账号切换")
    cur_u = st.selectbox("当前用户", config["users"], index=config["users"].index(config["current"]) if config["current"] in config["users"] else 0)
    if cur_u != config["current"]:
        config["current"] = cur_u
        with open(USER_CONFIG_FILE, 'w') as f: json.dump(config, f)
        st.rerun()
    with st.expander("管理用户"):
        new_u = st.text_input("新增用户")
        if st.button("添加") and new_u:
            config["users"].append(new_u)
            with open(USER_CONFIG_FILE, 'w') as f: json.dump(config, f)
            st.rerun()
    st.divider()
    st.caption("🥛 晚上睡前一小时记得喝杯热牛奶")

# --- 主页面 ---
st.markdown('<div class="spacer-top"></div>', unsafe_allow_html=True)
db = get_db(cur_u)

col_h1, col_h2 = st.columns([3, 1])
with col_h1: st.subheader(f"📊 {cur_u} 的资产看板")
with col_h2: 
    if st.button("🔄 刷新行情", type="primary", use_container_width=True): st.rerun()

# 1. 黄金看板
g = fetch_gold()
st.markdown(f"""
<div class="gold-row">
    <div class="gold-box"><div style="font-size:0.6rem;color:#856404">上海金</div><div class="gold-price">¥{g['au']:.2f}</div></div>
    <div class="gold-box"><div style="font-size:0.6rem;color:#856404">国际金</div><div class="gold-price">${g['xau']:.2f}</div></div>
    <div class="gold-box"><div style="font-size:0.6rem;color:#856404">折合价</div><div class="gold-price">¥{g['cny']:.2f}</div></div>
</div>
""", unsafe_allow_html=True)

# 2. 基金计算逻辑
fund_results = []
total_market_val = 0.0
total_day_profit = 0.0

for h in db["holdings"]:
    f = fetch_fund_data(h['code'])
    if f:
        shares = float(h['shares'])
        cost = float(h['cost'])
        # 今日盈亏 = 份额 * (当前价 - 倒推昨价)
        day_p = shares * (f['price'] - f['last_p'])
        # 累计盈亏 = 份额 * (当前价 - 成本价)
        total_p = shares * (f['price'] - cost)
        m_val = shares * f['price']
        
        total_market_val += m_val
        total_day_profit += day_p
        fund_results.append({**h, **f, "day_p": day_p, "total_p": total_profit, "m_val": m_val, "total_p": total_p})

# 3. 总资产汇总
p_color = "up" if total_day_profit >= 0 else "down"
st.markdown(f"""
<div class="summary-card">
    <div style="font-size:0.8rem; color:#adb5bd">预估总市值 (CNY)</div>
    <div style="font-size:1.8rem; font-weight:bold">¥{total_market_val:,.2f}</div>
    <div class="summary-grid">
        <div><div style="font-size:0.7rem;color:#adb5bd">今日盈亏</div><div class="{p_color}" style="font-size:1.2rem">{total_day_profit:+.2f}</div></div>
        <div><div style="font-size:0.7rem;color:#adb5bd">持仓基金</div><div style="font-size:1.2rem">{len(fund_results)} 支</div></div>
    </div>
</div>
""", unsafe_allow_html=True)

# 4. 基金详细列表
for f in fund_results:
    r_cls = "up" if f['rate'] >= 0 else "down"
    t_cls = "up" if f['total_p'] >= 0 else "down"
    st.markdown(f"""
    <div class="fund-card">
        <div class="fund-header">
            <div><span style="font-weight:bold">{f['name']}</span> <small style="color:#888;background:#f5f5f5;padding:2px 5px">{f['code']}</small></div>
            <div style="font-size:0.7rem;color:#999">{f['time']}</div>
        </div>
        <div class="fund-grid">
            <div style="flex:1"><div style="font-size:0.65rem;color:#999">当前价/涨幅</div><div class="{r_cls}">{f['price']:.4f}</div><div class="{r_cls}" style="font-size:0.65rem">{f['rate']:+.2f}%</div></div>
            <div style="flex:1"><div style="font-size:0.65rem;color:#999">今日盈亏</div><div class="{r_cls}">{f['day_p']:+.2f}</div></div>
            <div style="flex:1"><div style="font-size:0.65rem;color:#999">累计盈亏</div><div class="{t_cls}">{f['total_p']:+.2f}</div></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# 5. 底部管理区 (表单模式)
st.markdown('<div class="admin-section">', unsafe_allow_html=True)
with st.expander("⚙️ 管理我的持仓", expanded=st.session_state.get('admin_exp', True)):
    with st.form("fund_form_final"):
        c1, c2 = st.columns([1, 4])
        with c1: st.markdown('<div class="input-label">代码</div>', unsafe_allow_html=True)
        with c2: m_code = st.text_input("code_f", max_chars=6, label_visibility="collapsed")
        c3, c4 = st.columns([1, 4])
        with c3: st.markdown('<div class="input-label">份额</div>', unsafe_allow_html=True)
        with c4: m_shares = st.number_input("share_f", format="%.2f", label_visibility="collapsed")
        c5, c6 = st.columns([1, 4])
        with c5: st.markdown('<div class="input-label">成本</div>', unsafe_allow_html=True)
        with c6: m_cost = st.number_input("cost_f", format="%.4f", label_visibility="collapsed")
        
        b1, b2 = st.columns(2)
        if b1.form_submit_button("💾 保存持仓", type="primary", use_container_width=True):
            if m_code:
                db["holdings"] = [x for x in db["holdings"] if x["code"] != m_code]
                db["holdings"].append({"code": m_code, "shares": m_shares, "cost": m_cost})
                with open(f"db_{cur_u}.json", 'w', encoding='utf-8') as f: json.dump(db, f)
                st.rerun()
        if b2.form_submit_button("🗑️ 删除持仓", use_container_width=True):
            db["holdings"] = [x for x in db["holdings"] if x["code"] != m_code]
            with open(f"db_{cur_u}.json", 'w', encoding='utf-8') as f: json.dump(db, f)
            st.rerun()
st.markdown('</div>', unsafe_allow_html=True)
