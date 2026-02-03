import streamlit as st
from datetime import datetime
import json
import os
import urllib.request
import ssl
import re
import pytz

# --- 基础配置 ---
TZ = pytz.timezone('Asia/Shanghai')
USER_CONFIG_FILE = "user_config.json"
ssl_ctx = ssl._create_unverified_context()

st.set_page_config(page_title="资产管理 Pro - 精准版", layout="wide", initial_sidebar_state="expanded")

# --- 综合样式 ---
st.markdown("""
<style>
    .main { padding: 0.1rem !important; }
    .summary-card { background: #212529; color: white; padding: 15px; border-radius: 12px; margin-bottom: 12px; text-align: center; }
    .summary-grid { display: flex; justify-content: space-around; margin-top: 10px; }
    .gold-row { display: flex; gap: 6px; margin-bottom: 12px; }
    .gold-box { flex: 1; background: #fff9e6; padding: 8px 4px; border-radius: 8px; text-align: center; border: 1px solid #f0e6cc; }
    .gold-price { font-size: 1.1rem; font-weight: bold; color: #b8860b; }
    .fund-card { background: white; padding: 12px; margin-bottom: 10px; border-radius: 10px; border: 1px solid #eee; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }
    .up { color: #e03131 !important; font-weight: bold; }
    .down { color: #2f9e44 !important; font-weight: bold; }
    .admin-section { margin-top: 20px; padding: 15px; background: #f8f9fa; border-top: 2px solid #ddd; border-radius: 15px; }
    .input-label { text-align: right; padding-right: 10px; font-weight: bold; font-size: 0.9rem; color: #333; }
</style>
""", unsafe_allow_html=True)

# --- 核心数据接口：兼容估值与净值 ---
def fetch_fund_data_smart(code):
    try:
        url = f"http://fund.eastmoney.com/{code}.html"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10, context=ssl_ctx) as res:
            content = res.read().decode('utf-8')
            
            # 1. 提取基金名称
            name_match = re.search(r'<div class="fundDetail-tit">([^<]+)<span>', content)
            name = name_match.group(1) if name_match else "未知基金"
            
            # 2. 尝试提取实时估值 (白天交易时段)
            gsz_match = re.search(r'id="gz_gsz">([^<]+)</span>', content)
            gszzl_match = re.search(r'id="gz_gszzl">([^<]+)%</span>', content)
            
            # 判断是否处于有效的估值时间内
            if gsz_match and gsz_match.group(1) != "--" and gsz_match.group(1) != "":
                price = float(gsz_match.group(1))
                rate = float(gszzl_match.group(1))
                update_time = "实时估值 " + datetime.now(TZ).strftime("%H:%M:%S")
            else:
                # 3. 提取正式单位净值 (晚上或周末收盘数据)
                # 针对红/绿不同颜色的标签进行模糊匹配
                price_match = re.search(r'<dl class="dataItem02">.*?<span class="ui-font-large.*?ui-num">([^<]+)</span>', content, re.S)
                rate_match = re.search(r'<dl class="dataItem02">.*?<span class="ui-num">([^<]+)%</span>', content, re.S)
                date_match = re.search(r'<dl class="dataItem02">.*?<p>\(([^)]+)\)</p>', content, re.S)
                
                price = float(price_match.group(1))
                rate = float(rate_match.group(1))
                update_time = date_match.group(1) if date_match else "数据确认中"

            # 4. 逻辑闭环：倒推昨价，确保收益计算与网页同步
            calc_last_p = price / (1 + rate/100)
            
            return {
                "name": name, 
                "price": price, 
                "last_p": calc_last_p, 
                "rate": rate, 
                "time": update_time
            }
    except Exception as e:
        return None

def fetch_gold():
    d = {"au": 0.0, "xau": 0.0, "cny": 0.0}
    try:
        url = "http://hq.sinajs.cn/list=gds_AU9999,hf_XAU,fx_susdcnh"
        req = urllib.request.Request(url, headers={'Referer': 'http://finance.sina.com.cn'})
        with urllib.request.urlopen(req, timeout=5, context=ssl_ctx) as res:
            raw = res.read().decode('gbk')
            m1 = re.search(r'gds_AU9999="([^"]+)"', raw); m2 = re.search(r'hf_XAU="([^"]+)"', raw); m3 = re.search(r'fx_susdcnh="([^"]+)"', raw)
            if m1: d["au"] = float(m1.group(1).split(',')[0])
            if m2: d["xau"] = float(m2.group(1).split(',')[0])
            fx = float(m3.group(1).split(',')[1]) if m3 else 0
            if d["xau"] > 0 and fx > 0: d["cny"] = (d["xau"] * fx) / 31.1035
    except: pass
    return d

# --- 用户配置逻辑 ---
def load_json(p, d):
    if os.path.exists(p):
        with open(p, 'r', encoding='utf-8') as f: return json.load(f)
    return d

cfg = load_json(USER_CONFIG_FILE, {"users": ["Default"], "current": "Default"})

# --- 侧边栏 ---
with st.sidebar:
    st.subheader("👤 账号管理")
    cur_u = st.selectbox("切换用户", cfg["users"], index=cfg["users"].index(cfg["current"]))
    if cur_u != cfg["current"]:
        cfg["current"] = cur_u
        with open(USER_CONFIG_FILE, 'w') as f: json.dump(cfg, f)
        st.rerun()
    with st.expander("管理用户列表"):
        new_u = st.text_input("新增用户名")
        if st.button("确认添加") and new_u:
            cfg["users"].append(new_u)
            with open(USER_CONFIG_FILE, 'w') as f: json.dump(cfg, f)
            st.rerun()
    st.divider()
    st.caption("🥛 晚上睡前一小时记得喝杯热牛奶")

# --- 主界面 ---
db_path = f"db_{cur_u}.json"
db = load_json(db_path, {"holdings": []})

col_h1, col_h2 = st.columns([3, 1])
with col_h1: st.subheader(f"📊 {cur_u} 的资产看板")
with col_h2: 
    if st.button("🔄 刷新行情", type="primary", use_container_width=True): st.rerun()

# 黄金板块
g = fetch_gold()
st.markdown(f"""
<div class="gold-row">
    <div class="gold-box">上海金<br><span class="gold-price">¥{g['au']:.2f}</span></div>
    <div class="gold-box">国际金<br><span class="gold-price">${g['xau']:.2f}</span></div>
    <div class="gold-box">折合价<br><span class="gold-price">¥{g['cny']:.2f}</span></div>
</div>
""", unsafe_allow_html=True)

# 基金列表处理
results = []
total_market = 0.0
total_day = 0.0

for h in db["holdings"]:
    f = fetch_fund_data_smart(h['code'])
    if f:
        shares = float(h['shares'])
        cost = float(h['cost'])
        day_p = shares * (f['price'] - f['last_p'])
        total_p = shares * (f['price'] - cost)
        m_val = shares * f['price']
        
        total_market += m_val
        total_day += day_p
        results.append({**h, **f, "day_p": day_p, "total_p": total_p, "m_val": m_val})

# 总计卡片
p_color = "up" if total_day >= 0 else "down"
st.markdown(f"""
<div class="summary-card">
    <div style="font-size:0.8rem; opacity:0.8">预估总市值 (CNY)</div>
    <div style="font-size:1.8rem; font-weight:bold">¥{total_market:,.2f}</div>
    <div class="summary-grid">
        <div>今日盈亏<br><span class="{p_color}">{total_day:+.2f}</span></div>
        <div>持仓基金<br><span>{len(results)} 支</span></div>
    </div>
</div>
""", unsafe_allow_html=True)

# 基金卡片展示
for f in results:
    r_cls = "up" if f['rate'] >= 0 else "down"
    t_cls = "up" if f['total_p'] >= 0 else "down"
    st.markdown(f"""
    <div class="fund-card">
        <div style="display:flex; justify-content:space-between">
            <b>{f['name']}</b> 
            <small style="color:#888">{f['code']}</small>
            <span style="font-size:0.7rem; color:#999">{f['time']}</span>
        </div>
        <div style="display:flex; justify-content:space-between; text-align:center; margin-top:8px;">
            <div style="flex:1">当前价格<br><span class="{r_cls}">{f['price']:.4f}</span><br><span class="{r_cls}" style="font-size:0.7rem">{f['rate']:+.2f}%</span></div>
            <div style="flex:1">今日盈亏<br><span class="{r_cls}">{f['day_p']:+.2f}</span></div>
            <div style="flex:1">累计盈亏<br><span class="{t_cls}">{f['total_p']:+.2f}</span></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# 管理持仓：输入框默认为 None，点开即清空
st.markdown('<div class="admin-section">', unsafe_allow_html=True)
with st.expander("⚙️ 管理持仓设置", expanded=st.session_state.get('exp', True)):
    with st.form("fund_form_v5", clear_on_submit=True):
        c1, c2 = st.columns([1, 4])
        with c1: st.markdown('<div class="input-label">基金代码</div>', unsafe_allow_html=True)
        with c2: m_code = st.text_input("code_v5", max_chars=6, label_visibility="collapsed")
        
        c3, c4 = st.columns([1, 4])
        with c3: st.markdown('<div class="input-label">持有份额</div>', unsafe_allow_html=True)
        with c4: m_shares = st.number_input("shares_v5", value=None, format="%.2f", label_visibility="collapsed")
        
        c5, c6 = st.columns([1, 4])
        with c5: st.markdown('<div class="input-label">成本价格</div>', unsafe_allow_html=True)
        with c6: m_cost = st.number_input("cost_v5", value=None, format="%.4f", label_visibility="collapsed")
        
        b1, b2 = st.columns(2)
        if b1.form_submit_button("💾 保存持仓数据", type="primary", use_container_width=True):
            if m_code and m_shares is not None:
                db["holdings"] = [x for x in db["holdings"] if x["code"] != m_code]
                db["holdings"].append({"code": m_code, "shares": m_shares, "cost": m_cost if m_cost is not None else 0.0})
                with open(db_path, 'w', encoding='utf-8') as f: json.dump(db, f)
                st.rerun()
        if b2.form_submit_button("🗑️ 删除该基金", use_container_width=True):
            db["holdings"] = [x for x in db["holdings"] if x["code"] != m_code]
            with open(db_path, 'w', encoding='utf-8') as f: json.dump(db, f)
            st.rerun()
st.markdown('</div>', unsafe_allow_html=True)
