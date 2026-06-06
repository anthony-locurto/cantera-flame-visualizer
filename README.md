# Cantera Flame Visualizer 🔥

An interactive web app for simulating and visualizing 1D reacting flows,
built with [Cantera](https://cantera.org), [Streamlit](https://streamlit.io),
and [Plotly](https://plotly.com).

## Flame configurations

| Page | Configuration | Key outputs |
|---|---|---|
| Premixed flame | Freely propagating 1D | S_L, temperature, species, HRR, φ-sweep |
| Counterflow diffusion | Opposed-jet fuel vs. oxidizer | T, species, Z, χ, scalar dissipation |
| Counterflow premixed | Twin opposed premixed jets | T, species, strain-extinction curve |

## Quickstart

### 1. Create and activate the environment

```bash
conda env create -f environment.yml
conda activate combustion
```

### 2. Run the app

```bash
streamlit run app.py
```

The app opens at `http://localhost:8501`.

## Project structure

```
cantera_flame_viz/
├── app.py                          # Entry point / home page
├── environment.yml                 # Conda environment
├── pages/
│   ├── 1_Premixed_Flame.py         # Freely propagating premixed
│   ├── 2_Counterflow_Diffusion.py  # Counterflow diffusion flame
│   └── 3_Counterflow_Premixed.py   # Counterflow twin premixed
├── utils/
│   ├── cantera_runner.py           # Solver wrappers + st.cache_data
│   ├── plot_helpers.py             # Plotly figure builders
│   └── species_selector.py        # Species multiselect widget
└── .streamlit/
    └── config.toml                 # Theme
```

## Notes

- First solve per configuration takes 15–40 s; results are cached for the session.
- Mechanisms ship with Cantera (`gri30.yaml`, `h2o2.yaml`). No extra downloads needed.
- CSV export is available on every page after a successful solve.
- The φ-sweep and strain-rate sweep tabs run multiple solves in sequence and may
  take several minutes depending on the number of points selected.

## Example outputs

**CH4/air premixed flame at φ = 1.0, 300 K, 1 atm**
- S_L ≈ 37 cm/s
- T_ad ≈ 2226 K

**H2/air premixed flame at φ = 1.0, 300 K, 1 atm**
- S_L ≈ 210 cm/s
- T_ad ≈ 2390 K

## Dependencies

- Python 3.11
- Cantera ≥ 3.0
- Streamlit ≥ 1.32
- Plotly ≥ 5.18
- NumPy, Pandas

## License

MIT
