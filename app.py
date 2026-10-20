import os
import sys

import streamlit as st

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

st.set_page_config(page_title="Portfolio Analyzer", layout="wide")

pages = st.navigation([
    st.Page("views/markets.py", title="World markets", default=True),
    st.Page("views/investors.py", title="Famous investors"),
    st.Page("views/portfolio.py", title="My CAC 40 portfolio"),
    st.Page("views/options.py", title="Options (Black-Scholes)"),
], position="top")
pages.run()
