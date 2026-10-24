"""CRI-MSWM Calculator: Climate Resilience Index for Municipal Solid Waste Management.

Kamara, M.M., Limpiti, T., Chidthaisong, A., Barua, A., Limsakul, A., Towprayoon, S., Phongphiphat, A.
The Joint Graduate School of Energy and Environment (JGSEE), King Mongkut's University of Technology Thonburi.
"""
import io
import json
import math
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="CRI-MSWM Calculator", page_icon=":material/recycling:", layout="wide")

DATA = json.loads((Path(__file__).parent / "data" / "indicators.json").read_text(encoding="utf-8"))
META, IND = DATA["meta"], DATA["indicators"]
COMPONENTS = ["Environmental", "Technical", "Socioeconomic", "Governance"]
COMP_COLORS = {"Environmental": "#2a78d6", "Technical": "#eb6834", "Socioeconomic": "#1baf7a", "Governance": "#d39200"}
DIMENSIONS = {"P": "Exposure & pressure", "Ab": "Absorptive capacity", "Ad": "Adaptive capacity", "Tr": "Transformative capacity"}
LEVEL_COLORS = {1: "#c0392b", 2: "#d9772b", 3: "#b89500", 4: "#4c9a52", 5: "#1f7a4d"}
AHP = META["ahp_weights"]
BY_CODE = {d["code"]: d for d in IND}

st.markdown(
    """
    <style>
      .block-container {padding-top: 1.6rem; max-width: 1280px;}
      h1 {font-weight: 700; letter-spacing: -0.01em;}
      .eyebrow {font-size: 0.78rem; letter-spacing: 0.08em; text-transform: uppercase; color: #0f6b6f; font-weight: 600;}
      .lede {color: #4a5a57; font-size: 1.02rem; max-width: 78ch;}
      .chip {display: inline-block; padding: 1px 8px; border-radius: 999px; font-size: 0.72rem; border: 1px solid #d9e1df; color: #4a5a57; margin-left: 6px;}
      .lvl {display: inline-block; min-width: 26px; text-align: center; border-radius: 6px; color: white; font-weight: 600; padding: 1px 6px;}
      div[data-testid="stMetricValue"] {font-variant-numeric: tabular-nums;}
      .small {font-size: 0.82rem; color: #5a6966;}
    </style>
    """,
    unsafe_allow_html=True,
)


# ----------------------------------------------------------------------------- helpers
def band_score(ind, value):
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    num = ind["numeric"]
    cuts = num["cuts"]
    if num["rule"] == "hb":  # higher is better
        for k, c in enumerate(cuts):
            if value <= c:
                return k + 1
        return 5
    for k, c in enumerate(cuts):  # lower is better
        if value <= c:
            return 5 - k
    return 1


def classify(x):
    for lo, hi, name in META["classes"]:
        if x <= hi + 1e-9:
            return name
    return META["classes"][-1][2]


def load_bangkok():
    for d in IND:
        st.session_state[f"s_{d['code']}"] = d["bangkok"]["score"]
        if "numeric" in d:
            st.session_state[f"v_{d['code']}"] = float(d["numeric"]["bangkok_value"])
    st.session_state["city"] = "Bangkok, Thailand (2024–25)"


def clear_all():
    for d in IND:
        st.session_state[f"s_{d['code']}"] = None
        if "numeric" in d:
            st.session_state[f"v_{d['code']}"] = None
    st.session_state["city"] = ""


def current_scores():
    out = {}
    for d in IND:
        sc = None
        if "numeric" in d and st.session_state.get(f"v_{d['code']}") is not None:
            sc = band_score(d, st.session_state[f"v_{d['code']}"])
        if sc is None:
            sc = st.session_state.get(f"s_{d['code']}")
        out[d["code"]] = sc
    return out


def compute(scores, weights, geometric):
    comp = {}
    for c in COMPONENTS:
        vals = [scores[d["code"]] for d in IND if d["component"] == c and scores[d["code"]]]
        if not vals:
            comp[c] = None
        elif geometric:
            comp[c] = math.exp(sum(math.log(v) for v in vals) / len(vals))
        else:
            comp[c] = sum(vals) / len(vals)
    wsum = sum(weights[c] for c in COMPONENTS if comp[c] is not None)
    if wsum <= 0:
        cri = None
    elif geometric:
        cri = math.exp(sum(weights[c] / wsum * math.log(comp[c]) for c in COMPONENTS if comp[c] is not None))
    else:
        cri = sum(weights[c] / wsum * comp[c] for c in COMPONENTS if comp[c] is not None)
    dims = {}
    for k in DIMENSIONS:
        vals = [scores[d["code"]] for d in IND if d["dimension"] == k and scores[d["code"]]]
        dims[k] = sum(vals) / len(vals) if vals else None
    norm_w = {c: (weights[c] / wsum if wsum and comp[c] is not None else 0.0) for c in COMPONENTS}
    return cri, comp, dims, norm_w


if "initialised" not in st.session_state:
    load_bangkok()
    st.session_state["initialised"] = True

# ----------------------------------------------------------------------------- sidebar
with st.sidebar:
    st.markdown("### Assessment settings")
    st.text_input("City or system assessed", key="city", placeholder="e.g. Chiang Mai, Thailand (2025)")
    preset = st.radio("Component weights", ["Expert AHP weights", "Equal weights", "Custom weights"], index=0,
                      help="Expert AHP weights were derived from seven experts with the Analytic Hierarchy Process.")
    if preset == "Expert AHP weights":
        weights = dict(AHP)
    elif preset == "Equal weights":
        weights = {c: 0.25 for c in COMPONENTS}
    else:
        weights = {}
        for c in COMPONENTS:
            weights[c] = st.slider(c, 0.0, 1.0, float(AHP[c]), 0.01, key=f"w_{c}")
        if sum(weights.values()) == 0:
            st.warning("Set at least one weight above zero.")
    geometric = st.radio("Aggregation", ["Arithmetic (compensatory)", "Geometric (non-compensatory)"], index=0).startswith("Geometric")
    st.divider()
    c1, c2 = st.columns(2)
    c1.button("Load Bangkok example", on_click=load_bangkok, width="stretch")
    c2.button("Clear all scores", on_click=clear_all, width="stretch")
    st.divider()
    st.markdown("**Import scores (CSV)**")
    tmpl = pd.DataFrame([{"code": d["code"], "indicator": d["name"], "score_1_to_5": "", "measured_value": ""} for d in IND])
    st.download_button("Download blank template", tmpl.to_csv(index=False).encode("utf-8"), "cri_mswm_template.csv", "text/csv", width="stretch")
    up = st.file_uploader("Upload completed template", type=["csv"], label_visibility="collapsed")
    if up is not None and st.button("Apply uploaded scores", width="stretch"):
        df = pd.read_csv(up)
        n = 0
        for _, r in df.iterrows():
            code = str(r.get("code", "")).strip()
            if code not in BY_CODE:
                continue
            s = pd.to_numeric(r.get("score_1_to_5"), errors="coerce")
            v = pd.to_numeric(r.get("measured_value"), errors="coerce")
            if not pd.isna(s) and 1 <= s <= 5:
                st.session_state[f"s_{code}"] = int(s); n += 1
            if "numeric" in BY_CODE[code] and not pd.isna(v):
                st.session_state[f"v_{code}"] = float(v); n += 1
        st.success(f"Applied {n} values from the file.")

scores = current_scores()
cri, comp, dims, norm_w = compute(scores, weights, geometric)
n_scored = sum(1 for v in scores.values() if v)

# ----------------------------------------------------------------------------- header
st.markdown('<div class="eyebrow">Climate Resilience Index · Municipal Solid Waste Management</div>', unsafe_allow_html=True)
st.title("CRI-MSWM Calculator")
st.markdown(
    '<p class="lede">Assess the climate resilience of a city’s municipal solid waste management system with 41 expert-weighted '
    "indicators across four components and four resilience dimensions. Score each indicator, or enter a measured value where "
    "one applies, and the index updates instantly. The calculator opens with the Bangkok assessment (2024–25) as a worked example.</p>",
    unsafe_allow_html=True,
)

m1, m2, m3, m4 = st.columns(4)
m1.metric("CRI-MSWM (1–5)", "–" if cri is None else f"{cri:.2f}",
          None if cri is None or not st.session_state.get("city", "").startswith("Bangkok") else None)
m2.metric("Score (0–100)", "–" if cri is None else f"{(cri - 1) / 4 * 100:.1f}")
m3.metric("Resilience class", "–" if cri is None else classify(cri))
m4.metric("Indicators scored", f"{n_scored} of {len(IND)}")
if st.session_state.get("city"):
    st.caption(f"Assessment: **{st.session_state['city']}** · Weights: {preset} · Aggregation: {'geometric' if geometric else 'arithmetic'}")
if cri is not None:
    st.info(f"**{classify(cri)} resilience.** {META['class_notes'][classify(cri)]}", icon=":material/info:")

tab_assess, tab_results, tab_method, tab_about = st.tabs(["Indicator assessment", "Results dashboard", "Methodology", "About & citation"])

# ----------------------------------------------------------------------------- assessment
with tab_assess:
    st.markdown("Select a level for each indicator. Where a measured value is entered, the level is derived automatically from the scoring thresholds. Leave an indicator as *Not assessed* to exclude it: its component score becomes the mean of the assessed indicators, "
                "and if a whole component is unassessed the remaining component weights are rescaled.")
    ctabs = st.tabs([f"{c} ({sum(1 for d in IND if d['component'] == c)})" for c in COMPONENTS])
    for ct, c in zip(ctabs, COMPONENTS):
        with ct:
            for d in [x for x in IND if x["component"] == c]:
                code = d["code"]
                with st.container(border=True):
                    a, b = st.columns([3, 2])
                    lvl = scores[code]
                    badge = f'<span class="lvl" style="background:{LEVEL_COLORS[lvl]}">{lvl}</span>' if lvl else '<span class="lvl" style="background:#9aa5a3">–</span>'
                    a.markdown(f"**{code} · {d['name']}** <span class='chip'>{DIMENSIONS[d['dimension']]}</span> &nbsp; {badge}", unsafe_allow_html=True)
                    a.markdown(f"<span class='small'>Bangkok 2024–25: {d['bangkok']['value']} → level {d['bangkok']['score']}</span>", unsafe_allow_html=True)
                    numeric_set = "numeric" in d and st.session_state.get(f"v_{code}") is not None
                    options = [None, 1, 2, 3, 4, 5]
                    labels = {None: "Not assessed", **{i + 1: f"{i + 1} — {t}" for i, t in enumerate(d["levels"])}}
                    b.selectbox("Level", options, key=f"s_{code}", format_func=lambda x, L=labels: L[x],
                                label_visibility="collapsed", disabled=numeric_set,
                                help="Disabled while a measured value is entered." if numeric_set else None)
                    if "numeric" in d:
                        b.number_input(f"Measured value ({d['numeric']['unit']})", key=f"v_{code}", step=None,
                                       placeholder=f"Enter value in {d['numeric']['unit']}", format="%.2f")
                    if d.get("basis"):
                        a.markdown(f"<span class='small'>Framework basis: {d['basis']}</span>", unsafe_allow_html=True)

# ----------------------------------------------------------------------------- results
with tab_results:
    if cri is None:
        st.info("Score at least one indicator to see results.")
    else:
        g1, g2 = st.columns([1, 1.3])
        with g1:
            fig = go.Figure(go.Indicator(
                mode="gauge+number", value=round(cri, 2), number={"valueformat": ".2f", "font": {"size": 44}},
                title={"text": f"CRI-MSWM · {classify(cri)} resilience", "font": {"size": 16}},
                gauge={"axis": {"range": [1, 5], "tickvals": [1, 1.8, 2.6, 3.4, 4.2, 5]},
                       "bar": {"color": "#14201f", "thickness": 0.18},
                       "steps": [{"range": [1, 1.8], "color": "#f1c7c2"}, {"range": [1.8, 2.6], "color": "#f6dcc5"},
                                 {"range": [2.6, 3.4], "color": "#f3e9b8"}, {"range": [3.4, 4.2], "color": "#cfe6cf"},
                                 {"range": [4.2, 5], "color": "#b7dcc6"}],
                       "threshold": {"line": {"color": "#5a6966", "width": 2}, "thickness": 0.8, "value": META["bangkok_cri"]}}))
            fig.update_layout(height=290, margin=dict(l=20, r=20, t=50, b=10))
            st.plotly_chart(fig, width="stretch")
            st.caption(f"Grey marker: Bangkok 2024–25 (CRI = {META['bangkok_cri']:.2f}).")
        with g2:
            cdf = pd.DataFrame({"Component": COMPONENTS, "Score": [comp[c] for c in COMPONENTS], "Weight": [norm_w[c] for c in COMPONENTS]})
            fig2 = go.Figure()
            for _, r in cdf.iterrows():
                fig2.add_bar(y=[f"{r.Component}<br><sup>weight {r.Weight:.3f}</sup>"], x=[r.Score if r.Score else 0], orientation="h",
                             marker_color=COMP_COLORS[r.Component], text=[f"{r.Score:.2f}" if r.Score else "–"], textposition="outside",
                             showlegend=False, hovertemplate=f"{r.Component}: %{{x:.2f}}<extra></extra>")
            fig2.update_layout(title="Component scores", height=290, xaxis=dict(range=[1, 5.4], title="Score (1–5)"),
                               yaxis=dict(autorange="reversed"), margin=dict(l=10, r=20, t=50, b=40), bargap=0.35)
            st.plotly_chart(fig2, width="stretch")
        d1, d2 = st.columns([1.3, 1])
        with d1:
            ddf = pd.DataFrame({"Dimension": list(DIMENSIONS.values()), "Score": [dims[k] for k in DIMENSIONS],
                                "n": [sum(1 for d in IND if d["dimension"] == k) for k in DIMENSIONS]})
            fig3 = go.Figure(go.Bar(y=ddf["Dimension"], x=ddf["Score"].fillna(0), orientation="h", marker_color="#0f6b6f",
                                    text=[f"{s:.2f} (n={n})" if s else "–" for s, n in zip(ddf["Score"], ddf["n"])], textposition="outside"))
            fig3.update_layout(title="Resilience dimensions", height=280, xaxis=dict(range=[1, 5.6], title="Mean indicator score (1–5)"),
                               yaxis=dict(autorange="reversed"), margin=dict(l=10, r=20, t=50, b=40))
            st.plotly_chart(fig3, width="stretch")
        with d2:
            st.markdown("**Weakest indicators (level ≤ 2)**")
            weak = sorted([d for d in IND if scores[d["code"]] and scores[d["code"]] <= 2], key=lambda d: scores[d["code"]])
            if weak:
                for d in weak[:12]:
                    st.markdown(f"<span class='lvl' style='background:{LEVEL_COLORS[scores[d['code']]]}'>{scores[d['code']]}</span> "
                                f"**{d['code']}** {d['name'].split(' (')[0]} <span class='chip'>{d['component']}</span>", unsafe_allow_html=True)
            else:
                st.markdown("No indicator is at level 2 or below.")
        st.markdown("#### Indicator scores")
        table = pd.DataFrame([{"Code": d["code"], "Component": d["component"], "Indicator": d["name"], "Dimension": DIMENSIONS[d["dimension"]],
                               "Measured value": st.session_state.get(f"v_{d['code']}") if "numeric" in d else None,
                               "Level (1–5)": scores[d["code"]]} for d in IND])
        st.dataframe(table, hide_index=True, width="stretch", height=420,
                     column_config={"Level (1–5)": st.column_config.ProgressColumn("Level (1–5)", min_value=0, max_value=5, format="%d"),
                                    "Measured value": st.column_config.NumberColumn("Measured value", format="%.4g")})
        summary = pd.DataFrame([{"Item": "CRI-MSWM (1–5)", "Value": round(cri, 3)}, {"Item": "CRI-MSWM (0–100)", "Value": round((cri - 1) / 4 * 100, 1)},
                                {"Item": "Class", "Value": classify(cri)}] +
                               [{"Item": f"{c} score", "Value": None if comp[c] is None else round(comp[c], 3)} for c in COMPONENTS] +
                               [{"Item": f"{c} weight", "Value": round(norm_w[c], 4)} for c in COMPONENTS] +
                               [{"Item": DIMENSIONS[k], "Value": None if dims[k] is None else round(dims[k], 3)} for k in DIMENSIONS])
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as xw:
            summary.to_excel(xw, sheet_name="Summary", index=False)
            table.to_excel(xw, sheet_name="Indicators", index=False)
        e1, e2 = st.columns(2)
        e1.download_button("Download results (Excel)", buf.getvalue(), "cri_mswm_results.xlsx",
                           "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", width="stretch")
        e2.download_button("Download scores (CSV)", table.to_csv(index=False).encode("utf-8"), "cri_mswm_scores.csv", "text/csv", width="stretch")

# ----------------------------------------------------------------------------- methodology
with tab_method:
    st.markdown("#### Framework")
    st.markdown(
        "The CRI-MSWM combines the IPCC AR6 risk framework with the resilience-capacity literature. Indicators are grouped into four "
        "**components** (Environmental, Technical, Socioeconomic, Governance), which carry the expert weights, and four **resilience "
        "dimensions**: exposure and pressure, absorptive capacity, adaptive capacity and transformative capacity, which provide a diagnostic reading.")
    st.markdown("#### Development")
    st.markdown(
        "1. Literature review: 78 candidate indicators.  \n"
        "2. Expert validation by ten MSWM experts (three-point importance scale; Cronbach’s α = 0.905).  \n"
        "3. Panel review and climate-resilience refinement anchored in IPCC AR6, the Sendai Framework and UNDRR Scorecard, UNEP/OCHA disaster-waste guidance, ISO 14091 and UNFCCC adaptation planning: 41 indicators.  \n"
        "4. Assessment matrix with anchored five-level scales (policy thresholds, equal intervals, literature benchmarks, ordinal descriptors).  \n"
        "5. Component weights from seven experts with the Analytic Hierarchy Process; inconsistent judgments revised by a minimum-perturbation rule; group consistency ratio "
        f"CR = {META['ahp_cr']:.3f}.")
    wdf = pd.DataFrame({"Component": COMPONENTS, "AHP weight": [AHP[c] for c in COMPONENTS],
                        "95% bootstrap interval": [f"{lo:.3f}–{hi:.3f}" for lo, hi in zip(META["bootstrap_low"], META["bootstrap_high"])],
                        "Indicators": [sum(1 for d in IND if d["component"] == c) for c in COMPONENTS]})
    st.dataframe(wdf, hide_index=True, width="stretch")
    st.markdown("#### Calculation")
    st.latex(r"C_c=\frac{1}{n_c}\sum_{i\in c}s_i \qquad \mathrm{CRI}=\sum_c W_c\,C_c \qquad \mathrm{CRI}_{geo}=\prod_c C_c^{\,W_c}")
    st.markdown("where *s<sub>i</sub>* is the 1–5 level of indicator *i*, *C<sub>c</sub>* the score of component *c* and *W<sub>c</sub>* its weight. "
                "Indicators that are not assessed are excluded and the remaining component weights are rescaled.", unsafe_allow_html=True)
    st.markdown("#### Resilience classes")
    st.dataframe(pd.DataFrame([{"Class": n, "CRI-MSWM (1–5)": f"{lo:.2f}–{hi:.2f}" if lo == 1 else f"{lo + 0.01:.2f}–{hi:.2f}",
                                "0–100": f"{(lo - 1) * 25:.0f}–{(hi - 1) * 25:.0f}", "Interpretation": META["class_notes"][n]}
                               for lo, hi, n in reversed(META["classes"])]), hide_index=True, width="stretch",
                 column_config={"Interpretation": st.column_config.TextColumn(width="large")})
    st.markdown("#### Full assessment matrix")
    mx = pd.DataFrame([{"Code": d["code"], "Component": d["component"], "Indicator": d["name"], "Dimension": DIMENSIONS[d["dimension"]],
                        **{f"Level {i + 1}": t for i, t in enumerate(d["levels"])}} for d in IND])
    st.dataframe(mx, hide_index=True, width="stretch", height=420)

# ----------------------------------------------------------------------------- about
with tab_about:
    st.markdown("#### About")
    st.markdown(
        "The CRI-MSWM Calculator implements the Climate Resilience Index for Municipal Solid Waste Management developed in the doctoral research "
        "of Mamadee M. Kamara at the Joint Graduate School of Energy and Environment (JGSEE), King Mongkut’s University of Technology Thonburi, Thailand.")
    st.markdown("#### How to cite")
    st.code("Kamara, M.M., Limpiti, T., Chidthaisong, A., Barua, A., Limsakul, A., Towprayoon, S., Phongphiphat, A. (2026).\n"
            "Expert-weighted climate resilience index for municipal solid waste management: development with group AHP\n"
            "and application to Bangkok, Thailand. Manuscript submitted to Waste Management.", language=None)
    st.markdown("#### Disclaimer")
    st.markdown("Results depend on the quality of the input data. The Bangkok example uses data for 2022–2025 from field interviews with the "
                "Bangkok Metropolitan Administration and secondary sources; see the manuscript for sources and plausible ranges.")
    st.caption(f"Version {META['version']}")
