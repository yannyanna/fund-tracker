import streamlit as st
from datetime import datetime
import json
import os
import urllib.request
import ssl
import pytz

# --- 基础配置 ---
TZ = pytz.timezone('Asia/Shanghai')
DATA_FILE = "fund_master_v15.json"
ssl_ctx = ssl._create_unverified_context()

st.set_page_config(page_title="收益追踪 V15", layout="wide")

# --- 样式优化 ---
st.markdown("""
<style>
    .main { padding: 0rem !important; }
    .stSelectbox div[data-baseweb="select"] { border-radius: 20px; }
    .summary-bar { display: flex; justify-content: space-between; padding: 15px 20px; background: #fff; border-bottom: 1px solid #eee; }
    .sum-val { font-size: 1.5rem; font-weight: bold; color: #333; }
    .sum-lab { font-size: 0.8rem; color: #999; }
    .gold-box { background: #fffdf2; padding: 12px; margin: 5px 10px; border-radius: 10px; text-align: center; border: 1px solid #fdf0c2; }
    .gold-v { font-size: 1.8rem; color: #b8860b; font-weight: bold; }
    .f-row { display: flex; padding: 12px 15px; background: white; border-bottom: 1px solid #f2f2f2; align-items: center; }
    .f-left { flex: 2; }
    .f-name { font-size: 0.95rem; font-weight: 500; }
    .f-mid { flex: 1.2; text-align: right; }
    .f-right { flex: 1.5; text-align: right; }
    .up { color: #e74c3c; }
    .down { color: #27ae60; }
    .gray-sub { font-size: 0.75rem; color: #bbb; }
</style>
""", unsafe_allow_html=True)

# --- 数据持久化 ---
def load_db():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f: return json.load(f)
    return {"Default": {"holdings": []}}

def save_db(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f: json.dump(data, f, ensure_ascii=False, indent=2)

# --- 接口调用 ---
def fetch_gold():
    try:
        url = "http://hq.sinajs.cn/list=gds_AU9999"
        req = urllib.request.Request(url, headers={'Referer': 'http://finance.sina.com.cn'})
        with urllib.request.urlopen(req, timeout=3, context=ssl_ctx) as res:
            return float(res.read().decode('gbk').split('"')[1].split(',')[0])
    except: return 0.0

@st.cache_data(ttl=10) # 极短缓存，确保切换数据源时能快速响应
def fetch_fund_api(code, source):
    try:
        if source == "天天基金":
            url = f"http://fundgz.1234567.com.cn/js/{code}.js"
            with urllib.request.urlopen(url, timeout=3, context=ssl_ctx) as res:
                c = res.read().decode('utf-8'); d = json.loads(c[c.find('{'):c.rfind('}')+1])
                return {"name": d['name'], "gz": float(d['gsz']), "nj": float(d['dwjz']), "ratio": float(d['gszzl']), "time": d['gztime']}
        elif source == "新浪财经":
            url = f"http://hq.sinajs.cn/list=f_{code}"
            req = urllib.request.Request(url, headers={'Referer': 'http://finance.sina.com.cn'})
            with urllib.request.urlopen(req, timeout=3, context=ssl_ctx) as res:
                d = res.read().decode('gbk').split('"')[1].split(',')
                return {"name": "基金"+code, "gz": float(d[0]), "nj": float(d[2]), "ratio": (float(d[0])-float(d[2]))/float(d[2])*100, "time": d[4]}
        elif source == "网易财经":
            url = f"http://api.money.126.net/data/feed/f_{code},money.api"
            with urllib.request.urlopen(url, timeout=3, context=ssl_ctx) as res:
                c = res.read().decode('utf-8'); d = json.loads(c[c.find('(')+1:c.rfind(')')])["f_" + code]
                return {"name": d['name'], "gz": d['price'], "nj": d['yestclose'], "ratio": d['percent']*100, "time": d['time']}
    except: return None

# --- 初始化状态 ---
if 'db' not in st.session_state: st.session_state.db = load_db()

# --- 侧边栏 ---
with st.sidebar:
    st.header("👤 用户系统")
    usernames = list(st.session_state.db.keys())
    current_user = st.selectbox("当前账号", usernames)
    with st.expander("新建账号"):
        nu = st.text_input("用户名")
        if st.button("确定创建"):
            st.session_state.db[nu] = {"holdings": []}; save_db(st.session_state.db); st.rerun()

# --- 主界面 ---
# 1. 顶部控制栏
t_col1, t_col2 = st.columns([1, 1])
with t_col1:
    if st.button("🔄 手动刷新"):
        st.cache_data.clear(); st.rerun()
with t_col2:
    # 核心修改：通过 on_change 确保数据源切换立刻清理缓存并重刷
    data_src = st.selectbox("数据源", ["天天基金", "新浪财经", "网易财经"], 
                            key="src_selector", on_change=st.cache_data.clear)

# 2. 金价显示 (新浪行情)
gp = fetch_gold()
st.markdown(f'<div class="gold-box"><div class="gold-v">¥{gp:.2f}</div><div style="font-size:0.8rem; color:#999;">实时黄金行情 (Sina财经提供)</div></div>', unsafe_allow_html=True)

# 3. 核心计算逻辑
u_data = st.session_state.db[current_user]
fund_list = []
total_val, total_day_p = 0.0, 0.0

for h in u_data["holdings"]:
    f = fetch_fund_api(h['code'], data_src)
    if f:
        mv = h['shares'] * f['gz']
        dp = h['shares'] * (f['gz'] - f['nj'])
        tp = h['shares'] * (f['gz'] - h['cost'])
        tr = (f['gz'] - h['cost']) / h['cost'] * 100 if h['cost'] > 0 else 0
        fund_list.append({**h, **f, "mv": mv, "dp": dp, "tp": tp, "tr": tr})
        total_val += mv
        total_day_p += dp

st.markdown(f"""<div class="summary-bar">
    <div><div class="sum-lab">资产总值</div><div class="sum-val">¥{total_val:,.2f}</div></div>
    <div style="text-align:right;"><div class="sum-lab">当日预估收益</div><div class="sum-val {"up" if total_day_p >= 0 else "down"}">{total_day_p:+,.2f}</div></div>
</div>""", unsafe_allow_html=True)

# 4. 资产列表渲染
st.markdown('<div style="height:5px; background:#f5f5f5;"></div>', unsafe_allow_html=True)
for f in fund_list:
    d_clr = "up" if f['dp'] >= 0 else "down"
    t_clr = "up" if f['tp'] >= 0 else "down"
    st.markdown(f"""
    <div class="f-row">
        <div class="f-left"><div class="f-name">{f['name']}</div><div class="gray-sub">{f['code']} | {f.get('channel','默认')}</div></div>
        <div class="f-mid"><div class="{d_clr}" style="font-weight:bold;">{f['ratio']:+.2f}%</div><div class="gray-sub">盘中 {f['gz']:.4f}</div></div>
        <div class="f-right"><div class="f-val {d_clr}">{f['dp']:+,.2f}</div><div class="gray-sub {t_clr}">持有: {f['tp']:+,.2f}</div></div>
    </div>
    """, unsafe_allow_html=True)

# 5. 动态调仓管理
st.markdown("<br>", unsafe_allow_html=True)
with st.expander("💼 持仓增减与自动合并"):
    m_code = st.text_input("基金代码", key="m_code", placeholder="输入6位代码")
    target_h = next((i for i in u_data["holdings"] if i['code'] == m_code), None)
    
    if target_h:
        st.info(f"已有持仓：{target_h['shares']}份，当前成本：{target_h['cost']:.4f}")
        m_type = st.radio("调仓动作", ["加仓 (买入)", "减仓 (卖出)"], horizontal=True)
    else:
        m_type = "加仓 (买入)"
    
    c1, c2, c3 = st.columns(3)
    m_shares = c1.number_input("变动份额", value=None, key="m_shares")
    m_price = c2.number_input("成交单价", value=None, format="%.4f", key="m_price")
    m_chan = c3.selectbox("渠道标签", ["支付宝", "招商银行", "天天基金", "其他"], key="m_chan")
    
    if st.button("同步更新到资产库", type="primary"):
        if m_code and m_shares:
            if target_h:
                if "加仓" in m_type:
                    # 移动平均算法
                    new_total = target_h['shares'] + m_shares
                    target_h['cost'] = (target_h['shares'] * target_h['cost'] + m_shares * m_price) / new_total
                    target_h['shares'] = new_total
                else:
                    target_h['shares'] = max(0, target_h['shares'] - m_shares)
                target_h['channel'] = m_chan
            else:
                u_data["holdings"].append({"code": m_code, "shares": m_shares, "cost": m_price or 0.0, "channel": m_chan})
            
            save_db(st.session_state.db)
            st.cache_data.clear(); st.rerun()

with st.expander("🗑️ 清理持仓"):
    for i, h in enumerate(u_data["holdings"]):
        col_x, col_y = st.columns([4, 1])
        col_x.write(f"**{h['code']}** ({h.get('channel','默认')}) - {h['shares']} 份")
        if col_y.button("删除", key=f"del_{i}"):
            u_data["holdings"].pop(i); save_db(st.session_state.db); st.rerun()
