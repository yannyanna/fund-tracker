import streamlit as st
from datetime import datetime
import json
import os
import urllib.request
import ssl
import re

# --- 基础设置 ---
USER_CONFIG_FILE = "user_config.json"
ssl_ctx = ssl._create_unverified_context()

st.set_page_config(page_title="资产管理精准版", layout="wide")

# --- 核心计算函数：修复所有逻辑错误 ---
def fetch_fund_data(code):
    try:
        url = f"http://fundgz.1234567.com.cn/js/{code}.js?rt={int(datetime.now().timestamp())}"
        req = urllib.request.Request(url, headers={'Referer': 'http://fund.eastmoney.com'})
        with urllib.request.urlopen(req, timeout=5, context=ssl_ctx) as res:
            content = res.read().decode('utf-8')
            json_str = content[content.find('{'):content.rfind('}')+1]
            data = json.loads(json_str)
            
            # gsz: 当前最新价 (2月3日收盘净值 3.4470)
            # gszzl: 今日涨幅 (例如 6.17)
            # dwjz: 接口里的昨净值 (可能滞后)
            
            current_p = float(data['gsz'])
            rate_pct = float(data['gszzl']) / 100
            
            # --- 逻辑校准：不再信任接口的昨净字段，而是通过涨幅倒推 ---
            # 昨净 = 当前价 / (1 + 涨幅)
            calc_last_p = current_p / (1 + rate_pct)
            
            return {
                "name": data['name'],
                "current_price": current_p,
                "last_price": calc_last_p,
                "rate": float(data['gszzl']),
                "time": data['gztime']
            }
    except: return None

# --- UI 样式 ---
st.markdown("""
<style>
    .summary-card { background: #1a1c23; color: #fff; padding: 20px; border-radius: 15px; text-align: center; margin-bottom: 20px; }
    .fund-card { background: #fff; padding: 15px; border-radius: 10px; border-left: 5px solid #eee; margin-bottom: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.05); }
    .up { color: #eb4444 !important; font-weight: bold; }
    .down { color: #22ad5c !important; font-weight: bold; }
    .val-text { font-size: 1.1rem; }
</style>
""", unsafe_allow_html=True)

# --- 数据读写 ---
def load_db(user):
    path = f"db_{user}.json"
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f: return json.load(f)
    return {"holdings": []}

cfg = {"users": ["Default"], "current": "Default"}
if os.path.exists(USER_CONFIG_FILE):
    with open(USER_CONFIG_FILE, 'r') as f: cfg = json.load(f)

# --- 主逻辑 ---
cur_u = cfg["current"]
db = load_db(cur_u)

# 顶部操作
col_t1, col_t2 = st.columns([3, 1])
with col_t1: st.title(f"📈 {cur_u} 的持仓")
with col_t2: 
    if st.button("🔄 刷新数据", use_container_width=True): st.rerun()

results = []
total_market = 0.0
total_day = 0.0

for h in db["holdings"]:
    f = fetch_fund_data(h['code'])
    if f:
        shares = float(h['shares'])
        cost = float(h['cost'])
        
        # 精准计算
        day_profit = shares * (f['current_price'] - f['last_price'])
        total_profit = shares * (f['current_price'] - cost)
        market_val = shares * f['current_price']
        
        total_market += market_val
        total_day += day_profit
        
        results.append({
            "name": f['name'], "code": h['code'], "price": f['current_price'],
            "rate": f['rate'], "day_p": day_profit, "total_p": total_profit,
            "time": f['time']
        })

# 资产看板
p_color = "up" if total_day >= 0 else "down"
st.markdown(f"""
<div class="summary-card">
    <div style="font-size:0.9rem; opacity:0.7">预估总市值 (CNY)</div>
    <div style="font-size:2.2rem; margin:10px 0">¥{total_market:,.2f}</div>
    <div style="display:flex; justify-content: center; gap:40px">
        <div>今日盈亏：<span class="{p_color}">{total_day:+.2f}</span></div>
        <div>持仓数：<span>{len(results)}</span></div>
    </div>
</div>
""", unsafe_allow_html=True)

# 持仓列表
for res in results:
    r_cls = "up" if res['rate'] >= 0 else "down"
    t_cls = "up" if res['total_p'] >= 0 else "down"
    st.markdown(f"""
    <div class="fund-card" style="border-left-color: {'#eb4444' if res['rate']>=0 else '#22ad5c'}">
        <div style="display:flex; justify-content:space-between; margin-bottom:8px">
            <span style="font-weight:bold; font-size:1rem">{res['name']} <small style="color:#999">{res['code']}</small></span>
            <span style="font-size:0.7rem; color:#bbb">{res['time']}</span>
        </div>
        <div style="display:flex; justify-content:space-between; text-align:center">
            <div style="flex:1"><div style="font-size:0.7rem; color:#999">当前净值</div><div class="val-text {r_cls}">{res['price']:.4f}</div><div class="{r_cls}" style="font-size:0.7rem">{res['rate']:+.2f}%</div></div>
            <div style="flex:1"><div style="font-size:0.7rem; color:#999">今日盈亏</div><div class="val-text {r_cls}">{res['day_p']:+.2f}</div></div>
            <div style="flex:1"><div style="font-size:0.7rem; color:#999">累计盈亏</div><div class="val-text {t_cls}">{res['total_p']:+.2f}</div></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# 管理区
with st.expander("⚙️ 管理持仓"):
    with st.form("m_form"):
        c1, c2, c3 = st.columns(3)
        m_c = c1.text_input("代码")
        m_s = c2.number_input("份额", format="%.2f")
        m_p = c3.number_input("成本价", format="%.4f")
        b1, b2 = st.columns(2)
        if b1.form_submit_button("💾 保存", use_container_width=True):
            if m_c:
                db["holdings"] = [x for x in db["holdings"] if x["code"] != m_c]
                db["holdings"].append({"code": m_c, "shares": m_s, "cost": m_p})
                with open(f"db_{cur_u}.json", 'w', encoding='utf-8') as f: json.dump(db, f)
                st.rerun()
        if b2.form_submit_button("🗑️ 删除", use_container_width=True):
            db["holdings"] = [x for x in db["holdings"] if x["code"] != m_c]
            with open(f"db_{cur_u}.json", 'w', encoding='utf-8') as f: json.dump(db, f)
            st.rerun()
