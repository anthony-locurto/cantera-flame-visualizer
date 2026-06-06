"""
utils/species_selector.py
--------------------------
Renders a compact multiselect widget for choosing which species to plot.
Provides sensible defaults based on fuel type.
"""

from __future__ import annotations
import streamlit as st

# Priority species to pre-select by fuel
_DEFAULT_SPECIES: dict[str, list[str]] = {
    "CH4": ["CH4", "O2", "CO2", "H2O", "CO", "OH", "H2"],
    "H2":  ["H2", "O2", "H2O", "OH", "H", "O", "HO2"],
    "C2H6":["C2H6", "O2", "CO2", "H2O", "CO", "C2H4", "CH4"],
    "C3H8":["C3H8", "O2", "CO2", "H2O", "CO", "C3H6", "C2H4"],
    "C2H4":["C2H4", "O2", "CO2", "H2O", "CO", "C2H2", "CH4"],
    "CO":  ["CO", "O2", "CO2", "H2O", "OH", "H"],
}
_FALLBACK = ["O2", "CO2", "H2O", "CO", "OH"]


def species_multiselect(
    available: list[str],
    fuel: str,
    key: str = "species_select",
    max_shown: int = 8,
) -> list[str]:
    """
    Render a st.multiselect for species.
    Returns the user's selected list.
    """
    defaults = _DEFAULT_SPECIES.get(fuel, _FALLBACK)
    valid_defaults = [s for s in defaults if s in available][:max_shown]

    selected = st.multiselect(
        "Species to plot",
        options=available,
        default=valid_defaults,
        key=key,
        help="Select one or more species mole fractions to display.",
    )
    return selected
