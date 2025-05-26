import streamlit as st
st.set_page_config(page_title="ScoutIQ App", layout="centered")
from app.ui import run_ui
from app.auth import auth_functions as auth

def main():

    # 🛡️ If already logged in → show main app
    if 'user_info' in st.session_state:
        run_ui()
        return

    st.title("🔐 Log in to ScoutIQ")

    col1, col2, col3 = st.columns([1, 2, 1])
    choice = col2.selectbox("Do you have an account?", ["Yes", "No", "Forgot Password"])

    with col2.form("auth_form"):
        email = st.text_input("Email")
        password = st.text_input("Password", type="password") if choice in ["Yes", "No"] else ""
        submit = st.form_submit_button("Submit")
    st.page_link("Home.py", label="⬅️ Back to Home", icon="🏠")
    if submit:
        if choice == "Yes":
            auth.sign_in(email, password)
        elif choice == "No":
            auth.create_account(email, password)
        elif choice == "Forgot Password":
            auth.reset_password(email)

    if 'auth_success' in st.session_state:
        st.success(st.session_state.auth_success)
        del st.session_state.auth_success
    elif 'auth_warning' in st.session_state:
        st.warning(st.session_state.auth_warning)
        del st.session_state.auth_warning

if __name__ == "__main__":
    main()
