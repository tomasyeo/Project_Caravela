"""
dashboard.py — thin entry point for Project Caravela Streamlit dashboard.
Only page config and navigation here. No charts, no data loading.
"""
import streamlit as st

st.set_page_config(
    layout="wide",
    page_title="Project Caravela",
    page_icon="🛒",
    initial_sidebar_state="expanded",
)

pages = st.navigation([
    st.Page("pages/1_Executive.py",  title="Executive Overview",   icon="📊"),
    st.Page("pages/2_Products.py",   title="Product Performance",  icon="🏷️"),
    st.Page("pages/3_Geographic.py", title="Geographic Analysis",  icon="🗺️"),
    st.Page("pages/4_Customers.py",  title="Customer Analysis",    icon="👥"),
    st.Page("pages/5_Glossary.py",   title="Glossary",             icon="📖"),
])

pages.run()
