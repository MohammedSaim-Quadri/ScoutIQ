import streamlit as st

st.set_page_config(page_title="Pricing – ScoutIQ", layout="centered")
st.title("💼 ScoutIQ Pricing")

st.markdown("Choose a plan that fits your hiring or job-prep needs.")

# Free Tier
st.header("🆓 Free Plan")
st.markdown("- 3 AI question generations per month")
st.markdown("- PDF download included")
st.markdown("- No credit card needed")

st.divider()

# Pro Monthly
st.header("💎 Pro Plan – Monthly")
st.markdown("- Unlimited question generations")
st.markdown("- Priority support")
st.markdown("- $12/month")

st.markdown(
    "[👉 Upgrade to Monthly Pro](https://saimquadri.gumroad.com/l/scoutiq-pro-monthly)",
    unsafe_allow_html=True
)

# Pro Yearly
st.header("💎 Pro Plan – Yearly")
st.markdown("- Unlimited usage + save 20%")
st.markdown("- $120/year (2 months free)")

st.markdown(
    "[👉 Upgrade to Yearly Pro](https://saimquadri.gumroad.com/l/scoutiq-pro-yearly)",
    unsafe_allow_html=True
)

# Lifetime
st.header("🔓 Lifetime Access")
st.markdown("- Pay once, access forever")
st.markdown("- $250 one-time")

st.markdown(
    "[👉 Get Lifetime Access](https://saimquadri.gumroad.com/l/scoutiq-pro-lifetime)",
    unsafe_allow_html=True
)

st.divider()
st.markdown("💬 After purchase, **log in with the same email** to unlock Pro features.")
