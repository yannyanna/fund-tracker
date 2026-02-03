import streamlit as st
import json
import os
import urllib.request
import ssl

# --- 1. 基础配置与安全 ---
ssl_ctx = ssl._create_unverified_context()
DATA_FILE = "fund_master_v25.json"

st.set_page_config(page_title="收益追踪 V25", layout="wide")

# --- 2. 核心数据存取 (最简单的逻辑) ---
def load_db():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f: return json.load(f)
        except: pass
    return {"Default": []}

def save_db(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# 初始化数据
if 'db' not in st.session_state:
    st.session_state.db = load_db()

# --- 3. 侧边栏：账户切换 ---
with st.sidebar:
    st.header("👤 账户管理")
    nu = st.text_input("新建用户", placeholder="输入名字")
    if st.button("创建"):
        if nu and nu not in st.session_state.db:
            st.session_state.db[nu] = []
            save_db(st.session_state.db)
            st.rerun()
    
    u_list = list(st.session_state.db.keys())
    selected_user = st.selectbox("当前账户", u_list)

# --- 4. 刷新按钮 ---
if st.button("🔄 刷新", use_container_width=True):
    st.rerun()

# --- 5. 黄金价格 (带更新时间) ---
try:
    url = "http://hq.sinajs.cn/list=gds_AU9999"
    req = urllib.request.Request(url, headers={'Referer': 'http://finance.sina.com.cn'})
    with urllib.request.urlopen(req, timeout=3, context=ssl_ctx) as res:
        g = res.read().decode('gbk').split('"')[1].split(',')
        st.markdown(f"""
        <div style="background:#fffcf0; padding:15px; border-radius:10px; text-align:center; border:1px solid #ffe082;">
            <div style="font-size:1.8rem; color:#f57f17; font-weight:bold;">¥{g[0]}</div>
            <div style="font-size:0.8rem; color:#795548;">AU9999 黄金价格 (更新时间: {g[5]})</div>
        </div>
        """, unsafe_allow_html=True)
except:
    st.warning("无法获取黄金行情")

# --- 6. 基金列表显示 ---
total_v, total_dp = 0.0, 0.0
holdings = st.session_state.db[selected_user]
results = []

for i, h in enumerate(holdings):
    try:
        url = f"http://fundgz.1234567.com.cn/js/{h['code']}.js"
        with urllib.request.urlopen(url, timeout=3, context=ssl_ctx) as res:
            raw = res.read().decode('utf-8')
            d = json.loads(raw[raw.find('{'):raw.rfind('}')+1])
            
            price = float(d['gsz'])
            prev = float(d['dwjz'])
            ratio = float(d['gszzl'])
            
            mv = h['shares'] * price
            dp = h['shares'] * (price - prev)
            tp = h['shares'] * (price - h['cost'])
            
            total_v += mv
            total_dp += dp
            results.append({**d, "mv": mv, "dp": dp, "tp": tp, "ratio": ratio, "idx": i})
    except:
        st.error(f"基金 {h['code']} 加载失败")

# 资产看板
st.markdown(f"""
<div style="display:flex; justify-content:space-between; padding:15px; background:#fff; border-bottom:2px solid #eee;">
    <div><small style="color:#999;">总资产</small><br><b style="font-size:1.3rem;">¥{total_v:,.2f}</b></div>
    <div style="text-align:right;"><small style="color:#999;">今日预估</small><br><b style="font-size:1.3rem; color:{"#e74c3c" if total_dp>=0 else "#27ae60"}">{total_dp:+,.2f}</b></div>
</div>
""", unsafe_allow_html=True)

# 渲染每一行基金
for r in results:
    st.markdown(f"""
    <div style="display:flex; padding:10px; border-bottom:1px solid #f9f9f9; align-items:center;">
        <div style="flex:2"><b>{r['name']}</b><br><small style="color:#999">{r['fundcode']} | {r['gztime'][-8:]}</small></div>
        <div style="flex:1.2; text-align:right;"><span style="color:{"#e74c3c" if r['ratio']>=0 else "#27ae60"}; font-weight:bold;">{r['ratio']:+.2f}%</span><br><small>{r['gsz']}</small></div>
        <div style="flex:1.5; text-align:right;"><span style="color:{"#e74c3c" if r['dp']>=0 else "#27ae60"}">{r['dp']:+,.2f}</span><br><small style="color:#999">持有:{r['tp']:+,.2f}</small></div>
    </div>
    """, unsafe_allow_html=True)

# --- 7. 管理与添加 ---
st.markdown("<br>", unsafe_allow_html=True)
with st.expander("💼 资产管理"):
    # 添加功能 (无0化)
    st.subheader("添加/补仓")
    c1, c2, c3 = st.columns([1, 1, 1])
    a_code = c1.text_input("基金代码", placeholder="6位数字")
    a_share = c2.number_input("份额", value=None, placeholder="输入份额")
    a_cost = c3.number_input("成本", value=None, placeholder="输入成本")
    
    if st.button("确认保存到账本", type="primary"):
        if a_code and a_share:
            st.session_state.db[selected_user].append({"code": a_code, "shares": a_share, "cost": a_cost or 0.0})
            save_db(st.session_state.db)
            st.success("已保存！")
            st.rerun()

    # 删除功能
    st.subheader("现有持仓清理")
    for r in results:
        col_n, col_d = st.columns([4, 1])
        col_n.write(f"{r['name']} ({r['fundcode']})")
        if col_d.button("删除", key=f"btn_del_{r['idx']}"):
            st.session_state.db[selected_user].pop(r['idx'])
            save_db(st.session_state.db)
            st.rerun()
