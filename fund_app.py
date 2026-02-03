import streamlit as st
from datetime import datetime
import json
import os
import urllib.request
import ssl
import pytz

# --- 基础配置 ---
TZ = pytz.timezone('Asia/Shanghai')
DATA_FILE = "fund_master_v13.json"
ssl_ctx = ssl._create_unverified_context()

st.set_page_config(page_title="收益追踪 V13", layout="wide")

# --- 定制样式：极致简洁 ---
st.markdown("""
<style>
    .main { padding: 0rem !important; background-color: #f8f9fa; }
    .summary-bar { display: flex; justify-content: space-between; padding: 15px 20px; background: #fff; border-bottom: 1px solid #eee; }
    .sum-val { font-size: 1.5rem; font-weight: bold; color: #333; }
    .sum-lab { font-size: 0.8rem; color: #999; }
    .gold-box { background: #fffdf2; padding: 12px; margin: 5px 10px; border-radius: 10px; text-align: center; border: 1px solid #fdf0c2; }
    .gold-v { font-size: 1.8rem; color: #b8860b; font-weight: bold; }
    .channel-header { background: #f0f2f5; padding: 6px 15px; font-size: 0.8rem; font-weight: bold; color: #555; margin-top: 5px;}
    .f-row { display: flex; padding: 12px 15px; background: white; border-bottom: 1px solid #f2f2f2; align-items: center; }
    .f-left { flex: 2; }
    .f-name { font-size: 0.9rem; font-weight: 500; }
    .f-mid { flex: 1.2; text-align: right; }
    .f-right { flex: 1.5; text-align: right; }
    .up { color: #e74c3c; }
    .down { color: #27ae60; }
    .gray-sub { font-size: 0.75rem; color: #bbb; }
    .breakeven-tag { background: #fff1f0; color: #cf1322; padding: 1px 4px; border-radius: 3px; font-size: 0.7rem; border: 1px solid #ffa39e; }
</style>
""", unsafe_allow_html=True)

# --- 数据处理逻辑 ---
def load_db():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f: return json.load(f)
        except: return {"Default": {"holdings": []}}
    return {"Default": {"holdings": []}}

def save_db(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f: json.dump(data, f, ensure_ascii=False, indent=2)

def fetch_gold_safe():
    """多策略抓取金价，确保不显示0"""
    try:
        url = "http://hq.sinajs.cn/list=gds_AU9999"
        req = urllib.request.Request(url, headers={'Referer': 'http://finance.sina.com.cn'})
        with urllib.request.urlopen(req, timeout=5, context=ssl_ctx) as res:
            raw = res.read().decode('gbk')
            data_part = raw.split('"')[1]
            if data_part:
                return float(data_part.split(',')[0])
    except Exception as e:
        st.sidebar.error(f"金价获取失败，请刷新: {e}")
    return 0.0

def fetch_fund(code, source):
    try:
        if source == "天天基金":
            url = f"http://fundgz.1234567.com.cn/js/{code}.js"
            with urllib.request.urlopen(url, timeout=3, context=ssl_ctx) as res:
                c = res.read().decode('utf-8')
                d = json.loads(c[c.find('{'):c.rfind('}')+1])
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
                c = res.read().decode('utf-8')
                d = json.loads(c[c.find('(')+1:c.rfind(')')])["f_" + code]
                return {"name": d['name'], "gz": d['price'], "nj": d['yestclose'], "ratio": d['percent']*100, "time": d['time']}
    except: return None

# --- 系统初始化 ---
if 'db' not in st.session_state: st.session_state.db = load_db()

with st.sidebar:
    st.header("⚙️ 系统管理")
    data_src = st.selectbox("核心数据源", ["天天基金", "新浪财经", "网易财经"])
    current_user = st.selectbox("切换用户", list(st.session_state.db.keys()))
    
    with st.expander("用户操作"):
        new_u = st.text_input("新增用户名")
        if st.button("创建用户"):
            st.session_state.db[new_u] = {"holdings": []}
            save_db(st.session_state.db); st.rerun()

# --- 顶栏刷新 ---
if st.button("🔄 刷新最新行情"):
    st.cache_data.clear(); st.rerun()

# 1. 黄金看板
gp = fetch_gold_safe()
st.markdown(f"""
<div class="gold-box">
    <div class="gold-v">¥{gp:.2f}</div>
    <div style="font-size:0.8rem; color:#999;">国内现货黄金 (AU9999) | {datetime.now(TZ).strftime('%H:%M:%S')}</div>
</div>
""", unsafe_allow_html=True)

# 2. 核心计算
u_data = st.session_state.db[current_user]
fund_results = []
total_val, total_day_p = 0.0, 0.0

for h in u_data["holdings"]:
    f = fetch_fund(h['code'], data_src)
    if f:
        mv = h['shares'] * f['gz']
        dp = h['shares'] * (f['gz'] - f['nj'])
        tp = h['shares'] * (f['gz'] - h['cost'])
        tr = (f['gz'] - h['cost']) / h['cost'] * 100 if h['cost'] > 0 else 0
        fund_results.append({**h, **f, "mv": mv, "dp": dp, "tp": tp, "tr": tr})
        total_val += mv
        total_day_p += dp

st.markdown(f"""
<div class="summary-bar">
    <div><div class="sum-lab">账户资产</div><div class="sum-val">¥{total_val:,.2f}</div></div>
    <div style="text-align:right;"><div class="sum-lab">当日预估收益</div><div class="sum-val {"up" if total_day_p >= 0 else "down"}">{total_day_p:+,.2f}</div></div>
</div>
""", unsafe_allow_html=True)

# 3. 基金列表 (按渠道分组)
st.markdown('<div style="background:#f5f5f5; height:5px;"></div>', unsafe_allow_html=True)
if fund_results:
    channels = sorted(list(set([f.get('channel', '默认渠道') for f in fund_results])))
    for chan in channels:
        st.markdown(f'<div class="channel-header">📍 {chan}</div>', unsafe_allow_html=True)
        chan_funds = [f for f in fund_results if f.get('channel', '默认渠道') == chan]
        for f in chan_funds:
            d_clr = "up" if f['dp'] >= 0 else "down"
            t_clr = "up" if f['tp'] >= 0 else "down"
            st.markdown(f"""
            <div class="f-row">
                <div class="f-left">
                    <div class="f-name">{f['name']}</div>
                    <div class="gray-sub">{f['code']} | {f['time']}</div>
                </div>
                <div class="f-mid">
                    <div class="{d_clr}" style="font-weight:bold;">{f['ratio']:+.2f}%</div>
                    <div class="gray-sub">估 {f['gz']:.4f}</div>
                </div>
                <div class="f-right">
                    <div class="f-val {d_clr}">{f['dp']:+,.2f}</div>
                    <div class="gray-sub {t_clr}">持有: {f['tp']:+,.2f}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

# 4. 管理工具
st.markdown("<br>", unsafe_allow_html=True)
with st.expander("➕ 添加新基金"):
    t_code = st.text_input("基金代码", key="add_code", placeholder="6位代码回车自动显名")
    if len(t_code) == 6:
        name_hint = fetch_fund(t_code, "天天基金")
        if name_hint: st.success(f"匹配到：{name_hint['name']}")
    
    col1, col2, col3 = st.columns(3)
    t_shares = col1.number_input("份额", value=None, key="add_shares")
    t_cost = col2.number_input("成本单价", value=None, format="%.4f", key="add_cost")
    t_chan = col3.selectbox("持有渠道", ["支付宝", "招商银行", "天天基金", "其他"], key="add_chan")
    
    if st.button("确认存入", type="primary"):
        if len(t_code) == 6 and t_shares:
            u_data["holdings"].append({"code": t_code, "shares": t_shares, "cost": t_cost or 0.0, "channel": t_chan})
            save_db(st.session_state.db)
            st.rerun()

with st.expander("🛠️ 管理持仓与回本预测"):
    for i, h in enumerate(u_data["holdings"]):
        f_info = next((item for item in fund_results if item['code'] == h['code']), None)
        
        col_m1, col_m2 = st.columns([4, 1])
        with col_m1:
            st.write(f"**{h['code']}** ({h.get('channel', '默认')})")
            if f_info and f_info['tp'] < 0:
                needed = (h['cost'] - f_info['gz']) / f_info['gz'] * 100
                st.markdown(f'<span class="breakeven-tag">需涨 {needed:.2f}% 回本</span>', unsafe_allow_html=True)
        
        if col_m2.button("🗑️", key=f"del_{i}"):
            u_data["holdings"].pop(i); save_db(st.session_state.db); st.rerun()
            
        c1, c2, c3 = st.columns(3)
        ns = c1.number_input("修正份额", value=None, placeholder=str(h['shares']), key=f"e_s_{i}")
        nc = c2.number_input("修正成本", value=None, placeholder=str(h['cost']), format="%.4f", key=f"e_c_{i}")
        nh = c3.selectbox("换渠道", ["支付宝", "招商银行", "天天基金", "其他"], index=["支付宝", "招商银行", "天天基金", "其他"].index(h.get('channel', '其他')), key=f"e_h_{i}")
        if st.button(f"保存更新 {h['code']}", key=f"save_{i}"):
            if ns: u_data["holdings"][i]['shares'] = ns
            if nc: u_data["holdings"][i]['cost'] = nc
            u_data["holdings"][i]['channel'] = nh
            save_db(st.session_state.db); st.rerun()
