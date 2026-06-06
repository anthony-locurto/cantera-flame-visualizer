"""
utils/cantera_runner.py
-----------------------
Thin wrappers around Cantera flame objects.
All solver calls live here so pages stay clean.
Results are cached via st.cache_data to avoid re-running expensive solves
when the user tweaks plot settings without changing simulation inputs.
"""

from __future__ import annotations

import hashlib
import io
from dataclasses import dataclass, field
from typing import Optional

import cantera as ct
import numpy as np
import pandas as pd
import streamlit as st


# ---------------------------------------------------------------------------
# Result containers
# ---------------------------------------------------------------------------

@dataclass
class PremixedResult:
    """Solution from a freely propagating premixed flame."""
    flame_speed: float          # m/s
    grid: np.ndarray            # m
    T: np.ndarray               # K
    u: np.ndarray               # m/s
    species: dict[str, np.ndarray]   # mole fractions keyed by name
    hrr: np.ndarray             # W/m³  (heat release rate)
    mechanism: str
    fuel: str
    phi: float
    T_inlet: float              # K
    pressure: float             # Pa
    converged: bool = True
    message: str = ""


@dataclass
class CounterflowDiffResult:
    """Solution from a counterflow diffusion flame."""
    grid: np.ndarray
    T: np.ndarray
    u: np.ndarray
    V: np.ndarray               # radial strain (1/s)
    species: dict[str, np.ndarray]
    hrr: np.ndarray
    mixture_fraction: np.ndarray
    scalar_dissipation: np.ndarray   # chi (1/s)
    mechanism: str
    fuel: str
    oxidizer: str
    strain_rate: float          # 1/s  (inlet velocity ratio a = 2*U/L)
    pressure: float
    converged: bool = True
    message: str = ""


@dataclass
class CounterflowPremixedResult:
    """Solution from a counterflow twin premixed flame."""
    grid: np.ndarray
    T: np.ndarray
    u: np.ndarray
    V: np.ndarray
    species: dict[str, np.ndarray]
    hrr: np.ndarray
    mechanism: str
    fuel: str
    phi: float
    strain_rate: float          # 1/s
    pressure: float
    converged: bool = True
    message: str = ""


# ---------------------------------------------------------------------------
# Mechanism helpers
# ---------------------------------------------------------------------------

BUNDLED_MECHANISMS = {
    "GRI-Mech 3.0 (53 species)": "gri30.yaml",
    "H2/CO (Burke 2012, 13 species)": "h2o2.yaml",
}

COMMON_FUELS = ["CH4", "H2", "C2H6", "C3H8", "C2H4", "CO"]

DEFAULT_OXIDIZER = "O2:0.21, N2:0.79"


def load_gas(mechanism: str) -> ct.Solution:
    return ct.Solution(mechanism)


def available_fuels(mechanism: str) -> list[str]:
    """Return species present in the mechanism that are common fuels."""
    gas = load_gas(mechanism)
    names = gas.species_names
    return [f for f in COMMON_FUELS if f in names]


# ---------------------------------------------------------------------------
# Cache key helpers
# ---------------------------------------------------------------------------

def _hash(*args) -> str:
    blob = str(args).encode()
    return hashlib.md5(blob).hexdigest()


# ---------------------------------------------------------------------------
# Premixed flame solver
# ---------------------------------------------------------------------------

@st.cache_data(show_spinner=False)
def solve_premixed(
    mechanism: str,
    fuel: str,
    phi: float,
    T_inlet: float,
    pressure_atm: float,
    width: float = 0.03,        # m  — domain width; 3 cm is usually enough
    loglevel: int = 0,
) -> PremixedResult:
    """
    Solve a freely propagating premixed flame.

    Parameters
    ----------
    mechanism    : Cantera mechanism string, e.g. 'gri30.yaml'
    fuel         : Species name, e.g. 'CH4'
    phi          : Equivalence ratio
    T_inlet      : Unburned gas temperature (K)
    pressure_atm : Pressure in atmospheres
    width        : Domain width in metres
    loglevel     : Cantera verbosity (0 = silent)
    """
    try:
        gas = ct.Solution(mechanism)
        gas.set_equivalence_ratio(phi, fuel, DEFAULT_OXIDIZER)
        gas.TP = T_inlet, pressure_atm * ct.one_atm

        flame = ct.FreeFlame(gas, width=width)
        flame.set_refine_criteria(ratio=3, slope=0.06, curve=0.12)
        flame.solve(loglevel=loglevel, auto=True)

        species = {
            sp: flame.X[gas.species_index(sp)]
            for sp in gas.species_names
            if np.max(flame.X[gas.species_index(sp)]) > 1e-6
        }

        return PremixedResult(
            flame_speed=flame.velocity[0],
            grid=flame.grid,
            T=flame.T,
            u=flame.velocity,
            species=species,
            hrr=flame.heat_release_rate,
            mechanism=mechanism,
            fuel=fuel,
            phi=phi,
            T_inlet=T_inlet,
            pressure=pressure_atm * ct.one_atm,
        )

    except Exception as exc:
        return PremixedResult(
            flame_speed=float("nan"),
            grid=np.array([]),
            T=np.array([]),
            u=np.array([]),
            species={},
            hrr=np.array([]),
            mechanism=mechanism,
            fuel=fuel,
            phi=phi,
            T_inlet=T_inlet,
            pressure=pressure_atm * ct.one_atm,
            converged=False,
            message=str(exc),
        )


# ---------------------------------------------------------------------------
# Counterflow diffusion flame solver
# ---------------------------------------------------------------------------

@st.cache_data(show_spinner=False)
def solve_counterflow_diff(
    mechanism: str,
    fuel: str,
    oxidizer: str,
    strain_rate: float,
    T_fuel: float,
    T_oxidizer: float,
    pressure_atm: float,
    width: float = 0.02,
    loglevel: int = 0,
) -> CounterflowDiffResult:
    """
    Solve a counterflow diffusion flame.

    strain_rate : global strain rate a = (U_fuel + U_ox) / L  (1/s)
    width       : domain width L (m); inlet velocities derived from strain_rate
    """
    try:
        gas = ct.Solution(mechanism)

        # Inlet velocities from strain rate: a = (U_f + U_ox) / L
        # Assume symmetric: U_f = U_ox = a*L/2
        U = strain_rate * width / 2.0

        gas.TPX = T_fuel, pressure_atm * ct.one_atm, f"{fuel}:1.0"
        rho_fuel = gas.density

        gas.TPX = T_oxidizer, pressure_atm * ct.one_atm, oxidizer
        rho_ox = gas.density

        # Mass flux = rho * U; CounterflowDiffusionFlame expects mdot
        mdot_fuel = rho_fuel * U
        mdot_ox   = rho_ox   * U

        gas.TPX = T_fuel, pressure_atm * ct.one_atm, f"{fuel}:1.0"
        flame = ct.CounterflowDiffusionFlame(gas, width=width)
        flame.fuel_inlet.mdot       = mdot_fuel
        flame.fuel_inlet.X          = f"{fuel}:1.0"
        flame.fuel_inlet.T          = T_fuel
        flame.oxidizer_inlet.mdot   = mdot_ox
        flame.oxidizer_inlet.X      = oxidizer
        flame.oxidizer_inlet.T      = T_oxidizer

        flame.set_refine_criteria(ratio=3, slope=0.06, curve=0.12, prune=0.05)
        flame.solve(loglevel=loglevel, auto=True)

        # Mixture fraction (Bilger's definition via Cantera)
        Z = flame.mixture_fraction("Bilger")

        # Scalar dissipation: chi = 2 * D_mix * (dZ/dx)^2
        dZdx   = np.gradient(Z, flame.grid)
        D_mix  = flame.mix_diff_coeffs[gas.species_index("N2")]  # proxy
        chi    = 2.0 * D_mix * dZdx**2

        species = {
            sp: flame.X[gas.species_index(sp)]
            for sp in gas.species_names
            if np.max(flame.X[gas.species_index(sp)]) > 1e-6
        }

        return CounterflowDiffResult(
            grid=flame.grid,
            T=flame.T,
            u=flame.velocity,
            V=flame.strain_rate("potential flow"),
            species=species,
            hrr=flame.heat_release_rate,
            mixture_fraction=Z,
            scalar_dissipation=chi,
            mechanism=mechanism,
            fuel=fuel,
            oxidizer=oxidizer,
            strain_rate=strain_rate,
            pressure=pressure_atm * ct.one_atm,
        )

    except Exception as exc:
        return CounterflowDiffResult(
            grid=np.array([]),
            T=np.array([]),
            u=np.array([]),
            V=np.array([]),
            species={},
            hrr=np.array([]),
            mixture_fraction=np.array([]),
            scalar_dissipation=np.array([]),
            mechanism=mechanism,
            fuel=fuel,
            oxidizer=oxidizer,
            strain_rate=strain_rate,
            pressure=pressure_atm * ct.one_atm,
            converged=False,
            message=str(exc),
        )


# ---------------------------------------------------------------------------
# Counterflow premixed flame solver
# ---------------------------------------------------------------------------

@st.cache_data(show_spinner=False)
def solve_counterflow_premixed(
    mechanism: str,
    fuel: str,
    phi: float,
    strain_rate: float,
    T_inlet: float,
    pressure_atm: float,
    width: float = 0.02,
    loglevel: int = 0,
) -> CounterflowPremixedResult:
    """
    Solve a counterflow twin premixed flame (symmetric opposed jets).
    """
    try:
        gas = ct.Solution(mechanism)
        gas.set_equivalence_ratio(phi, fuel, DEFAULT_OXIDIZER)
        gas.TP = T_inlet, pressure_atm * ct.one_atm

        U     = strain_rate * width / 2.0
        mdot  = gas.density * U

        flame = ct.CounterflowPremixedFlame(gas, width=width)
        flame.reactants.mdot = mdot
        flame.reactants.X    = gas.X
        flame.reactants.T    = T_inlet
        flame.products.mdot  = mdot
        flame.products.X     = gas.X
        flame.products.T     = T_inlet

        flame.set_refine_criteria(ratio=3, slope=0.06, curve=0.12, prune=0.05)
        flame.solve(loglevel=loglevel, auto=True)

        species = {
            sp: flame.X[gas.species_index(sp)]
            for sp in gas.species_names
            if np.max(flame.X[gas.species_index(sp)]) > 1e-6
        }

        return CounterflowPremixedResult(
            grid=flame.grid,
            T=flame.T,
            u=flame.velocity,
            V=flame.strain_rate("potential flow"),
            species=species,
            hrr=flame.heat_release_rate,
            mechanism=mechanism,
            fuel=fuel,
            phi=phi,
            strain_rate=strain_rate,
            pressure=pressure_atm * ct.one_atm,
        )

    except Exception as exc:
        return CounterflowPremixedResult(
            grid=np.array([]),
            T=np.array([]),
            u=np.array([]),
            V=np.array([]),
            species={},
            hrr=np.array([]),
            mechanism=mechanism,
            fuel=fuel,
            phi=phi,
            strain_rate=strain_rate,
            pressure=pressure_atm * ct.one_atm,
            converged=False,
            message=str(exc),
        )


# ---------------------------------------------------------------------------
# DataFrame export helper
# ---------------------------------------------------------------------------

def result_to_dataframe(result) -> pd.DataFrame:
    """Convert any result dataclass to a tidy DataFrame for CSV export."""
    if not result.converged or len(result.grid) == 0:
        return pd.DataFrame()

    data = {"x_m": result.grid, "T_K": result.T, "u_m_s": result.u}

    if hasattr(result, "hrr"):
        data["hrr_W_m3"] = result.hrr
    if hasattr(result, "mixture_fraction"):
        data["mixture_fraction"] = result.mixture_fraction
    if hasattr(result, "scalar_dissipation"):
        data["scalar_dissipation_1_s"] = result.scalar_dissipation

    for sp, arr in result.species.items():
        data[f"X_{sp}"] = arr

    return pd.DataFrame(data)
