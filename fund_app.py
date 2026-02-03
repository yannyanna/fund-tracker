import streamlit as st
import json
import os
import urllib.request
import ssl

# --- 环境配置 ---
ssl_ctx = ssl._create_unverified_context()
DATA_FILE = "fund_master_v18.json"

st.set_page_config(page_title="收益追踪 V18-S", layout="wide")

# --- 数据持久化 ---
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

# --- 核心接口：修复新浪数据源抓取逻辑 ---
@st.cache_data(ttl=30)
def fetch_fund_data(code, source):
    try:
        if "天天" in source:
            url = f"http://fundgz.1234567.com.cn/js/{code}.js"
            with urllib.request.urlopen(url, timeout=3, context=ssl_ctx) as res:
                content = res.read().decode('utf-8')
                data = json.loads(content[content.find('{'):content.rfind('}')+1])
                return {"name": data['name'], "gz": float(data['gsz']), "nj": float(data['dwjz']), "ratio": float(data['gszzl'])}
        else: # 新浪同步源修复版
            url = f"http://hq.sinajs.cn/list=f_{code}"
            req = urllib.request.Request(url, headers={'Referer': 'http://finance.sina.com.cn'})
            with urllib.request.urlopen(req, timeout=3, context=ssl_ctx) as res:
                raw = res.read().decode('gbk')
                # 核心逻辑：精准提取引号内的内容
                parts = raw.split('"')[1].split(',')
                if len(parts) < 5: return None
                # 新浪接口：0=估值, 1=?, 2=昨日净值, 4=日期/时间
                gz_val = float(parts[0])
                nj_val = float(parts[2])
                # 排除异常值（有时新浪会把日期误传到价格位）
                if gz_val > 1000: gz_val = nj_val 
                return {
                    "name": f"基金{code}", # 新浪接口通常不直接给中文名，在此兜底
                    "gz": gz_val,
                    "nj": nj_val,
                    "ratio": (gz_val - nj_val) / nj_val * 100
                }
    except Exception as e:
        return None

# --- 侧边栏 ---
with st.sidebar:
    st.header("👤 账户管理")
    nu = st.text_input("新建用户名")
    if st.button("创建并自动切换"):
        if nu and nu not in st.session_state.db:
            new_db = st.session_state.db.copy()
            new_db[nu] = {"holdings": []}
            save_db(new_db)
            st.session_state.current_user = nu # 记录当前状态
            st.rerun()

    user_list = list(st.session_state.db.keys())
    # 自动定位到最新创建或选中的用户
    u_idx = user_list.index(st.session_state.current_user) if 'current_user' in st.session_state else 0
    current_user = st.selectbox("当前登录账户", user_list, index=u_idx)
    st.session_state.current_user = current_user

# --- 主界面 ---
# 切换数据源联动刷新逻辑
t_col1, t_col2 = st.columns(2)
with t_col1:
    if st.button("🔄 同步行情数据"):
        st.cache_data.clear(); st.rerun()
with t_col2:
    # 关键：在这里强制执行清理，确保切换即显示内容
    data_src = st.selectbox("核心数据源", ["天天基金(推荐)", "新浪财经(同步)"], 
                            key="src_select", 
                            on_change=st.cache_data.clear)

# 资产逻辑
u_data = st.session_state.db[current_user]
fund_list = []
total_v, total_dp = 0.0, 0.0

# 渲染列表
for h in u_data["holdings"]:
    f = fetch_fund_data(h['code'], data_src)
    if f:
        mv = h['shares'] * f['gz']
        dp = h['shares'] * (f['gz'] - f['nj'])
        tp = h['shares'] * (f['gz'] - h['cost'])
        fund_list.append({**h, **f, "mv": mv, "dp": dp, "tp": tp})
        total_v += mv
        total_dp += dp

# 汇总显示
st.markdown(f"""
<div style="background:#fff; padding:15px; border-bottom:2px solid #eee; display:flex; justify-content:space-between;">
    <div><div style="color:#999; font-size:0.8rem;">资产总额</div><div style="font-size:1.5rem; font-weight:bold;">¥{total_v:,.2f}</div></div>
    <div style="text-align:right;"><div style="color:#999; font-size:0.8rem;">当日预估</div><div style="font-size:1.5rem; font-weight:bold; color:{"#e74c3c" if total_dp>=0 else "#27ae60"}">{total_dp:+,.2f}</div></div>
</div>
""", unsafe_allow_html=True)

for f in fund_list:
    st.markdown(f"""
    <div style="display:flex; padding:12px 15px; border-bottom:1px solid #f5f5f5; align-items:center; background:white;">
        <div style="flex:2"><b>{f['name']}</b><br><small style="color:#999">{f['code']}</small></div>
        <div style="flex:1; text-align:right;"><span style="color:{"#e74c3c" if f['ratio']>=0 else "#27ae60"}; font-weight:bold;">{f['ratio']:+.2f}%</span><br><small style="color:#999">{f['gz']:.4f}</small></div>
        <div style="flex:1.5; text-align:right;"><span style="color:{"#e74c3c" if f['dp']>=0 else "#27ae60"}">{f['dp']:+,.2f}</span><br><small style="color:#999">持有:{f['tp']:+,.2f}</small></div>
    </div>
    """, unsafe_allow_html=True)

# 管理区
with st.expander("💼 持仓管理（持有份额/持有成本）"):
    m_code = st.text_input("基金代码")
    if len(m_code) == 6:
        info = fetch_fund_data(m_code, "天天基金")
        if info: st.success(f"匹配成功：{info['name']}")
    
    target = next((i for i in u_data["holdings"] if i['code'] == m_code), None)
    c1, c2 = st.columns(2)
    
    if target:
        st.caption(f"当前持仓：{target['shares']} 份 | 成本：{target['cost']:.4f}")
        m_op = st.radio("调仓动作", ["加仓 (买入)", "减仓 (卖出)"], horizontal=True)
        m_s = c1.number_input("变动份额", value=0.0)
        m_p = c2.number_input("成交单价", value=0.0, format="%.4f")
    else:
        m_op = "建仓"
        m_s = c1.number_input("持有份额", value=0.0)
        m_p = c2.number_input("持有成本", value=0.0, format="%.4f")

    if st.button("保存修改", type="primary"):
        if m_code and m_s > 0:
            if target:
                if "加仓" in m_op:
                    new_shares = target['shares'] + m_s
                    target['cost'] = (target['shares'] * target['cost'] + m_s * m_p) / new_shares
                    target['shares'] = new_shares
                else:
                    target['shares'] = max(0.0, target['shares'] - m_s)
            else:
                u_data["holdings"].append({"code": m_code, "shares": m_s, "cost": m_p})
            save_db(st.session_state.db); st.rerun()

with st.expander("🗑️ 删除持仓"):
    for i, h in enumerate(u_data["holdings"]):
        if st.button(f"删除 {h['code']}", key=f"del_{i}"):
            u_data["holdings"].pop(i); save_db(st.session_state.db); st.rerun()
