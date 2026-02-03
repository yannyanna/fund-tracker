import streamlit as st
from datetime import datetime
import json
import os
import urllib.request
import ssl
import pytz

# --- 基础配置 ---
TZ = pytz.timezone('Asia/Shanghai')
DATA_FILE = "fund_master_v9.json"
ssl_ctx = ssl._create_unverified_context()

st.set_page_config(page_title="收益追踪 V9", layout="wide")

# --- 养基宝深度定制 CSS ---
st.markdown("""
<style>
    .main { padding: 0rem !important; background-color: #f8f9fa; }
    .summary-bar { display: flex; justify-content: space-between; padding: 15px 20px; background: #fff; border-bottom: 1px solid #eee; }
    .sum-val { font-size: 1.5rem; font-weight: bold; color: #333; }
    .sum-lab { font-size: 0.8rem; color: #999; }
    
    .gold-box { background: #fffdf2; padding: 12px; margin: 10px; border-radius: 10px; text-align: center; border: 1px solid #fdf0c2; }
    .gold-v { font-size: 1.8rem; color: #b8860b; font-weight: bold; }

    .f-row { display: flex; padding: 12px 15px; background: white; border-bottom: 1px solid #f2f2f2; align-items: center; }
    .f-left { flex: 2; }
    .f-name { font-size: 0.95rem; font-weight: 500; color: #333; }
    .f-code { font-size: 0.75rem; color: #aaa; }
    
    .f-mid { flex: 1.2; text-align: right; }
    .f-right { flex: 1.5; text-align: right; }
    
    .up { color: #e74c3c; }
    .down { color: #27ae60; }
    .gray-sub { font-size: 0.75rem; color: #bbb; }
</style>
""", unsafe_allow_html=True)

# --- 数据源函数 ---
def load_db():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f: return json.load(f)
    return {"Default": {"holdings": []}}

def save_db(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f: json.dump(data, f, ensure_ascii=False, indent=2)

def fetch_gold_sina():
    try:
        url = "http://hq.sinajs.cn/list=gds_AU9999"
        req = urllib.request.Request(url, headers={'Referer': 'http://finance.sina.com.cn'})
        with urllib.request.urlopen(req, timeout=5, context=ssl_ctx) as res:
            return float(res.read().decode('gbk').split('"')[1].split(',')[0])
    except: return 0.0

def fetch_fund_multi_source(code, source):
    try:
        if source == "天天基金":
            url = f"http://fundgz.1234567.com.cn/js/{code}.js"
            with urllib.request.urlopen(url, timeout=3, context=ssl_ctx) as res:
                c = res.read().decode('utf-8')
                d = json.loads(c[c.find('{'):c.rfind('}')+1])
                return {"gz": float(d['gsz']), "nj": float(d['dwjz']), "ratio": float(d['gszzl']), "time": d['gztime']}
        
        elif source == "新浪财经":
            # 采用新浪行情专用接口，避免字段偏移
            url = f"http://hq.sinajs.cn/list=f_{code}"
            req = urllib.request.Request(url, headers={'Referer': 'http://finance.sina.com.cn'})
            with urllib.request.urlopen(req, timeout=3, context=ssl_ctx) as res:
                d = res.read().decode('gbk').split('"')[1].split(',')
                # 新浪行情接口格式：[净值, 累计净值, 昨日净值, 日期, 时间, 状态...]
                return {"gz": float(d[0]), "nj": float(d[2]), "ratio": (float(d[0])-float(d[2]))/float(d[2])*100, "time": d[4]}

        elif source == "网易财经":
            url = f"http://api.money.126.net/data/feed/f_{code},money.api"
            with urllib.request.urlopen(url, timeout=3, context=ssl_ctx) as res:
                c = res.read().decode('utf-8')
                d = json.loads(c[c.find('(')+1:c.rfind(')')])["f_" + code]
                return {"gz": d['price'], "nj": d['yestclose'], "ratio": d['percent']*100, "time": d['time']}
    except: return None

# --- 主逻辑 ---
if 'db' not in st.session_state: st.session_state.db = load_db()

with st.sidebar:
    st.header("👤 用户 & 核心设置")
    data_src = st.selectbox("核心数据源", ["天天基金", "新浪财经", "网易财经"], index=0)
    current_user = st.selectbox("切换账号", list(st.session_state.db.keys()))
    
    if st.button("🔄 刷新数据"):
        st.cache_data.clear(); st.rerun()

    with st.expander("账号管理"):
        new_u = st.text_input("新增用户名")
        if st.button("保存用户"):
            st.session_state.db[new_u] = {"holdings": []}
            save_db(st.session_state.db); st.rerun()

u_data = st.session_state.db[current_user]

# 1. 黄金面板
gold_p = fetch_gold_sina()
st.markdown(f"""
<div class="gold-box">
    <div class="gold-v">¥{gold_p:.2f}</div>
    <div style="font-size:0.8rem; color:#999;">国内黄金 (AU9999) | {datetime.now(TZ).strftime('%H:%M:%S')}</div>
</div>
""", unsafe_allow_html=True)

# 2. 资产看板（并列展示）
holdings = u_data["holdings"]
total_val, total_day_profit = 0.0, 0.0
fund_results = []

if holdings:
    for h in holdings:
        f = fetch_fund_multi_source(h['code'], data_src)
        if f:
            mv = h['shares'] * f['gz']
            dp = h['shares'] * (f['gz'] - f['nj'])
            tp = h['shares'] * (f['gz'] - h['cost'])
            tr = (f['gz'] - h['cost']) / h['cost'] * 100 if h['cost'] > 0 else 0
            total_val += mv
            total_day_profit += dp
            fund_results.append({**h, **f, "mv": mv, "dp": dp, "tp": tp, "tr": tr})

st.markdown(f"""
<div class="summary-bar">
    <div>
        <div class="sum-lab">总资产 (元)</div>
        <div class="sum-val">¥{total_val:,.2f}</div>
    </div>
    <div style="text-align:right;">
        <div class="sum-lab">当日收益</div>
        <div class="sum-val {"up" if total_day_profit >= 0 else "down"}">
            {total_day_profit:+,.2f}
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# 3. 仿养基宝单行列表
st.markdown('<div style="background:#f5f5f5; height:8px;"></div>', unsafe_allow_html=True)
for f in fund_results:
    d_clr = "up" if f['dp'] >= 0 else "down"
    t_clr = "up" if f['tp'] >= 0 else "down"
    st.markdown(f"""
    <div class="f-row">
        <div class="f-left">
            <div class="f-name">{f['code']}</div>
            <div class="gray-sub">成本 {f['cost']:.4f}</div>
        </div>
        <div class="f-mid">
            <div class="f-val {d_clr}">{f['ratio']:+.2f}%</div>
            <div class="gray-sub">{f['gz']:.4f} ({f['time'][11:16]})</div>
        </div>
        <div class="f-right">
            <div class="f-val {d_clr}">{f['dp']:+,.2f}</div>
            <div class="gray-sub {t_clr}">持有: {f['tp']:+,.2f} ({f['tr']:+.2f}%)</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# 4. 底部集中管理区 (修改/添加)
st.markdown('<div style="margin-top:20px;"></div>', unsafe_allow_html=True)
with st.expander("🛠️ 集中管理持仓"):
    for i, h in enumerate(u_data["holdings"]):
        c1, c2, c3 = st.columns([2, 2, 1])
        ns = c1.number_input(f"{h['code']} 份额", value=None, placeholder=f"{h['shares']}", key=f"s_{i}")
        nc = c2.number_input(f"{h['code']} 成本", value=None, placeholder=f"{h['cost']}", format="%.4f", key=f"c_{i}")
        if c3.button("🗑️", key=f"d_{i}"):
            u_data["holdings"].pop(i); save_db(st.session_state.db); st.rerun()
        if st.button(f"保存更新 {h['code']}", key=f"v_{i}"):
            if ns: u_data["holdings"][i]['shares'] = ns
            if nc: u_data["holdings"][i]['cost'] = nc
            save_db(st.session_state.db); st.rerun()

with st.expander("➕ 添加新基金持仓"):
    new_code = st.text_input("6位代码")
    ac1, ac2 = st.columns(2)
    as_ = ac1.number_input("份额", value=None, placeholder="输入份额")
    ac = ac2.number_input("成本价", value=None, placeholder="输入单价", format="%.4f")
    if st.button("确认存入"):
        if new_code and as_:
            u_data["holdings"].append({"code": new_code, "shares": as_, "cost": ac or 0.0})
            save_db(st.session_state.db); st.rerun()
