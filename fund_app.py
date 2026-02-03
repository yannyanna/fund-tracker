import streamlit as st
from datetime import datetime, date
import time
import json
import os
import urllib.request
import pytz

TZ = pytz.timezone('Asia/Shanghai')
st.set_page_config(page_title="基金收益追踪", page_icon="📈", layout="wide", initial_sidebar_state="collapsed")

# CSS样式 - 优化版
st.markdown("""
<style>
.main{padding:0.5rem 1rem}
/* 黄金卡片 - 放大1.5倍 */
.gold-card{
    background:linear-gradient(135deg,#f1c40f 0%,#f39c12 100%);
    color:white;
    padding:22px;
    border-radius:15px;
    margin-bottom:20px;
    box-shadow:0 6px 20px rgba(243,156,18,0.4);
    transform:scale(1.05);
    transform-origin:center;
}
.gold-title{font-size:16px;opacity:0.9;margin-bottom:8px;font-weight:bold}
.gold-price{font-size:48px;font-weight:bold;text-align:center;line-height:1.2}
.gold-unit{font-size:16px;opacity:0.9;text-align:center;margin-top:8px}
.gold-sub{font-size:14px;opacity:0.8;text-align:center;margin-top:5px}
/* 总览卡片 */
.summary-card{
    background:white;
    padding:20px;
    border-radius:12px;
    margin-bottom:15px;
    box-shadow:0 2px 10px rgba(0,0,0,0.08);
}
.summary-title{font-size:13px;color:#666;margin-bottom:5px}
.summary-value{font-size:24px;font-weight:bold;color:#333}
.summary-profit{font-size:20px;font-weight:bold}
/* 基金卡片 - 参考截图 */
.fund-card{
    background:white;
    padding:15px;
    border-radius:12px;
    margin-bottom:12px;
    box-shadow:0 1px 5px rgba(0,0,0,0.06);
    border-bottom:1px solid #f0f0f0;
}
.fund-header{
    display:flex;
    justify-content:space-between;
    align-items:flex-start;
    margin-bottom:12px;
}
.fund-name{font-size:17px;font-weight:bold;color:#333;line-height:1.3}
.fund-code{font-size:12px;color:#999;margin-top:3px;display:block}
.fund-amount{font-size:15px;color:#666;margin-top:5px}
.change-box{text-align:right}
.change-percent{font-size:26px;font-weight:bold;line-height:1}
.change-value{font-size:14px;margin-top:4px}
.change-label{font-size:11px;color:#999;margin-top:2px}
/* 收益行 */
.profit-row{
    display:flex;
    justify-content:space-between;
    align-items:center;
    margin-top:12px;
    padding-top:12px;
    border-top:1px solid #f5f5f5;
}
.profit-item{text-align:center;flex:1}
.profit-label{font-size:12px;color:#999;margin-bottom:4px}
.profit-num{font-size:16px;font-weight:bold}
/* 红绿配色 */
.up-red{color:#e74c3c}
.down-green{color:#27ae60}
/* 更新时间 */
.update-time{
    color:#999;
    font-size:11px;
    text-align:center;
    margin-top:20px;
    padding:15px;
}
/* 隐藏Streamlit元素 */
#MainMenu,footer,header{visibility:hidden}
div[data-baseweb="input"] input{color:#333 !important}
</style>
""", unsafe_allow_html=True)

DATA_FILE = "fund_data.json"
USER_FILE = "user_config.json"

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

def load_user():
    if os.path.exists(USER_FILE):
        try:
            with open(USER_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return {"username": ""}

def save_user(user_data):
    with open(USER_FILE, 'w', encoding='utf-8') as f:
        json.dump(user_data, f, ensure_ascii=False, indent=2)

# 初始化
if 'data' not in st.session_state:
    st.session_state.data = load_data()
if 'user' not in st.session_state:
    st.session_state.user = load_user()

def get_beijing_time():
    return datetime.now(TZ)

def get_gold_price():
    """获取实时黄金价格"""
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

# ========== 用户名设置 ==========
with st.sidebar:
    st.header("👤 用户设置")
    username = st.text_input("用户名", value=st.session_state.user.get('username', ''), placeholder="请输入用户名")
    if st.button("保存用户名"):
        st.session_state.user['username'] = username
        save_user(st.session_state.user)
        st.success("用户名已保存！")
    
    st.divider()
    st.markdown("**关于**")
    st.markdown("基金收益追踪 v1.0")

# ========== 主界面 ==========
username_display = st.session_state.user.get('username', '')
if username_display:
    st.title(f"👋 你好，{username_display}")
else:
    st.title("📱 基金收益追踪")

# ========== 黄金价格卡片（放大1.5倍） ==========
gold_data = get_gold_price()
st.markdown(f"""
<div class="gold-card">
    <div style="display:flex;justify-content:space-between;align-items:center;">
        <div style="flex:1;">
            <div class="gold-title">🟡 国际黄金</div>
            <div class="gold-sub">${gold_data['usd_oz']:,.2f}/盎司</div>
        </div>
        <div style="flex:1.5;text-align:center;">
            <div class="gold-price">¥{gold_data['cny_gram']:,.2f}</div>
            <div class="gold-unit">人民币/克</div>
        </div>
        <div style="flex:1;text-align:right;">
            <div class="gold-sub">汇率 {gold_data['rate']:.4f}</div>
            <div class="gold-sub">{gold_data['time']}更新</div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# ========== 添加基金（输入框优化） ==========
with st.expander("➕ 添加基金"):
    # 使用text_input配合value=""来避免默认0值
    col1, col2, col3, col4 = st.columns([2, 2, 2, 2])
    with col1:
        # 基金代码用text_input，没有默认值问题
        code = st.text_input("基金代码", placeholder="如:002611", value="")
    with col2:
        # 份额用number_input但设置value=None，配合placeholder
        shares_input = st.text_input("持有份额", placeholder="如:46531", value="")
        shares = float(shares_input) if shares_input.replace('.','').isdigit() else 0.0
    with col3:
        # 成本价同样处理
        cost_input = st.text_input("成本价", placeholder="如:2.4930", value="")
        cost = float(cost_input) if cost_input.replace('.','').isdigit() else 0.0
    with c4:
        buy_date = st.date_input("买入日期", value=date.today())
    
    if st.button("添加", type="primary"):
        if code and len(code) == 6 and shares > 0 and cost > 0:
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
            st.error("请填写完整的基金信息")

holdings = st.session_state.data['holdings']
if not holdings:
    st.info("请添加基金开始追踪")
    st.stop()

codes = [h['code'] for h in holdings]
fund_data = get_fund_data(codes)
data_update_time = ""
if fund_data and len(fund_data) > 0:
    data_update_time = fund_data[0].get('data_time', '')

# 计算数据
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
                'hold_days': hold_days,
                'shares': shares,
                'cost': cost
            })

# ========== 总览卡片（参考截图样式） ==========
st.markdown(f"""
<div class="summary-card">
    <div style="display:flex;justify-content:space-between;margin-bottom:15px;">
        <div>
            <div class="summary-title">账户资产</div>
            <div class="summary-value">¥{total_market:,.2f}</div>
        </div>
        <div style="text-align:right;">
            <div class="summary-title">当日收益</div>
            <div class="summary-profit" style="color:{'#e74c3c' if total_today_profit >= 0 else '#27ae60'}">
                {'+' if total_today_profit >= 0 else ''}¥{total_today_profit:,.2f}
            </div>
        </div>
    </div>
    <div style="display:flex;justify-content:space-between;font-size:13px;color:#666;">
        <span>持仓成本 ¥{total_cost:,.2f}</span>
        <span>持有收益 {'+' if total_hold_profit >= 0 else ''}¥{total_hold_profit:,.2f}</span>
    </div>
</div>
""", unsafe_allow_html=True)

# ========== 基金列表（参考截图样式） ==========
st.markdown("### 我的持仓")

for r in results:
    is_up = r['growth'] >= 0
    growth_color = "up-red" if is_up else "down-green"
    profit_color = "up-red" if r['hold_profit'] >= 0 else "down-green"
    growth_sign = "+" if is_up else ""
    profit_sign = "+" if r['hold_profit'] >= 0 else ""
    
    st.markdown(f"""
    <div class="fund-card">
        <div class="fund-header">
            <div>
                <div class="fund-name">{r['name']}</div>
                <span class="fund-code">{r['code']}</span>
                <div class="fund-amount">¥ {r['market_value']:,.2f}</div>
            </div>
            <div class="change-box">
                <div class="change-percent {growth_color}">{growth_sign}{r['growth']:.2f}%</div>
                <div class="change-value {growth_color}">{growth_sign}¥{r['today_profit']:,.2f}</div>
                <div class="change-label">当日收益</div>
            </div>
        </div>
        <div class="profit-row">
            <div class="profit-item">
                <div class="profit-label">持有收益({r['hold_days']}天)</div>
                <div class="profit-num {profit_color}">{profit_sign}¥{r['hold_profit']:,.2f}</div>
            </div>
            <div class="profit-item">
                <div class="profit-label">最新净值</div>
                <div class="profit-num">¥{r['nav']:.4f}</div>
            </div>
            <div class="profit-item">
                <div class="profit-label">持仓成本</div>
                <div class="profit-num">¥{r['cost']:.4f}</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# 删除按钮
with st.expander("🗑️ 删除基金"):
    for h in holdings:
        if st.button("删除 " + h['name'], key="del_" + h['code']):
            st.session_state.data['holdings'] = [x for x in holdings if x['code'] != h['code']]
            save_data(st.session_state.data)
            st.rerun()

# 更新时间
beijing_now = get_beijing_time().strftime('%H:%M:%S')
beijing_date = get_beijing_time().strftime('%Y-%m-%d')
st.markdown(f"""
<div class="update-time">
    ⏰ 北京时间：{beijing_date} {beijing_now}<br>
    基金数据：{data_update_time if data_update_time else '实时'}<br>
    <small>估值仅供参考，投资有风险</small>
</div>
""", unsafe_allow_html=True)

time.sleep(30)
st.rerun()
