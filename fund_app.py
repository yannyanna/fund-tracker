import streamlit as st
from datetime import datetime, date
import time
import json
import os
import urllib.request
import pytz

TZ = pytz.timezone('Asia/Shanghai')

st.set_page_config(page_title="基金收益追踪", page_icon="📈", layout="wide")

# 数据文件
DATA_FILE = "fund_data.json"

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return {"holdings": []}

def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

if 'data' not in st.session_state:
    st.session_state.data = load_data()

def get_beijing_time():
    return datetime.now(TZ)

def get_gold_price():
    try:
        url = "https://data-asg.goldprice.org/dbXRates/USD"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            html = response.read().decode('utf-8')
            data = json.loads(html)
            
            gold_usd_oz = 0
            usd_cny_rate = 7.2
            
            if 'items' in data and len(data['items']) > 0:
                for item in data['items']:
                    if item.get('curr') == 'XAU':
                        gold_usd_oz = item.get('xauPrice', 0)
                    if item.get('curr') == 'CNY':
                        usd_cny_rate = item.get('rate', 7.2)
            
            if gold_usd_oz > 0:
                gold_cny_gram = (gold_usd_oz * usd_cny_rate) / 31.1035
                return {
                    'usd_oz': gold_usd_oz,
                    'cny_gram': gold_cny_gram,
                    'rate': usd_cny_rate,
                    'time': get_beijing_time().strftime('%H:%M:%S')
                }
    except:
        pass
    
    return {
        'usd_oz': 2800,
        'cny_gram': 650,
        'rate': 7.2,
        'time': get_beijing_time().strftime('%H:%M:%S')
    }

def get_fund_data(codes):
    data_list = []
    data_time = ""
    for code in codes:
        try:
            url = "http://fundgz.1234567.com.cn/js/" + code + ".js"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=10) as response:
                html = response.read().decode('utf-8')
                start = html.find('{')
                end = html.rfind('}') + 1
                json_str = html[start:end]
                d = json.loads(json_str)
                if 'gztime' in d and not data_time:
                    data_time = d['gztime']
                try:
                    growth = float(d['gszzl'])
                except:
                    growth = 0
                try:
                    current_nav = float(d['gsz'])
                    last_nav = float(d['dwjz'])
                except:
                    current_nav = 0
                    last_nav = 0
                data_list.append({
                    'code': code,
                    'name': d.get('name', '基金' + code),
                    'nav': current_nav,
                    'last_nav': last_nav,
                    'growth': growth,
                    'data_time': data_time
                })
        except:
            data_list.append({
                'code': code,
                'name': '基金' + code,
                'nav': 0,
                'last_nav': 0,
                'growth': 0,
                'data_time': ''
            })
    return data_list

def get_fund_name(code):
    try:
        url = "http://fundgz.1234567.com.cn/js/" + code + ".js"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            html = response.read().decode('utf-8')
            start = html.find('{')
            end = html.rfind('}') + 1
            json_str = html[start:end]
            d = json.loads(json_str)
            return d.get('name', '基金' + code)
    except:
        return '基金' + code

def days_between(d1, d2):
    try:
        date1 = datetime.strptime(d1, "%Y-%m-%d").date()
        date2 = datetime.strptime(d2, "%Y-%m-%d").date()
        return (date2 - date1).days
    except:
        return 0

# ========== 页面开始 ==========
st.title("📱 基金收益追踪")

# 黄金价格
gold = get_gold_price()
st.markdown(f"### 🟡 黄金 ¥{gold['cny_gram']:.2f}/克  (${gold['usd_oz']:.2f}/盎司)")

# 添加基金
with st.expander("➕ 添加基金"):
    code = st.text_input("基金代码", placeholder="如:002611")
    
    # 使用两列布局，避免变量名冲突
    col_a, col_b = st.columns(2)
    with col_a:
        shares_str = st.text_input("持有份额", placeholder="46531")
    with col_b:
        cost_str = st.text_input("成本价", placeholder="2.4930")
    
    buy_date = st.date_input("买入日期", value=date.today())
    
    if st.button("添加", type="primary"):
        if code and len(code) == 6:
            try:
                shares = float(shares_str) if shares_str else 0
                cost = float(cost_str) if cost_str else 0
            except:
                shares = 0
                cost = 0
            
            if shares > 0 and cost > 0:
                name = get_fund_name(code)
                st.session_state.data['holdings'].append({
                    'code': code,
                    'name': name,
                    'shares': shares,
                    'cost': cost,
                    'buy_date': buy_date.strftime("%Y-%m-%d")
                })
                save_data(st.session_state.data)
                st.success("已添加 " + name)
                time.sleep(1)
                st.rerun()
            else:
                st.error("份额和成本价必须大于0")
        else:
            st.error("请输入6位基金代码")

holdings = st.session_state.data['holdings']
if not holdings:
    st.info("请添加基金")
    st.stop()

codes = [h['code'] for h in holdings]
fund_data = get_fund_data(codes)

# 计算
total_cost = 0
total_market = 0
total_today_profit = 0
total_hold_profit = 0
results = []
today_str = get_beijing_time().strftime("%Y-%m-%d")

for h in holdings:
    for d in fund_data:
        if d['code'] == h['code']:
            nav = d['nav']
            last_nav = d['last_nav']
            growth = d['growth']
            shares = h['shares']
            cost = h['cost']
            
            market_value = shares * nav
            cost_value = shares * cost
            hold_profit = market_value - cost_value
            today_profit = shares * (nav - last_nav) if last_nav > 0 else 0
            
            total_cost += cost_value
            total_market += market_value
            total_today_profit += today_profit
            total_hold_profit += hold_profit
            
            hold_days = days_between(h.get('buy_date', today_str), today_str)
            
            results.append({
                'name': h['name'],
                'code': h['code'],
                'nav': nav,
                'growth': growth,
                'market_value': market_value,
                'today_profit': today_profit,
                'hold_profit': hold_profit,
                'hold_days': hold_days
            })

# 总览
st.markdown("---")
st.metric("总资产", f"¥{total_market:,.2f}")
st.metric("当日收益", f"¥{total_today_profit:,.2f}")
st.metric("持有收益", f"¥{total_hold_profit:,.2f}")

# 基金列表
st.markdown("### 持仓")
for r in results:
    with st.container():
        st.markdown(f"**{r['name']}** ({r['code']})")
        st.markdown(f"涨跌幅: {r['growth']:+.2f}% | 净值: ¥{r['nav']:.4f}")
        st.markdown(f"持有收益: ¥{r['hold_profit']:,.2f} ({r['hold_days']}天) | 市值: ¥{r['market_value']:,.2f}")
        st.markdown("---")

# 删除
with st.expander("🗑️ 删除"):
    for h in holdings:
        if st.button("删除 " + h['name'], key="del_" + h['code']):
            st.session_state.data['holdings'] = [x for x in holdings if x['code'] != h['code']]
            save_data(st.session_state.data)
            st.rerun()

# 时间
beijing_now = get_beijing_time().strftime('%H:%M:%S')
st.caption(f"北京时间: {beijing_now} | 下次更新: 30秒后")

time.sleep(30)
st.rerun()
