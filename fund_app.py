import streamlit as st
from datetime import datetime
import json
import os
import urllib.request
import pytz
from streamlit_autorefresh import st_autorefresh

# --- 基础配置 ---
TZ = pytz.timezone('Asia/Shanghai')
DATA_FILE = "fund_user_v2.json"

st.set_page_config(page_title="极速收益追踪", page_icon="📈", layout="wide")

# --- 样式优化：压缩行距与美化 ---
st.markdown("""
<style>
    .main{padding: 0.2rem 0.5rem}
    /* 压缩 Metric 行距 */
    [data-testid="stMetric"] { background: #f8f9fa; padding: 5px 10px; border-radius: 8px; }
    [data-testid="stMetricValue"] { font-size: 1.8rem !important; }
    div[data-testid="column"] { padding: 0 5px; }
    .fund-card { border-left: 4px solid #e74c3c; padding: 10px; margin: 8px 0; background: white; box-shadow: 0 1px 3px rgba(0,0,0,0.1); border-radius: 4px; }
    .up { color: #e74c3c; font-weight: bold; }
    .down { color: #27ae60; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# --- 数据持久化 ---
def load_db():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"Default": {"holdings": []}}

def save_db(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False)

# --- 数据抓取逻辑 ---
@st.cache_data(ttl=60)
def fetch_gold_data():
    """获取黄金价格，增加容错和备用逻辑"""
    now_str = datetime.now(TZ).strftime('%H:%M:%S')
    try:
        url = "https://data-asg.goldprice.org/dbXRates/USD"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as res:
            d = json.loads(res.read().decode('utf-8'))
            usd = next(i['xauPrice'] for i in d['items'] if i['curr'] == 'XAU')
            rate = next(i['rate'] for i in d['items'] if i['curr'] == 'CNY')
            return {"cny": (usd * rate) / 31.1035, "time": now_str}
    except Exception as e:
        # 如果报错，返回上一次的值（Streamlit缓存会处理）或一个标记值
        return {"cny": 0.0, "time": f"重试中 {now_str}"}

def get_fund_info(code):
    """根据代码自动获取基金名称"""
    try:
        url = f"http://fundgz.1234567.com.cn/js/{code}.js"
        with urllib.request.urlopen(url, timeout=3) as res:
            c = res.read().decode('utf-8')
            d = json.loads(c[c.find('{'):c.rfind('}')+1])
            return d['name']
    except: return f"基金{code}"

@st.cache_data(ttl=30)
def fetch_all_funds(codes):
    results = {}
    for code in codes:
        try:
            url = f"http://fundgz.1234567.com.cn/js/{code}.js"
            with urllib.request.urlopen(url, timeout=3) as res:
                c = res.read().decode('utf-8')
                results[code] = json.loads(c[c.find('{'):c.rfind('}')+1])
        except: results[code] = None
    return results

# --- 逻辑处理 ---
db = load_db()
st_autorefresh(interval=30000, key="auto_ref")

# 侧边栏：仅保留用户名
with st.sidebar:
    st.subheader("👤 账号切换")
    usernames = list(db.keys())
    current_user = st.selectbox("当前用户", usernames)
    
    new_user = st.text_input("新增用户")
    if st.button("创建"):
        if new_user and new_user not in db:
            db[new_user] = {"holdings": []}
            save_db(db)
            st.rerun()

u_data = db[current_user]

# --- 主界面 ---
# 1. 黄金展示 (修复显示问题)
gold = fetch_gold_data()
g_val = f"¥{gold['cny']:.2f}" if gold['cny'] > 0 else "加载中..."
st.markdown(f"**🟡 国际金价：** {g_val} /克 <small style='color:#999'>(刷新:{gold['time']})</small>", unsafe_allow_html=True)

# 2. 基金计算
holdings = u_data["holdings"]
if not holdings:
    st.info("点击下方【持仓管理】添加基金")
else:
    live_funds = fetch_all_funds([h['code'] for h in holdings])
    t_val, t_profit = 0, 0
    fund_display_list = []

    for h in holdings:
        f = live_funds.get(h['code'])
        if f:
            cur_nav = float(f['gsz'])
            last_nav = float(f['dwjz'])
            m_val = h['shares'] * cur_nav
            d_profit = h['shares'] * (cur_nav - last_nav)
            t_val += m_val
            t_profit += d_profit
            fund_display_list.append({
                "name": f['name'], "code": h['code'], "growth": float(f['gszzl']),
                "val": m_val, "day": d_profit, "time": f['gztime'], "cost": h['cost'], "shares": h['shares']
            })

    # 总览：压缩行距
    st.markdown('<div style="margin-top:-10px"></div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    c1.metric("总资产", f"¥{t_val:,.2f}")
    c2.metric("当日收益", f"¥{t_profit:,.2f}", f"{(t_profit/(t_val-t_profit+0.1)*100):.2f}%")
    st.markdown('<div style="margin-bottom:-10px"></div>', unsafe_allow_html=True)

    st.divider()

    # 3. 基金列表与修改
    for i, item in enumerate(fund_display_list):
        is_up = item['growth'] >= 0
        style = "up" if is_up else "down"
        with st.container():
            st.markdown(f"""
            <div class="fund-card" style="border-left-color: {'#e74c3c' if is_up else '#27ae60'}">
                <div style="display:flex; justify-content:space-between">
                    <b>{item['name']}</b>
                    <span class="{style}">{item['growth']:+.2f}%</span>
                </div>
                <div style="display:flex; justify-content:space-between; font-size: 0.85rem; margin-top:5px; color:#444">
                    <span>市值: ¥{item['val']:,.2f}</span>
                    <span class="{style}">当日: ¥{item['day']:,.2f}</span>
                </div>
                <div style="font-size: 0.75rem; color:#888; margin-top:3px">
                    成本: {item['cost']:.4f} | 份额: {item['shares']:.2f} | {item['time']}
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # 修改功能：放在每个卡片折叠区，节省空间
            with st.expander(f"修改 {item['code']}"):
                col_edit1, col_edit2 = st.columns(2)
                new_s = col_edit1.number_input("份额", value=float(item['shares']), key=f"s_{item['code']}")
                new_c = col_edit2.number_input("成本", value=float(item['cost']), format="%.4f", step=0.0001, key=f"c_{item['code']}")
                c_del, c_save = st.columns(2)
                if c_save.button("保存修改", key=f"save_{item['code']}"):
                    u_data["holdings"][i].update({"shares": new_s, "cost": new_c})
                    save_db(db)
                    st.rerun()
                if c_del.button("删除基金", key=f"del_{item['code']}"):
                    u_data["holdings"].pop(i)
                    save_db(db)
                    st.rerun()

# 4. 添加管理
with st.expander("➕ 添加新基金"):
    add_code = st.text_input("基金代码 (6位)")
    col_a1, col_a2 = st.columns(2)
    add_shares = col_a1.number_input("持有份额", min_value=0.0, step=10.0)
    add_cost = col_a2.number_input("买入成本", min_value=0.0, format="%.4f", step=0.0001)
    if st.button("立即添加", type="primary"):
        if len(add_code) == 6:
            fname = get_fund_info(add_code)
            u_data["holdings"].append({"code": add_code, "name": fname, "shares": add_shares, "cost": add_cost})
            save_db(db)
            st.success(f"已添加: {fname}")
            st.rerun()
