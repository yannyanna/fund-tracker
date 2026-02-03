import streamlit as st
from datetime import datetime, date
import time
import json
import os
import urllib.request
import pytz

TZ = pytz.timezone('Asia/Shanghai')
st.set_page_config(page_title="基金收益追踪", page_icon="📈", layout="wide", initial_sidebar_state="collapsed")
st.markdown("<style>.main{padding:0.5rem 1rem}.summary-card{background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);color:white;padding:20px;border-radius:15px;margin-bottom:15px}.summary-title{font-size:14px;opacity:0.9;margin-bottom:5px}.summary-value{font-size:28px;font-weight:bold}.fund-card{background:white;padding:15px;border-radius:12px;margin-bottom:12px;box-shadow:0 2px 8px rgba(0,0,0,0.08)}.fund-name{font-size:16px;font-weight:bold;color:#333}.fund-code{font-size:12px;color:#999;margin-left:8px}.change-big{font-size:32px;font-weight:bold;text-align:right}.change-small{font-size:14px;text-align:right;margin-top:5px}.up-red{color:#e74c3c}.down-green{color:#27ae60}.detail-grid{display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px;margin-top:15px;padding-top:15px;border-top:1px solid #eee}.detail-item{text-align:center}.detail-label{font-size:12px;color:#999;margin-bottom:3px}.detail-value{font-size:14px;font-weight:bold;color:#333}.profit-box{background:#fff5f5;padding:10px;border-radius:8px;margin-top:10px;text-align:center}.profit-label{font-size:12px;color:#666}.profit-value{font-size:20px;font-weight:bold}.update-time{color:#999;font-size:11px;text-align:center;margin-top:20px;padding:15px}#MainMenu,footer,header{visibility:hidden}</style>", unsafe_allow_html=True)

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
                data_list.append({'code': code, 'name': d.get('name', '基金' + code), 'nav': current_nav, 'last_nav': last_nav, 'growth': growth, 'data_time': data_time})
        except:
            data_list.append({'code': code, 'name': '基金' + code, 'nav': 0, 'last_nav': 0, 'growth': 0, 'data_time': ''})
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

st.title("📱 基金收益追踪")
with st.expander("➕ 添加基金"):
    c1, c2, c3, c4 = st.columns([2, 2, 2, 2])
    with c1:
        code = st.text_input("基金代码", placeholder="如:002611")
    with c2:
        shares = st.number_input("持有份额", min_value=0.0, value=46531.0, step=100.0)
    with c3:
        cost = st.number_input("成本价", min_value=0.0001, value=2.4930, step=0.0001, format="%.4f")
    with c4:
        buy_date = st.date_input("买入日期", value=date(2024, 12, 28))
    if st.button("添加", type="primary"):
        if code and len(code) == 6:
            name = get_fund_name(code)
            st.session_state.data['holdings'].append({'code': code, 'name': name, 'shares': shares, 'cost': cost, 'buy_date': buy_date.strftime("%Y-%m-%d")})
            save_data(st.session_state.data)
            st.success("已添加 " + name)
            time.sleep(1)
            st.rerun()
        else:
            st.error("请输入6位基金代码")

holdings = st.session_state.data['holdings']
if not holdings:
    st.info("请添加基金开始追踪")
    st.stop()

codes = [h['code'] for h in holdings]
fund_data = get_fund_data(codes)
data_update_time = ""
if fund_data and len(fund_data) > 0:
    data_update_time = fund_data[0].get('data_time', '')

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
            results.append({'name': h['name'], 'code': h['code'], 'nav': nav, 'growth': growth, 'market_value': market_value, 'today_profit': today_profit, 'hold_profit': hold_profit, 'hold_days': hold_days, 'shares': shares, 'cost': cost})

col1, col2 = st.columns(2)
with col1:
    st.metric("总资产", f"¥{total_market:,.2f}")
with col2:
    st.metric("当日收益", f"¥{total_today_profit:,.2f}", f"{(total_today_profit/total_cost*100) if total_cost else 0:.2f}%")
col3, col4 = st.columns(2)
with col3:
    st.metric("持有收益", f"¥{total_hold_profit:,.2f}")
with col4:
    st.metric("持仓成本", f"¥{total_cost:,.2f}")

st.markdown("---")
st.markdown("### 我的持仓")

for r in results:
    is_up = r['growth'] >= 0
    growth_color = "#e74c3c" if is_up else "#27ae60"
    profit_color = "#e74c3c" if r['hold_profit'] >= 0 else "#27ae60"
    with st.container():
        c1, c2 = st.columns([3, 2])
        with c1:
            st.markdown(f"**{r['name']}** <span style='color:#999;font-size:12px'>{r['code']}</span>", unsafe_allow_html=True)
        with c2:
            st.markdown(f"<div style='text-align:right;font-size:28px;font-weight:bold;color:{growth_color}'>{r['growth']:+.2f}%</div>", unsafe_allow_html=True)
            st.markdown(f"<div style='text-align:right;font-size:12px;color:#999'>当日涨跌</div>", unsafe_allow_html=True)
        st.markdown(f"<div style='background:#fff5f5;padding:10px;border-radius:8px;margin:10px 0;text-align:center'><div style='font-size:12px;color:#666'>持有收益（{r['hold_days']}天）</div><div style='font-size:20px;font-weight:bold;color:{profit_color}'>{'+' if r['hold_profit'] >= 0 else ''}¥{r['hold_profit']:,.2f}</div></div>", unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown(f"<div style='text-align:center'><div style='font-size:12px;color:#999'>最新净值</div><div style='font-weight:bold'>¥{r['nav']:.4f}</div></div>", unsafe_allow_html=True)
        with c2:
            st.markdown(f"<div style='text-align:center'><div style='font-size:12px;color:#999'>持仓成本</div><div style='font-weight:bold'>¥{r['cost']:.4f}</div></div>", unsafe_allow_html=True)
        with c3:
            st.markdown(f"<div style='text-align:center'><div style='font-size:12px;color:#999'>持有金额</div><div style='font-weight:bold'>¥{r['market_value']:,.2f}</div></div>", unsafe_allow_html=True)
        st.markdown("---")

with st.expander("🗑️ 删除基金"):
    for h in holdings:
        if st.button("删除 " + h['name'], key="del_" + h['code']):
            st.session_state.data['holdings'] = [x for x in holdings if x['code'] != h['code']]
            save_data(st.session_state.data)
            st.rerun()

beijing_now = get_beijing_time().strftime('%H:%M:%S')
beijing_date = get_beijing_time().strftime('%Y-%m-%d')
st.markdown(f"<div style='color:#999;font-size:11px;text-align:center;margin-top:20px'>⏰ 北京时间：{beijing_date} {beijing_now}<br>数据更新时间：{data_update_time if data_update_time else '实时'}<br><small>估值仅供参考，投资有风险</small></div><div style='color:#3498db;font-size:11px;text-align:center;margin-top:5px'>数据来源：天天基金网</div>", unsafe_allow_html=True)
time.sleep(30)
st.rerun()
