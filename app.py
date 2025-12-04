import streamlit as st

pages = [
    "strategy_utility/UI_strategy_utility.py",
    "pareto/UI_pareto.py",
    "lemke_howson/UI_LH.py"
]

pg = st.navigation(pages)
pg.run()