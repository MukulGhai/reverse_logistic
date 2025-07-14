import streamlit as st
import pandas as pd
from datetime import datetime
import os
import qrcode
from io import BytesIO
from PIL import Image

def show_offer_page():
    st.title("🎁 Your Personalized Offers")

    # ----------------- Utility Functions ------------------
    def get_user_points(username):
        total_earned = 0
        total_redeemed = 0

        # Total credits earned
        if os.path.exists("return_logs.csv"):
            df = pd.read_csv("return_logs.csv")
            user_df = df[df["Username"] == username]
            total_earned = user_df["Credit Earned"].sum()

        # Total credits redeemed
        if os.path.exists("redeem_log.csv"):
            redeem_df = pd.read_csv("redeem_log.csv")
            redeem_user_df = redeem_df[redeem_df["Username"] == username]
            if "Points" in redeem_user_df.columns:
                total_redeemed = redeem_user_df["Points"].sum()

        return total_earned - total_redeemed

    def log_redeem(username, offer_title, points_used):
        redeem_log = "redeem_log.csv"
        data = pd.DataFrame([{
            "Username": username,
            "Offer": offer_title,
            "Points": points_used,
            "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }])
        if os.path.exists(redeem_log):
            data.to_csv(redeem_log, mode='a', header=False, index=False)
        else:
            data.to_csv(redeem_log, index=False)

    def has_redeemed(username, offer_title):
        if os.path.exists("redeem_log.csv"):
            df = pd.read_csv("redeem_log.csv")
            return not df[(df["Username"] == username) & (df["Offer"] == offer_title)].empty
        return False

    def generate_qr_code(data):
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(data)
        qr.make(fit=True)
        img = qr.make_image(fill="black", back_color="white")
        return img

    # ------------------ Get Session Info ------------------
    username = st.session_state.get("username", "guest")
    green_points = get_user_points(username)

    st.write(f"👤 Welcome, **{username}**")
    st.write(f"🌿 Your GreenPoints: **{green_points}**")

    # ------------------ Offer Data ------------------------
    offers = [
        {"title": "10% Off on Recycled Products", "points_required": 300},
        {"title": "Free Repair Coupon", "points_required": 700},
        {"title": "VIP Access to Refurbished Goods", "points_required": 1000},
    ]

    offer_icons = {
        "10% Off on Recycled Products": "♻️",
        "Free Repair Coupon": "🛠️",
        "VIP Access to Refurbished Goods": "👑"
    }

    # ------------------ Search Offers ---------------------
    search = st.text_input("🔍 Search Offers")
    filtered_offers = [o for o in offers if search.lower() in o["title"].lower()]

    # ------------------ Show Offers -----------------------
    for i, offer in enumerate(filtered_offers):
        progress = min(green_points / offer["points_required"], 1.0)
        unlocked = green_points >= offer["points_required"]
        already_redeemed = has_redeemed(username, offer["title"])

        bg_color = "#e8f5e9" if unlocked else "#2d2d2d"
        text_color = "#000000" if unlocked else "#ffffff"

        with st.container():
            st.markdown(f"""
            <div style="
                background-color:{bg_color}; 
                padding: 15px; 
                border-radius: 10px; 
                margin-bottom: 10px;
                color: {text_color}; 
                box-shadow: 0 0 10px rgba(0,0,0,0.2);">
                <h4>{offer_icons.get(offer['title'], '')} {offer['title']}</h4>
                <p><b>Required Points:</b> {offer['points_required']}</p>
                <p><b>Your Points:</b> {green_points}</p>
            </div>
            """, unsafe_allow_html=True)

            st.progress(progress)

            col1, col2 = st.columns([1, 1])
            with col1:
                if unlocked and not already_redeemed:
                    if st.button(f"🎉 Redeem", key=f"redeem_{i}"):
                        log_redeem(username, offer["title"], offer["points_required"])

                        qr_img = generate_qr_code(f"{username} redeemed: {offer['title']}")
                        buf = BytesIO()
                        qr_img.save(buf, format="PNG")
                        st.image(buf.getvalue(), caption="🎫 Scan to Redeem Offer", use_column_width=False)
                        st.success(f"✅ Redeemed '{offer['title']}'!")
                        st.rerun()
                elif already_redeemed:
                    st.info("✅ Already Redeemed")
            with col2:
                if not unlocked:
                    st.button("🔒 Locked", key=f"lock_{i}", disabled=True)

    # ------------------ Show Redeem History ----------------
    if os.path.exists("redeem_log.csv"):
        st.markdown("---")
        st.subheader("🧾 Redeem History")
        history = pd.read_csv("redeem_log.csv")
        user_history = history[history["Username"] == username]
        if not user_history.empty:
            st.dataframe(user_history.sort_values("Timestamp", ascending=False), use_container_width=True)
        else:
            st.info("You haven't redeemed any offers yet.")

# Run as standalone
if __name__ == "__main__":
    show_offer_page()
