import streamlit as st
from datetime import datetime
import json
import os
import urllib.request
import pytz
from streamlit_autorefresh import st_autorefresh

# --- 基础配置 ---
TZ = pytz.timezone('Asia/Shanghai')
DATA_FILE = "fund_user_data.json"

st.set_page_config(page_title="极速收益追踪", page_icon="⚡", layout="wide")

# 极简 CSS：只保留结构，不使用复杂的渐变，提升浏览器渲染速度
st.markdown("""
<style>
    .metric-container { background: #f8f9fa; padding: 10px; border-radius: 8px; border: 1px solid #eee; margin-bottom: 10px; }
    .fund-card { border-left: 5px solid #e74c3c; padding: 10px; margin: 5px 0; background: white; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
    .up { color: #e74c3c; font-weight: bold; }
    .down { color: #27ae60; font-weight: bold; }
    .stMetric { background: #ffffff; padding: 10px; border-radius: 5px; }
</style>
""", unsafe_allow_html=True)

# --- 核心逻辑：数据持久化 ---
def load_db():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"Default": {"holdings": [], "profile": {"age": 25, "height": 175}}}

def save_db(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False)

# --- 高速缓存接口数据 ---
@st.cache_data(ttl=300) # 黄金价格 5 分钟更新一次足够
def fetch_gold_quick():
    try:
        url = "https://data-asg.goldprice.org/dbXRates/USD"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=3) as res:
            d = json.loads(res.read().decode('utf-8'))
            usd = next(i['xauPrice'] for i in d['items'] if i['curr'] == 'XAU')
            rate = next(i['rate'] for i in d['items'] if i['curr'] == 'CNY')
            return {"cny": (usd * rate) / 31.1035, "time": datetime.now(TZ).strftime('%H:%M')}
    except:
        return {"cny": 0.0, "time": "N/A"}

@st.cache_data(ttl=30) # 基金估值 30 秒更新一次
def fetch_fund_batch(codes):
    results = {}
    for code in codes:
        try:
            url = f"http://fundgz.1234567.com.cn/js/{code}.js"
            with urllib.request.urlopen(url, timeout=2) as res:
                c = res.read().decode('utf-8')
                d = json.loads(c[c.find('{'):c.rfind('}')+1])
                results[code] = d
        except:
            results[code] = None
    return results

# --- 侧边栏：多用户管理 ---
db = load_db()
with st.sidebar:
    st.subheader("👤 用户管理")
    usernames = list(db.keys())
    selected_user = st.selectbox("当前账号", usernames)
    
    with st.expander("账号操作"):
        new_name = st.text_input("新用户名")
        if st.button("创建"):
            if new_name and new_name not in db:
                db[new_name] = {"holdings": [], "profile": {}}
                save_db(db)
                st.rerun()
    
    st.divider()
    # 记录你的个人信息需求
    u_data = db[selected_user]
    st.write(f"用户：{selected_user}")
    u_data["profile"]["age"] = st.number_input("年龄", value=u_data["profile"].get("age", 25))
    u_data["profile"]["height"] = st.number_input("身高(cm)", value=u_data["profile"].get("height", 175))
    if st.button("保存配置"):
        save_db(db)
        st.toast("配置已同步")

# --- 主界面 ---
st_autorefresh(interval=30000, key="auto_ref") # 30秒静默刷新

# 顶部紧凑数据栏
gold = fetch_gold_quick()
col_g1, col_g2 = st.columns([1, 1])
col_g1.metric("实时金价", f"¥{gold['cny']:.2f}/克")
col_g2.write(f"🕒 刷新时间: {gold['time']}")

# 持仓逻辑
holdings = u_data["holdings"]
if not holdings:
    st.info("暂无持仓，请在下方添加")
else:
    live_funds = fetch_fund_batch([h['code'] for h in holdings])
    
    t_val, t_profit = 0, 0
    fund_items = []

    for h in holdings:
        f = live_funds.get(h['code'])
        if f:
            cur_val = h['shares'] * float(f['gsz'])
            day_profit = h['shares'] * (float(f['gsz']) - float(f['dwjz']))
            t_val += cur_val
            t_profit += day_profit
            fund_items.append({
                "name": f['name'], "code": h['code'], "growth": float(f['gszzl']),
                "val": cur_val, "day": day_profit, "time": f['gztime']
            })

    # 总览卡片
    c1, c2 = st.columns(2)
    c1.metric("当前总资产", f"¥{t_val:,.2f}")
    c2.metric("今日预估收益", f"¥{t_profit:,.2f}", f"{(t_profit/(t_val-t_profit)*100):.2f}%" if t_val!=t_profit else "0%")

    st.divider()

    # 列表展示
    for item in fund_items:
        style = "up" if item['growth'] >= 0 else "down"
        st.markdown(f"""
        <div class="fund-card" style="border-left-color: {'#e74c3c' if item['growth']>=0 else '#27ae60'}">
            <div style="display:flex; justify-content:space-between">
                <b>{item['name']} <small style="color:#666">({item['code']})</small></b>
                <span class="{style}">{item['growth']:+.2f}%</span>
            </div>
            <div style="display:flex; justify-content:space-between; font-size: 0.9em; margin-top:5px">
                <span>市值: ¥{item['val']:,.2f}</span>
                <span class="{style}">今日: ¥{item['day']:,.2f}</span>
            </div>
            <div style="text-align:right; font-size:0.7em; color:#999">{item['time']}</div>
        </div>
        """, unsafe_allow_html=True)

# 管理操作
with st.expander("➕/➖ 持仓管理"):
    tab1, tab2 = st.tabs(["添加", "删除"])
    with tab1:
        nc = st.text_input("代码", max_chars=6)
        ns = st.number_input("份额", min_value=0.0)
        np = st.number_input("成本", min_value=0.0)
        if st.button("添加基金"):
            u_data["holdings"].append({"code": nc, "shares": ns, "cost": np})
            save_db(db)
            st.rerun()
    with tab2:
        for i, h in enumerate(holdings):
            if st.button(f"删除 {h['code']}", key=f"del_{i}"):
                u_data["holdings"].pop(i)
                save_db(db)
                st.rerun()
