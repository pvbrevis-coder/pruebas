import streamlit as st
import pandas as pd
import numpy as np
import streamlit.components.v1 as components

# ==========================================
# PALETA
# ==========================================
P_TEAL   = "#84DCC6"
P_MINT   = "#A5FFD6"
P_SALMON = "#FFA69E"
P_CORAL  = "#FF686B"
P_DARK   = "#1f2937"
P_MID    = "#374151"
P_GRAY   = "#6b7280"


def formato_latino(numero, decimales=1):
    if pd.isna(numero): return "0"
    if decimales == 0:
        formateado = f"{int(numero):,}"
    else:
        formateado = f"{numero:,.{decimales}f}"
    return formateado.replace(',', 'X').replace('.', ',').replace('X', '.')


def render():
    df_var = st.session_state.df_variantes

    st.subheader("Pronóstico por variante de proceso")
    st.caption(
        "Estimaciones basadas en el historial de casos, asumiendo condiciones "
        "similares a futuro. Haz clic en una tarjeta para ver el detalle."
    )

    # ── Funciones estadísticas ────────────────────────────────────────────
    def emp_percentil(valores, p):
        sorted_v = np.sort(valores)
        idx      = (p / 100) * (len(sorted_v) - 1)
        lo, hi   = int(np.floor(idx)), int(np.ceil(idx))
        return sorted_v[lo] + (sorted_v[hi] - sorted_v[lo]) * (idx - lo)

    def fit_lognormal(valores):
        logs = np.log(np.maximum(0.01, valores))
        return logs.mean(), logs.std(ddof=1)

    def lognormal_percentil(mu, sigma, p):
        from scipy.stats import norm as _norm
        return np.exp(mu + sigma * _norm.ppf(p / 100))

    def lognormal_fit_ok(valores):
        if len(valores) < 8:
            return False
        logs = np.log(np.maximum(0.01, valores))
        s2   = logs.std()
        if s2 == 0:
            return False
        skew = np.abs(((logs - logs.mean()) ** 3).mean() / s2 ** 3)
        return skew < 1.5

    def calcular_stats_pronostico(valores):
        n           = len(valores)
        advertencia = None
        nota_metodo = ""

        if n >= 100:
            metodo      = "empirico"
            nota_metodo = (
                f"Percentiles empíricos (n={n}). Con una muestra amplia, los percentiles "
                "se calculan directamente de los datos históricos sin suponer distribución. "
                "Resultados estables a este tamaño de muestra."
            )
            ps = {p: emp_percentil(valores, p) for p in [10, 25, 50, 75, 90]}

        elif n >= 30:
            if lognormal_fit_ok(valores):
                metodo    = "lognormal"
                mu, sigma = fit_lognormal(valores)
                nota_metodo = (
                    f"Lognormal MLE (n={n}). Se ajustó una distribución lognormal "
                    "por máxima verosimilitud. La bondad de ajuste fue verificada "
                    "(sesgo de los logaritmos < 1,5) y resultó satisfactoria."
                )
                ps = {p: lognormal_percentil(mu, sigma, p) for p in [10, 25, 50, 75, 90]}
            else:
                metodo      = "empirico"
                nota_metodo = (
                    f"Percentiles empíricos (n={n}). Se intentó ajuste lognormal "
                    "pero no fue satisfactorio. Se usan percentiles empíricos."
                )
                advertencia = (
                    "Ajuste estadístico no satisfactorio — percentiles empíricos "
                    "pueden ser imprecisos en los extremos con esta muestra."
                )
                ps = {p: emp_percentil(valores, p) for p in [10, 25, 50, 75, 90]}
            if n < 60:
                nota_n = f"Muestra moderada ({n} casos) — estimaciones en extremos con mayor margen de error."
                advertencia = (advertencia + " " + nota_n) if advertencia else nota_n

        else:
            metodo      = "empirico"
            nota_metodo = (
                f"Percentiles empíricos (n={n}). Muestra insuficiente para ajuste "
                "estadístico confiable. Las estimaciones son referenciales."
            )
            advertencia = (
                f"Muestra insuficiente ({n} casos). "
                "Interpretar con cautela."
            )
            ps = {p: emp_percentil(valores, p) for p in [10, 25, 50, 75, 90]}

        if advertencia:
            nota_metodo = nota_metodo + " — " + advertencia

        return {
            'n': n, 'metodo': metodo, 'nota_metodo': nota_metodo,
            'p10': round(ps[10]), 'p25': round(ps[25]), 'p50': round(ps[50]),
            'p75': round(ps[75]), 'p90': round(ps[90]),
        }

    # ── Calcular estadísticas ─────────────────────────────────────────────
    N_MIN_PRON = 10
    variantes_stats = []
    diccionario_rutas_pron = df_var.set_index('Nombre_Variante')['Ruta'].to_dict()
    total_casos_pron       = len(df_var)

    for var_nombre, grp in df_var.groupby('Nombre_Variante'):
        vals = grp['Duracion_Total'].dropna().values
        if len(vals) < N_MIN_PRON:
            continue
        st_v = calcular_stats_pronostico(vals)
        st_v['variante'] = var_nombre
        st_v['ruta']     = diccionario_rutas_pron.get(var_nombre, '')
        st_v['casos']    = len(vals)
        st_v['pct']      = (len(vals) / total_casos_pron) * 100
        variantes_stats.append(st_v)

    variantes_stats.sort(key=lambda x: x['casos'], reverse=True)

    n_excl_pron = sum(
        1 for _, g in df_var.groupby('Nombre_Variante')
        if len(g['Duracion_Total'].dropna()) < N_MIN_PRON
    )
    if n_excl_pron > 0:
        st.caption(
            f"ℹ {n_excl_pron} variante(s) excluida(s) por tener menos de {N_MIN_PRON} casos."
        )

    if not variantes_stats:
        st.info(f"No hay variantes con al menos {N_MIN_PRON} casos para generar pronósticos.")
        return

    max_dias_pron = max(v['p90'] for v in variantes_stats) * 1.10

    def riesgo_variante(st_v):
        cv = ((st_v['p90'] - st_v['p10']) / st_v['p50']
              if st_v['p50'] > 0 else 99)
        if st_v['p50'] <= 10 and cv < 1.2: return "bajo"
        if st_v['p50'] <= 20 and cv < 1.8: return "medio"
        return "alto"

    RIESGO_CFG = {
        "bajo":  {"label": "Predecible",        "border": P_TEAL,   "text": "#1a6b5a"},
        "medio": {"label": "Moderado",          "border": P_SALMON, "text": "#7a3030"},
        "alto":  {"label": "Alta variabilidad", "border": P_CORAL,  "text": "#7a1515"},
    }

    # ── Generar tarjetas HTML ─────────────────────────────────────────────
    cards_inner = ""
    for i_v, st_v in enumerate(variantes_stats):
        r    = riesgo_variante(st_v)
        cfg  = RIESGO_CFG[r]
        var  = st_v['variante']
        p10, p25, p50, p75, p90 = (
            st_v['p10'], st_v['p25'], st_v['p50'], st_v['p75'], st_v['p90']
        )
        n_casos  = st_v['n']
        pct_txt  = formato_latino(st_v['pct'], 1)
        ruta_txt = st_v['ruta']
        nota_txt = st_v['nota_metodo'].replace("'", "&#39;").replace('"', "&quot;")
        cid = f"card_{i_v}"

        pb10 = min(100, (p10 / max_dias_pron) * 100)
        pb25 = min(100, (p25 / max_dias_pron) * 100)
        pb50 = min(100, (p50 / max_dias_pron) * 100)
        pb75 = min(100, (p75 / max_dias_pron) * 100)
        pb90 = min(100, (p90 / max_dias_pron) * 100)
        w80  = max(0, pb90 - pb10)
        w50  = max(0, pb75 - pb25)

        dot_ok  = P_TEAL
        dot_mid = "#5aab9a"
        dot_bad = P_CORAL

        cards_inner += f"""
        <div class="card" id="{cid}"
             data-border="{cfg['border']}"
             onclick="toggleCard('{cid}')">
            <div class="header">
                <div style="flex:1;min-width:0;">
                    <div class="meta">
                        <span class="varname">{var}</span>
                        <span class="badge"
                              style="color:{cfg['text']};border-color:{cfg['border']};">
                            {cfg['label']}
                        </span>
                        <span class="ncasos">
                            {n_casos} casos &middot; {pct_txt}% del total
                        </span>
                    </div>
                    <div class="ruta">{ruta_txt}</div>
                </div>
                <div style="display:flex;align-items:flex-start;gap:8px;flex-shrink:0;">
                    <div style="text-align:right;">
                        <div class="median-num"
                             style="color:{cfg['border']};">{p50}<span
                             style="font-size:13px;color:#6b7280;"> d&#237;as</span></div>
                        <div class="median-label">duraci&#243;n t&#237;pica</div>
                    </div>
                    <div class="chevron">&#9660;</div>
                </div>
            </div>
            <div class="barra">
                <div class="b-fondo"></div>
                <div style="position:absolute;top:20px;left:{pb10:.1f}%;
                            width:{w80:.1f}%;height:8px;
                            background:{P_MINT};border-radius:4px;"></div>
                <div style="position:absolute;top:20px;left:{pb25:.1f}%;
                            width:{w50:.1f}%;height:8px;
                            background:{P_TEAL};border-radius:4px;"></div>
                <div style="position:absolute;top:16px;left:{pb50:.1f}%;
                            transform:translateX(-50%);width:3px;height:16px;
                            background:#1a6b5a;border-radius:2px;"></div>
                <div style="position:absolute;top:0;left:{pb50:.1f}%;
                            transform:translateX(-50%);font-size:11px;
                            color:#1a6b5a;font-weight:bold;white-space:nowrap;">
                    {p50}d
                </div>
            </div>
            <div class="b-labels">
                <span>P10: {p10}d</span>
                <span style="color:#6b7280;">
                    <b style="color:{P_TEAL};">&#9632;</b>
                    50% entre {p25}&#8211;{p75}d &nbsp;
                    <b style="color:{P_MINT};">&#9632;</b>
                    80% entre {p10}&#8211;{p90}d
                </span>
                <span>P90: {p90}d</span>
            </div>
            <div class="detail" onclick="event.stopPropagation()">
                <hr style="border:none;border-top:1px solid {cfg['border']}44;margin:12px 0;">
                <div class="narrativa-titulo">
                    Estimaci&#243;n para un caso futuro de este tipo
                </div>
                <div class="narrativa">
                    <div>
                        <span class="dot" style="background:{dot_ok};"></span>
                        <b>En la mitad de los casos</b>, el proceso se resuelve
                        en <b>{p50} d&#237;as o menos</b>.
                    </div>
                    <div>
                        <span class="dot" style="background:{dot_mid};"></span>
                        <b>8 de cada 10 casos</b> se resuelven entre
                        <b>{p10} y {p90} d&#237;as</b>.
                    </div>
                    <div>
                        <span class="dot" style="background:{dot_bad};"></span>
                        <b>1 de cada 10 casos</b> supera los
                        <b style="color:{P_CORAL};">{p90} d&#237;as</b>.
                    </div>
                </div>
                <div class="nota-wrap">
                    <span class="nota-label">Nota metodol&#243;gica</span>
                    <div class="tooltip-box">{nota_txt}</div>
                </div>
            </div>
        </div>"""

    n_cards = len(variantes_stats)
    all_cards_html = f"""<!DOCTYPE html><html>
    <head><meta charset="utf-8">
    <style>
        *{{box-sizing:border-box;}}
        body{{margin:0;padding:0;font-family:Arial,sans-serif;}}
        .leyenda{{display:flex;gap:10px;flex-wrap:wrap;
                  margin-bottom:14px;font-size:12px;}}
        .leyenda-item{{display:flex;align-items:center;gap:6px;
                       background:#f8fafc;border:1px solid #e2e8f0;
                       border-radius:6px;padding:5px 10px;color:#6b7280;}}
        .cards{{display:flex;flex-direction:column;gap:10px;}}
        .card{{background:#F9F9F9;border:2px solid #e5e7eb;border-radius:10px;
               padding:14px 18px;box-shadow:0 1px 4px rgba(0,0,0,0.06);
               cursor:pointer;transition:border-color 0.15s;}}
        .card.open{{cursor:default;}}
        .header{{display:flex;justify-content:space-between;
                 align-items:flex-start;gap:12px;margin-bottom:6px;}}
        .meta{{display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin-bottom:4px;}}
        .badge{{font-size:11px;font-weight:bold;padding:2px 8px;
                border-radius:20px;background:#fff;border:1px solid;}}
        .ncasos{{font-size:12px;color:#6b7280;}}
        .ruta{{font-size:12px;color:#9ca3af;font-family:monospace;
               margin-bottom:12px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}}
        .varname{{font-weight:bold;font-size:15px;color:{P_DARK};}}
        .median-num{{font-size:24px;font-weight:bold;}}
        .median-label{{font-size:11px;color:#9ca3af;text-align:right;}}
        .barra{{position:relative;height:38px;margin-bottom:4px;}}
        .b-fondo{{position:absolute;top:20px;left:0;right:0;height:8px;
                  background:#e8ecf0;border-radius:4px;}}
        .b-labels{{display:flex;justify-content:space-between;
                   font-size:11px;color:#9ca3af;margin-top:2px;}}
        .detail{{display:none;}}
        .card.open .detail{{display:block;}}
        .narrativa-titulo{{font-size:13px;font-weight:bold;color:{P_MID};
                           margin-bottom:10px;}}
        .narrativa{{font-size:13px;line-height:2.0;color:{P_MID};margin-bottom:14px;}}
        .dot{{display:inline-block;width:12px;height:12px;border-radius:50%;
              vertical-align:middle;margin-right:8px;}}
        .nota-wrap{{background:#f8fafc;border:1px solid #e2e8f0;border-radius:6px;
                    padding:9px 12px;font-size:12px;display:inline-block;position:relative;}}
        .nota-label{{font-weight:bold;color:#0369a1;
                     border-bottom:1px dotted #0369a1;cursor:help;}}
        .tooltip-box{{display:none;position:absolute;bottom:calc(100% + 8px);left:0;
                      background:{P_DARK};color:#f9fafb;border-radius:8px;
                      padding:10px 14px;font-size:12px;line-height:1.6;width:380px;
                      z-index:9999;box-shadow:0 4px 16px rgba(0,0,0,0.25);
                      pointer-events:none;}}
        .nota-wrap:hover .tooltip-box{{display:block;}}
        .chevron{{font-size:12px;color:#9ca3af;flex-shrink:0;margin-top:4px;
                  transition:transform 0.2s;user-select:none;}}
        .card.open .chevron{{transform:rotate(180deg);}}
    </style>
    </head><body>
    <div class="leyenda">
        <div class="leyenda-item">
            <div style="width:32px;height:8px;background:{P_MINT};border-radius:3px;"></div>
            80% de los casos (P10&#8211;P90)
        </div>
        <div class="leyenda-item">
            <div style="width:32px;height:8px;background:{P_TEAL};border-radius:3px;"></div>
            50% de los casos (P25&#8211;P75)
        </div>
        <div class="leyenda-item">
            <div style="width:3px;height:16px;background:#1a6b5a;border-radius:2px;"></div>
            Duraci&#243;n t&#237;pica (mediana)
        </div>
    </div>
    <div class="cards">
        {cards_inner}
    </div>
    <script>
        function toggleCard(id) {{
            var card = document.getElementById(id);
            var isOpen = card.classList.contains('open');
            card.classList.toggle('open');
            var border = card.getAttribute('data-border');
            card.style.borderColor = isOpen ? '#e5e7eb' : border;
            resize();
        }}
        function resize() {{
            var h = document.body.scrollHeight + 20;
            window.parent.postMessage(
                {{isStreamlitMessage:true, type:'streamlit:setFrameHeight', height:h}},
                '*'
            );
        }}
        window.addEventListener('load', function() {{ setTimeout(resize, 100); }});
    </script>
    </body></html>"""

    altura_inicial = n_cards * 135 + 60
    components.html(all_cards_html, height=altura_inicial, scrolling=True)