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

# --- 数据持久化层 ---
def load_db():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return {"Default": {"holdings": []}}

def save_db(data):
    # 同步更新内存和文件系统
    st.session_state.db = data
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# --- 初始化内存状态 ---
if 'db' not in st.session_state:
    st.session_state.db = load_db()

# --- 核心数据接口 ---
def fetch_gold():
    try:
        url = "http://hq.sinajs.cn/list=gds_AU9999"
        req = urllib.request.Request(url, headers={'Referer': 'http://finance.sina.com.cn'})
        with urllib.request.urlopen(req, timeout=3, context=ssl_ctx) as res:
            return float(res.read().decode('gbk').split('"')[1].split(',')[0])
    except:
        return 0.0

@st.cache_data(ttl=60) # 缓存1分钟，提升加载速度
def fetch_fund_api(code, source):
    try:
        if "天天" in source:
            url = f"http://fundgz.1234567.com.cn/js/{code}.js"
            with urllib.request.urlopen(url, timeout=3, context=ssl_ctx) as res:
                c = res.read().decode('utf-8')
                d = json.loads(c[c.find('{'):c.rfind('}')+1])
                return {"name": d['name'], "gz": float(d['gsz']), "nj": float(d['dwjz']), "ratio": float(d['gszzl'])}
        else: # 新浪财经同步源
            url = f"http://hq.sinajs.cn/list=f_{code}"
            req = urllib.request.Request(url, headers={'Referer': 'http://finance.sina.com.cn'})
            with urllib.request.urlopen(req, timeout=3, context=ssl_ctx) as res:
                r = res.read().decode('gbk').split('"')[1].split(',')
                # 过滤新浪接口偶尔返回的日期干扰（价格通常小于100）
                gz = float(r[0]) if float(r[0]) < 100 else float(r[2])
                return {"name": "基金"+code, "gz": gz, "nj": float(r[2]), "ratio": (gz-float(r[2]))/float(r[2])*100}
    except:
        return None

# --- 侧边栏：账户管理逻辑 ---
with st.sidebar:
    st.header("👤 账户中心")
    nu = st.text_input("新建用户名")
    if st.button("创建并自动切换"):
        if nu and nu not in st.session_state.db:
            new_db = st.session_state.db.copy()
            new_db[nu] = {"holdings": []}
            save_db(new_db)
            st.session_state.target_user = nu # 标记需要切换的目标
            st.rerun()
    
    user_list = list(st.session_state.db.keys())
    # 自动切换逻辑的核心：寻找目标索引
    default_idx = 0
    if 'target_user' in st.session_state and st.session_state.target_user in user_list:
        default_idx = user_list.index(st.session_state.target_user)
        del st.session_state.target_user # 切换后清除标记
        
    current_user = st.selectbox("当前登录账户", user_list, index=default_idx)

# --- 主界面渲染 ---

# 1. 顶部控制栏（实现切换即更新）
t_col1, t_col2 = st.columns([1, 1])
with t_col1:
    if st.button("🔄 同步行情数据"):
        st.cache_data.clear()
        st.rerun()
with t_col2:
    # 关键：on_change 机制保证切换数据源时立即清理缓存刷新
    data_src = st.selectbox("核心数据源", ["天天基金(推荐)", "新浪财经(同步)"], 
                            key="src_selector", on_change=st.cache_data.clear)

# 2. 黄金看板 (数据源保持新浪实时价)
gp = fetch_gold()
st.markdown(f'''
<div style="background:#fffdf2; padding:15px; border-radius:12px; text-align:center; border:1px solid #fdf0c2; margin:10px 0;">
    <div style="font-size:1.8rem; color:#b8860b; font-weight:bold;">¥{gp:.2f}</div>
    <div style="font-size:0.8rem; color:#999;">上海黄金交易所 AU9999 实时价格</div>
</div>
''', unsafe_allow_html=True)

# 3. 核心资产列表渲染
u_data = st.session_state.db[current_user]
fund_results = []
total_val, total_day_profit = 0.0, 0.0

for h in u_data["holdings"]:
    f = fetch_fund_api(h['code'], data_src)
    if f:
        mv = h['shares'] * f['gz']
        dp = h['shares'] * (f['gz'] - f['nj'])
        tp = h['shares'] * (f['gz'] - h['cost'])
        fund_results.append({**h, **f, "mv": mv, "dp": dp, "tp": tp})
        total_val += mv
        total_day_profit += dp

# 资产概览条
st.markdown(f"""
<div style="display:flex; justify-content:space-between; padding:12px 15px; background:#fff; border-bottom:2px solid #eee;">
    <div><div style="font-size:0.8rem; color:#999;">{current_user} 的资产总额</div><div style="font-size:1.5rem; font-weight:bold;">¥{total_val:,.2f}</div></div>
    <div style="text-align:right;"><div style="font-size:0.8rem; color:#999;">今日预估收益</div><div style="font-size:1.5rem; font-weight:bold; color:{"#e74c3c" if total_day_profit>=0 else "#27ae60"}">{total_day_profit:+,.2f}</div></div>
</div>
""", unsafe_allow_html=True)

# 基金明细项
for f in fund_results:
    st.markdown(f"""
    <div style="display:flex; padding:12px 15px; background:white; border-bottom:1px solid #f8f8f8; align-items:center;">
        <div style="flex:2"><div><b>{f['name']}</b></div><div style="font-size:0.75rem; color:#999;">{f['code']}</div></div>
        <div style="flex:1.2; text-align:right"><div style="color:{"#e74c3c" if f['ratio']>=0 else "#27ae60"}; font-weight:bold;">{f['ratio']:+.2f}%</div><div style="font-size:0.75rem; color:#999;">{f['gz']:.4f}</div></div>
        <div style="flex:1.5; text-align:right"><div style="color:{"#e74c3c" if f['dp']>=0 else "#27ae60"}">{f['dp']:+,.2f}</div><div style="font-size:0.75rem; color:#999;">持有:{f['tp']:+,.2f}</div></div>
    </div>
    """, unsafe_allow_html=True)

# 4. 智能管理中心
st.markdown("<br>", unsafe_allow_html=True)
with st.expander("💼 持仓管理（自动合并与成本计算）"):
    m_code = st.text_input("输入基金代码（6位）", placeholder="如 002611")
    
    # 实时识别基金名称
    if len(m_code) == 6:
        info = fetch_fund_api(m_code, "天天基金")
        if info: st.success(f"已识别目标：{info['name']}")
    
    target = next((i for i in u_data["holdings"] if i['code'] == m_code), None)
    
    col_a, col_b = st.columns(2)
    if target:
        st.warning(f"当前已有持仓：{target['shares']} 份 | 当前成本：{target['cost']:.4f}")
        m_op = st.radio("选择操作", ["加仓 (买入)", "减仓 (卖出)"], horizontal=True)
        m_s = col_a.number_input("变动份额", value=None)
        m_p = col_b.number_input("成交单价", value=None, format="%.4f")
    else:
        m_op = "初次建仓"
        m_s = col_a.number_input("持有份额", value=None)
        m_p = col_b.number_input("持有成本", value=None, format="%.4f")
    
    if st.button("确认提交修改并保存", type="primary"):
        if m_code and m_s:
            if target:
                if "加仓" in m_op:
                    # 移动加权平均成本算法
                    new_total_shares = target['shares'] + m_s
                    target['cost'] = (target['shares'] * target['cost'] + m_s * m_p) / new_total_shares
                    target['shares'] = new_total_shares
                else:
                    target['shares'] = max(0.0, target['shares'] - m_s)
            else:
                u_data["holdings"].append({"code": m_code, "shares": m_s, "cost": m_p or 0.0})
            
            save_db(st.session_state.db)
            st.cache_data.clear() # 提交后强制清理缓存获取最新行情
            st.rerun()

with st.expander("🗑️ 快速清理与账户维护"):
    for i, h in enumerate(u_data["holdings"]):
        c_x, c_y = st.columns([4, 1])
        c_x.write(f"代码: **{h['code']}** | 份额: {h['shares']} | 成本: {h['cost']:.4f}")
        if c_y.button("删除", key=f"del_{i}"):
            u_data["holdings"].pop(i)
            save_db(st.session_state.db)
            st.rerun()
