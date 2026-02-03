import streamlit as st
from datetime import datetime
import json
import os
import urllib.request
import ssl
import pytz

# --- 基础配置 ---
TZ = pytz.timezone('Asia/Shanghai')
DATA_FILE = "fund_master_v18.json"
ssl_ctx = ssl._create_unverified_context()

st.set_page_config(page_title="收益追踪 V18-Final", layout="wide")

# --- 深度修复保存逻辑 ---
def load_db():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f: return json.load(f)
        except: pass
    return {"Default": {"holdings": []}}

def save_db(data):
    st.session_state.db = data
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# --- 初始化 ---
if 'db' not in st.session_state: st.session_state.db = load_db()

# --- 接口逻辑 ---
def fetch_gold():
    try:
        url = "http://hq.sinajs.cn/list=gds_AU9999"
        req = urllib.request.Request(url, headers={'Referer': 'http://finance.sina.com.cn'})
        with urllib.request.urlopen(req, timeout=3, context=ssl_ctx) as res:
            return float(res.read().decode('gbk').split('"')[1].split(',')[0])
    except: return 0.0

def fetch_fund(code, source):
    try:
        if "天天" in source:
            url = f"http://fundgz.1234567.com.cn/js/{code}.js"
            with urllib.request.urlopen(url, timeout=3, context=ssl_ctx) as res:
                c = res.read().decode('utf-8'); d = json.loads(c[c.find('{'):c.rfind('}')+1])
                return {"name": d['name'], "gz": float(d['gsz']), "nj": float(d['dwjz']), "ratio": float(d['gszzl'])}
        else: # 新浪
            url = f"http://hq.sinajs.cn/list=f_{code}"
            req = urllib.request.Request(url, headers={'Referer': 'http://finance.sina.com.cn'})
            with urllib.request.urlopen(req, timeout=3, context=ssl_ctx) as res:
                r = res.read().decode('gbk').split('"')[1].split(',')
                return {"name": "基金"+code, "gz": float(r[0]), "nj": float(r[2]), "ratio": (float(r[0])-float(r[2]))/float(r[2])*100}
    except: return None

# --- 侧边栏 ---
with st.sidebar:
    st.header("👤 账户管理")
    # 创建用户并自动切换逻辑
    new_user_input = st.text_input("新建用户名")
    if st.button("创建并自动切换"):
        if new_user_input and new_user_input not in st.session_state.db:
            new_db = st.session_state.db.copy()
            new_db[new_user_input] = {"holdings": []}
            save_db(new_db)
            st.session_state.last_user = new_user_input # 标记新用户
            st.rerun()
    
    user_list = list(st.session_state.db.keys())
    default_idx = user_list.index(st.session_state.get('last_user', user_list[0])) if st.session_state.get('last_user') in user_list else 0
    current_user = st.selectbox("当前登录账户", user_list, index=default_idx)

# --- 主界面 ---
# 1. 顶部控制（切换数据源联动刷新）
t_col1, t_col2 = st.columns([1, 1])
with t_col1:
    if st.button("🔄 强制刷新行情"):
        st.cache_data.clear(); st.rerun()
with t_col2:
    data_src = st.selectbox("核心数据源", ["天天基金(推荐)", "新浪财经(同步)"], on_change=st.cache_data.clear)

# 2. 黄金看板
gp = fetch_gold()
st.markdown(f'<div style="background:#fffdf2; padding:15px; border-radius:12px; text-align:center; border:1px solid #fdf0c2; margin-bottom:10px;"><div style="font-size:1.8rem; color:#b8860b; font-weight:bold;">¥{gp:.2f}</div><div style="font-size:0.8rem; color:#999;">国内现货黄金实时价</div></div>', unsafe_allow_html=True)

# 3. 数据渲染
u_data = st.session_state.db[current_user]
results = []
total_v, total_dp = 0.0, 0.0

for h in u_data["holdings"]:
    f = fetch_fund(h['code'], data_src)
    if f:
        mv = h['shares'] * f['gz']
        dp = h['shares'] * (f['gz'] - f['nj'])
        tp = h['shares'] * (f['gz'] - h['cost'])
        results.append({**h, **f, "mv": mv, "dp": dp, "tp": tp})
        total_v += mv
        total_dp += dp

st.markdown(f"""<div style="display:flex; justify-content:space-between; padding:10px 15px; background:#fff; border-bottom:1px solid #eee;">
    <div><div style="font-size:0.8rem; color:#999;">账户资产</div><div style="font-size:1.4rem; font-weight:bold;">¥{total_v:,.2f}</div></div>
    <div style="text-align:right;"><div style="font-size:0.8rem; color:#999;">当日收益</div><div style="font-size:1.4rem; font-weight:bold; color:{"#e74c3c" if total_dp>=0 else "#27ae60"}">{total_dp:+,.2f}</div></div>
</div>""", unsafe_allow_html=True)

for f in results:
    st.markdown(f"""
    <div style="display:flex; padding:12px 15px; background:white; border-bottom:1px solid #f2f2f2; align-items:center;">
        <div style="flex:2"><div><b>{f['name']}</b></div><div style="font-size:0.75rem; color:#999;">{f['code']}</div></div>
        <div style="flex:1.2; text-align:right"><div style="color:{"#e74c3c" if f['ratio']>=0 else "#27ae60"}; font-weight:bold;">{f['ratio']:+.2f}%</div><div style="font-size:0.75rem; color:#999;">{f['gz']:.4f}</div></div>
        <div style="flex:1.5; text-align:right"><div style="color:{"#e74c3c" if f['dp']>=0 else "#27ae60"}">{f['dp']:+,.2f}</div><div style="font-size:0.75rem; color:#999;">持有:{f['tp']:+,.2f}</div></div>
    </div>
    """, unsafe_allow_html=True)

# 4. 资产增减与名称自动识别
st.markdown("<br>", unsafe_allow_html=True)
with st.expander("📝 资产增减仓 / 修改持仓"):
    m_code = st.text_input("输入基金代码", help="输入6位代码后自动显示名称")
    if len(m_code) == 6:
        info = fetch_fund(m_code, "天天基金")
        if info: st.success(f"已识别：{info['name']}")
    
    target = next((i for i in u_data["holdings"] if i['code'] == m_code), None)
    
    col1, col2 = st.columns(2)
    # 根据你的要求改名，并增加逻辑
    if target:
        st.info(f"当前持有：{target['shares']} 份 | 持有成本：{target['cost']:.4f}")
        op = st.radio("调仓类型", ["加仓 (买入)", "减仓 (卖出)"], horizontal=True)
    else:
        op = "加仓 (买入)"
    
    m_s = col1.number_input("持有份额" if not target else "变动份额", value=None)
    m_p = col2.number_input("持有成本" if not target else "成交单价", value=None, format="%.4f")
    
    if st.button("保存更新", type="primary"):
        if m_code and m_s:
            if target:
                if "加仓" in op:
                    new_total = target['shares'] + m_s
                    target['cost'] = (target['shares'] * target['cost'] + m_s * m_p) / new_total
                    target['shares'] = new_total
                else:
                    target['shares'] = max(0, target['shares'] - m_s)
            else:
                u_data["holdings"].append({"code": m_code, "shares": m_s, "cost": m_p or 0.0})
            save_db(st.session_state.db); st.rerun()

with st.expander("🗑️ 管理/删除记录"):
    for i, h in enumerate(u_data["holdings"]):
        c_del1, c_del2 = st.columns([4, 1])
        c_del1.write(f"**{h['code']}** | 成本 {h['cost']:.4f}")
        if c_del2.button("删除", key=f"del_{i}"):
            u_data["holdings"].pop(i); save_db(st.session_state.db); st.rerun()
