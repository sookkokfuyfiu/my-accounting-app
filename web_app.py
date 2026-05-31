import streamlit as st
import mysql.connector
import pandas as pd

# ================= 資料庫設定 =================
# ================= 資料庫設定 =================
DB_CONFIG = {
    'host': 'gateway01.ap-northeast-1.prod.aws.tidbcloud.com',  # 例如: 'gateway01.ap-northeast-1.prod.aws.tidbcloud.com'
    'port': 4000,                      # ⚠️ 注意！這裡要改成 4000
    'user': '3BRXQtSDgidR3qL.root',      # 例如: '3BRXQtSDgidR3qL.root'
    'password': 'v2jCqCG1J9U8b3RF', # 貼上你剛剛 Generate 出來的那串密碼
    'database': 'AccountingSystem',    # 這個保持不變，因為你剛剛已經建好這個資料庫了
    'ssl_verify_cert': False,           # 🌟 雲端資料庫通常需要加密連線，加上這一行會比較穩！
    'ssl_verify_identity': False
}

def execute_db(sql, values=None, fetchall=False, fetchone=False):
    conn = None
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(buffered=True)
        cursor.execute(sql, values)
        if fetchall:
            return cursor.fetchall()
        elif fetchone:
            return cursor.fetchone()
        else:
            conn.commit()
            return True
    except mysql.connector.Error as e:
        st.error(f"資料庫錯誤：{e}")
        return False
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

# ================= 網頁設定與狀態管理 =================
st.set_page_config(page_title="雲端記帳系統", page_icon="💰", layout="centered")

# 使用 session_state 來記住使用者是不是已經登入了
if 'user_id' not in st.session_state:
    st.session_state.user_id = None
if 'user_name' not in st.session_state:
    st.session_state.user_name = None

# ================= 介面：尚未登入 =================
if st.session_state.user_id is None:
    st.title("💰 歡迎來到雲端記帳系統")
    
    # 建立兩個頁籤：登入 和 註冊
    tab_login, tab_register = st.tabs(["🚪 登入", "📝 註冊"])
    
    with tab_login:
        st.subheader("登入你的帳號")
        login_name = st.text_input("使用者名稱")
        login_password = st.text_input("密碼", type="password")
    
        if st.button("進入系統"):
            user = execute_db("SELECT `使用者ID`, `使用者名稱` FROM `使用者` WHERE `使用者名稱` = %s AND `密碼` = %s", (login_name, login_password), fetchone=True)
        
            if user:
                st.session_state['logged_in'] = True
                st.session_state['user_id'] = user[0]
                st.session_state['user_name'] = user[1]
                st.success(f"歡迎回來，{user[1]}！")
                st.rerun()
            else:
                st.error("帳號或密碼錯誤，請再試一次！")
                    
    with tab_register:
        st.subheader("建立新帳號")
        reg_name = st.text_input("設定使用者名稱", key="reg_name")
        reg_password = st.text_input("設定密碼", type="password", key="reg_password")
        reg_email = st.text_input("設定電子信箱", key="reg_email")

        if st.button("註冊帳號"):
            if not reg_name or not reg_password or not reg_email:
                st.warning("名稱、密碼和信箱都必須填寫！")
        else:
            if execute_db("INSERT INTO `使用者` (`使用者名稱`, `密碼`, `信箱`) VALUES (%s, %s, %s)", (reg_name, reg_password, reg_email)):
                st.success(f"使用者「{reg_name}」註冊成功！請切換到登入頁籤登入。")
# ================= 介面：已登入主畫面 =================
else:
    # 側邊欄 (Sidebar) 設計
    with st.sidebar:
        st.write(f"👤 **{st.session_state.user_name}**，你好！")
        if st.button("🚪 登出系統"):
            st.session_state.user_id = None
            st.session_state.user_name = None
            st.rerun()

    st.title("📊 我的財務儀表板")
    
    # 建立功能頁籤
    tab_record, tab_balance, tab_settings = st.tabs(["💰 新增交易", "📈 帳戶餘額", "⚙️ 帳戶與類別設定"])
    
    # --- 頁籤 1：新增交易 ---
    with tab_record:
        st.subheader("記一筆帳")
        accounts = execute_db("SELECT `帳戶ID`, `帳戶名稱` FROM `帳戶` WHERE `使用者ID` = %s", (st.session_state.user_id,), fetchall=True)
        categories = execute_db("SELECT `類別ID`, `類別名稱` FROM `交易類別` WHERE `使用者ID` = %s", (st.session_state.user_id,), fetchall=True)
        
        if not accounts or not categories:
            st.warning("⚠️ 請先到「帳戶與類別設定」建立至少一個帳戶與一個類別才能開始記帳喔！")
        else:
            acc_dict = {f"{a[1]}": a[0] for a in accounts}
            cat_dict = {f"{c[1]}": c[0] for c in categories}
            
            col1, col2 = st.columns(2)
            with col1:
                sel_acc = st.selectbox("選擇帳戶", list(acc_dict.keys()))
                sel_type = st.selectbox("交易類型", ["支出", "收入"])
            with col2:
                sel_cat = st.selectbox("選擇類別", list(cat_dict.keys()))
                amount = st.number_input("輸入金額", min_value=0, value=0, step=10)
                
            if st.button("送出紀錄", type="primary", use_container_width=True):
                if amount <= 0:
                    st.error("金額必須大於 0！")
                else:
                    acc_id, cat_id = acc_dict[sel_acc], cat_dict[sel_cat]
                    sql_insert = "INSERT INTO `交易紀錄` (`帳戶ID`, `類別ID`, `交易類型`, `金額`) VALUES (%s, %s, %s, %s)"
                    if execute_db(sql_insert, (acc_id, cat_id, sel_type, amount)):
                        # 更新餘額
                        if sel_type == "支出":
                            execute_db("UPDATE `帳戶` SET `目前餘額` = `目前餘額` - %s WHERE `帳戶ID` = %s", (amount, acc_id))
                        else:
                            execute_db("UPDATE `帳戶` SET `目前餘額` = `目前餘額` + %s WHERE `帳戶ID` = %s", (amount, acc_id))
                        st.success("記帳成功！餘額已同步更新。")

    # --- 頁籤 2：帳戶餘額 ---
    with tab_balance:
        st.subheader("目前各帳戶餘額")
        balances = execute_db("SELECT `帳戶名稱`, `目前餘額` FROM `帳戶` WHERE `使用者ID` = %s", (st.session_state.user_id,), fetchall=True)
        if balances:
            # 使用 pandas 把資料變成漂亮的網頁表格
            df = pd.DataFrame(balances, columns=["帳戶名稱", "目前餘額 (元)"])
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("目前沒有任何帳戶資料。")

    # --- 頁籤 3：設定 ---
    with tab_settings:
        st.subheader("建立新帳戶 (錢包)")
        new_acc_name = st.text_input("帳戶名稱 (如: 現金)", key="new_acc")
        new_acc_bal = st.number_input("初始餘額", value=0, key="new_bal")
        if st.button("新增帳戶"):
            if new_acc_name:
                execute_db("INSERT INTO `帳戶` (`帳戶名稱`, `目前餘額`, `使用者ID`) VALUES (%s, %s, %s)", (new_acc_name, new_acc_bal, st.session_state.user_id))
                st.success(f"帳戶「{new_acc_name}」建立成功！")
                
        st.divider() # 分隔線
        
        st.subheader("建立新類別 (標籤)")
        new_cat_name = st.text_input("類別名稱 (如: 餐飲)", key="new_cat")
        new_cat_type = st.selectbox("類型", ["支出", "收入"], key="new_cat_type")
        if st.button("新增類別"):
            if new_cat_name:
                execute_db("INSERT INTO `交易類別` (`類別名稱`, `類別類型`, `使用者ID`) VALUES (%s, %s, %s)", (new_cat_name, new_cat_type, st.session_state.user_id))
                st.success(f"類別「{new_cat_name}」建立成功！")
