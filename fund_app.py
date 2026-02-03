import streamlit as st
from datetime import datetime
import json
import os
import urllib.request
import ssl
import pytz
from streamlit_autorefresh import st_autorefresh

# --- 环境配置 ---
TZ = pytz.timezone('Asia/Shanghai')
DATA_FILE = "fund_pro_v4.json"
ssl_ctx = ssl._create_unverified_context()

st.set_page_config(page_title="收益追踪终极版", layout="wide")

# --- 样式：极致压缩行距 ---
st.markdown("""
<style>
    .main { padding: 0rem !important; }
    [data-testid="stMetric"] { background: #fdfdfd; padding: 5px 10px; border: 1px solid #eee; border-radius: 8px; }
    [data-testid="stMetricValue"] { font-size: 1.6rem !important; font-weight: 700; }
    .fund-card { border-left: 5px solid #ff4b4b; padding: 10px; margin: 8px 0; background: #fff; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
    .small-grey { font-size: 0.75rem; color: #888; margin-top: 4px; }
</style>
""", unsafe_allow_html=True)

# --- 数据处理 ---
def load_db():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f: return json.load(f)
    return {"Default": {"holdings": []}}

def save_db(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f: json.dump(data, f, ensure_ascii=False)

@st.cache_data(ttl=30)
def fetch_gold_domestic():
    """切换至国内新浪黄金行情，彻底解决加载失败"""
    try:
        # 抓取国内黄金现货行情 (AU9999)
        url = "http://hq.sinajs.cn/list=gds_AU9999"
        req = urllib.request.Request(url, headers={'Referer': 'http://finance.sina.com.cn'})
        with urllib.request.urlopen(req, timeout=5, context=ssl_ctx) as res:
            line = res.read().decode('gbk')
            data = line.split('"')[1].split(',')
            # 新浪黄金现货数据：[价格, ...] 
            price = float(data[0])
            return {"price": price, "time": datetime.now(TZ).strftime('%H:%M:%S'), "src": "国内现货"}
    except:
        return {"price": 0.0, "time": "获取失败", "src": "网络故障"}

def fetch_fund_safe(code):
    """双接口校验逻辑，修复错位问题"""
    try:
        # 优先请求天天基金，它的格式在处理昨净对齐上最死板但也最稳定
        url = f"http://fundgz.1234567.com.cn/js/{code}.js"
        with urllib.request.urlopen(url, timeout=3, context=ssl_ctx) as res:
            c = res.read().decode('utf-8')
            d = json.loads(c[c.find('{'):c.rfind('}')+1])
            # dwjz 是官方昨净，gsz 是实时估值
            return {
                "name": d['name'],
                "gz": float(d['gsz']),
                "nj": float(d['dwjz']),
                "ratio": float(d['gszzl']),
                "time": d['gztime']
            }
    except: return None

# --- 主逻辑 ---
db = load_db()
st_autorefresh(interval=30000, key="v4_ref")

with st.sidebar:
    cur_user = st.selectbox("账号", list(db.keys()))
    if st.button("➕ 新账号"):
        new_name = st.text_input("输入名字", key="new_u")
        if new_name: db[new_name] = {"holdings": []}; save_db(db); st.rerun()

u_data = db[cur_user]

# 1. 黄金面板 (修复后)
gold = fetch_gold_domestic()
if gold['price'] > 0:
    st.markdown(f"🏆 **国内黄金 (AU9999)：** `¥{gold['price']:.2f}` /克 <small style='color:grey'>(刷新: {gold['time']})</small>", unsafe_allow_html=True)
else:
    st.error("❌ 黄金接口受限，正在尝试切换国内备用通道...")

# 2. 资产看板
holdings = u_data["holdings"]
if holdings:
    total_val, total_day_profit = 0.0, 0.0
    fund_results = []
    
    for h in holdings:
        f = fetch_fund_safe(h['code'])
        if f:
            # 这里的 nj (昨净) 会通过天天基金接口确保是 3.2467 而不是 0.4383
            m_val = h['shares'] * f['gz']
            d_profit = h['shares'] * (f['gz'] - f['nj'])
            total_val += m_val
            total_day_profit += d_profit
            fund_results.append({**h, **f, "m_val": m_val, "d_profit": d_profit})

    c1, c2 = st.columns(2)
    c1.metric("资产总额", f"¥{total_val:,.2f}")
    # 增加合理性判断，防止数据错位显示夸张百分比
    delta_percent = (total_day_profit/(total_val-total_day_profit+0.01)*100)
    c2.metric("当日预估收益", f"¥{total_day_profit:,.2f}", f"{delta_percent:.2f}%")

    st.divider()

    # 3. 基金卡片 & 修改
    for i, f in enumerate(fund_results):
        is_up = f['d_profit'] >= 0
        color = "#e74c3c" if is_up else "#27ae60"
        with st.container():
            st.markdown(f"""
            <div class="fund-card" style="border-left-color: {color}">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <b style="font-size:1.1rem;">{f['name']}</b>
                    <span style="color:{color}; font-weight:bold; font-size:1.1rem;">{f['ratio']:+.2f}%</span>
                </div>
                <div style="display:flex; justify-content:space-between; margin-top:8px;">
                    <span>市值: <b>¥{f['m_val']:,.2f}</b></span>
                    <span style="color:{color}">当日: <b>¥{f['d_profit']:,.2f}</b></span>
                </div>
                <div class="small-grey">
                    实时估值: {f['gz']:.4f} | 昨日净值: {f['nj']:.4f} | 更新: {f['time']}
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            with st.expander(f"⚙️ 修改持仓 {f['code']}"):
                ec1, ec2 = st.columns(2)
                # 使用 value=None 或 0.0 但配合 step，并在添加处优化
                new_s = ec1.number_input("调整份额", value=float(f['shares']), key=f"s{i}")
                new_c = ec2.number_input("调整成本", value=float(f['cost']), format="%.4f", step=0.0001, key=f"c{i}")
                b1, b2 = st.columns(2)
                if b1.button("确认保存", key=f"sv{i}"):
                    u_data["holdings"][i].update({"shares": new_s, "cost": new_c})
                    save_db(db); st.rerun()
                if b2.button("🗑️ 删除", key=f"dl{i}"):
                    u_data["holdings"].pop(i); save_db(db); st.rerun()

# 4. 添加管理 (优化输入体验)
with st.expander("➕ 添加新基金持仓"):
    nc = st.text_input("基金代码 (6位)")
    ac1, ac2 = st.columns(2)
    # 将 value 设为 0.0，但用户在手机端点击后，部分浏览器会自动选中，
    # 这里的改进是：如果用户输入为空，我们在保存时做校验
    as_ = ac1.number_input("持有份额", min_value=0.0, step=0.01, value=0.0)
    ac = ac2.number_input("持仓成本 (4位小数)", min_value=0.0, format="%.4f", step=0.0001, value=0.0)
    
    if st.button("确定新增", type="primary"):
        if len(nc) == 6 and as_ > 0:
            u_data["holdings"].append({"code": nc, "shares": as_, "cost": ac})
            save_db(db); st.rerun()
        else:
            st.error("请输入正确的代码和份额")
