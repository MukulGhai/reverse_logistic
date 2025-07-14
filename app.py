import streamlit as st
import pandas as pd
import joblib
import os
import datetime
import hashlib
import plotly.express as px
from app_retailer import show_retailer_dashboard

st.set_page_config(page_title="Return and Earn Portal", layout="centered")

# -------------------- Load Model --------------------
model = joblib.load("random_forest_model.pkl")
label_encoder = joblib.load("label_encoder.pkl")

# -------------------- Session Setup --------------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""
if "admin_mode" not in st.session_state:
    st.session_state.admin_mode = False
if "credit_multiplier" not in st.session_state:
    st.session_state.credit_multiplier = 0.5
if "theme_mode" not in st.session_state:
    st.session_state.theme_mode = "Dark"

# -------------------- Theme Toggle --------------------
theme_choice = st.sidebar.selectbox("Theme", ["Light", "Dark"], index=1 if st.session_state.theme_mode == "Dark" else 0)
st.session_state.theme_mode = theme_choice

if theme_choice == "Dark":
    st.markdown("""
    <style>
    body, .stApp {
        background-color: #181818 !important;
        color: #f1f1f1 !important;
    }
    .stButton>button, .stTextInput>div>input, .stSelectbox>div>div>div>input, .stNumberInput>div>input,
    .stTextArea>div>textarea, .stDateInput input, .stTimeInput input {
        background-color: #222 !important;
        color: #f1f1f1 !important;
        border: 1px solid #444 !important;
    }
    .stDataFrame, .stTable {
        background-color: #1e1e1e !important;
        color: #f1f1f1 !important;
    }
    </style>
    """, unsafe_allow_html=True)
else:
    st.markdown("""
    <style>
    body, .stApp {
        background-color: #ffffff !important;
        color: #111111 !important;
    }
    .stButton>button, .stTextInput>div>input, .stSelectbox>div>div>div>input, .stNumberInput>div>input,
    .stTextArea>div>textarea, .stDateInput input, .stTimeInput input {
        background-color: #f9f9f9 !important;
        color: #111111 !important;
        border: 1px solid #ccc !important;
    }
    .stDataFrame, .stTable {
        background-color: #fdfdfd !important;
        color: #111111 !important;
    }
    </style>
    """, unsafe_allow_html=True)


# -------------------- Auth Helpers --------------------
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def load_users():
    if os.path.exists("users.csv"):
        return pd.read_csv("users.csv")
    else:
        return pd.DataFrame(columns=["username", "password"])

def save_user(username, password):
    users = load_users()
    new_user = pd.DataFrame([{"username": username, "password": hash_password(password)}])
    users = pd.concat([users, new_user], ignore_index=True)
    users.to_csv("users.csv", index=False)

def check_user(username, password):
    users = load_users()
    return ((users["username"] == username) & (users["password"] == hash_password(password))).any()

# -------------------- Navigation --------------------
page = st.sidebar.selectbox("Navigate", ["Home", "Profile", "🔒 Admin Login"])

if st.sidebar.button("Logout"):
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.admin_mode = False
    st.rerun()

# -------------------- Admin Login --------------------
if page == "🔒 Admin Login":
    st.title("🔐 Admin Login")
    passcode = st.text_input("Enter Admin Passcode", type="password")
    if st.button("Login as Admin"):
        if passcode == "admin123":
            st.session_state.admin_mode = True
            st.success("✅ Access Granted")
            show_retailer_dashboard()
            st.stop()
        else:
            st.error("❌ Incorrect Passcode")

elif st.session_state.admin_mode:
    st.title("🛠️ Retailer Dashboard")
    show_retailer_dashboard()
    st.stop()

# -------------------- Home Page --------------------
elif page == "Home":
    st.title("♻️ Return and Earn Portal")

    if not st.session_state.logged_in:
        st.subheader("🔐 Login / Register")
        auth_mode = st.radio("Choose an option:", ["Login", "Register"])
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")

        if auth_mode == "Register":
            if st.button("Register"):
                users = load_users()
                if username in users["username"].values:
                    st.error("Username already exists.")
                elif username and password:
                    save_user(username, password)
                    st.success("Registered successfully! Please login.")
                else:
                    st.warning("Enter username and password.")
        else:
            if st.button("Login"):
                if check_user(username, password):
                    st.session_state.logged_in = True
                    st.session_state.username = username
                    st.success("Logged in successfully!")
                    st.rerun()
                else:
                    st.error("Invalid credentials.")
        st.stop()

    st.success(f"Welcome, {st.session_state.username}! 👋")
    st.header("📦 Product Return Form")

    item_name = st.text_input("Item Name")
    condition = st.selectbox("Condition", ["New", "Good", "Fair", "Poor"])
    days_used = st.number_input("Days Used", min_value=0, step=1)
    pickup_date = st.date_input("Preferred Pickup Date", min_value=datetime.date.today())
    pickup_time = st.time_input("Preferred Pickup Time")

    if st.button("🚀 Submit Return"):
        if item_name and condition:
            try:
                condition_encoded = label_encoder.transform([condition])[0]
                input_df = pd.DataFrame([[condition_encoded, days_used]], columns=["condition_encoded", "days_used"])
                score = model.predict(input_df)[0]
                credit = round(score * st.session_state.credit_multiplier)
                action = "RRR" if score <= 33 else "Repair" if score <= 66 else "Resell"

                log_data = pd.DataFrame([{
                    "Username": st.session_state.username,
                    "Product Name": item_name,
                    "Condition": condition,
                    "Days Used": days_used,
                    "Score": round(score, 2),
                    "Credit Earned": credit,
                    "action": action,
                    "Time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "Pickup Date": str(pickup_date),
                    "Pickup Time": str(pickup_time)
                }])

                if os.path.exists("return_logs.csv"):
                    log_data.to_csv("return_logs.csv", mode='a', header=False, index=False)
                else:
                    log_data.to_csv("return_logs.csv", index=False)

                st.success(f"✅ Return submitted for '{item_name}'!")
                st.info(f"💸 Credit Earned: {credit} GreenPoints")
                st.balloons()

            except Exception as e:
                st.error(f"Something went wrong: {e}")
        else:
            st.warning("Please complete all fields.")

# -------------------- Profile Page --------------------
elif page == "Profile":
    if not st.session_state.logged_in:
        st.warning("Please login to view your profile.")
        st.stop()

    st.title(f"👤 Profile: {st.session_state.username}")
    st.subheader("📦 Your Return History")

    try:
        df = pd.read_csv("return_logs.csv")
        user_df = df[df["Username"] == st.session_state.username]
        st.dataframe(
            user_df[
                ["Product Name", "Condition", "Days Used", "Score", "Credit Earned",
                 "action", "Pickup Date", "Pickup Time", "Time"]
            ].sort_values("Time", ascending=False),
            use_container_width=True
        )
    except Exception as e:
        st.info("No return history found.")

    st.subheader("📊 Your Outcome Distribution")
    try:
        user_df["Category"] = user_df["Score"].apply(
            lambda s: "Recycle" if s <= 33 else "Repair" if s <= 66 else "Resell"
        )
        pie_fig = px.pie(user_df, names="Category", title="Your Return Classification")
        st.plotly_chart(pie_fig)
    except Exception:
        st.info("Not enough data to display pie chart.")

    st.subheader("🏆 Leaderboard")
    try:
        leaderboard = df.groupby("Username")["Credit Earned"].sum().reset_index().sort_values("Credit Earned", ascending=False).head(10)
        st.table(leaderboard.rename(columns={"Credit Earned": "Total Credits"}))
    except:
        st.info("Leaderboard not available.")

    st.subheader("🌿 Total Credits Earned")
    try:
        total_credits = user_df["Credit Earned"].sum()
        st.success(f"You've earned {total_credits} GreenPoints so far! 🌟")
    except:
        st.info("No credits earned yet.")
