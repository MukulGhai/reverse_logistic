import streamlit as st
import pandas as pd
import joblib
import os
import datetime
import hashlib
import plotly.express as px
from app_retailer import show_retailer_dashboard
from offer_page import show_offer_page

st.set_page_config(page_title="Return and Earn Portal", layout="wide")

# ----------- Load ML Model ----------
model = joblib.load("random_forest_model.pkl")
label_encoder = joblib.load("label_encoder.pkl")

# ----------- Session Initialization ----------
default_state = {
    "logged_in": False,
    "username": "",
    "user_email": "",
    "admin_mode": False,
    "credit_multiplier": 0.5,
    "theme_mode": "Dark"
}
for key, val in default_state.items():
    if key not in st.session_state:
        st.session_state[key] = val

# ----------- Theme Toggle ----------
theme = st.sidebar.selectbox("Theme", ["Light", "Dark"], index=1 if st.session_state.theme_mode == "Dark" else 0)
st.session_state.theme_mode = theme
st.markdown(
    f"""
    <style>
        body, .stApp {{
            background-color: {'#181818' if theme == 'Dark' else '#ffffff'} !important;
            color: {'#f1f1f1' if theme == 'Dark' else '#111111'} !important;
        }}
        .stButton>button, .stTextInput>div>input {{
            background-color: {'#222' if theme == 'Dark' else '#f9f9f9'} !important;
            color: {'#f1f1f1' if theme == 'Dark' else '#111111'} !important;
            border: 1px solid {'#444' if theme == 'Dark' else '#ccc'} !important;
        }}
    </style>
    """,
    unsafe_allow_html=True
)

# ----------- Auth Utilities ----------
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def load_user_data():
    return pd.read_csv("users.csv") if os.path.exists("users.csv") else pd.DataFrame(columns=["email", "username", "password"])

def save_user_data(df):
    df.to_csv("users.csv", index=False)

def register_user(email, username, password):
    users = load_user_data()
    if username in users["username"].values:
        st.error("Username already exists.")
    elif email in users["email"].values:
        st.error("Email already registered.")
    else:
        new_user = pd.DataFrame([[email, username, hash_password(password)]], columns=["email", "username", "password"])
        save_user_data(pd.concat([users, new_user], ignore_index=True))
        st.success("✅ Registered successfully! Please login.")

def check_user(username, password):
    users = load_user_data()
    match = users[(users["username"] == username) & (users["password"] == hash_password(password))]
    if not match.empty:
        st.session_state.user_email = match.iloc[0]["email"]
        return True
    return False

# ----------- Sidebar Navigation ----------
page = st.sidebar.selectbox("Navigate", ["Home", "Profile", "🎁 Offer Page", "🔒 Admin Login"])

if st.sidebar.button("Logout"):
    for key in ["logged_in", "username", "user_email", "admin_mode"]:
        st.session_state[key] = "" if key in ["username", "user_email"] else False
    st.rerun()

# ----------- Admin Panel ----------
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

# ----------- Home Page ----------
elif page == "Home":
    st.title("♻️ Return and Earn Portal")

    if not st.session_state.logged_in:
        st.subheader("🔐 Login / Register")
        auth_mode = st.radio("Choose an option:", ["Login", "Register"])
        email = st.text_input("Email")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")

        if auth_mode == "Register" and st.button("Register"):
            register_user(email, username, password)
        elif auth_mode == "Login" and st.button("Login"):
            if check_user(username, password):
                st.session_state.logged_in = True
                st.session_state.username = username
                st.success("Logged in successfully! ✅")
                st.rerun()
            else:
                st.error("Invalid credentials.")
        st.stop()

    # If logged in
    st.success(f"Welcome, {st.session_state.username} 👋")
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
                score = model.predict(pd.DataFrame([[condition_encoded, days_used]], columns=["condition_encoded", "days_used"]))[0]
                credit = round(score * st.session_state.credit_multiplier)
                action = "RRR" if score <= 33 else "Repair" if score <= 66 else "Resell"

                new_log = pd.DataFrame([{
                    "Email": st.session_state.user_email,
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
                    new_log.to_csv("return_logs.csv", mode='a', header=False, index=False)
                else:
                    new_log.to_csv("return_logs.csv", index=False)

                st.success(f"✅ Return submitted for '{item_name}'!")
                st.info(f"💸 Credit Earned: {credit} GreenPoints")
                st.balloons()
            except Exception as e:
                st.error(f"Something went wrong: {e}")
        else:
            st.warning("Please complete all fields.")

# ----------- Offer Page ----------
elif page == "🎁 Offer Page":
    show_offer_page()

# ----------- Profile Page ----------
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
            user_df[["Product Name", "Condition", "Days Used", "Score", "Credit Earned",
                     "action", "Pickup Date", "Pickup Time", "Time"]]
            .sort_values("Time", ascending=False),
            use_container_width=True
        )
    except:
        st.info("No return history found.")

    st.subheader("📊 Your Outcome Distribution")
    try:
        user_df["Category"] = user_df["Score"].apply(lambda s: "Recycle" if s <= 33 else "Repair" if s <= 66 else "Resell")
        st.plotly_chart(px.pie(user_df, names="Category", title="Your Return Classification"))
    except:
        st.info("Not enough data to display pie chart.")

    st.subheader("🏆 Leaderboard")
    try:
        leaderboard = df.groupby("Username")["Credit Earned"].sum().reset_index()
        leaderboard = leaderboard.sort_values("Credit Earned", ascending=False).head(10)
        st.table(leaderboard.rename(columns={"Credit Earned": "Total Credits"}))
    except:
        st.info("Leaderboard not available.")

    st.subheader("🌿 Total Credits Earned")
    try:
        redeemed_points = 0
        if os.path.exists("redeem_log.csv"):
            redeemed_df = pd.read_csv("redeem_log.csv")
            redeemed_points = redeemed_df[redeemed_df["Username"] == st.session_state.username]["Points"].sum()

        total_earned = user_df["Credit Earned"].sum()
        net_points = total_earned - redeemed_points

        st.success(f"🌿 Total Earned: {total_earned} GreenPoints")
        st.success(f"🎟️ Redeemed: {redeemed_points} GreenPoints")
        st.success(f"✅ Available: {net_points} GreenPoints")
    except:
        st.info("No credits earned yet.")
