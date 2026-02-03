import streamlit as st
from datetime import datetime
import json
import os
import urllib.request
import ssl
import pytz

# --- 基础配置 ---
TZ = pytz.timezone('Asia/Shanghai')
DATA_FILE = "fund_master_v14.json"
ssl_ctx = ssl._create_unverified_context()

st.set_page_config(page_title="收益追踪 V14", layout="wide")

# --- 样式：养基宝 1:1 风格 ---
st.markdown("""
<style>
    .main { padding: 0rem !important; }
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
    .status-tag { font-size: 0.65rem; padding: 1px 3px; border-radius: 3px; border: 1px solid #ddd; }
</style>
""", unsafe_allow_html=True)

# --- 核心函数 ---
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
        with urllib.request.urlopen(req, timeout=3, context=ssl_ctx) as res:
            return float(res.read().decode('gbk').split('"')[1].split(',')[0])
    except: return 0.0

def fetch_fund(code, source):
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

# --- 初始化 ---
if 'db' not in st.session_state: st.session_state.db = load_db()

# 侧边栏：仅账号管理
with st.sidebar:
    st.header("👤 账户中心")
    usernames = list(st.session_state.db.keys())
    current_user = st.selectbox("当前登录", usernames)
    with st.expander("管理用户"):
        nu = st.text_input("新账号名")
        if st.button("立即创建"):
            st.session_state.db[nu] = {"holdings": []}; save_db(st.session_state.db); st.rerun()

# --- 主界面开始 ---
# 1. 顶部操作栏（刷新 + 数据源切换）
ctrl_col1, ctrl_col2, ctrl_col3 = st.columns([1, 3, 2])
if ctrl_col1.button("🔄 刷新"):
    st.cache_data.clear(); st.rerun()
data_src = ctrl_col3.selectbox("🛰️ 数据源切换", ["天天基金", "新浪财经", "网易财经"], label_visibility="collapsed")

# 2. 黄金看板
gp = fetch_gold()
st.markdown(f'<div class="gold-box"><div class="gold-v">¥{gp:.2f}</div><div style="font-size:0.8rem; color:#999;">国内黄金 AU9999 | {datetime.now(TZ).strftime("%H:%M:%S")}</div></div>', unsafe_allow_html=True)

# 3. 资产计算
u_data = st.session_state.db[current_user]
results = []
total_val, total_day_p = 0.0, 0.0

for h in u_data["holdings"]:
    f = fetch_fund(h['code'], data_src)
    if f:
        mv = h['shares'] * f['gz']
        dp = h['shares'] * (f['gz'] - f['nj'])
        tp = h['shares'] * (f['gz'] - h['cost'])
        tr = (f['gz'] - h['cost']) / h['cost'] * 100 if h['cost'] > 0 else 0
        results.append({**h, **f, "mv": mv, "dp": dp, "tp": tp, "tr": tr})
        total_val += mv
        total_day_p += dp

st.markdown(f"""<div class="summary-bar">
    <div><div class="sum-lab">资产总额</div><div class="sum-val">¥{total_val:,.2f}</div></div>
    <div style="text-align:right;"><div class="sum-lab">当日盈亏</div><div class="sum-val {"up" if total_day_p >= 0 else "down"}">{total_day_p:+,.2f}</div></div>
</div>""", unsafe_allow_html=True)

# 4. 基金列表
st.markdown('<div style="height:5px; background:#f5f5f5;"></div>', unsafe_allow_html=True)
for f in results:
    d_clr = "up" if f['dp'] >= 0 else "down"
    t_clr = "up" if f['tp'] >= 0 else "down"
    st.markdown(f"""
    <div class="f-row">
        <div class="f-left"><div class="f-name">{f['name']}</div><div class="gray-sub">{f['code']} | {f.get('channel','默认')}</div></div>
        <div class="f-mid"><div class="{d_clr}" style="font-weight:bold;">{f['ratio']:+.2f}%</div><div class="gray-sub">{f['gz']:.4f}</div></div>
        <div class="f-right"><div class="f-val {d_clr}">{f['dp']:+,.2f}</div><div class="gray-sub {t_clr}">持有: {f['tp']:+,.2f}</div></div>
    </div>
    """, unsafe_allow_html=True)

# 5. 持仓管理（调仓与新增）
st.markdown("<br>", unsafe_allow_html=True)
with st.expander("📝 资产增减仓 / 新增持仓"):
    acode = st.text_input("基金代码", key="acode", placeholder="输入6位代码")
    existing_h = next((item for item in u_data["holdings"] if item['code'] == acode), None)
    
    if existing_h:
        st.warning(f"检测到已有持仓：当前份额 {existing_h['shares']}, 成本 {existing_h['cost']:.4f}")
        op_type = st.radio("操作类型", ["买入(加仓)", "卖出(减仓)"], horizontal=True)
    else:
        st.info("新基金识别中...")
        op_type = "买入(加仓)"
        
    c1, c2, c3 = st.columns(3)
    a_shares = c1.number_input("成交份额", value=None, key="ashares")
    a_price = c2.number_input("成交单价", value=None, format="%.4f", key="aprice")
    a_chan = c3.selectbox("渠道", ["支付宝", "招商银行", "天天基金", "其他"], key="achan")
    
    if st.button("提交交易记录", type="primary"):
        if acode and a_shares:
            if existing_h:
                if "买入" in op_type:
                    # 加仓算法：移动平均成本
                    new_total_shares = existing_h['shares'] + a_shares
                    new_cost = (existing_h['shares'] * existing_h['cost'] + a_shares * a_price) / new_total_shares
                    existing_h['shares'] = new_total_shares
                    existing_h['cost'] = new_cost
                else:
                    # 减仓算法：仅扣份额
                    existing_h['shares'] = max(0, existing_h['shares'] - a_shares)
                existing_h['channel'] = a_chan
            else:
                u_data["holdings"].append({"code": acode, "shares": a_shares, "cost": a_price or 0.0, "channel": a_chan})
            
            save_db(st.session_state.db); st.rerun()

with st.expander("🗑️ 快速清理与回本提醒"):
    for i, h in enumerate(u_data["holdings"]):
        f_info = next((item for item in results if item['code'] == h['code']), None)
        mc1, mc2, mc3 = st.columns([3, 1, 1])
        with mc1:
            st.write(f"**{h['code']}** | 份额: {h['shares']}")
            if f_info and f_info['tp'] < 0:
                needed = (h['cost'] - f_info['gz']) / f_info['gz'] * 100
                st.caption(f"回本需涨: {needed:.2f}%")
        if mc3.button("彻底移除", key=f"del_{i}"):
            u_data["holdings"].pop(i); save_db(st.session_state.db); st.rerun()
