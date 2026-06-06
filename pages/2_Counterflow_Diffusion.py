"""
pages/2_Counterflow_Diffusion.py
---------------------------------
Counterflow diffusion flame page.
Fuel and oxidizer streams oppose each other across a stagnation plane.
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import streamlit as st

from utils.cantera_runner import (
    BUNDLED_MECHANISMS,
    available_fuels,
    solve_counterflow_diff,
    result_to_dataframe,
    DEFAULT_OXIDIZER,
)
from utils.plot_helpers import (
    plot_T_HRR,
    plot_species,
    plot_velocity,
    plot_mixture_fraction,
)
from utils.species_selector import species_multiselect

st.set_page_config(page_title="Counterflow Diffusion Flame", page_icon="🔥", layout="wide")

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

with st.sidebar:
    st.header("Counterflow diffusion inputs")

    mech_label   = st.selectbox("Mechanism", list(BUNDLED_MECHANISMS.keys()))
    mechanism    = BUNDLED_MECHANISMS[mech_label]
    fuels        = available_fuels(mechanism)
    fuel         = st.selectbox("Fuel", fuels)

    oxidizer     = st.text_input(
        "Oxidizer composition",
        value=DEFAULT_OXIDIZER,
        help="Cantera species string, e.g. 'O2:0.21, N2:0.79'",
    )

    strain_rate  = st.slider(
        "Global strain rate a (1/s)",
        min_value=50, max_value=2000, value=200, step=50,
        help="a = (U_fuel + U_ox) / L",
    )

    T_fuel       = st.number_input("Fuel stream temperature (K)",
                                    min_value=250, max_value=700, value=300, step=10)
    T_oxidizer   = st.number_input("Oxidizer stream temperature (K)",
                                    min_value=250, max_value=700, value=300, step=10)
    pressure_atm = st.number_input("Pressure (atm)",
                                    min_value=0.1, max_value=20.0, value=1.0, step=0.5)

    st.divider()
    run_btn = st.button("▶  Run simulation", type="primary", use_container_width=True)

# ---------------------------------------------------------------------------
# Main panel
# ---------------------------------------------------------------------------

st.title("🔥 Counterflow diffusion flame")
st.caption(
    f"Mechanism: **{mech_label}** · Fuel: **{fuel}** · "
    f"a = **{strain_rate} s⁻¹** · P = **{pressure_atm:.1f} atm**"
)

if not run_btn:
    st.info("Configure inputs in the sidebar and click **Run simulation**.")
    st.stop()

with st.spinner("Solving counterflow diffusion flame…"):
    result = solve_counterflow_diff(
        mechanism=mechanism,
        fuel=fuel,
        oxidizer=oxidizer,
        strain_rate=float(strain_rate),
        T_fuel=float(T_fuel),
        T_oxidizer=float(T_oxidizer),
        pressure_atm=float(pressure_atm),
    )

if not result.converged:
    st.error(f"Solver did not converge.\n\n```\n{result.message}\n```")
    st.stop()

# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

col1, col2, col3, col4 = st.columns(4)
col1.metric("Peak temperature",      f"{result.T.max():.0f} K")
col2.metric("Peak HRR",              f"{result.hrr.max() / 1e6:.1f} MW/m³")
col3.metric("Peak scalar dissipation", f"{result.scalar_dissipation.max():.1f} s⁻¹")
col4.metric("Grid points",           f"{len(result.grid)}")

st.divider()

grid_mm = result.grid * 1e3

tab_T, tab_species, tab_vel, tab_Z = st.tabs(
    ["Temperature & HRR", "Species", "Velocity", "Mixture fraction"]
)

with tab_T:
    st.plotly_chart(
        plot_T_HRR(grid_mm, result.T, result.hrr),
        use_container_width=True,
    )

with tab_species:
    selected = species_multiselect(list(result.species.keys()), fuel, key="cd_species")
    if selected:
        st.plotly_chart(
            plot_species(grid_mm, result.species, selected),
            use_container_width=True,
        )

with tab_vel:
    st.plotly_chart(
        plot_velocity(grid_mm, result.u, title="Axial velocity (counterflow)"),
        use_container_width=True,
    )

with tab_Z:
    st.plotly_chart(
        plot_mixture_fraction(grid_mm, result.mixture_fraction,
                              result.scalar_dissipation),
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
        file_name=f"cf_diff_{fuel}_a{strain_rate}.csv",
        mime="text/csv",
    )
