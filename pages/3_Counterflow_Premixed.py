"""
pages/3_Counterflow_Premixed.py
--------------------------------
Counterflow twin premixed flame page.
Symmetric opposed premixed jets — measures flame response to strain.
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import numpy as np
import streamlit as st

from utils.cantera_runner import (
    BUNDLED_MECHANISMS,
    available_fuels,
    solve_counterflow_premixed,
    result_to_dataframe,
)
from utils.plot_helpers import (
    plot_T_HRR,
    plot_species,
    plot_velocity,
    plot_sl_vs_strain,
)
from utils.species_selector import species_multiselect

st.set_page_config(page_title="Counterflow Premixed Flame", page_icon="🔥", layout="wide")

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

with st.sidebar:
    st.header("Counterflow premixed inputs")

    mech_label   = st.selectbox("Mechanism", list(BUNDLED_MECHANISMS.keys()))
    mechanism    = BUNDLED_MECHANISMS[mech_label]
    fuels        = available_fuels(mechanism)
    fuel         = st.selectbox("Fuel", fuels)

    phi = st.slider("Equivalence ratio φ", 0.5, 2.0, 1.0, 0.05)

    strain_rate = st.slider(
        "Global strain rate a (1/s)",
        min_value=50, max_value=5000, value=500, step=50,
        help="Increasing a stretches and eventually extinguishes the flames",
    )

    T_inlet      = st.number_input("Reactant temperature (K)",
                                    min_value=250, max_value=700, value=300, step=10)
    pressure_atm = st.number_input("Pressure (atm)",
                                    min_value=0.1, max_value=20.0, value=1.0, step=0.5)

    st.divider()
    st.subheader("Strain rate sweep")
    run_sweep     = st.checkbox("Sweep strain rate (extinction curve)", value=False)
    a_min         = st.slider("a min (1/s)", 50,  500, 100,  50, disabled=not run_sweep)
    a_max         = st.slider("a max (1/s)", 500, 5000, 2000, 100, disabled=not run_sweep)
    a_n_points    = st.slider("Points", 3, 12, 6, disabled=not run_sweep)

    st.divider()
    run_btn = st.button("▶  Run simulation", type="primary", use_container_width=True)

# ---------------------------------------------------------------------------
# Main panel
# ---------------------------------------------------------------------------

st.title("🔥 Counterflow twin premixed flame")
st.caption(
    f"Mechanism: **{mech_label}** · Fuel: **{fuel}** · φ = **{phi:.2f}** · "
    f"a = **{strain_rate} s⁻¹** · P = **{pressure_atm:.1f} atm**"
)

if not run_btn:
    st.info("Configure inputs in the sidebar and click **Run simulation**.")
    st.stop()

with st.spinner("Solving counterflow premixed flame…"):
    result = solve_counterflow_premixed(
        mechanism=mechanism,
        fuel=fuel,
        phi=phi,
        strain_rate=float(strain_rate),
        T_inlet=float(T_inlet),
        pressure_atm=float(pressure_atm),
    )

if not result.converged:
    st.error(f"Solver did not converge.\n\n```\n{result.message}\n```")
    st.stop()

# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

col1, col2, col3, col4 = st.columns(4)
col1.metric("Peak temperature",   f"{result.T.max():.0f} K")
col2.metric("Peak HRR",           f"{result.hrr.max() / 1e6:.1f} MW/m³")
col3.metric("Strain rate",        f"{strain_rate} s⁻¹")
col4.metric("Grid points",        f"{len(result.grid)}")

st.divider()

grid_mm = result.grid * 1e3

tab_T, tab_species, tab_vel, tab_sweep = st.tabs(
    ["Temperature & HRR", "Species", "Velocity", "Strain sweep"]
)

with tab_T:
    st.plotly_chart(
        plot_T_HRR(grid_mm, result.T, result.hrr),
        use_container_width=True,
    )

with tab_species:
    selected = species_multiselect(list(result.species.keys()), fuel, key="cp_species")
    if selected:
        st.plotly_chart(
            plot_species(grid_mm, result.species, selected),
            use_container_width=True,
        )

with tab_vel:
    st.plotly_chart(
        plot_velocity(grid_mm, result.u, title="Axial velocity (twin flame)"),
        use_container_width=True,
    )

with tab_sweep:
    if not run_sweep:
        st.info("Enable **Strain rate sweep** in the sidebar to map peak T vs. strain rate.")
    else:
        a_vals   = np.linspace(a_min, a_max, a_n_points)
        T_peaks  = []
        progress = st.progress(0, text="Running strain sweep…")

        for i, a_i in enumerate(a_vals):
            r = solve_counterflow_premixed(
                mechanism=mechanism,
                fuel=fuel,
                phi=phi,
                strain_rate=round(float(a_i), 1),
                T_inlet=float(T_inlet),
                pressure_atm=float(pressure_atm),
            )
            T_peaks.append(r.T.max() if r.converged else float("nan"))
            label = (f"a = {a_i:.0f} s⁻¹ → T_max = {r.T.max():.0f} K"
                     if r.converged else f"a = {a_i:.0f} s⁻¹ → did not converge")
            progress.progress((i + 1) / len(a_vals), text=label)

        progress.empty()
        st.plotly_chart(
            plot_sl_vs_strain(a_vals, np.array(T_peaks), fuel, phi),
            use_container_width=True,
        )

# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------

st.divider()
df = result_to_dataframe(result)
if not df.empty:
    st.download_button(
        "⬇  Download solution CSV",
        data=df.to_csv(index=False).encode(),
        file_name=f"cf_premixed_{fuel}_phi{phi:.2f}_a{strain_rate}.csv",
        mime="text/csv",
    )
