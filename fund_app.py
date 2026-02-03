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
DATA_FILE = "fund_tracker.json"
BACKUP_FILE = "fund_tracker.json.bak"
ssl_ctx = ssl._create_unverified_context()

st.set_page_config(page_title="资产追踪", layout="wide")

# --- 样式优化 ---
st.markdown("""
<style>
    .main { padding: 0rem !important; }
    .refresh-bar { display: flex; justify-content: space-between; align-items: center; padding: 10px 20px; background: #f8f9fa; border-bottom: 1px solid #dee2e6; margin-bottom: 20px; }
    .update-time { font-size: 0.85rem; color: #6c757d; }
    .gold-container { display: flex; gap: 20px; margin-bottom: 25px; }
    .gold-box { flex: 1; background: linear-gradient(135deg, #fffdf2 0%, #fff9e6 100%); padding: 20px; border-radius: 12px; text-align: center; border: 1px solid #f0e6cc; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .gold-title { font-size: 0.85rem; color: #856404; margin-bottom: 8px; font-weight: 500; }
    .gold-price { font-size: 2rem; font-weight: bold; color: #b8860b; margin: 5px 0; }
    .gold-sub { font-size: 0.8rem; color: #997; margin-top: 5px; }
    .fund-card { background: white; padding: 15px 20px; margin-bottom: 12px; border-radius: 10px; border: 1px solid #e9ecef; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }
    .fund-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
    .fund-name { font-size: 1.1rem; font-weight: 600; color: #212529; }
    .fund-code { font-size: 0.8rem; color: #6c757d; background: #f8f9fa; padding: 2px 8px; border-radius: 12px; }
    .fund-grid { display: grid; grid-template-columns: 1fr 1fr 1fr 1fr; gap: 15px; text-align: center; }
    .fund-item { padding: 10px; background: #f8f9fa; border-radius: 8px; }
    .fund-label { font-size: 0.75rem; color: #6c757d; margin-bottom: 4px; }
    .fund-value { font-size: 1.1rem; font-weight: 600; }
    .up { color: #dc3545; }
    .down { color: #28a745; }
    .input-group { display: flex; gap: 10px; align-items: end; margin-bottom: 15px; }
    .stButton>button { border-radius: 20px; }
</style>
""", unsafe_allow_html=True)

# --- 数据持久化 ---
def load_db():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"holdings": []}

def save_db(data):
    # 自动备份
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            with open(BACKUP_FILE, 'w', encoding='utf-8') as bf:
                bf.write(f.read())
    
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# --- 数据获取 ---
def fetch_data():
    """获取黄金和汇率数据，返回字典"""
    result = {
        "au9999": 0.0,      # 国内黄金 元/克
        "xau_usd": 0.0,     # 国际黄金 美元/盎司
        "usdcny": 0.0,      # 汇率
        "xau_cny": 0.0,     # 国际黄金换算后 元/克
        "update_time": datetime.now(TZ).strftime("%m-%d %H:%M:%S"),
        "error": None
    }
    
    try:
        # 批量请求：国内黄金 + 国际黄金 + 汇率
        codes = "gds_AU9999,hf_XAU,fx_susdcnh"
        url = f"http://hq.sinajs.cn/list={codes}"
        req = urllib.request.Request(url, headers={'Referer': 'http://finance.sina.com.cn'})
        
        with urllib.request.urlopen(req, timeout=5, context=ssl_ctx) as res:
            data = res.read().decode('gbk')
            
            # 解析国内黄金 AU9999
            if 'gds_AU9999' in data:
                match = re.search(r'gds_AU9999="([^"]+)"', data)
                if match:
                    result["au9999"] = float(match.group(1).split(',')[0])
            
            # 解析国际黄金 XAU
            if 'hf_XAU' in data:
                match = re.search(r'hf_XAU="([^"]+)"', data)
                if match:
                    parts = match.group(1).split(',')
                    result["xau_usd"] = float(parts[0])  # 最新价
            
            # 解析汇率 USDCNH
            if 'fx_susdcnh' in data:
                match = re.search(r'fx_susdcnh="([^"]+)"', data)
                if match:
                    parts = match.group(1).split(',')
                    result["usdcny"] = float(parts[1])  # 买入价作为参考
            
            # 换算国际黄金为人民币/克
            if result["xau_usd"] > 0 and result["usdcny"] > 0:
                result["xau_cny"] = (result["xau_usd"] * result["usdcny"]) / 31.1034768
                
    except Exception as e:
        result["error"] = str(e)
    
    return result

def fetch_fund_data(code):
    """获取单个基金数据"""
    try:
        url = f"http://fundgz.1234567.com.cn/js/{code}.js"
        req = urllib.request.Request(url, headers={'Referer': 'http://fund.eastmoney.com'})
        
        with urllib.request.urlopen(req, timeout=5, context=ssl_ctx) as res:
            content = res.read().decode('utf-8')
            # 解析 jsonpgz({"name":"...","fundcode":"...","jzrq":"...","dwjz":"...","gsz":"...","gszzl":"...","gztime":"..."});
            json_str = content[content.find('{'):content.rfind('}')+1]
            data = json.loads(json_str)
            
            return {
                "name": data.get("name", "未知"),
                "code": data.get("fundcode", code),
                "nav": float(data.get("dwjz", 0)),      # 昨日净值
                "estimate": float(data.get("gsz", 0)),   # 实时估值
                "change_pct": float(data.get("gszzl", 0)), # 涨跌幅%
                "time": data.get("gztime", "--")
            }
    except Exception:
        return None

# --- 初始化 ---
if 'db' not in st.session_state:
    st.session_state.db = load_db()
if 'gold_data' not in st.session_state:
    st.session_state.gold_data = None
if 'fund_cache' not in st.session_state:
    st.session_state.fund_cache = {}
if 'last_refresh' not in st.session_state:
    st.session_state.last_refresh = None

# --- 顶部刷新栏 ---
col1, col2 = st.columns([1, 3])
with col1:
    if st.button("🔄 刷新数据", type="primary", use_container_width=True):
        with st.spinner("获取数据中..."):
            # 获取黄金数据
            st.session_state.gold_data = fetch_data()
            # 清空基金缓存（强制重新获取）
            st.session_state.fund_cache = {}
            st.session_state.last_refresh = datetime.now(TZ).strftime("%m-%d %H:%M:%S")
        st.rerun()

with col2:
    if st.session_state.last_refresh:
        st.markdown(f'<div class="refresh-bar"><span class="update-time">最后更新: {st.session_state.last_refresh}</span></div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="refresh-bar"><span class="update-time">点击左侧按钮刷新数据</span></div>', unsafe_allow_html=True)

# --- 黄金数据显示 ---
st.subheader("💰 黄金行情")
gold = st.session_state.gold_data

if gold and not gold.get("error"):
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown(f"""
        <div class="gold-box">
            <div class="gold-title">上海黄金 AU9999</div>
            <div class="gold-price">¥{gold['au9999']:.2f}</div>
            <div class="gold-sub">元/克</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="gold-box">
            <div class="gold-title">国际现货黄金</div>
            <div class="gold-price">${gold['xau_usd']:.2f}</div>
            <div class="gold-sub">美元/盎司 | 汇率:{gold['usdcny']:.4f}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="gold-box">
            <div class="gold-title">国际黄金(换算)</div>
            <div class="gold-price">¥{gold['xau_cny']:.2f}</div>
            <div class="gold-sub">元/克 (理论值)</div>
        </div>
        """, unsafe_allow_html=True)
else:
    st.info("点击刷新按钮获取黄金数据")

# --- 基金管理 ---
st.markdown("---")
st.subheader("📊 基金持仓")

# 添加基金
with st.expander("➕ 添加/修改持仓"):
    col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
    
    with col1:
        new_code = st.text_input("基金代码", max_chars=6, key="new_code", 
                                placeholder="输入6位数字")
        # 自动显示基金名称
        fund_name_preview = ""
        if new_code and len(new_code) == 6 and new_code.isdigit():
            # 检查缓存或实时获取名称
            if new_code in st.session_state.fund_cache:
                fund_name_preview = st.session_state.fund_cache[new_code].get("name", "")
            else:
                with st.spinner(""):
                    fund_info = fetch_fund_data(new_code)
                    if fund_info:
                        fund_name_preview = fund_info["name"]
                        st.session_state.fund_cache[new_code] = fund_info
        
        if fund_name_preview:
            st.caption(f"📌 {fund_name_preview}")
    
    with col2:
        new_shares = st.number_input("持有份额", min_value=0.0, format="%.2f", 
                                    key="new_shares", placeholder="0.00")
    
    with col3:
        new_cost = st.number_input("成本价(元)", min_value=0.0, format="%.4f", 
                                  key="new_cost", step=0.0001, placeholder="0.0000")
    
    with col4:
        st.write("")
        st.write("")
        if st.button("添加", type="primary"):
            if not (new_code and len(new_code) == 6 and new_code.isdigit()):
                st.error("请输入6位数字基金代码")
            elif new_shares <= 0:
                st.error("份额必须大于0")
            elif new_cost <= 0:
                st.error("成本价必须大于0")
            else:
                # 检查是否已存在
                existing = next((i for i, h in enumerate(st.session_state.db["holdings"]) 
                               if h["code"] == new_code), None)
                
                if existing is not None:
                    # 更新现有持仓（移动平均）
                    old = st.session_state.db["holdings"][existing]
                    total_shares = old["shares"] + new_shares
                    old["cost"] = (old["shares"] * old["cost"] + new_shares * new_cost) / total_shares
                    old["shares"] = total_shares
                    st.success(f"已加仓 {new_code}，新成本价: ¥{old['cost']:.4f}")
                else:
                    st.session_state.db["holdings"].append({
                        "code": new_code,
                        "name": fund_name_preview or f"基金{new_code}",
                        "shares": new_shares,
                        "cost": new_cost
                    })
                    st.success(f"已添加 {new_code}")
                
                save_db(st.session_state.db)
                st.rerun()

# 显示持仓列表
if not st.session_state.db["holdings"]:
    st.info("暂无持仓，点击上方添加")
else:
    total_market_value = 0.0
    total_day_profit = 0.0
    total_total_profit = 0.0
    
    for idx, holding in enumerate(st.session_state.db["holdings"]):
        code = holding["code"]
        
        # 获取实时数据（优先用缓存）
        if code not in st.session_state.fund_cache:
            with st.spinner(f"获取{code}..."):
                st.session_state.fund_cache[code] = fetch_fund_data(code)
        
        fund_data = st.session_state.fund_cache.get(code)
        
        if fund_data:
            # 计算收益
            market_value = holding["shares"] * fund_data["estimate"]
            day_profit = holding["shares"] * (fund_data["estimate"] - fund_data["nav"])
            total_profit = holding["shares"] * (fund_data["estimate"] - holding["cost"])
            total_return = ((fund_data["estimate"] - holding["cost"]) / holding["cost"] * 100) if holding["cost"] > 0 else 0
            
            total_market_value += market_value
            total_day_profit += day_profit
            total_total_profit += total_profit
            
            # 颜色判断
            day_color = "up" if day_profit >= 0 else "down"
            total_color = "up" if total_profit >= 0 else "down"
            change_color = "up" if fund_data["change_pct"] >= 0 else "down"
            
            st.markdown(f"""
            <div class="fund-card">
                <div class="fund-header">
                    <div>
                        <span class="fund-name">{fund_data["name"]}</span>
                        <span class="fund-code">{code}</span>
                    </div>
                    <div style="font-size: 0.8rem; color: #6c757d;">
                        估值时间: {fund_data["time"]}
                    </div>
                </div>
                <div class="fund-grid">
                    <div class="fund-item">
                        <div class="fund-label">实时估值</div>
                        <div class="fund-value">{fund_data["estimate"]:.4f}</div>
                    </div>
                    <div class="fund-item">
                        <div class="fund-label">涨跌幅</div>
                        <div class="fund-value {change_color}">{fund_data["change_pct"]:+.2f}%</div>
                    </div>
                    <div class="fund-item">
                        <div class="fund-label">当日预估</div>
                        <div class="fund-value {day_color}">{day_profit:+.2f}</div>
                    </div>
                    <div class="fund-item">
                        <div class="fund-label">持有收益</div>
                        <div class="fund-value {total_color}">{total_profit:+.2f} ({total_return:+.2f}%)</div>
                    </div>
                </div>
                <div style="margin-top: 10px; font-size: 0.8rem; color: #6c757d; text-align: right;">
                    持仓: {holding["shares"]:.2f}份 | 成本: ¥{holding["cost"]:.4f} | 市值: ¥{market_value:.2f}
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # 删除按钮
            if st.button(f"🗑️ 删除", key=f"del_{idx}"):
                st.session_state.db["holdings"].pop(idx)
                save_db(st.session_state.db)
                st.rerun()
        else:
            st.error(f"无法获取 {code} 的数据，请检查代码是否正确")
    
    # 汇总栏
    if total_market_value > 0:
        st.markdown("---")
        sum_color = "up" if total_day_profit >= 0 else "down"
        st.markdown(f"""
        <div style="display: flex; justify-content: space-between; padding: 20px; background: #f8f9fa; border-radius: 10px; margin-top: 20px;">
            <div style="text-align: center; flex: 1;">
                <div style="font-size: 0.85rem; color: #6c757d;">总市值</div>
                <div style="font-size: 1.5rem; font-weight: bold;">¥{total_market_value:,.2f}</div>
            </div>
            <div style="text-align: center; flex: 1;">
                <div style="font-size: 0.85rem; color: #6c757d;">当日预估收益</div>
                <div style="font-size: 1.5rem; font-weight: bold;" class="{sum_color}">{total_day_profit:+,.2f}</div>
            </div>
            <div style="text-align: center; flex: 1;">
                <div style="font-size: 0.85rem; color: #6c757d;">累计收益</div>
                <div style="font-size: 1.5rem; font-weight: bold;" class="{sum_color}">{total_total_profit:+,.2f}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
