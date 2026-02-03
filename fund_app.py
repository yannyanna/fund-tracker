import streamlit as st
import json
import os
import urllib.request
import ssl
from datetime import datetime

# --- 环境与安全配置 ---
ssl_ctx = ssl._create_unverified_context()
DATA_FILE = "fund_master_v20.json"

st.set_page_config(page_title="收益追踪 V20-Pro", layout="wide")

# --- 数据持久化层 ---
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

if 'db' not in st.session_state: st.session_state.db = load_db()

# --- 核心数据接口 ---
def fetch_gold():
    try:
        url = "http://hq.sinajs.cn/list=gds_AU9999"
        req = urllib.request.Request(url, headers={'Referer': 'http://finance.sina.com.cn'})
        with urllib.request.urlopen(req, timeout=3, context=ssl_ctx) as res:
            return float(res.read().decode('gbk').split('"')[1].split(',')[0])
    except: return 0.0

def fetch_fund_data(code, source):
    try:
        if "天天" in source:
            url = f"http://fundgz.1234567.com.cn/js/{code}.js"
            with urllib.request.urlopen(url, timeout=3, context=ssl_ctx) as res:
                c = res.read().decode('utf-8')
                d = json.loads(c[c.find('{'):c.rfind('}')+1])
                # 天天基金：gsz是估值，dwjz是昨日净值，gztime是更新时间
                return {"name": d['name'], "price": float(d['gsz']), "prev": float(d['dwjz']), 
                        "ratio": float(d['gszzl']), "time": d['gztime']}
        else: # 新浪源
            url = f"http://hq.sinajs.cn/list=f_{code}"
            req = urllib.request.Request(url, headers={'Referer': 'http://finance.sina.com.cn'})
            with urllib.request.urlopen(req, timeout=3, context=ssl_ctx) as res:
                raw = res.read().decode('gbk')
                parts = raw.split('"')[1].split(',')
                if len(parts) < 5: return None
                curr, prev = float(parts[0]), float(parts[2])
                if curr > 1000: curr = prev # 过滤异常
                return {"name": f"基金{code}", "price": curr, "prev": prev, 
                        "ratio": (curr-prev)/prev*100, "time": parts[4]}
    except: return None

# --- 侧边栏 ---
with st.sidebar:
    st.header("👤 账户管理")
    nu = st.text_input("新建用户", placeholder="输入名字")
    if st.button("创建并自动登录"):
        if nu and nu not in st.session_state.db:
            new_db = st.session_state.db.copy()
            new_db[nu] = {"holdings": []}
            save_db(new_db)
            st.session_state.current_user = nu 
            st.rerun()

    u_list = list(st.session_state.db.keys())
    if 'current_user' not in st.session_state: st.session_state.current_user = u_list[0]
    c_user = st.selectbox("当前账户", u_list, index=u_list.index(st.session_state.current_user))
    st.session_state.current_user = c_user

# --- 主界面逻辑 ---

# 1. 顶部双控栏：数据源切换自动触发 Rerun
col_btn, col_src = st.columns([1, 1])
with col_btn:
    if st.button("🔄 强制同步全部数据"):
        st.cache_data.clear()
        st.rerun()
with col_src:
    # 只要这个值变了，Streamlit 会自动重新运行整个 script
    data_src = st.selectbox("🛰️ 核心数据源", ["天天基金(推荐)", "新浪财经(同步)"], key="src_selector")

# 2. 黄金看板
gold_p = fetch_gold()
st.markdown(f"""
<div style="background: linear-gradient(135deg, #fffcf0 0%, #fff8e1 100%); padding:15px; border-radius:12px; text-align:center; border:1px solid #ffe082; margin-bottom:15px;">
    <div style="font-size:1.8rem; color:#f57f17; font-weight:800;">¥{gold_p:.2f}</div>
    <div style="font-size:0.8rem; color:#795548; margin-top:2px;">实金 AU9999 实时汇率</div>
</div>
""", unsafe_allow_html=True)

# 3. 资产计算渲染
u_data = st.session_state.db[st.session_state.current_user]
results = []
total_v, total_dp = 0.0, 0.0
is_official = False # 标记是否为官方净值

today_str = datetime.now().strftime("%Y-%m-%d")

for h in u_data["holdings"]:
    f = fetch_fund_data(h['code'], data_src)
    if f:
        # 判断是否为今日最终净值 (天天基金的时间戳包含日期)
        if today_str in f['time'] and "15:00" not in f['time']:
             is_official = True # 如果更新时间晚于15:00且日期是今天
        
        mv = h['shares'] * f['price']
        dp = h['shares'] * (f['price'] - f['prev'])
        tp = h['shares'] * (f['price'] - h['cost'])
        results.append({**h, **f, "mv": mv, "dp": dp, "tp": tp})
        total_v += mv
        total_dp += dp

# 汇总看板：根据时间自动切换“预估”或“实际”
status_text = "今日收益" if is_official else "当日预估"
st.markdown(f"""
<div style="background:#fff; padding:15px; border-bottom:3px solid #eee; display:flex; justify-content:space-between;">
    <div><div style="color:#999; font-size:0.8rem;">{st.session_state.current_user} 的资产</div><div style="font-size:1.5rem; font-weight:bold;">¥{total_v:,.2f}</div></div>
    <div style="text-align:right;"><div style="color:#999; font-size:0.8rem;">{status_text}</div><div style="font-size:1.5rem; font-weight:bold; color:{"#e74c3c" if total_dp>=0 else "#27ae60"}">{total_dp:+,.2f}</div></div>
</div>
""", unsafe_allow_html=True)

# 列表
for f in results:
    label = "" if is_official else "估 "
    st.markdown(f"""
    <div style="display:flex; padding:12px 15px; border-bottom:1px solid #f2f2f2; align-items:center; background:white;">
        <div style="flex:2"><b>{f['name']}</b><br><small style="color:#999">{f['code']}</small></div>
        <div style="flex:1; text-align:right;"><span style="color:{"#e74c3c" if f['ratio']>=0 else "#27ae60"}; font-weight:bold;">{f['ratio']:+.2f}%</span><br><small style="color:#999">{label}{f['price']:.4f}</small></div>
        <div style="flex:1.5; text-align:right;"><span style="color:{"#e74c3c" if f['dp']>=0 else "#27ae60"}">{f['dp']:+,.2f}</span><br><small style="color:#999">持有:{f['tp']:+,.2f}</small></div>
    </div>
    """, unsafe_allow_html=True)

# 4. 资产管理区
st.markdown("<br>", unsafe_allow_html=True)
with st.expander("💼 持仓管理（增减仓自动合算）"):
    m_code = st.text_input("基金代码", placeholder="输入6位数字")
    if len(m_code) == 6:
        info = fetch_fund_data(m_code, "天天基金")
        if info: st.success(f"匹配成功：{info['name']}")
    
    target = next((i for i in u_data["holdings"] if i['code'] == m_code), None)
    c1, c2 = st.columns(2)
    
    if target:
        st.caption(f"当前持仓：{target['shares']} 份 | 成本：{target['cost']:.4f}")
        m_op = st.radio("操作", ["加仓 (买入)", "减仓 (卖出)"], horizontal=True)
        m_s = c1.number_input("变动份额", value=None, placeholder="变动数量")
        m_p = c2.number_input("成交单价", value=None, placeholder="成交价格", format="%.4f")
    else:
        m_op = "建仓"
        m_s = c1.number_input("持有份额", value=None, placeholder="总份额")
        m_p = c2.number_input("持有成本", value=None, placeholder="成本单价", format="%.4f")

    if st.button("同步至资产库", type="primary"):
        if m_code and m_s is not None:
            if target:
                if "加仓" in m_op:
                    new_shares = target['shares'] + m_s
                    target['cost'] = (target['shares'] * target['cost'] + m_s * (m_p or 0)) / new_shares
                    target['shares'] = new_shares
                else:
                    target['shares'] = max(0.0, target['shares'] - m_s)
            else:
                u_data["holdings"].append({"code": m_code, "shares": m_s, "cost": m_p or 0.0})
            save_db(st.session_state.db); st.rerun()

with st.expander("🗑️ 删除持仓"):
    for i, h in enumerate(u_data["holdings"]):
        if st.button(f"彻底删除 {h['code']}", key=f"del_{i}"):
            u_data["holdings"].pop(i); save_db(st.session_state.db); st.rerun()
