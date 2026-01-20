import streamlit as st
from app.common import load_data, save_data
import app.initialize as session_init

st.set_page_config(page_title="Flooding Coordination - Admin", layout="wide")

session_init.init_session_state()

with st.sidebar:
    st.session_state.hf_api_key = st.text_input("Novita API Key", value=st.session_state.hf_api_key,
                                                type="password")

if st.session_state.username == "admin":
    st.header("🛠️ Admin Control Panel")
    data = load_data()

    st.subheader("Manage Users")
    users = list(data["users"].keys())

    if len(users) <= 1:
        st.info("No other users found.")
    else:
        for u in users:
            if u == "admin": continue

            with st.container(border=True):
                col1, col2, col3, col4 = st.columns([2, 1, 2, 2])
                current_points = data["users"][u].get("points", 0)

                col1.write(f"**{u}**")
                col1.caption(f"Current Points: {current_points}")

                deduct_amount = col2.number_input("Amount", min_value=0, max_value=current_points, step=1, key=f"d_amt_{u}")

                if col3.button("📉 Deduct Points", key=f"btn_ded_{u}"):
                    if deduct_amount > 0:
                        data["users"][u]["points"] = max(0, current_points - deduct_amount)
                        save_data(data)
                        st.success(f"Deducted {deduct_amount} points from {u}")
                        st.rerun()

                if col4.button("❌ Delete Account", key=f"btn_del_{u}"):
                    del data["users"][u]
                    save_data(data)
                    st.warning(f"Deleted user {u}")
                    st.rerun()
else:
    st.error("Access Denied.")