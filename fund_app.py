import streamlit as st
from datetime import datetime
import json
import os
import urllib.request
import ssl
import pytz
from streamlit_autorefresh import st_autorefresh

# --- 基础配置 ---
TZ = pytz.timezone('Asia/Shanghai')
DATA_FILE = "fund_master_v5.json"
ssl_ctx = ssl._create_unverified_context()

st.set_page_config(page_title="收益追踪 V5", layout="wide")

# --- 样式：黄金价格 1.5 倍 & 紧凑布局 ---
st.markdown("""
<style>
    .main { padding: 0rem !important; }
    .gold-header { background: #fffdf5; padding: 15px; border-radius: 12px; border: 1px solid #ffeaa7; margin-bottom: 10px; text-align: center; }
    .gold-value { font-size: 2.2rem !important; color: #d4af37; font-weight: 800; line-height: 1.2; }
    .gold-label { font-size: 1rem; color: #999; }
    [data-testid="stMetric"] { background: #f8f9fa; padding: 5px 10px; border-radius: 8px; }
    .fund-card { border-left: 5px solid #ff4b4b; padding: 10px; margin: 8px 0; background: #fff; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
</style>
""", unsafe_allow_html=True)

# --- 用户与数据管理修复 ---
def load_db():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f: return json.load(f)
        except: pass
    return {"Default": {"holdings": []}}

def save_db(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

if 'db' not in st.session_state:
    st.session_state.db = load_db()

# --- 增强型数据抓取 ---
@st.cache_data(ttl=30)
def fetch_gold_sina():
    try:
        url = "http://hq.sinajs.cn/list=gds_AU9999"
        req = urllib.request.Request(url, headers={'Referer': 'http://finance.sina.com.cn'})
        with urllib.request.urlopen(req, timeout=5, context=ssl_ctx) as res:
            line = res.read().decode('gbk')
            price = float(line.split('"')[1].split(',')[0])
            return {"price": price, "time": datetime.now(TZ).strftime('%H:%M:%S')}
    except: return {"price": 0.0, "time": "ERR"}

def fetch_fund_v5(code):
    try:
        url = f"http://fundgz.1234567.com.cn/js/{code}.js"
        with urllib.request.urlopen(url, timeout=3, context=ssl_ctx) as res:
            c = res.read().decode('utf-8')
            d = json.loads(c[c.find('{'):c.rfind('}')+1])
            return {"name": d['name'], "gz": float(d['gsz']), "nj": float(d['dwjz']), "ratio": float(d['gszzl']), "time": d['gztime']}
    except: return None

# --- 侧边栏：修复用户名无法保存问题 ---
with st.sidebar:
    st.title("👤 账户管理")
    usernames = list(st.session_state.db.keys())
    
    # 新增用户逻辑
    with st.expander("➕ 新增账号"):
        new_u = st.text_input("用户名", key="input_new_u")
        if st.button("确认添加"):
            if new_u and new_u not in st.session_state.db:
                st.session_state.db[new_u] = {"holdings": []}
                save_db(st.session_state.db)
                st.rerun()

    current_user = st.selectbox("当前登录", usernames)

u_data = st.session_state.db[current_user]

# --- 主界面渲染 ---
st_autorefresh(interval=30000, key="v5_ref")

# 1. 黄金面板：1.5 倍大小 [参考截图风格]
gold = fetch_gold_sina()
st.markdown(f"""
<div class="gold-header">
    <div class="gold-label">🟡 国内黄金 (AU9999) 人民币/克</div>
    <div class="gold-value">¥{gold['price']:.2f}</div>
    <div style="font-size:0.8rem; color:#ccc;">更新时间: {gold['time']}</div>
</div>
""", unsafe_allow_html=True)

# 2. 基金看板
holdings = u_data["holdings"]
if holdings:
    live_data = {h['code']: fetch_fund_v5(h['code']) for h in holdings}
    total_val, total_day_profit = 0.0, 0.0
    fund_results = []
    
    for i, h in enumerate(holdings):
        f = live_data.get(h['code'])
        if f:
            m_val = h['shares'] * f['gz']
            d_profit = h['shares'] * (f['gz'] - f['nj'])
            total_val += m_val
            total_day_profit += d_profit
            fund_results.append({**h, **f, "m_val": m_val, "d_profit": d_profit, "idx": i})

    # 总览：压缩行距 [参考截图]
    c1, c2 = st.columns(2)
    c1.metric("资产总额", f"¥{total_val:,.2f}")
    c2.metric("当日收益", f"¥{total_day_profit:,.2f}", f"{(total_day_profit/(total_val-total_day_profit+0.1)*100):.2f}%")

    st.divider()

    # 3. 基金列表 & 修改功能
    for f in fund_results:
        color = "#e74c3c" if f['d_profit'] >= 0 else "#27ae60"
        with st.container():
            st.markdown(f"""
            <div class="fund-card" style="border-left-color: {color}">
                <div style="display:flex; justify-content:space-between;">
                    <b style="font-size:1.1rem;">{f['name']} <small style="color:#999; font-weight:normal;">{f['code']}</small></b>
                    <span style="color:{color}; font-weight:bold;">{f['ratio']:+.2f}%</span>
                </div>
                <div style="display:flex; justify-content:space-between; margin-top:8px;">
                    <span>市值: <b>¥{f['m_val']:,.2f}</b></span>
                    <span style="color:{color}">收益: <b>¥{f['d_profit']:,.2f}</b></span>
                </div>
                <div style="font-size:0.75rem; color:#bbb; margin-top:4px;">
                    估值: {f['gz']:.4f} | 昨净: {f['nj']:.4f} | 更新: {f['time']}
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            with st.expander(f"⚙️ 修改/删除"):
                ec1, ec2 = st.columns(2)
                # 使用 value=None 配合 placeholder 实现“直接输入，无需删除0.00”
                new_s = ec1.number_input("份额", value=None, placeholder=str(f['shares']), key=f"edit_s_{f['idx']}")
                new_c = ec2.number_input("成本", value=None, placeholder=f"{f['cost']:.4f}", format="%.4f", key=f"edit_c_{f['idx']}")
                
                bc1, bc2 = st.columns(2)
                if bc1.button("保存", key=f"btn_s_{f['idx']}"):
                    if new_s is not None: u_data["holdings"][f['idx']]['shares'] = new_s
                    if new_c is not None: u_data["holdings"][f['idx']]['cost'] = new_c
                    save_db(st.session_state.db); st.rerun()
                if bc2.button("删除", key=f"btn_d_{f['idx']}"):
                    u_data["holdings"].pop(f['idx'])
                    save_db(st.session_state.db); st.rerun()

# 4. 添加管理：彻底解决 0.00 删除烦恼
with st.expander("➕ 添加新基金持仓"):
    new_code = st.text_input("代码 (6位)")
    ac1, ac2 = st.columns(2)
    # 设置 value=None，用户点开就是空的，直接输入
    add_s = ac1.number_input("持有份额", value=None, placeholder="直接输入份额", step=0.01)
    add_c = ac2.number_input("持仓成本", value=None, placeholder="直接输入成本", format="%.4f", step=0.0001)
    
    if st.button("立即存入", type="primary"):
        if len(new_code) == 6 and add_s and add_c:
            u_data["holdings"].append({"code": new_code, "shares": add_s, "cost": add_c})
            save_db(st.session_state.db)
            st.success("添加成功！")
            st.rerun()
