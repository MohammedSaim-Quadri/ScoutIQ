from app.ui import run_ui
import streamlit as st
from app.auth import auth_functions as auth

def main():
    if 'user_info' not in st.session_state:
        col1, col2, col3 = st.columns([1, 2, 1])
        choice = col2.selectbox("Do you have an account?", ["Yes", "No", "Forgot Password"])
        with col2.form("auth_form"):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password") if choice in ["Yes", "No"] else ""
            submit = st.form_submit_button("Submit")

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
        return

    run_ui()

if __name__ == "__main__":
    main()
