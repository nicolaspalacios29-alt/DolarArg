import math
import numpy as np
import pandas as pd
import requests
import streamlit as st

st.set_page_config(page_title="Dashboard macro dólar Argentina", layout="wide")

SCENARIOS = {
    "Optimista": {
        "arInfl": {2026: 24.0, 2027: 16.0, 2028: 11.0},
        "usInfl": {2026: 2.8, 2027: 2.5, 2028: 2.3},
        "exports": {2026: 98000.0, 2027: 106000.0, 2028: 118000.0},
        "imports": {2026: 82000.0, 2027: 92000.0, 2028: 102000.0},
        "reserves": {2026: 50000.0, 2027: 60000.0, 2028: 72000.0},
        "crawling": {2026: 18.0, 2027: 12.0, 2028: 9.0},
        "riesgoPais": {2026: 420.0, 2027: 340.0, 2028: 280.0},
        "mercadoDic": {2026: 1650.0, 2027: 1900.0, 2028: 2140.0},
        "itcrm": 92.0,
        "energyBalance": 8.0,
        "netReserves": 18.0,
    },
    "Base": {
        "arInfl": {2026: 27.0, 2027: 19.0, 2028: 15.0},
        "usInfl": {2026: 2.8, 2027: 2.5, 2028: 2.3},
        "exports": {2026: 92700.0, 2027: 100000.0, 2028: 110000.0},
        "imports": {2026: 80200.0, 2027: 88000.0, 2028: 95000.0},
        "reserves": {2026: 50000.0, 2027: 60000.0, 2028: 70000.0},
        "crawling": {2026: 20.0, 2027: 15.0, 2028: 12.0},
        "riesgoPais": {2026: 496.0, 2027: 380.0, 2028: 300.0},
        "mercadoDic": {2026: 1707.0, 2027: 2050.0, 2028: 2350.0},
        "itcrm": 88.0,
        "energyBalance": 10.0,
        "netReserves": 14.0,
    },
    "Estrés": {
        "arInfl": {2026: 32.0, 2027: 25.0, 2028: 20.0},
        "usInfl": {2026: 2.8, 2027: 2.7, 2028: 2.5},
        "exports": {2026: 88000.0, 2027: 93000.0, 2028: 100000.0},
        "imports": {2026: 83500.0, 2027: 92500.0, 2028: 102500.0},
        "reserves": {2026: 44000.0, 2027: 46000.0, 2028: 50000.0},
        "crawling": {2026: 25.0, 2027: 20.0, 2028: 16.0},
        "riesgoPais": {2026: 700.0, 2027: 580.0, 2028: 500.0},
        "mercadoDic": {2026: 1950.0, 2027: 2400.0, 2028: 2900.0},
        "itcrm": 104.0,
        "energyBalance": 5.0,
        "netReserves": 7.0,
    },
}

MONTHS = [
    ("Mar-26", 1),("Abr-26", 2),("May-26", 3),("Jun-26", 4),("Jul-26", 5),("Ago-26", 6),("Sep-26", 7),("Oct-26", 8),("Nov-26", 9),("Dic-26", 10),
    ("Ene-27", 11),("Feb-27", 12),("Mar-27", 13),("Abr-27", 14),("May-27", 15),("Jun-27", 16),("Jul-27", 17),("Ago-27", 18),("Sep-27", 19),("Oct-27", 20),("Nov-27", 21),("Dic-27", 22),
    ("Ene-28", 23),("Feb-28", 24),("Mar-28", 25),("Abr-28", 26),("May-28", 27),("Jun-28", 28),("Jul-28", 29),("Ago-28", 30),("Sep-28", 31),("Oct-28", 32),("Nov-28", 33),("Dic-28", 34),
]

def monthly_rate(a):
    return math.pow(1 + a / 100.0, 1 / 12.0) - 1

def year_from_label(label):
    return 2026 if label.endswith("-26") else 2027 if label.endswith("-27") else 2028

def percentile(values, p):
    s = sorted(values)
    return s[int((len(s)-1) * p)]

def fmt_ars(n):
    return f"$ {n:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def fmt_num(n, d=1):
    return f"{n:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")

def fmt_usd_mm(n):
    return f"USD {fmt_num(n,1)} MM"

def mercado_path(idx, spot, assumptions, year):
    if year == 2026:
        start_market, start_idx, end_market, end_idx = spot, 1, assumptions["mercadoDic"][2026], 10
    elif year == 2027:
        start_market, start_idx, end_market, end_idx = assumptions["mercadoDic"][2026], 11, assumptions["mercadoDic"][2027], 22
    else:
        start_market, start_idx, end_market, end_idx = assumptions["mercadoDic"][2027], 23, assumptions["mercadoDic"][2028], 34

    if end_idx == start_idx:
        return end_market

    progress = (idx - start_idx) / (end_idx - start_idx)
    progress = max(0.0, min(1.0, progress))
    return start_market + (end_market - start_market) * progress

@st.cache_data(ttl=300)
def fetch_dolarapi():
    out = {"status": "ready", "values": {}, "errors": []}
    try:
        data = requests.get("https://dolarapi.com/v1/dolares", timeout=20).json()
        oficial = next((x for x in data if x.get("casa") == "oficial"), None)
        mep = next((x for x in data if x.get("casa") == "bolsa"), None)
        ccl = next((x for x in data if x.get("casa") == "contadoconliqui"), None)
        mayorista = next((x for x in data if x.get("casa") == "mayorista"), None)
        blue = next((x for x in data if x.get("casa") == "blue"), None)
        out["values"] = {
            "oficial": oficial,
            "mep": mep,
            "ccl": ccl,
            "mayorista": mayorista,
            "blue": blue,
        }
    except Exception as e:
        out["status"] = "error"
        out["errors"].append(f"DolarApi: {e}")
    return out

@st.cache_data(ttl=3600)
def fetch_bcra():
    out = {"status": "ready", "sources": [], "values": {}, "errors": []}
    try:
        bcra = requests.get("https://api.bcra.gob.ar/estadisticas/v4.0/monetarias?limit=500", timeout=20).json()
        rows = bcra.get("results", [])

        def find_bcra(keyword):
            hit = next((r for r in rows if keyword in str(r.get("descripcion", "")).lower()), None)
            if not hit:
                raise ValueError(f"No encontré {keyword} en BCRA")
            var_id = hit["idVariable"]
            detail = requests.get(f"https://api.bcra.gob.ar/estadisticas/v4.0/monetarias/{var_id}?limit=10", timeout=20).json()
            latest = detail.get("results", [{}])[0].get("detalle", [])[0]
            return {
                "id": var_id,
                "fecha": latest["fecha"],
                "valor": float(latest["valor"]),
                "descripcion": hit.get("descripcion"),
            }

        out["values"]["fx"] = find_bcra("tipo de cambio")
        out["values"]["reserves"] = find_bcra("reservas")
        out["values"]["monetary_base"] = find_bcra("base monetaria")
        out["sources"].append("BCRA v4.0 monetarias")
    except Exception as e:
        out["errors"].append(f"BCRA: {e}")

    if out["errors"] and not out["values"]:
        out["status"] = "error"
    elif out["errors"]:
        out["status"] = "partial"
    return out

def build_series(spot, assumptions, base_monetaria, piso_banda, techo_banda, weights):
    prev_final = spot
    current_reserves = assumptions["reserves"][2026]
    current_bm = base_monetaria
    cumulative_ppp = spot
    k = spot / (base_monetaria / assumptions["reserves"][2026])
    out = []

    for mes, idx in MONTHS:
        year = year_from_label(mes)
        m_infl_ar = monthly_rate(assumptions["arInfl"][year])
        m_infl_us = monthly_rate(assumptions["usInfl"][year])
        saldo_mensual = (assumptions["exports"][year] - assumptions["imports"][year]) / 12.0
        reserve_target = assumptions["reserves"][year]
        riesgo = assumptions["riesgoPais"][year]

        cumulative_ppp *= (1 + m_infl_ar) / (1 + m_infl_us)
        current_reserves = current_reserves + (saldo_mensual * 0.30) + ((reserve_target - current_reserves) * 0.12)
        current_bm *= (1 + m_infl_ar * 0.75)
        monetario = k * (current_bm / current_reserves)
        mercado = mercado_path(idx, spot, assumptions, year)

        riesgo_factor = 1 + ((riesgo - 450) / 1000.0) * 0.28
        tc_pre = (
            weights["ppp"] * cumulative_ppp
            + weights["monetario"] * monetario
            + weights["mercado"] * mercado
            + weights["regimen"] * prev_final
            + weights["riesgo"] * (spot * riesgo_factor)
        )

        band_sup = techo_banda * math.pow(1.01, idx - 1)
        band_inf = piso_banda * math.pow(1.005, idx - 1)
        final = max(band_inf, min(tc_pre, band_sup))
        prev_final = final

        out.append({
            "Orden": idx,
            "Mes": mes,
            "PPP": round(cumulative_ppp, 1),
            "Monetario": round(monetario, 1),
            "Mercado": round(mercado, 1),
            "Final": round(final, 1),
            "Reservas": round(current_reserves, 0),
        })
    return pd.DataFrame(out)

def montecarlo(assumptions, spot, base_monetaria, piso_banda, techo_banda, weights, runs=300):
    r26, r27, r28 = [], [], []
    for _ in range(runs):
        shock = {
            **assumptions,
            "arInfl": {
                2026: assumptions["arInfl"][2026] + (np.random.rand() - 0.5) * 4,
                2027: assumptions["arInfl"][2027] + (np.random.rand() - 0.5) * 5,
                2028: assumptions["arInfl"][2028] + (np.random.rand() - 0.5) * 5,
            },
            "exports": {
                2026: assumptions["exports"][2026] * (1 + (np.random.rand() - 0.5) * 0.06),
                2027: assumptions["exports"][2027] * (1 + (np.random.rand() - 0.5) * 0.08),
                2028: assumptions["exports"][2028] * (1 + (np.random.rand() - 0.5) * 0.10),
            },
            "imports": {
                2026: assumptions["imports"][2026] * (1 + (np.random.rand() - 0.5) * 0.06),
                2027: assumptions["imports"][2027] * (1 + (np.random.rand() - 0.5) * 0.08),
                2028: assumptions["imports"][2028] * (1 + (np.random.rand() - 0.5) * 0.10),
            },
            "reserves": {
                2026: assumptions["reserves"][2026] * (1 + (np.random.rand() - 0.5) * 0.08),
                2027: assumptions["reserves"][2027] * (1 + (np.random.rand() - 0.5) * 0.10),
                2028: assumptions["reserves"][2028] * (1 + (np.random.rand() - 0.5) * 0.12),
            },
            "riesgoPais": {
                2026: assumptions["riesgoPais"][2026] + (np.random.rand() - 0.5) * 120,
                2027: assumptions["riesgoPais"][2027] + (np.random.rand() - 0.5) * 140,
                2028: assumptions["riesgoPais"][2028] + (np.random.rand() - 0.5) * 160,
            },
            "mercadoDic": {
                2026: assumptions["mercadoDic"][2026] * (1 + (np.random.rand() - 0.5) * 0.05),
                2027: assumptions["mercadoDic"][2027] * (1 + (np.random.rand() - 0.5) * 0.06),
                2028: assumptions["mercadoDic"][2028] * (1 + (np.random.rand() - 0.5) * 0.08),
            },
        }
        run = build_series(spot, shock, base_monetaria, piso_banda, techo_banda, weights)
        r26.append(run.iloc[9]["Final"])
        r27.append(run.iloc[21]["Final"])
        r28.append(run.iloc[33]["Final"])

    return {
        "2026": {"p10": percentile(r26, .1), "p50": percentile(r26, .5), "p90": percentile(r26, .9)},
        "2027": {"p10": percentile(r27, .1), "p50": percentile(r27, .5), "p90": percentile(r27, .9)},
        "2028": {"p10": percentile(r28, .1), "p50": percentile(r28, .5), "p90": percentile(r28, .9)},
    }

st.title("dashboard macro dólar argentina")
st.caption("v7: integración API para oficial, MEP y CCL")

with st.sidebar:
    scenario = st.selectbox("Escenario", list(SCENARIOS.keys()), index=1)

    live_bcra = fetch_bcra()
    live_dolar = fetch_dolarapi()

    if st.button("actualizar datos"):
        fetch_bcra.clear()
        fetch_dolarapi.clear()
        live_bcra = fetch_bcra()
        live_dolar = fetch_dolarapi()

    if live_bcra["status"] == "error":
        st.error("BCRA no respondió. El modelo sigue con defaults.")
    elif live_bcra["status"] == "partial":
        st.warning("BCRA respondió parcialmente.")
    else:
        st.success("BCRA cargado.")

    if live_dolar["status"] == "error":
        st.warning("DolarApi no respondió. MEP/CCL usarán fallback manual.")

    assumptions = {k: (v.copy() if isinstance(v, dict) else v) for k, v in SCENARIOS[scenario].items()}

    bcra_fx = live_bcra["values"].get("fx", {}).get("valor", 1392.99)
    bcra_base = live_bcra["values"].get("monetary_base", {}).get("valor", 40737.0)
    bcra_res = live_bcra["values"].get("reserves", {}).get("valor")

    if bcra_res is not None:
        assumptions["reserves"][2026] = max(assumptions["reserves"][2026], bcra_res)

    mep_default = float(live_dolar["values"].get("mep", {}).get("venta", 1419.78)) if live_dolar["values"].get("mep") else 1419.78
    ccl_default = float(live_dolar["values"].get("ccl", {}).get("venta", 1469.98)) if live_dolar["values"].get("ccl") else 1469.98
    blue_default = float(live_dolar["values"].get("blue", {}).get("venta", 1425.00)) if live_dolar["values"].get("blue") else 1425.00

    spot = st.number_input("spot oficial", value=float(bcra_fx), step=1.0)
    mep_input = st.number_input("dólar MEP", value=float(mep_default), step=1.0)
    ccl_input = st.number_input("dólar CCL", value=float(ccl_default), step=1.0)
    blue_input = st.number_input("dólar blue", value=float(blue_default), step=1.0)
    base_monetaria = st.number_input("base monetaria", value=float(bcra_base), step=100.0)
    piso_banda = st.number_input("piso banda", value=855.26, step=10.0)
    techo_banda = st.number_input("techo banda", value=1632.48, step=10.0)
    big_mac_ars = st.number_input("big mac ARS", value=8500.0, step=100.0)
    big_mac_usd = st.number_input("big mac USD", value=6.12, step=0.1)

official = spot
mep = mep_input
ccl = ccl_input
blue = blue_input
brecha = (mep / official - 1) * 100
brecha_ccl = (ccl / official - 1) * 100
big_mac_fx = big_mac_ars / big_mac_usd
saldo_2026 = assumptions["exports"][2026] - assumptions["imports"][2026]

weights = {"ppp": 0.35, "monetario": 0.25, "mercado": 0.20, "regimen": 0.10, "riesgo": 0.10}
df = build_series(spot, assumptions, base_monetaria, piso_banda, techo_banda, weights)
mc = montecarlo(assumptions, spot, base_monetaria, piso_banda, techo_banda, weights)
fair_value = df.iloc[9]["PPP"] * 0.40 + df.iloc[9]["Monetario"] * 0.35 + df.iloc[9]["Mercado"] * 0.25
atraso = (fair_value / official - 1) * 100

r1 = st.columns(4)
r1[0].metric("oficial", fmt_ars(official))
r1[1].metric("MEP", fmt_ars(mep))
r1[2].metric("CCL", fmt_ars(ccl))
r1[3].metric("blue", fmt_ars(blue))

r1b = st.columns(4)
r1b[0].metric("brecha MEP", f"{fmt_num(brecha,1)}%")
r1b[1].metric("brecha CCL", f"{fmt_num(brecha_ccl,1)}%")
r1b[2].metric("dic-2026", fmt_ars(df.iloc[9]["Final"]))
r1b[3].metric("dic-2027", fmt_ars(df.iloc[21]["Final"]))

r2 = st.columns(4)
r2[0].metric("dic-2028", fmt_ars(df.iloc[33]["Final"]))
r2[1].metric("inflación AR", f"{fmt_num(assumptions['arInfl'][2026],1)}%")
r2[2].metric("inflación US", f"{fmt_num(assumptions['usInfl'][2026],1)}%")
r2[3].metric("reservas netas", f"USD {fmt_num(assumptions['netReserves'],1)} B")

r2b = st.columns(4)
r2b[0].metric("saldo comercial", fmt_usd_mm(saldo_2026 / 1000))
r2b[1].metric("riesgo país", f"{fmt_num(assumptions['riesgoPais'][2026],0)}")
r2b[2].metric("ITCRM/TCR", f"{fmt_num(assumptions['itcrm'],1)}")
r2b[3].metric("big mac FX", fmt_ars(big_mac_fx))

tab1, tab2, tab3, tab4, tab5 = st.tabs(["pantalla principal", "probabilidades", "valuación", "datos reales", "tabla"])

with tab1:
    c1, c2 = st.columns([2.4, 1])
    with c1:
        st.subheader("trayectoria mensual")
        df_chart = df.sort_values("Orden").copy()
        df_chart["Fecha"] = pd.date_range(start="2026-03-01", periods=len(df_chart), freq="MS")
        chart_df = df_chart.set_index("Fecha")[["Final", "PPP", "Monetario", "Mercado"]]
        st.line_chart(chart_df)

    with c2:
        st.subheader("drivers clave")
        drivers_df = pd.DataFrame({
            "Variable": ["brecha MEP", "brecha CCL", "crawling 2026", "balance energético", "atraso cambiario"],
            "Valor": [
                f"{fmt_num(brecha,1)}%",
                f"{fmt_num(brecha_ccl,1)}%",
                f"{fmt_num(assumptions['crawling'][2026],1)}%",
                f"USD {fmt_num(assumptions['energyBalance'],1)} B",
                f"{fmt_num(atraso,1)}%",
            ]
        })
        st.dataframe(drivers_df, use_container_width=True, hide_index=True)

with tab2:
    cols = st.columns(3)
    for col, year in zip(cols, ["2026", "2027", "2028"]):
        with col:
            st.subheader(f"dic-{year}")
            st.metric("P10", fmt_ars(mc[year]["p10"]))
            st.metric("P50", fmt_ars(mc[year]["p50"]))
            st.metric("P90", fmt_ars(mc[year]["p90"]))

with tab3:
    vals = pd.DataFrame({
        "Método": ["PPP dic-2026", "Monetario dic-2026", "Mercado dic-2026", "Big Mac", "Fair value blended"],
        "Valor": [df.iloc[9]["PPP"], df.iloc[9]["Monetario"], df.iloc[9]["Mercado"], big_mac_fx, fair_value],
    })
    st.dataframe(vals, use_container_width=True, hide_index=True)
    st.metric("atraso / sobrevaluación estimada", f"{fmt_num(atraso,1)}%")

with tab4:
    st.write("BCRA")
    st.json(live_bcra)
    st.write("DolarApi")
    st.json(live_dolar)

with tab5:
    st.dataframe(df.drop(columns=["Orden"]), use_container_width=True)
