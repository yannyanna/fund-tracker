import streamlit as st
from datetime import datetime
import json
import os
import urllib.request
import ssl
import pytz

# --- 基础配置 ---
TZ = pytz.timezone('Asia/Shanghai')
DATA_FILE = "fund_master_v17.json"
ssl_ctx = ssl._create_unverified_context()

st.set_page_config(page_title="收益追踪 V17-Final", layout="wide")

# --- UI 样式 ---
st.markdown("""
<style>
    .main { padding: 0rem !important; }
    .summary-bar { display: flex; justify-content: space-between; padding: 15px; background: #fff; border-bottom: 2px solid #eee; }
    .sum-val { font-size: 1.4rem; font-weight: bold; color: #333; }
    .gold-box { background: #fffdf2; padding: 12px; margin: 10px; border-radius: 10px; text-align: center; border: 1px solid #fdf0c2; }
    .gold-v { font-size: 1.8rem; color: #b8860b; font-weight: bold; }
    .f-row { display: flex; padding: 12px 15px; background: white; border-bottom: 1px solid #f2f2f2; align-items: center; }
    .up { color: #e74c3c; }
    .down { color: #27ae60; }
    .gray-sub { font-size: 0.75rem; color: #999; }
</style>
""", unsafe_allow_html=True)

# --- 数据持久化核心修复 ---
def load_db():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return {"Default": {"holdings": []}}

def save_db(data):
    # 同时更新内存和文件
    st.session_state.db = data
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        st.error(f"数据保存失败（权限受限）: {e}")

# --- 接口修复：剔除不稳定源 ---
def fetch_gold():
    try:
        url = "http://hq.sinajs.cn/list=gds_AU9999"
        req = urllib.request.Request(url, headers={'Referer': 'http://finance.sina.com.cn'})
        with urllib.request.urlopen(req, timeout=3, context=ssl_ctx) as res:
            return float(res.read().decode('gbk').split('"')[1].split(',')[0])
    except: return 0.0

def fetch_fund_data(code, source):
    try:
        if source == "天天基金(推荐)":
            url = f"http://fundgz.1234567.com.cn/js/{code}.js"
            with urllib.request.urlopen(url, timeout=3, context=ssl_ctx) as res:
                c = res.read().decode('utf-8'); d = json.loads(c[c.find('{'):c.rfind('}')+1])
                return {"name": d['name'], "gz": float(d['gsz']), "nj": float(d['dwjz']), "ratio": float(d['gszzl']), "time": d['gztime']}
        
        elif source == "新浪财经(同步)":
            # 新浪的高级行情接口，比腾讯稳得多
            url = f"http://hq.sinajs.cn/list=f_{code}"
            req = urllib.request.Request(url, headers={'Referer': 'http://finance.sina.com.cn'})
            with urllib.request.urlopen(req, timeout=3, context=ssl_ctx) as res:
                raw = res.read().decode('gbk').split('"')[1].split(',')
                # 过滤异常日期数据，确保获取的是价格
                gz_price = float(raw[0])
                prev_price = float(raw[2])
                if gz_price > 1000 and len(str(int(gz_price))) >= 8: # 误抓日期
                    gz_price = prev_price 
                return {"name": "基金"+code, "gz": gz_price, "nj": prev_price, "ratio": (gz_price-prev_price)/prev_price*100, "time": raw[4]}
    except: return None

# --- 初始化 ---
if 'db' not in st.session_state:
    st.session_state.db = load_db()

# --- 侧边栏 ---
with st.sidebar:
    st.header("👤 账户与保存")
    usernames = list(st.session_state.db.keys())
    current_user = st.selectbox("当前账号", usernames)
    
    with st.expander("新增用户名"):
        nu = st.text_input("输入新名字")
        if st.button("创建并保存"):
            if nu and nu not in st.session_state.db:
                new_db = st.session_state.db.copy()
                new_db[nu] = {"holdings": []}
                save_db(new_db)
                st.rerun()

# --- 主界面 ---
col_a, col_b = st.columns([1, 1])
with col_a:
    if st.button("🔄 刷新数据"):
        st.cache_data.clear(); st.rerun()
with col_b:
    data_src = st.selectbox("核心数据源", ["天天基金(推荐)", "新浪财经(同步)"], on_change=st.cache_data.clear)

# 黄金
gp = fetch_gold()
st.markdown(f'<div class="gold-box"><div class="gold-v">¥{gp:.2f}</div><div class="gray-sub">国内实金 AU9999</div></div>', unsafe_allow_html=True)

# 计算
u_data = st.session_state.db[current_user]
results = []
total_v, total_dp = 0.0, 0.0

for h in u_data["holdings"]:
    f = fetch_fund_data(h['code'], data_src)
    if f:
        mv = h['shares'] * f['gz']
        dp = h['shares'] * (f['gz'] - f['nj'])
        tp = h['shares'] * (f['gz'] - h['cost'])
        results.append({**h, **f, "mv": mv, "dp": dp, "tp": tp})
        total_v += mv
        total_dp += dp

st.markdown(f"""<div class="summary-bar">
    <div><div class="gray-sub">资产总额</div><div class="sum-val">¥{total_v:,.2f}</div></div>
    <div style="text-align:right;"><div class="gray-sub">当日盈亏</div><div class="sum-val {"up" if total_dp >= 0 else "down"}">{total_dp:+,.2f}</div></div>
</div>""", unsafe_allow_html=True)

# 列表
for f in results:
    d_clr = "up" if f['dp'] >= 0 else "down"
    st.markdown(f"""
    <div class="f-row">
        <div style="flex:2"><div><b>{f['name']}</b></div><div class="gray-sub">{f['code']}</div></div>
        <div style="flex:1.2; text-align:right"><div class="{d_clr}">{f['ratio']:+.2f}%</div><div class="gray-sub">{f['gz']:.4f}</div></div>
        <div style="flex:1.5; text-align:right"><div class="{d_clr}">{f['dp']:+,.2f}</div><div class="gray-sub">持有:{f['tp']:+,.2f}</div></div>
    </div>
    """, unsafe_allow_html=True)

# 增减仓
with st.expander("💼 持仓增减仓"):
    m_code = st.text_input("基金代码")
    target = next((i for i in u_data["holdings"] if i['code'] == m_code), None)
    c1, c2 = st.columns(2)
    m_s = c1.number_input("变动份额", value=None)
    m_p = c2.number_input("成交单价", value=None, format="%.4f")
    if st.button("提交保存", type="primary"):
        if m_code and m_s:
            if target:
                new_total = target['shares'] + m_s
                target['cost'] = (target['shares'] * target['cost'] + m_s * m_p) / new_total
                target['shares'] = new_total
            else:
                u_data["holdings"].append({"code": m_code, "shares": m_s, "cost": m_p or 0.0})
            save_db(st.session_state.db)
            st.rerun()

with st.expander("🗑️ 删除记录"):
    for i, h in enumerate(u_data["holdings"]):
        if st.button(f"彻底删除 {h['code']}", key=f"d_{i}"):
            u_data["holdings"].pop(i); save_db(st.session_state.db); st.rerun()
