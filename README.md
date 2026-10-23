# CRI-MSWM Calculator

Interactive calculator for the **Climate Resilience Index for Municipal Solid Waste Management (CRI-MSWM)**.

**Live app: https://cri-mswm.streamlit.app**

The index assesses the climate resilience of a city's municipal solid waste management (MSWM) system with
41 indicators grouped into four components (Environmental, Technical, Socioeconomic, Governance) and four
resilience dimensions (exposure and pressure, absorptive, adaptive and transformative capacity).
Component weights were derived from seven experts with the Analytic Hierarchy Process (AHP).

## Features
- Score each indicator on an anchored 1–5 scale, or enter a measured value that is converted automatically
- Expert AHP, equal or custom component weights; arithmetic or geometric aggregation
- Results dashboard: overall index and class, component and dimension scores, weakest indicators
- Import scores from a CSV template; export results to Excel or CSV
- Bangkok (2024–25) assessment included as a worked example

## Run locally
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Citation
Kamara, M.M., Limpiti, T., Chidthaisong, A., Barua, A., Limsakul, A., Towprayoon, S., Phongphiphat, A. (2026).
Expert-weighted climate resilience index for municipal solid waste management: development with group AHP and
application to Bangkok, Thailand. Manuscript submitted to *Waste Management*.

The Joint Graduate School of Energy and Environment (JGSEE), King Mongkut's University of Technology Thonburi, Thailand.

## License
MIT License — see `LICENSE`.
