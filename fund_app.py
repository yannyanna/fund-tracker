import streamlit as st
import json
import os
import urllib.request
import ssl

# 1. 基础配置
ssl_ctx = ssl._create_unverified_context()
DATA_FILE = "fund_db.json"

# 2. 读写函数（最原始的文件操作，确保不丢数据）
def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

if not os.path.exists(DATA_FILE):
    save_data({"Default": []})

with open(DATA_FILE, "r", encoding="utf-8") as f:
    db = json.load(f)

# 3. 侧边栏：用户管理
user_list = list(db.keys())
st.sidebar.title("账户管理")
new_user = st.sidebar.text_input("新建用户")
if st.sidebar.button("创建"):
    if new_user and new_user not in db:
        db[new_user] = []
        save_data(db)
        st.rerun()

curr_user = st.sidebar.selectbox("当前账户", user_list)

# 4. 刷新按钮（只触发页面重跑，不删任何东西）
if st.button("🔄 刷新"):
    st.rerun()

# 5. 黄金报价
try:
    with urllib.request.urlopen("http://hq.sinajs.cn/list=gds_AU9999", timeout=3, context=ssl_ctx) as res:
        g = res.read().decode('gbk').split('"')[1].split(',')
        st.metric("黄金价格 (AU9999)", f"¥{g[0]}", f"时间: {g[5]}")
except:
    st.warning("黄金行情获取失败")

# 6. 基金列表与计算
st.subheader(f"📊 {curr_user} 的持仓明细")
total_v, total_p = 0.0, 0.0

for i, h in enumerate(db[curr_user]):
    try:
        url = f"http://fundgz.1234567.com.cn/js/{h['code']}.js"
        with urllib.request.urlopen(url, timeout=3, context=ssl_ctx) as res:
            d = json.loads(res.read().decode('utf-8').split('(')[1].split(')')[0])
            price = float(d['gsz'])
            prev = float(d['dwjz'])
            
            mv = h['shares'] * price
            dp = h['shares'] * (price - prev)
            total_v += mv
            total_dp = h['shares'] * (price - prev)
            total_p += dp
            
            # 显示每一行
            col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
            col1.write(f"**{d['name']}**\n{h['code']} ({d['gztime'][-8:]})")
            col2.write(f"估值: {price}")
            col3.write(f"当日: {dp:+.2f}")
            if col4.button("删除", key=f"del_{i}"):
                db[curr_user].pop(i)
                save_data(db)
                st.rerun()
    except:
        st.error(f"代码 {h['code']} 数据抓取失败")

st.divider()
st.write(f"### 总资产: ¥{total_v:,.2f} | 今日盈亏: {total_p:+,.2f}")

# 7. 添加基金（无0化处理）
with st.expander("➕ 添加新基金"):
    c_code = st.text_input("基金代码", key="add_code")
    c_shares = st.number_input("持有份额", value=None, placeholder="请输入份额")
    c_cost = st.number_input("持有成本", value=None, placeholder="请输入成本单价")
    
    if st.button("确认添加"):
        if c_code and c_shares:
            db[curr_user].append({"code": c_code, "shares": c_shares, "cost": c_cost or 0.0})
            save_data(db)
            st.rerun()
