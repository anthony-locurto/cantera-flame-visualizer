"""
utils/plot_helpers.py
---------------------
Reusable Plotly figure builders.
Each function returns a go.Figure ready for st.plotly_chart().
"""

from __future__ import annotations

import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

# ---------------------------------------------------------------------------
# Design tokens — matches .streamlit/config.toml dark theme
# ---------------------------------------------------------------------------

COLORS = {
    "temperature": "#E8593C",   # coral/flame
    "hrr":         "#EF9F27",   # amber
    "velocity":    "#3B8BD4",   # blue
    "species":     px.colors.qualitative.Plotly,
    "mixture_frac":"#1D9E75",   # teal
    "chi":         "#9F77DD",   # purple
}

LAYOUT_BASE = dict(
    template="plotly_dark",
    font=dict(family="sans-serif", size=13),
    margin=dict(l=60, r=30, t=40, b=50),
    hovermode="x unified",
    legend=dict(
        bgcolor="rgba(0,0,0,0)",
        borderwidth=0,
        font=dict(size=12),
    ),
)


def _fig(**kwargs) -> go.Figure:
    layout = {**LAYOUT_BASE, **kwargs}
    return go.Figure(layout=go.Layout(**layout))


# ---------------------------------------------------------------------------
# Temperature + HRR (dual y-axis) — used by all three pages
# ---------------------------------------------------------------------------

def plot_T_HRR(
    grid_mm: np.ndarray,
    T: np.ndarray,
    hrr: np.ndarray,
    x_label: str = "Position (mm)",
) -> go.Figure:
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    fig.add_trace(
        go.Scatter(
            x=grid_mm, y=T,
            name="Temperature (K)",
            line=dict(color=COLORS["temperature"], width=2.5),
        ),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(
            x=grid_mm, y=hrr / 1e6,
            name="HRR (MW/m³)",
            line=dict(color=COLORS["hrr"], width=2, dash="dot"),
            opacity=0.9,
        ),
        secondary_y=True,
    )

    fig.update_layout(**LAYOUT_BASE, title="Temperature and heat release rate")
    fig.update_xaxes(title_text=x_label)
    fig.update_yaxes(title_text="Temperature (K)", secondary_y=False,
                     color=COLORS["temperature"])
    fig.update_yaxes(title_text="HRR (MW/m³)", secondary_y=True,
                     color=COLORS["hrr"])
    return fig


# ---------------------------------------------------------------------------
# Multi-species mole fraction
# ---------------------------------------------------------------------------

def plot_species(
    grid_mm: np.ndarray,
    species_dict: dict[str, np.ndarray],
    selected: list[str],
    x_label: str = "Position (mm)",
) -> go.Figure:
    fig = _fig(title="Species mole fractions")

    for i, sp in enumerate(selected):
        if sp not in species_dict:
            continue
        fig.add_trace(go.Scatter(
            x=grid_mm,
            y=species_dict[sp],
            name=sp,
            line=dict(color=COLORS["species"][i % len(COLORS["species"])], width=2),
        ))

    fig.update_xaxes(title_text=x_label)
    fig.update_yaxes(title_text="Mole fraction (–)")
    return fig


# ---------------------------------------------------------------------------
# Axial velocity
# ---------------------------------------------------------------------------

def plot_velocity(
    grid_mm: np.ndarray,
    u: np.ndarray,
    x_label: str = "Position (mm)",
    title: str = "Axial velocity",
) -> go.Figure:
    fig = _fig(title=title)
    fig.add_trace(go.Scatter(
        x=grid_mm, y=u,
        name="u (m/s)",
        line=dict(color=COLORS["velocity"], width=2),
        fill="tozeroy",
        fillcolor="rgba(59,139,212,0.08)",
    ))
    fig.update_xaxes(title_text=x_label)
    fig.update_yaxes(title_text="Velocity (m/s)")
    return fig


# ---------------------------------------------------------------------------
# Mixture fraction + scalar dissipation (counterflow diffusion)
# ---------------------------------------------------------------------------

def plot_mixture_fraction(
    grid_mm: np.ndarray,
    Z: np.ndarray,
    chi: np.ndarray,
) -> go.Figure:
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    fig.add_trace(
        go.Scatter(
            x=grid_mm, y=Z,
            name="Mixture fraction Z",
            line=dict(color=COLORS["mixture_frac"], width=2.5),
        ),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(
            x=grid_mm, y=chi,
            name="Scalar dissipation χ (1/s)",
            line=dict(color=COLORS["chi"], width=2, dash="dot"),
        ),
        secondary_y=True,
    )

    fig.update_layout(**LAYOUT_BASE, title="Mixture fraction and scalar dissipation")
    fig.update_xaxes(title_text="Position (mm)")
    fig.update_yaxes(title_text="Mixture fraction Z (–)", secondary_y=False,
                     color=COLORS["mixture_frac"])
    fig.update_yaxes(title_text="χ (1/s)", secondary_y=True, color=COLORS["chi"])
    return fig


# ---------------------------------------------------------------------------
# S_L vs phi sweep (premixed page)
# ---------------------------------------------------------------------------

def plot_sl_sweep(
    phi_vals: np.ndarray,
    sl_vals: np.ndarray,
    fuel: str,
) -> go.Figure:
    fig = _fig(title=f"Laminar flame speed vs. equivalence ratio — {fuel}")

    fig.add_trace(go.Scatter(
        x=phi_vals,
        y=[v * 100 for v in sl_vals],   # m/s → cm/s
        mode="lines+markers",
        line=dict(color=COLORS["temperature"], width=2.5),
        marker=dict(size=6),
        name="S_L",
    ))

    # Mark peak
    peak_idx = int(np.nanargmax(sl_vals))
    fig.add_annotation(
        x=phi_vals[peak_idx],
        y=sl_vals[peak_idx] * 100,
        text=f"  peak {sl_vals[peak_idx]*100:.1f} cm/s<br>  at φ={phi_vals[peak_idx]:.2f}",
        showarrow=True,
        arrowhead=2,
        arrowcolor=COLORS["temperature"],
        font=dict(size=12),
        ax=40, ay=-30,
    )

    fig.update_xaxes(title_text="Equivalence ratio φ (–)")
    fig.update_yaxes(title_text="S_L (cm/s)")
    return fig


# ---------------------------------------------------------------------------
# S_L vs strain rate sweep (counterflow premixed)
# ---------------------------------------------------------------------------

def plot_sl_vs_strain(
    strain_vals: np.ndarray,
    sl_proxy: np.ndarray,
    fuel: str,
    phi: float,
) -> go.Figure:
    fig = _fig(title=f"Peak T vs. strain rate — {fuel}, φ={phi:.2f}")

    fig.add_trace(go.Scatter(
        x=strain_vals,
        y=sl_proxy,
        mode="lines+markers",
        line=dict(color=COLORS["hrr"], width=2.5),
        marker=dict(size=6),
        name="T_max (K)",
    ))

    fig.update_xaxes(title_text="Strain rate a (1/s)", type="log")
    fig.update_yaxes(title_text="Peak temperature (K)")
    return fig
