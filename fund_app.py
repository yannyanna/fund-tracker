import streamlit as st
import json
import os
import urllib.request
import ssl

# --- 核心配置 ---
ssl_ctx = ssl._create_unverified_context()
DATA_FILE = "fund_master_v18.json"

st.set_page_config(page_title="收益追踪 V19", layout="wide")

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

# --- 核心接口 ---
def fetch_gold():
    try:
        url = "http://hq.sinajs.cn/list=gds_AU9999"
        req = urllib.request.Request(url, headers={'Referer': 'http://finance.sina.com.cn'})
        with urllib.request.urlopen(req, timeout=3, context=ssl_ctx) as res:
            # 这里的接口非常稳，直接解析新浪金价
            return float(res.read().decode('gbk').split('"')[1].split(',')[0])
    except: return 0.0

def fetch_fund_data(code, source):
    try:
        if "天天" in source:
            url = f"http://fundgz.1234567.com.cn/js/{code}.js"
            with urllib.request.urlopen(url, timeout=3, context=ssl_ctx) as res:
                content = res.read().decode('utf-8')
                data = json.loads(content[content.find('{'):content.rfind('}')+1])
                return {"name": data['name'], "gz": float(data['gsz']), "nj": float(data['dwjz']), "ratio": float(data['gszzl'])}
        else: # 新浪源
            url = f"http://hq.sinajs.cn/list=f_{code}"
            req = urllib.request.Request(url, headers={'Referer': 'http://finance.sina.com.cn'})
            with urllib.request.urlopen(req, timeout=3, context=ssl_ctx) as res:
                raw = res.read().decode('gbk')
                parts = raw.split('"')[1].split(',')
                if len(parts) < 5: return None
                gz_val, nj_val = float(parts[0]), float(parts[2])
                if gz_val > 1000: gz_val = nj_val # 过滤异常日期值
                return {"name": f"基金{code}", "gz": gz_val, "nj": nj_val, "ratio": (gz_val - nj_val) / nj_val * 100}
    except: return None

# --- 侧边栏 ---
with st.sidebar:
    st.header("👤 账户中心")
    nu = st.text_input("新建用户名", placeholder="输入名字")
    if st.button("创建并自动切换"):
        if nu and nu not in st.session_state.db:
            new_db = st.session_state.db.copy()
            new_db[nu] = {"holdings": []}
            save_db(new_db)
            st.session_state.current_user = nu 
            st.rerun()

    user_list = list(st.session_state.db.keys())
    if 'current_user' not in st.session_state: st.session_state.current_user = user_list[0]
    current_user = st.selectbox("当前登录账户", user_list, 
                                index=user_list.index(st.session_state.current_user))
    st.session_state.current_user = current_user

# --- 主界面 ---
# 1. 顶部控制
t_col1, t_col2 = st.columns([1, 1])
with t_col2:
    data_src = st.selectbox("🛰️ 数据源切换", ["天天基金(推荐)", "新浪财经(同步)"], key="src_mode")

# 2. 黄金看板（回归）
gold_p = fetch_gold()
st.markdown(f"""
<div style="background: linear-gradient(135deg, #fffcf0 0%, #fff7d6 100%); padding:15px; border-radius:12px; text-align:center; border:1px solid #fcebb3; margin-bottom:15px; box-shadow: 0 2px 4px rgba(0,0,0,0.02);">
    <div style="font-size:1.8rem; color:#b8860b; font-weight:800;">¥{gold_p:.2f}</div>
    <div style="font-size:0.8rem; color:#999; margin-top:4px;">上海黄金交易所 AU9999 实盘价</div>
</div>
""", unsafe_allow_html=True)

# 3. 资产计算与渲染
u_data = st.session_state.db[st.session_state.current_user]
fund_list = []
total_v, total_dp = 0.0, 0.0

for h in u_data["holdings"]:
    f = fetch_fund_data(h['code'], data_src)
    if f:
        mv = h['shares'] * f['gz']
        dp = h['shares'] * (f['gz'] - f['nj'])
        tp = h['shares'] * (f['gz'] - h['cost'])
        fund_list.append({**h, **f, "mv": mv, "dp": dp, "tp": tp})
        total_v += mv
        total_dp += dp

# 汇总条
st.markdown(f"""
<div style="background:#fff; padding:15px; border-bottom:3px solid #f0f0f0; display:flex; justify-content:space-between; align-items:center;">
    <div><div style="color:#999; font-size:0.85rem;">{st.session_state.current_user} 的资产</div><div style="font-size:1.6rem; font-weight:bold;">¥{total_v:,.2f}</div></div>
    <div style="text-align:right;"><div style="color:#999; font-size:0.85rem;">今日盈亏</div><div style="font-size:1.6rem; font-weight:bold; color:{"#e74c3c" if total_dp>=0 else "#27ae60"}">{total_dp:+,.2f}</div></div>
</div>
""", unsafe_allow_html=True)

for f in fund_list:
    st.markdown(f"""
    <div style="display:flex; padding:14px 15px; border-bottom:1px solid #f8f8f8; align-items:center; background:white;">
        <div style="flex:2"><b>{f['name']}</b><br><small style="color:#999">{f['code']}</small></div>
        <div style="flex:1; text-align:right;"><span style="color:{"#e74c3c" if f['ratio']>=0 else "#27ae60"}; font-weight:bold;">{f['ratio']:+.2f}%</span><br><small style="color:#999">{f['gz']:.4f}</small></div>
        <div style="flex:1.5; text-align:right;"><span style="color:{"#e74c3c" if f['dp']>=0 else "#27ae60"}">{f['dp']:+,.2f}</span><br><small style="color:#999">持有:{f['tp']:+,.2f}</small></div>
    </div>
    """, unsafe_allow_html=True)

# 4. 优化后的调仓区（无 0 输入）
st.markdown("<br>", unsafe_allow_html=True)
with st.expander("💼 资产调仓 / 增减仓"):
    m_code = st.text_input("基金代码", placeholder="输入6位数字")
    
    if len(m_code) == 6:
        info = fetch_fund_data(m_code, "天天基金")
        if info: st.success(f"已识别：{info['name']}")
    
    target = next((i for i in u_data["holdings"] if i['code'] == m_code), None)
    c1, c2 = st.columns(2)
    
    # 核心：使用 value=None 实现点击即输入
    if target:
        st.info(f"现有：{target['shares']} 份 | 成本：{target['cost']:.4f}")
        m_op = st.radio("动作", ["加仓 (买入)", "减仓 (卖出)"], horizontal=True)
        m_s = c1.number_input("变动份额", value=None, placeholder="变动数")
        m_p = c2.number_input("成交单价", value=None, placeholder="成交价", format="%.4f")
    else:
        m_op = "建仓"
        m_s = c1.number_input("持有份额", value=None, placeholder="份额")
        m_p = c2.number_input("持有成本", value=None, placeholder="成本单价", format="%.4f")

    if st.button("更新持仓记录", type="primary"):
        if m_code and m_s is not None:
            if target:
                if "加仓" in m_op:
                    new_sh = target['shares'] + m_s
                    target['cost'] = (target['shares'] * target['cost'] + m_s * (m_p or 0)) / new_sh
                    target['shares'] = new_sh
                else:
                    target['shares'] = max(0.0, target['shares'] - m_s)
            else:
                u_data["holdings"].append({"code": m_code, "shares": m_s, "cost": m_p or 0.0})
            save_db(st.session_state.db); st.rerun()

with st.expander("🗑️ 快速清理记录"):
    for i, h in enumerate(u_data["holdings"]):
        if st.button(f"删除 {h['code']}", key=f"del_{i}"):
            u_data["holdings"].pop(i); save_db(st.session_state.db); st.rerun()
