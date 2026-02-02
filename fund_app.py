import streamlit as st
from datetime import datetime, date
import time
import json
import os
import urllib.request

st.set_page_config(page_title="基金收益追踪", page_icon="📈", layout="wide", initial_sidebar_state="collapsed")

# CSS样式 - 模仿App风格
st.markdown("""
<style>
.main{padding:0.5rem 1rem}
/* 顶部总览卡片 */
.summary-card{
    background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);
    color:white;
    padding:20px;
    border-radius:15px;
    margin-bottom:15px;
    box-shadow:0 4px 15px rgba(0,0,0,0.1);
}
.summary-title{font-size:14px;opacity:0.9;margin-bottom:5px}
.summary-value{font-size:28px;font-weight:bold}
.summary-sub{font-size:16px;margin-top:5px}
/* 基金卡片 */
.fund-card{
    background:white;
    padding:15px;
    border-radius:12px;
    margin-bottom:12px;
    box-shadow:0 2px 8px rgba(0,0,0,0.08);
}
.fund-header{
    display:flex;
    justify-content:space-between;
    align-items:center;
    margin-bottom:10px;
}
.fund-name{font-size:16px;font-weight:bold;color:#333}
.fund-code{font-size:12px;color:#999;margin-left:8px}
/* 涨跌幅大字体 */
.change-big{
    font-size:32px;
    font-weight:bold;
    text-align:right;
}
.change-small{
    font-size:14px;
    text-align:right;
    margin-top:5px;
}
/* 红绿配色 - A股习惯：涨红跌绿 */
.up-red{color:#e74c3c}
.down-green{color:#27ae60}
/* 详情网格 */
.detail-grid{
    display:grid;
    grid-template-columns:1fr 1fr 1fr;
    gap:10px;
    margin-top:15px;
    padding-top:15px;
    border-top:1px solid #eee;
}
.detail-item{text-align:center}
.detail-label{font-size:12px;color:#999;margin-bottom:3px}
.detail-value{font-size:14px;font-weight:bold;color:#333}
/* 持有收益 */
.profit-box{
    background:#fff5f5;
    padding:10px;
    border-radius:8px;
    margin-top:10px;
    text-align:center;
}
.profit-label{font-size:12px;color:#666}
.profit-value{font-size:20px;font-weight:bold;color:#e74c3c}
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
</style>
""", unsafe_allow_html=True)

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

def get_fund_data(codes):
    """获取基金实时数据"""
    data_list = []
    for code in codes:
        try:
            url = f"http://fundgz.1234567.com.cn/js/{code}.js"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=10) as response:
                html = response.read().decode('utf-8')
                json_str = html[html.find('{'):html.rfind('}')+1]
                d = json.loads(json_str)
                
                try:
                    growth = float(d['gszzl'])
                except:
                    growth = 0
                
                # 获取昨日净值计算当日收益
                try:
                    last_nav = float(d['dwjz'])
                    current_nav = float(d['gsz'])
                    # 估算当日涨跌额 = (当前估算 - 昨日净值) * 份额（后面计算）
                except:
                    last_nav = 0
                    current_nav = 0
                
                data_list.append({
                    'code': code,
                    'name': d.get('name', f'基金{code}'),
                    'nav': current_nav,
                    'last_nav': last_nav,
                    'growth': growth
                })
        except:
            data_list.append({
                'code': code,
                'name': f'基金{code}',
                'nav': 1.0,
                'last_nav': 1.0,
                'growth': 0
            })
    return data_list

def get_fund_name(code):
    try:
        url = f"http://fundgz.1234567.com.cn/js/{code}.js"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            html = response.read().decode('utf-8')
            json_str = html[html.find('{'):html.rfind('}')+1]
            d = json.loads(json_str)
            return d.get('name', f'基金{code}')
    except:
        return f'基金{code}'

def days_between(d1, d2):
    """计算持有天数"""
    try:
        date1 = datetime.strptime(d1, "%Y-%m-%d").date()
        date2 = datetime.strptime(d2, "%Y-%m-%d").date()
        return (date2 - date1).days
    except:
        return 0

# ========== 界面开始 ==========

st.title("📱 基金收益追踪")

# 添加基金
with st.expander("➕ 添加基金"):
    c1, c2, c3, c4 = st.columns([2, 2, 2, 2])
    with c1:
        code = st.text_input("基金代码", placeholder="如:002611.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=10) as response:
                html = response.read().decode('utf-8')
                json_str = html[html.find('{'):html.rfind('}')+1]
                d = json.loads(json_str)
                
                try:
                    growth = float(d['gszzl'])
                except:
                    growth = 0
                
                # 获取昨日净值计算当日收益
                try:
                    last_nav = float(d['dwjz'])
                    current_nav = float(d['gsz'])
                    # 估算当日涨跌额 = (当前估算 - 昨日净值) * 份额（后面计算）
                except:
                    last_nav = 0
                    current_nav = 0
                
                data_list.append({
                    'code': code,
                    'name': d.get('name', f'基金{code}'),
                    'nav': current_nav,
                    'last_nav': last_nav,
                    'growth': growth
                })
        except:
            data_list.append({
                'code': code,
                'name': f'基金{code}',
                'nav': 1.0,
                'last_nav': 1.0,
                'growth': 0
            })
    return data_list

def get_fund_name(code):
    try:
        url = f"http://fundgz.1234567.com.cn/js/{code}.js"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            html = response.read().decode('utf-8')
            json_str = html[html.find('{'):html.rfind('}')+1]
            d = json.loads(json_str)
            return d.get('name', f'基金{code}')
    except:
        return f'基金{code}'

def days_between(d1, d2):
    """计算持有天数"""
    try:
        date1 = datetime.strptime(d1, "%Y-%m-%d").date()
        date2 = datetime.strptime(d2, "%Y-%m-%d").date()
        return (date2 - date1).days
    except:
        return 0

# ========== 界面开始 ==========

st.title("📱 基金收益追踪")

# 添加基金
with st.expander("➕ 添加基金"):
    c1, c2, c3, c4 = st.columns([2, 2, 2, 2])
    with c1:
        code = st.text_input("基金代码", placeholder="如:002611")
    with c2:
        shares = st.number_input("持有份额", min_value=0.0, value=1000.0, step=100.0)
    with c3:
        cost = st.number_input("成本价", min_value=0.0001, value=1.0, step=0.0001, format="%.4f")
    with c4:
        # 默认今天，可修改
        buy_date = st.date_input("买入日期", value=date.today())
    
    if st.button("添加", type="primary"):
        if code and len(code) == 6:
            name = get_fund_name(code)
            st.session_state.data['holdings'].append({
                'code': code,
                'name': name,
                'shares': shares,
                'cost': cost,
                'buy_date': buy_date.strftime("%Y-%m-%d")
            })
            save_data(st.session_state.data)
            st.success(f"已添加 {name}")
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

# 计算总数据
total_cost = 0      # 总成本
total_market = 0    # 总市值
total_today_profit = 0  # 当日总收益
total_hold_profit = 0   # 持有总收益

results = []
today_str = datetime.now().strftime("%Y-%m-%d")

for h in holdings:
    for d in fund_data:
        if d['code'] == h['code']:
            nav = d['nav']           # 当前净值
            last_nav = d['last_nav'] # 昨日净值
            growth = d['growth']     # 涨跌幅%
            shares = h['shares']     # 份额
            cost = h['cost']         # 成本价
            
            market_value = shares * nav           # 市值
            cost_value = shares * cost           .request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=10) as response:
                html = response.read().decode('utf-8')
                json_str = html[html.find('{'):html.rfind('}')+1]
                d = json.loads(json_str)
                
                try:
                    growth = float(d['gszzl'])
                except:
                    growth = 0
                
                # 获取昨日净值计算当日收益
                try:
                    last_nav = float(d['dwjz'])
                    current_nav = float(d['gsz'])
                    # 估算当日涨跌额 = (当前估算 - 昨日净值) * 份额（后面计算）
                except:
                    last_nav = 0
                    current_nav = 0
                
                data_list.append({
                    'code': code,
                    'name': d.get('name', f'基金{code}'),
                    'nav': current_nav,
                    'last_nav': last_nav,
                    'growth': growth
                })
        except:
            data_list.append({
                'code': code,
                'name': f'基金{code}',
                'nav': 1.0,
                'last_nav': 1.0,
                'growth': 0
            })
    return data_list

def get_fund_name(code):
    try:
        url = f"http://fundgz.1234567.com.cn/js/{code}.js"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            html = response.read().decode('utf-8')
            json_str = html[html.find('{'):html.rfind('}')+1]
            d = json.loads(json_str)
            return d.get('name', f'基金{code}')
    except:
        return f'基金{code}'

def days_between(d1, d2):
    """计算持有天数"""
    try:
        date1 = datetime.strptime(d1, "%Y-%m-%d").date()
        date2 = datetime.strptime(d2, "%Y-%m-%d").date()
        return (date2 - date1).days
    except:
        return 0

# ========== 界面开始 ==========

st.title("📱 基金收益追踪")

# 添加基金
with st.expander("➕ 添加基金"):
    c1, c2, c3, c4 = st.columns([2, 2, 2, 2])
    with c1:
        code = st.text_input("基金代码", placeholder="如:002611")
    with c2:
        shares = st.number_input("持有份额", min_value=0.0, value=1000.0, step=100.0)
    with c3:
        cost = st.number_input("成本价", min_value=0.0001, value=1.0, step=0.0001, format="%.4f")
    with c4:
        # 默认今天，可修改
        buy_date = st.date_input("买入日期", value=date.today())
    
    if st.button("添加", type="primary"):
        if code and len(code) == 6:
            name = get_fund_name(code)
            st.session_state.data['holdings'].append({
                'code': code,
                'name': name,
                'shares': shares,
                'cost': cost,
                'buy_date': buy_date.strftime("%Y-%m-%d")
            })
            save_data(st.session_state.data)
            st.success(f"已添加 {name}")
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

# 计算总数据
total_cost = 0      # 总成本
total_market = 0    # 总市值
total_today_profit = 0  # 当日总收益
total_hold_profit = 0   # 持有总收益

results = []
today_str = datetime.now().strftime("%Y-%m-%d")

for h in holdings:
    for d in fund_data:
        if d['code'] == h['code']:
            nav = d['nav']           # 当前净值
            last_nav = d['last_nav'] # 昨日净值
            growth = d['growth']     # 涨跌幅%
            shares = h['shares']     # 份额
            cost = h['cost']         # 成本价
            
            market_value = shares * nav           # 市值
            cost_value = shares * cost            # 成本
            hold_profit = market_value - cost_value  # 持有收益
            today_profit = shares * (nav - last_nav) if last_nav > 0 else 0  # 当日收益
            
            total_cost += cost_value
            total_market += market_value
            total_today_profit += today_profit
            total_hold_profit += hold_profit
            
            # 计算持有天数
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

# ========== 顶部总览卡片 ==========
st.markdown(f"""
<div class="summary-card">
    <div style="display:flex;justify-content:space-between;">
        <div style="flex:1;">
            <div class="summary-title">总资产</div>
            <div class="summary-value">¥{total_market:,.2f}</div>
        </div>
        <div style="flex:1;text-align:right;">
            <div class="summary-title">当日收益</div>
            <div class="summary-value" style="color:{'#ff6b6b' if total_today_profit >= 0 else '#90ee90'}">
                {'+' if total_today_profit >= 0 else ''}¥{total_today_profit:,.2f}
            </div>
            <div class="summary-sub" style="color:{'#ff6b6b' if total_today_profit >= 0 else '#90ee90'}">
                {'+' if total_today_profit >= 0 else ''}{(total_today_profit/total_cost*100) if total_cost else 0:.2f}%
            </div>
        </div>
    </div>
    <div style="margin-top:15px;padding-top:15px;border-top:1px solid rgba(255,255,255,0.3);display:flex;justify-content:space-between;">
        <div>
            <div class="summary-title">持有收益</div>
            <div style="font-size:20px;font-weight:bold;color:{'#ff6b6b' if total_hold_profit >= 0 else '#90ee90'}">
                {'+' if total_hold_profit >= 0 else ''}¥{total_hold_profit:,.2f}
            </div>
        </div>
        <div style="text-align:right;">
            <div class="summary-title">持仓成本</div>
            <div style="font-size:20px;font-weight:bold;">¥{total_cost:,.2f}</div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# ========== 基金列表 ==========
st.markdown("### 我的持仓")

for r in results:
    # 判断涨跌颜色：涨红跌绿
    is_up = r['growth'] >= 0
    growth_class = "up-red" if is_up else "down-green"
    profit_class = "up-red" if r['hold_profit'] >= 0 else "down-green"
    growth_sign = "+" if is_up else ""
    profit_sign = "+" if r['hold_profit'] >= 0 else ""
    
    st.markdown(f"""
    <div class="fund-card">
        <div class="fund-header">
            <div>
                <span class="fund-name">{r['name']}</span>
                <span class="fund-code">{r['code']}</span>
            </div>
            <div>
                <div class="change-big {growth_class}">{growth_sign}{r['growth']:.2f}%</div>
                <div class="change-small {growth_class}">当日涨跌</div>
            </div>
        </div>
        
        <div class="profit-box">
            <div class="profit-label">持有收益（{r['hold_days']}天）</div>
            <div class="profit-value {profit_class}">{profit_sign}¥{r['hold_profit']:,.2f}</div>
        </div>
        
        <div class="detail-grid">
            <div class="detail-item">
                <div class="detail-label">最新净值</div>
                <div class="detail-value">¥{r['nav']:.4f}</div>
            </div>
            <div class="detail-item">
                <div class="detail-label">持仓成本</div>
                <div class="detail-value">¥{r['cost']:.4f}</div>
            </div>
            <div class="detail-item">
                <div class="detail-label">持有金额</div>
                <div class="detail-value">¥{r['market_value']:,.2f}</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# 删除按钮
with st.expander("🗑️ 删除基金"):
    for h in holdings:
        if st.button(f"删除 {h['name']}", key=f"del_{h['code']}"):
            st.session_state.data['holdings'] = [x for x in holdings if x['code'] != h['code']]
            save_data(st.session_state.data)
            st.rerun()

# 更新时间
st.markdown(f"""
<div class="update-time">
    ⏰ 数据更新于 {datetime.now().strftime('%H:%M:%S')} | 30秒后自动刷新<br>
    <small>估值仅供参考，投资有风险</small>
</div>
""", unsafe_allow_html=True)

time.sleep(30)
st.rerun()
