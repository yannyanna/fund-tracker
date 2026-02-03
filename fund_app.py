import streamlit as st
from datetime import datetime
import json
import os
import urllib.request
import ssl
import pytz

# --- 基础配置 ---
TZ = pytz.timezone('Asia/Shanghai')
DATA_FILE = "fund_master_v11.json"
ssl_ctx = ssl._create_unverified_context()

st.set_page_config(page_title="收益追踪 V11-Pro", layout="wide")

# --- 深度定制样式 ---
st.markdown("""
<style>
    .main { padding: 0rem !important; background-color: #f8f9fa; }
    .summary-bar { display: flex; justify-content: space-between; padding: 15px 20px; background: #fff; border-bottom: 1px solid #eee; }
    .sum-val { font-size: 1.5rem; font-weight: bold; color: #333; }
    .sum-lab { font-size: 0.8rem; color: #999; }
    .gold-box { background: #fffdf2; padding: 10px; margin: 5px 10px; border-radius: 10px; text-align: center; border: 1px solid #fdf0c2; }
    .gold-v { font-size: 1.8rem; color: #b8860b; font-weight: bold; }
    .channel-header { background: #eee; padding: 5px 15px; font-size: 0.8rem; font-weight: bold; color: #666; }
    .f-row { display: flex; padding: 12px 15px; background: white; border-bottom: 1px solid #f2f2f2; align-items: center; }
    .f-left { flex: 2; }
    .f-name { font-size: 0.9rem; font-weight: 500; color: #333; }
    .f-mid { flex: 1.2; text-align: right; }
    .f-right { flex: 1.5; text-align: right; }
    .up { color: #e74c3c; }
    .down { color: #27ae60; }
    .status-done { color: #52c41a; font-size: 0.7rem; border: 1px solid #b7eb8f; padding: 0 4px; border-radius: 3px; }
    .status-ing { color: #1890ff; font-size: 0.7rem; border: 1px solid #91d5ff; padding: 0 4px; border-radius: 3px; }
</style>
""", unsafe_allow_html=True)

# --- 数据处理逻辑 ---
def load_db():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f: return json.load(f)
    return {"Default": {"holdings": []}}

def save_db(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f: json.dump(data, f, ensure_ascii=False, indent=2)

@st.cache_data(ttl=600)
def get_fund_name(code):
    try:
        url = f"http://fundgz.1234567.com.cn/js/{code}.js"
        with urllib.request.urlopen(url, timeout=2, context=ssl_ctx) as res:
            c = res.read().decode('utf-8')
            return json.loads(c[c.find('{'):c.rfind('}')+1])['name']
    except: return None

def fetch_data(code, source):
    try:
        if source == "天天基金":
            url = f"http://fundgz.1234567.com.cn/js/{code}.js"
            with urllib.request.urlopen(url, timeout=3, context=ssl_ctx) as res:
                c = res.read().decode('utf-8')
                d = json.loads(c[c.find('{'):c.rfind('}')+1])
                # 天天基金判断是否为净值：如果 gztime 的日期等于今天，通常仍为估值
                return {"name": d['name'], "gz": float(d['gsz']), "nj": float(d['dwjz']), "ratio": float(d['gszzl']), "time": d['gztime'], "is_final": False}
        elif source == "新浪财经":
            url = f"http://hq.sinajs.cn/list=f_{code}"
            req = urllib.request.Request(url, headers={'Referer': 'http://finance.sina.com.cn'})
            with urllib.request.urlopen(req, timeout=3, context=ssl_ctx) as res:
                d = res.read().decode('gbk').split('"')[1].split(',')
                # 如果当前日期 > d[3](净值日期)，说明还是估值；如果相等，说明净值已出
                is_final = datetime.now(TZ).strftime('%Y-%m-%d') == d[3]
                return {"name": "基金"+code, "gz": float(d[0]), "nj": float(d[2]), "ratio": (float(d[0])-float(d[2]))/float(d[2])*100, "time": d[4], "is_final": is_final}
    except: return None

# --- 初始化 ---
if 'db' not in st.session_state: st.session_state.db = load_db()

# 侧边栏
with st.sidebar:
    st.header("👤 账户与设置")
    data_src = st.selectbox("核心数据源", ["天天基金", "新浪财经"])
    current_user = st.selectbox("切换账号", list(st.session_state.db.keys()))
    
    with st.expander("账号管理"):
        new_u = st.text_input("新增用户名")
        if st.button("保存"):
            st.session_state.db[new_u] = {"holdings": []}
            save_db(st.session_state.db); st.rerun()

u_data = st.session_state.db[current_user]

# --- 主界面渲染 ---
# 1. 顶部操作栏
t_col1, t_col2 = st.columns([1, 5])
if t_col1.button("🔄 刷新"):
    st.cache_data.clear(); st.rerun()

# 2. 黄金看板
try:
    with urllib.request.urlopen("http://hq.sinajs.cn/list=gds_AU9999", timeout=3, context=ssl_ctx) as res:
        gp = float(res.read().decode('gbk').split('"')[1].split(',')[0])
except: gp = 0.0

st.markdown(f'<div class="gold-box"><div class="gold-v">¥{gp:.2f}</div><div style="font-size:0.8rem; color:#999;">国内现货金价 | {datetime.now(TZ).strftime("%H:%M:%S")}</div></div>', unsafe_allow_html=True)

# 3. 资产计算与分组
fund_results = []
total_val, total_day_p = 0.0, 0.0

for h in u_data["holdings"]:
    f = fetch_data(h['code'], data_src)
    if f:
        mv = h['shares'] * f['gz']
        dp = h['shares'] * (f['gz'] - f['nj'])
        tp = h['shares'] * (f['gz'] - h['cost'])
        tr = (f['gz'] - h['cost']) / h['cost'] * 100 if h['cost'] > 0 else 0
        total_val += mv
        total_day_p += dp
        fund_results.append({**h, **f, "mv": mv, "dp": dp, "tp": tp, "tr": tr})

# 汇总栏
st.markdown(f"""<div class="summary-bar">
    <div><div class="sum-lab">总资产 (元)</div><div class="sum-val">¥{total_val:,.2f}</div></div>
    <div style="text-align:right;"><div class="sum-lab">当日预估收益</div><div class="sum-val {"up" if total_day_p >= 0 else "down"}">{total_day_p:+,.2f}</div></div>
</div>""", unsafe_allow_html=True)

# 4. 分渠道显示列表
if fund_results:
    # 按渠道排序分组
    channels = sorted(list(set([f.get('channel', '默认渠道') for f in fund_results])))
    for chan in channels:
        st.markdown(f'<div class="channel-header">📍 {chan}</div>', unsafe_allow_html=True)
        chan_funds = [f for f in fund_results if f.get('channel', '默认渠道') == chan]
        for f in chan_funds:
            d_clr = "up" if f['dp'] >= 0 else "down"
            t_clr = "up" if f['tp'] >= 0 else "down"
            status_html = '<span class="status-done">官方净值</span>' if f['is_final'] else '<span class="status-ing">实时估值</span>'
            
            st.markdown(f"""
            <div class="f-row">
                <div class="f-left">
                    <div class="f-name">{f['name']}</div>
                    <div class="gray-sub">{f['code']} | {status_html}</div>
                </div>
                <div class="f-mid">
                    <div class="{d_clr}" style="font-weight:bold;">{f['ratio']:+.2f}%</div>
                    <div class="gray-sub">价 {f['gz']:.4f}</div>
                </div>
                <div class="f-right">
                    <div class="f-val {d_clr}">{f['dp']:+,.2f}</div>
                    <div class="gray-sub {t_clr}">持有: {f['tp']:+,.2f}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

# 5. 集中管理与思路拓展 (添加/修改)
st.markdown("<br>", unsafe_allow_html=True)
with st.expander("➕ 添加新持仓 (自动识别/渠道管理)"):
    a_code = st.text_input("基金代码", key="in_code", placeholder="输入6位代码")
    # 自动识别名称
    if len(a_code) == 6:
        name = get_fund_name(a_code)
        if name: st.success(f"已识别基金：{name}")
        else: st.warning("未找到该基金")
    
    col_a1, col_a2, col_a3 = st.columns(3)
    a_s = col_a1.number_input("份额", value=None, key="in_shares")
    a_c = col_a2.number_input("成本", value=None, format="%.4f", key="in_cost")
    a_h = col_a3.selectbox("持有渠道", ["支付宝", "招商银行", "天天基金", "其他"], key="in_chan")
    
    if st.button("确认存入系统", type="primary"):
        if len(a_code) == 6 and a_s and a_c:
            u_data["holdings"].append({"code": a_code, "shares": a_s, "cost": a_c, "channel": a_h})
            save_db(st.session_state.db)
            # 自动清空：Streamlit 会在 rerun 时根据 key 重置组件
            st.session_state.in_code = ""
            st.session_state.in_shares = None
            st.session_state.in_cost = None
            st.rerun()

with st.expander("🛠️ 批量管理/删除持仓"):
    for i, h in enumerate(u_data["holdings"]):
        m1, m2, m3, m4 = st.columns([2, 2, 2, 1])
        ns = m1.number_input(f"{h['code']} 份额", value=None, placeholder=str(h['shares']), key=f"ms{i}")
        nc = m2.number_input(f"{h['code']} 成本", value=None, placeholder=str(h['cost']), format="%.4f", key=f"mc{i}")
        nch = m3.selectbox(f"渠道", ["支付宝", "招商银行", "天天基金", "其他"], index=["支付宝", "招商银行", "天天基金", "其他"].index(h.get('channel', '其他')), key=f"mh{i}")
        if m4.button("🗑️", key=f"del{i}"):
            u_data["holdings"].pop(i); save_db(st.session_state.db); st.rerun()
        if st.button(f"保存更新 {h['code']}", key=f"sv{i}"):
            if ns: u_data["holdings"][i]['shares'] = ns
            if nc: u_data["holdings"][i]['cost'] = nc
            u_data["holdings"][i]['channel'] = nch
            save_db(st.session_state.db); st.rerun()
