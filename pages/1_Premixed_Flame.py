"""
pages/1_Premixed_Flame.py
--------------------------
Freely propagating premixed flame — Phase 1 flagship page.

Sidebar inputs  →  Cantera solve  →  Plotly charts + metrics
Optional φ-sweep to generate S_L vs. φ curve.
"""

import io
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import numpy as np
import streamlit as st

from utils.cantera_runner import (
    BUNDLED_MECHANISMS,
    available_fuels,
    solve_premixed,
    result_to_dataframe,
)
from utils.plot_helpers import plot_T_HRR, plot_species, plot_velocity, plot_sl_sweep
from utils.species_selector import species_multiselect

st.set_page_config(page_title="Premixed Flame", page_icon="🔥", layout="wide")

# ---------------------------------------------------------------------------
# Sidebar — simulation inputs
# ---------------------------------------------------------------------------

with st.sidebar:
    st.header("Premixed flame inputs")

    mech_label = st.selectbox("Mechanism", list(BUNDLED_MECHANISMS.keys()))
    mechanism  = BUNDLED_MECHANISMS[mech_label]

    fuels = available_fuels(mechanism)
    fuel  = st.selectbox("Fuel", fuels)

    phi = st.slider(
        "Equivalence ratio φ",
        min_value=0.5, max_value=2.0, value=1.0, step=0.05,
        help="φ < 1 lean · φ = 1 stoichiometric · φ > 1 rich",
    )

    T_inlet = st.number_input(
        "Unburned gas temperature (K)",
        min_value=250, max_value=700, value=300, step=10,
    )

    pressure_atm = st.number_input(
        "Pressure (atm)",
        min_value=0.1, max_value=20.0, value=1.0, step=0.5,
    )

    st.divider()
    st.subheader("φ-sweep (S_L curve)")
    run_sweep    = st.checkbox("Run equivalence ratio sweep", value=False)
    phi_min      = st.slider("φ min", 0.5, 1.0, 0.6, 0.05, disabled=not run_sweep)
    phi_max      = st.slider("φ max", 1.0, 2.0, 1.6, 0.05, disabled=not run_sweep)
    phi_n_points = st.slider("Points", 3, 15, 7, disabled=not run_sweep)

    st.divider()
    run_btn = st.button("▶  Run simulation", type="primary", use_container_width=True)

# ---------------------------------------------------------------------------
# Main panel
# ---------------------------------------------------------------------------

st.title("🔥 Freely propagating premixed flame")
st.caption(f"Mechanism: **{mech_label}** · Fuel: **{fuel}** · φ = **{phi:.2f}** · "
           f"T₀ = **{T_inlet} K** · P = **{pressure_atm:.1f} atm**")

if not run_btn:
    st.info("Configure inputs in the sidebar and click **Run simulation**.")
    st.stop()

# ---------------------------------------------------------------------------
# Solve
# ---------------------------------------------------------------------------

with st.spinner("Solving flame… this may take 10–30 s on first run."):
    result = solve_premixed(
        mechanism=mechanism,
        fuel=fuel,
        phi=phi,
        T_inlet=T_inlet,
        pressure_atm=pressure_atm,
    )

if not result.converged:
    st.error(f"Solver did not converge.\n\n```\n{result.message}\n```")
    st.stop()

# ---------------------------------------------------------------------------
# Key metrics
# ---------------------------------------------------------------------------

col1, col2, col3, col4 = st.columns(4)
col1.metric("Laminar flame speed S_L", f"{result.flame_speed * 100:.2f} cm/s")
col2.metric("Adiabatic flame temperature", f"{result.T.max():.0f} K")
col3.metric("Peak HRR", f"{result.hrr.max() / 1e6:.1f} MW/m³")
col4.metric("Grid points", f"{len(result.grid)}")

st.divider()

# ---------------------------------------------------------------------------
# Plots
# ---------------------------------------------------------------------------

grid_mm = result.grid * 1e3   # m → mm

tab_T, tab_species, tab_vel, tab_sweep = st.tabs(
    ["Temperature & HRR", "Species", "Velocity", "φ-sweep"]
)

with tab_T:
    st.plotly_chart(
        plot_T_HRR(grid_mm, result.T, result.hrr),
        use_container_width=True,
    )

with tab_species:
    selected_species = species_multiselect(
        list(result.species.keys()), fuel, key="pm_species"
    )
    if selected_species:
        st.plotly_chart(
            plot_species(grid_mm, result.species, selected_species),
            use_container_width=True,
        )
    else:
        st.info("Select at least one species above.")

with tab_vel:
    st.plotly_chart(
        plot_velocity(grid_mm, result.u),
        use_container_width=True,
    )

with tab_sweep:
    if not run_sweep:
        st.info("Enable **φ-sweep** in the sidebar to generate an S_L vs. φ curve.")
    else:
        phi_vals = np.linspace(phi_min, phi_max, phi_n_points)
        sl_vals  = []
        progress = st.progress(0, text="Running φ-sweep…")

        for i, phi_i in enumerate(phi_vals):
            r = solve_premixed(
                mechanism=mechanism,
                fuel=fuel,
                phi=round(float(phi_i), 3),
                T_inlet=T_inlet,
                pressure_atm=pressure_atm,
            )
            sl_vals.append(r.flame_speed if r.converged else float("nan"))
            progress.progress((i + 1) / len(phi_vals),
                               text=f"φ = {phi_i:.2f} → S_L = "
                                    f"{r.flame_speed*100:.1f} cm/s" if r.converged
                                    else f"φ = {phi_i:.2f} → did not converge")

        progress.empty()
        st.plotly_chart(
            plot_sl_sweep(phi_vals, np.array(sl_vals), fuel),
            use_container_width=True,
        )

# ---------------------------------------------------------------------------
# CSV export
# ---------------------------------------------------------------------------

st.divider()
st.subheader("Export data")

df = result_to_dataframe(result)
if not df.empty:
    csv_bytes = df.to_csv(index=False).encode()
    st.download_button(
        label="⬇  Download solution CSV",
        data=csv_bytes,
        file_name=f"premixed_{fuel}_phi{phi:.2f}_{T_inlet}K_{pressure_atm}atm.csv",
        mime="text/csv",
    )
    with st.expander("Preview data (first 10 rows)"):
        st.dataframe(df.head(10), use_container_width=True)
