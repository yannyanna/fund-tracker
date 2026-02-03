import streamlit as st
from datetime import datetime
import json
import urllib.request
import pytz
from streamlit_autorefresh import st_autorefresh

# --- 基础配置 ---
TZ = pytz.timezone('Asia/Shanghai')
st.set_page_config(page_title="收益追踪-修复版", layout="wide")

# --- 样式逻辑 ---
st.markdown("""<style>
    [data-testid="stMetric"] { background: #f0f2f6; padding: 10px; border-radius: 10px; }
    .fund-card { border-left: 5px solid #ff4b4b; padding: 10px; margin: 5px 0; background: white; border-radius: 5px; box-shadow: 0 1px 2px rgba(0,0,0,0.1); }
</style>""", unsafe_allow_html=True)

# --- 数据抓取优化 ---
@st.cache_data(ttl=60)
def fetch_data_source():
    # 黄金：尝试抓取，失败则返回你提供的 1078
    now_str = datetime.now(TZ).strftime('%H:%M:%S')
    gold_price = 1078.0  # 默认使用你查到的准确值
    gold_status = "参考价(手动)"
    
    try:
        # 尝试备用接口：这里模拟一个更稳定的获取方式
        url = "https://data-asg.goldprice.org/dbXRates/USD"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=3) as res:
            d = json.loads(res.read().decode('utf-8'))
            usd = next(i['xauPrice'] for i in d['items'] if i['curr'] == 'XAU')
            rate = next(i['rate'] for i in d['items'] if i['curr'] == 'CNY')
            gold_price = (usd * rate) / 31.1035
            gold_status = "实时(国际)"
    except:
        pass
    return {"cny": gold_price, "time": now_str, "status": gold_status}

def get_live_fund(code):
    try:
        # 天天基金接口：gsz 是当前估值，dwjz 是昨日官方净值
        url = f"http://fundgz.1234567.com.cn/js/{code}.js"
        with urllib.request.urlopen(url, timeout=3) as res:
            c = res.read().decode('utf-8')
            return json.loads(c[c.find('{'):c.rfind('}')+1])
    except: return None

# --- 主逻辑 ---
st_autorefresh(interval=30000, key="f_ref")

# 黄金显示
g = fetch_data_source()
st.subheader(f"🟡 黄金价格: ¥{g['cny']:.2f} /克")
st.caption(f"状态: {g['status']} | 刷新: {g['time']}")

# 模拟持仓数据 (实际应从你的数据库加载)
# 假设 002611 份额 46531.0
my_holdings = [{"code": "002611", "shares": 46531.0, "cost": 2.4930}]

t_val, t_profit = 0.0, 0.0

for h in my_holdings:
    f = get_live_fund(h['code'])
    if f:
        # 核心逻辑修复：
        # gsz = 3.3821 (当前)
        # dwjz = 3.2467 (昨日)
        curr_gsz = float(f['gsz'])
        last_dwjz = float(f['dwjz'])
        
        m_val = h['shares'] * curr_gsz
        # 当日收益计算：(3.3821 - 3.2467) * 份额
        d_profit = h['shares'] * (curr_gsz - last_dwjz)
        
        t_val += m_val
        t_profit += d_profit
        
        # UI展示
        st.markdown(f"""
        <div class="fund-card">
            <div style="display:flex; justify-content:space-between">
                <b>{f['name']} ({h['code']})</b>
                <span style="color:#ff4b4b">+{f['gszzl']}%</span>
            </div>
            <div style="display:flex; justify-content:space-between; margin-top:10px">
                <span>估值: {curr_gsz:.4f} (昨净: {last_dwjz:.4f})</span>
                <b>收益: ¥{d_profit:,.2f}</b>
            </div>
        </div>
        """, unsafe_allow_html=True)

st.divider()
c1, c2 = st.columns(2)
c1.metric("总资产", f"¥{t_val:,.2f}")
c2.metric("今日预估收益", f"¥{t_profit:,.2f}")
