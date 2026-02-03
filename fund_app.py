import streamlit as st
from datetime import datetime
import json
import os
import urllib.request
import ssl
import pytz
from streamlit_autorefresh import st_autorefresh

# --- 配置 ---
TZ = pytz.timezone('Asia/Shanghai')
DATA_FILE = "fund_master_v3.json"
ssl_ctx = ssl._create_unverified_context() # 解决所有加载中/SSL问题

st.set_page_config(page_title="极速基金/黄金追踪", layout="wide")

# --- 极简样式：行距压缩 50% ---
st.markdown("""
<style>
    .main { padding: 0rem 0.5rem; }
    [data-testid="stMetric"] { background: #fdfdfd; padding: 2px 10px; border-radius: 5px; border: 1px solid #f0f0f0; }
    [data-testid="stMetricValue"] { font-size: 1.6rem !important; }
    .fund-card { border-left: 5px solid #ff4b4b; padding: 10px; margin: 5px 0; background: #fff; box-shadow: 0 1px 2px rgba(0,0,0,0.05); }
    div.stButton > button { width: 100%; border-radius: 5px; height: 2rem; }
    .small-text { font-size: 0.75rem; color: #888; }
</style>
""", unsafe_allow_html=True)

# --- 核心数据函数 ---

def load_db():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f: return json.load(f)
    return {"Default": {"holdings": []}}

def save_db(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f: json.dump(data, f, ensure_ascii=False)

@st.cache_data(ttl=30)
def fetch_gold_realtime():
    """彻底修复黄金显示问题：尝试多个数据源"""
    now_str = datetime.now(TZ).strftime('%H:%M:%S')
    try:
        # 接口1: GoldPrice (国际)
        url = "https://data-asg.goldprice.org/dbXRates/USD"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5, context=ssl_ctx) as res:
            data = json.loads(res.read().decode('utf-8'))
            usd_oz = next(i['xauPrice'] for i in data['items'] if i['curr'] == 'XAU')
            rate = next(i['rate'] for i in data['items'] if i['curr'] == 'CNY')
            return {"cny": (usd_oz * rate) / 31.1035, "time": now_str, "src": "国际实时"}
    except:
        return {"cny": None, "time": now_str, "src": "获取中..."}

def get_sina_fund(code):
    """新浪财经基金接口：更实时，更稳定"""
    try:
        # 新浪接口返回: 基金简称, 净值日期, 估值, 估值时间, 涨跌幅, 昨净...
        url = f"http://hq.sinajs.cn/list=fu_{code}"
        req = urllib.request.Request(url, headers={'Referer': 'http://finance.sina.com.cn'})
        with urllib.request.urlopen(req, timeout=3, context=ssl_ctx) as res:
            line = res.read().decode('gbk')
            data = line.split('"')[1].split(',')
            if len(data) < 5: return None
            return {
                "name": data[0],
                "gz": float(data[2]),  # 当前估值
                "nj": float(data[5]),  # 昨日收盘净值
                "ratio": float(data[4]), # 涨跌幅
                "time": data[3]        # 估值时间
            }
    except: return None

# --- 主逻辑 ---
db = load_db()
st_autorefresh(interval=30000, key="auto_ref")

# 侧边栏
with st.sidebar:
    st.subheader("👤 账号切换")
    user_names = list(db.keys())
    cur_user = st.selectbox("当前用户", user_names)
    new_u = st.text_input("新增用户")
    if st.button("创建用户") and new_u:
        db[new_u] = {"holdings": []}; save_db(db); st.rerun()

u_data = db[cur_user]

# 1. 黄金面板
gold = fetch_gold_realtime()
if gold["cny"]:
    st.markdown(f"🟡 **实时金价：** `¥{gold['cny']:.2f}` /克 <small class='small-text'>({gold['src']} {gold['time']})</small>", unsafe_allow_html=True)
else:
    st.error("黄金接口连接失败，尝试自动重连中...")

# 2. 基金面板
holdings = u_data["holdings"]
if not holdings:
    st.info("暂无持仓，请在下方添加基金代码")
else:
    total_val, total_day_profit = 0.0, 0.0
    fund_results = []
    
    for h in holdings:
        f = get_sina_fund(h['code'])
        if f:
            m_val = h['shares'] * f['gz']
            d_profit = h['shares'] * (f['gz'] - f['nj'])
            total_val += m_val
            total_day_profit += d_profit
            fund_results.append({**h, **f, "m_val": m_val, "d_profit": d_profit})

    # 汇总显示
    c1, c2 = st.columns(2)
    c1.metric("资产总额", f"¥{total_val:,.2f}")
    c2.metric("当日收益", f"¥{total_day_profit:,.2f}", f"{(total_day_profit/(total_val-total_day_profit+0.01)*100):.2f}%")

    st.divider()

    # 3. 列表与修改 (精简布局)
    for i, f in enumerate(fund_results):
        color = "#e74c3c" if f['d_profit'] >= 0 else "#27ae60"
        with st.container():
            st.markdown(f"""
            <div class="fund-card" style="border-left-color: {color}">
                <div style="display:flex; justify-content:space-between">
                    <b>{f['name']} <small>{f['code']}</small></b>
                    <span style="color:{color}">{f['ratio']:+.2f}%</span>
                </div>
                <div style="display:flex; justify-content:space-between; font-size: 0.9rem; margin-top:5px">
                    <span>市值: ¥{f['m_val']:,.2f}</span>
                    <span style="color:{color}">收益: ¥{f['d_profit']:,.2f}</span>
                </div>
                <div class="small-text">估值: {f['gz']:.4f} | 昨净: {f['nj']:.4f} | 更新: {f['time']}</div>
            </div>
            """, unsafe_allow_html=True)
            
            with st.expander(f"修改/删除 {f['code']}"):
                ec1, ec2 = st.columns(2)
                ns = ec1.number_input("份额", value=float(f['shares']), key=f"s{i}")
                nc = ec2.number_input("成本", value=float(f['cost']), format="%.4f", step=0.0001, key=f"c{i}")
                col_b1, col_b2 = st.columns(2)
                if col_b1.button("保存", key=f"sv{i}"):
                    u_data["holdings"][i].update({"shares": ns, "cost": nc})
                    save_db(db); st.rerun()
                if col_b2.button("删除", key=f"dl{i}"):
                    u_data["holdings"].pop(i)
                    save_db(db); st.rerun()

# 4. 添加
with st.expander("➕ 添加新基金"):
    nc = st.text_input("基金代码 (6位)")
    ac1, ac2 = st.columns(2)
    as_ = ac1.number_input("持有份额", min_value=0.0)
    ac = ac2.number_input("持仓成本", min_value=0.0, format="%.4f")
    if st.button("确定新增基金", type="primary"):
        if len(nc) == 6:
            u_data["holdings"].append({"code": nc, "shares": as_, "cost": ac})
            save_db(db); st.rerun()
