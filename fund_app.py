import streamlit as st
from datetime import datetime
import json
import os
import urllib.request
import ssl
import pytz

# --- 基础配置 ---
TZ = pytz.timezone('Asia/Shanghai')
DATA_FILE = "fund_master_v16.json"
ssl_ctx = ssl._create_unverified_context()

st.set_page_config(page_title="收益追踪 V16-Pro", layout="wide")

# --- UI 样式 ---
st.markdown("""
<style>
    .main { padding: 0rem !important; }
    .summary-bar { display: flex; justify-content: space-between; padding: 15px 20px; background: #fff; border-bottom: 2px solid #eee; }
    .sum-val { font-size: 1.6rem; font-weight: bold; color: #333; }
    .sum-lab { font-size: 0.85rem; color: #888; }
    .gold-box { background: linear-gradient(135deg, #fffcf0 0%, #fff7d6 100%); padding: 15px; margin: 10px; border-radius: 12px; text-align: center; border: 1px solid #fcebb3; box-shadow: 0 2px 4px rgba(0,0,0,0.02); }
    .gold-v { font-size: 2rem; color: #b8860b; font-weight: 800; }
    .f-row { display: flex; padding: 14px 18px; background: white; border-bottom: 1px solid #f8f8f8; align-items: center; }
    .f-left { flex: 2; }
    .f-name { font-size: 1rem; font-weight: 600; color: #222; }
    .f-mid { flex: 1.2; text-align: right; }
    .f-right { flex: 1.5; text-align: right; }
    .up { color: #eb4432; }
    .down { color: #00a854; }
    .gray-sub { font-size: 0.75rem; color: #999; margin-top: 2px; }
    .status-badge { font-size: 0.65rem; padding: 1px 4px; border-radius: 4px; background: #f0f0f0; color: #666; }
</style>
""", unsafe_allow_html=True)

# --- 数据持久化 ---
def load_db():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f: return json.load(f)
    return {"Default": {"holdings": []}}

def save_db(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f: json.dump(data, f, ensure_ascii=False, indent=2)

# --- 核心接口：追求养基宝精度 ---
def fetch_gold():
    try:
        url = "http://hq.sinajs.cn/list=gds_AU9999"
        req = urllib.request.Request(url, headers={'Referer': 'http://finance.sina.com.cn'})
        with urllib.request.urlopen(req, timeout=3, context=ssl_ctx) as res:
            return float(res.read().decode('gbk').split('"')[1].split(',')[0])
    except: return 0.0

def fetch_fund_data(code, source):
    try:
        if source == "雪球财经(准)":
            # 雪球私有接口，估值极准
            url = f"https://fund.xueqiu.com/dj/fund/detail.json?fund_code={code}"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=3, context=ssl_ctx) as res:
                d = json.loads(res.read().decode('utf-8'))['data']['fund_rate_new'][0]
                # 雪球的数据包含最新净值和涨跌幅
                return {"name": "基金"+code, "gz": float(d['value']), "nj": float(d['value'])/(1+float(d['percentage'])/100), "ratio": float(d['percentage']), "time": d['time']}
        
        elif source == "腾讯财经(快)":
            url = f"http://qt.gtimg.cn/q=s_jj{code}"
            with urllib.request.urlopen(url, timeout=3, context=ssl_ctx) as res:
                d = res.read().decode('gbk').split('~')
                # 腾讯接口：[代码, 名称, 净值, 涨跌, 涨跌幅, 时间]
                return {"name": d[1], "gz": float(d[2]), "nj": float(d[2])-float(d[3]), "ratio": float(d[4]), "time": d[5][:8]}

        elif source == "天天基金(全)":
            url = f"http://fundgz.1234567.com.cn/js/{code}.js"
            with urllib.request.urlopen(url, timeout=3, context=ssl_ctx) as res:
                c = res.read().decode('utf-8'); d = json.loads(c[c.find('{'):c.rfind('}')+1])
                return {"name": d['name'], "gz": float(d['gsz']), "nj": float(d['dwjz']), "ratio": float(d['gszzl']), "time": d['gztime']}
    except: return None

# --- 系统逻辑 ---
if 'db' not in st.session_state: st.session_state.db = load_db()

with st.sidebar:
    st.header("👤 账户管理")
    current_user = st.selectbox("切换账号", list(st.session_state.db.keys()))
    if st.button("➕ 新建用户"):
        new_name = st.text_input("用户名")
        if new_name: st.session_state.db[new_name] = {"holdings": []}; save_db(st.session_state.db); st.rerun()

# --- 主界面渲染 ---
# 1. 顶部控制栏
col_rf, col_src = st.columns([1, 1])
with col_rf:
    if st.button("🔄 刷新行情"):
        st.cache_data.clear(); st.rerun()
with col_src:
    # 切换时自动清除缓存，确保数据源变更立刻触发新抓取
    data_src = st.selectbox("核心数据源", ["雪球财经(准)", "腾讯财经(快)", "天天基金(全)"], 
                            on_change=st.cache_data.clear)

# 2. 黄金现货
gp = fetch_gold()
st.markdown(f'<div class="gold-box"><div class="gold-v">¥{gp:.2f}</div><div style="font-size:0.8rem; color:#999;">上海黄金交易所 AU9999 实时价</div></div>', unsafe_allow_html=True)

# 3. 资产计算
u_data = st.session_state.db[current_user]
funds = []
total_v, total_dp = 0.0, 0.0

for h in u_data["holdings"]:
    f = fetch_fund_data(h['code'], data_src)
    if f:
        mv = h['shares'] * f['gz']
        dp = h['shares'] * (f['gz'] - f['nj'])
        tp = h['shares'] * (f['gz'] - h['cost'])
        tr = (f['gz'] - h['cost']) / h['cost'] * 100 if h['cost'] > 0 else 0
        funds.append({**h, **f, "mv": mv, "dp": dp, "tp": tp, "tr": tr})
        total_v += mv
        total_dp += dp

st.markdown(f"""<div class="summary-bar">
    <div><div class="sum-lab">我的总资产</div><div class="sum-val">¥{total_v:,.2f}</div></div>
    <div style="text-align:right;"><div class="sum-lab">今日盈亏预估</div><div class="sum-val {"up" if total_dp >= 0 else "down"}">{total_dp:+,.2f}</div></div>
</div>""", unsafe_allow_html=True)

# 4. 列表渲染
st.markdown('<div style="height:8px; background:#f5f5f5;"></div>', unsafe_allow_html=True)
for f in funds:
    d_clr = "up" if f['dp'] >= 0 else "down"
    t_clr = "up" if f['tp'] >= 0 else "down"
    st.markdown(f"""
    <div class="f-row">
        <div class="f-left"><div class="f-name">{f['name']}</div><div class="gray-sub">{f['code']} · {f.get('channel','默认')}</div></div>
        <div class="f-mid"><div class="{d_clr}" style="font-weight:bold; font-size:1.1rem;">{f['ratio']:+.2f}%</div><div class="gray-sub">估 {f['gz']:.4f}</div></div>
        <div class="f-right"><div class="f-val {d_clr}" style="font-weight:500;">{f['dp']:+,.2f}</div><div class="gray-sub {t_clr}">持有: {f['tp']:+,.2f}</div></div>
    </div>
    """, unsafe_allow_html=True)

# 5. 智能调仓管理
st.markdown("<br>", unsafe_allow_html=True)
with st.expander("💼 资产增减仓 (自动计算新成本)"):
    m_code = st.text_input("输入基金代码", key="m_code")
    target = next((i for i in u_data["holdings"] if i['code'] == m_code), None)
    
    if target:
        st.success(f"匹配持仓：{target['shares']}份，成本 {target['cost']:.4f}")
        m_mode = st.radio("交易动作", ["加仓 (买入)", "减仓 (卖出)"], horizontal=True)
    else:
        m_mode = "加仓 (买入)"
    
    c1, c2, c3 = st.columns(3)
    m_s = c1.number_input("变动份额", value=None, key="m_s")
    m_p = c2.number_input("变动单价", value=None, format="%.4f", key="m_p")
    m_c = c3.selectbox("渠道", ["支付宝", "招商银行", "天天基金", "其他"], key="m_c")
    
    if st.button("同步至资产库", type="primary"):
        if m_code and m_s:
            if target:
                if "加仓" in m_mode:
                    new_total = target['shares'] + m_s
                    target['cost'] = (target['shares'] * target['cost'] + m_s * m_p) / new_total
                    target['shares'] = new_total
                else:
                    target['shares'] = max(0, target['shares'] - m_s)
                target['channel'] = m_c
            else:
                u_data["holdings"].append({"code": m_code, "shares": m_s, "cost": m_p or 0.0, "channel": m_c})
            
            save_db(st.session_state.db); st.cache_data.clear(); st.rerun()

with st.expander("🗑️ 快捷管理"):
    for i, h in enumerate(u_data["holdings"]):
        cx, cy = st.columns([4, 1])
        cx.write(f"**{h['code']}** | {h['shares']} 份 | 成本 {h['cost']:.4f}")
        if cy.button("删除", key=f"del_{i}"):
            u_data["holdings"].pop(i); save_db(st.session_state.db); st.rerun()
