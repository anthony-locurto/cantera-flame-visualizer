"""
Cantera Flame Visualizer
========================
Main entry point. Run with:  streamlit run app.py
"""

import streamlit as st

st.set_page_config(
    page_title="Cantera Flame Visualizer",
    page_icon="🔥",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("🔥 Cantera Flame Visualizer")
st.markdown(
    """
    An interactive tool for simulating and visualizing 1D reacting flows using
    [Cantera](https://cantera.org). Select a flame configuration from the sidebar to get started.

    ---
    **Available configurations:**

    | Page | Configuration | Key outputs |
    |---|---|---|
    | Premixed flame | Freely propagating, 1D | S_L, T profile, species, HRR |
    | Counterflow diffusion | Opposed-jet, fuel vs. oxidizer | Z, scalar dissipation, extinction |
    | Counterflow premixed | Opposed twin flames | S_L vs. strain, extinction strain |

    ---
    *Built with Cantera · Streamlit · Plotly*
    """
)

st.info("👈 Select a flame type from the sidebar to begin.")
