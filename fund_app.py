import streamlit as st
from datetime import datetime
import json
import os
import urllib.request
import ssl
import pytz

# --- 基础配置 ---
TZ = pytz.timezone('Asia/Shanghai')
DATA_FILE = "fund_master_v7.json"
ssl_ctx = ssl._create_unverified_context()

st.set_page_config(page_title="收益追踪 V7", layout="wide")

# --- 深度定制 CSS：完全对齐 App 体验 ---
st.markdown("""
<style>
    .main { padding: 0rem !important; }
    /* 顶部账户概览 */
    .summary-bar { display: flex; justify-content: space-between; padding: 15px 20px; background: #fff; border-bottom: 1px solid #f8f8f8; }
    .sum-val { font-size: 1.4rem; font-weight: bold; line-height: 1.2; }
    .sum-lab { font-size: 0.8rem; color: #999; margin-bottom: 4px; }
    
    /* 黄金区域 */
    .gold-section { background: #fffdf2; padding: 12px; margin: 10px; border-radius: 10px; text-align: center; border: 1px solid #fdf0c2; }
    .gold-p { font-size: 1.8rem; color: #b8860b; font-weight: bold; }

    /* 仿养基宝基金行 */
    .f-row { display: flex; padding: 12px 15px; background: white; border-bottom: 1px solid #f5f5f5; align-items: center; }
    .f-left { flex: 2; overflow: hidden; }
    .f-name { font-size: 0.95rem; font-weight: 500; color: #333; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .f-code { font-size: 0.75rem; color: #aaa; }
    
    .f-mid { flex: 1.2; text-align: right; }
    .f-right { flex: 1.5; text-align: right; }
    
    .f-val { font-size: 0.95rem; font-weight: 600; }
    .f-sub { font-size: 0.7rem; color: #bbb; }
    
    .up { color: #e74c3c; }
    .down { color: #27ae60; }
    .grey { color: #888; }
</style>
""", unsafe_allow_html=True)

# --- 核心数据逻辑 ---
def load_db():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f: return json.load(f)
    return {"Default": {"holdings": []}}

def save_db(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f: json.dump(data, f, ensure_ascii=False, indent=2)

def fetch_gold():
    try:
        url = "http://hq.sinajs.cn/list=gds_AU9999"
        req = urllib.request.Request(url, headers={'Referer': 'http://finance.sina.com.cn'})
        with urllib.request.urlopen(req, timeout=5, context=ssl_ctx) as res:
            return float(res.read().decode('gbk').split('"')[1].split(',')[0])
    except: return 0.0

def fetch_fund(code, src="天天基金"):
    try:
        if src == "天天基金":
            url = f"http://fundgz.1234567.com.cn/js/{code}.js"
            with urllib.request.urlopen(url, timeout=3, context=ssl_ctx) as res:
                c = res.read().decode('utf-8')
                d = json.loads(c[c.find('{'):c.rfind('}')+1])
                return {"name": d['name'], "gz": float(d['gsz']), "nj": float(d['dwjz']), "ratio": float(d['gszzl']), "time": d['gztime']}
        else:
            url = f"http://hq.sinajs.cn/list=fu_{code}"
            req = urllib.request.Request(url, headers={'Referer': 'http://finance.sina.com.cn'})
            with urllib.request.urlopen(req, timeout=3, context=ssl_ctx) as res:
                d = res.read().decode('gbk').split('"')[1].split(',')
                return {"name": d[0], "gz": float(d[2]), "nj": float(d[5]), "ratio": float(d[4]), "time": d[3]}
    except: return None

# --- 程序启动 ---
if 'db' not in st.session_state: st.session_state.db = load_db()

with st.sidebar:
    st.header("⚙️ 系统设置")
    data_src = st.radio("数据源", ["天天基金", "新浪财经"])
    current_user = st.selectbox("账号切换", list(st.session_state.db.keys()))
    
    with st.expander("账号管理"):
        new_u = st.text_input("新增用户名")
        if st.button("确认添加账号") and new_u:
            st.session_state.db[new_u] = {"holdings": []}
            save_db(st.session_state.db); st.rerun()

u_data = st.session_state.db[current_user]

# --- 顶栏操作 ---
t_col1, t_col2 = st.columns([4, 1])
with t_col2:
    if st.button("🔄 刷新"):
        st.cache_data.clear(); st.rerun()

# 1. 黄金价格
gp = fetch_gold()
st.markdown(f"""
<div class="gold-section">
    <div class="gold-p">¥{gp:.2f}</div>
    <div style="font-size:0.8rem; color:#999;">国内现货黄金 (AU9999) | 实时行情</div>
</div>
""", unsafe_allow_html=True)

# 2. 核心资产概览
holdings = u_data["holdings"]
total_val, total_day_profit = 0.0, 0.0
fund_data_list = []

if holdings:
    for h in holdings:
        f = fetch_fund(h['code'], src=data_src)
        if f:
            mv = h['shares'] * f['gz']
            dp = h['shares'] * (f['gz'] - f['nj'])
            # 持有盈亏计算
            total_p = h['shares'] * (f['gz'] - h['cost'])
            total_r = (f['gz'] - h['cost']) / h['cost'] * 100 if h['cost'] > 0 else 0
            
            total_val += mv
            total_day_profit += dp
            fund_data_list.append({**h, **f, "mv": mv, "dp": dp, "tp": total_p, "tr": total_r})

st.markdown(f"""
<div class="summary-bar">
    <div>
        <div class="sum-lab">账户资产 (元)</div>
        <div class="sum-val">¥{total_val:,.2f}</div>
    </div>
    <div style="text-align:right;">
        <div class="sum-lab">当日预估收益</div>
        <div class="sum-val {"up" if total_day_profit >= 0 else "down"}">
            {total_day_profit:+,.2f}
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# 3. 基金列表行 (仿养基宝)
st.markdown('<div style="background:#f5f5f5; height:8px;"></div>', unsafe_allow_html=True)
for i, f in enumerate(fund_data_list):
    day_color = "up" if f['dp'] >= 0 else "down"
    all_color = "up" if f['tp'] >= 0 else "down"
    
    st.markdown(f"""
    <div class="f-row">
        <div class="f-left">
            <div class="f-name">{f['name']}</div>
            <div class="f-code">{f['code']} | 成本 {f['cost']:.4f}</div>
        </div>
        <div class="f-mid">
            <div class="f-val {day_color}">{f['ratio']:+.2f}%</div>
            <div class="f-sub">估值 {f['gz']:.4f}</div>
        </div>
        <div class="f-right">
            <div class="f-val {day_color}">{f['dp']:+,.2f}</div>
            <div class="f-sub {all_color}">持有: {f['tp']:+,.2f} ({f['tr']:+.2f}%)</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    with st.expander(f"编辑 {f['code']}"):
        c1, c2 = st.columns(2)
        ns = c1.number_input("调整份额", value=None, placeholder=f"{f['shares']:.2f}", key=f"edit_s_{i}")
        nc = c2.number_input("调整成本", value=None, placeholder=f"{f['cost']:.4f}", format="%.4f", key=f"edit_c_{i}")
        b1, b2 = st.columns(2)
        if b1.button("保存修改", key=f"sv_{i}"):
            if ns: u_data["holdings"][i]['shares'] = ns
            if nc: u_data["holdings"][i]['cost'] = nc
            save_db(st.session_state.db); st.rerun()
        if b2.button("删除持仓", key=f"del_{i}"):
            u_data["holdings"].pop(i); save_db(st.session_state.db); st.rerun()

# 4. 底部添加区域
with st.expander("➕ 添加新基金"):
    nc = st.text_input("基金代码", placeholder="6位数字")
    col_a1, col_a2 = st.columns(2)
    as_ = col_a1.number_input("持有份额", value=None, placeholder="直接输入")
    ap = col_a2.number_input("平均成本", value=None, placeholder="直接输入", format="%.4f")
    if st.button("确认存入"):
        if nc and as_:
            u_data["holdings"].append({"code": nc, "shares": as_, "cost": ap or 0.0})
            save_db(st.session_state.db); st.rerun()
