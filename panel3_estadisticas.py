import streamlit as st
import pandas as pd
import numpy as np

# ==========================================
# PALETA
# ==========================================
P_TEAL   = "#84DCC6"
P_CORAL  = "#FF686B"
P_BORDER = "#e5e7eb"
P_GRAY   = "#6b7280"


def formato_latino(numero, decimales=1):
    if pd.isna(numero): return "0"
    if decimales == 0:
        formateado = f"{int(numero):,}"
    else:
        formateado = f"{numero:,.{decimales}f}"
    return formateado.replace(',', 'X').replace('.', ',').replace('X', '.')


def mostrar_tabla_html(styler):
    html = styler.to_html()
    html = html.replace('<table', '<table class="tabla-arial"')
    st.markdown(html, unsafe_allow_html=True)


def mostrar_nota_outliers():
    st.markdown(
        '<div class="nota-outliers">* Celdas marcadas en rojo presentan valores atípicos (outliers). '
        'Pase el cursor para ver detalles.</div>',
        unsafe_allow_html=True
    )


def render():
    df_trans       = st.session_state.df_transiciones
    df_var         = st.session_state.df_variantes
    periodo_fechas = st.session_state.periodo_fechas

    st.subheader("Análisis Estadístico de Tiempos")
    st.caption(
        f"Distribución de duraciones históricas por recurso, etapa y variante. "
        f"{periodo_fechas}."
    )

    _, col_conf = st.columns([4, 1])
    with col_conf:
        st.number_input(
            "Nivel de confianza (%)", min_value=50, max_value=99, value=95, step=1
        )

    N_MIN_VALIDO = 10

    def calcular_estadisticas(df_agrupado, col_agrupacion, col_valor, rename_col):
        resultados = []
        for grupo, datos in df_agrupado.groupby(col_agrupacion):
            valores = datos[col_valor].dropna().values
            n = len(valores)
            if n == 0:
                continue

            media   = np.mean(valores)
            mediana = np.median(valores)

            ps = {}
            for p in [5, 25, 75, 95]:
                sorted_v = np.sort(valores)
                idx_f    = (p / 100) * (len(sorted_v) - 1)
                lo, hi   = int(np.floor(idx_f)), int(np.ceil(idx_f))
                ps[p]    = sorted_v[lo] + (sorted_v[hi] - sorted_v[lo]) * (idx_f - lo)

            q1, q3    = ps[25], ps[75]
            iqr       = q3 - q1
            fence_sup = q3 + 1.5 * iqr
            fence_inf = q1 - 1.5 * iqr
            n_outliers = int(np.sum((valores > fence_sup) | (valores < fence_inf)))
            pct_out    = (n_outliers / n * 100) if n > 0 else 0.0

            if n < N_MIN_VALIDO:
                fiabilidad = "⚠ Muestra insuficiente"
            elif n_outliers > 0:
                fiabilidad = f"⚠ {n_outliers} atípico{'s' if n_outliers != 1 else ''} ({formato_latino(pct_out, 1)}%)"
            else:
                fiabilidad = "✓ OK"

            resultados.append({
                rename_col: grupo,
                "n":        n,
                "Mediana":  mediana,
                "Media":    media,
                "P5":       ps[5],
                "P25":      ps[25],
                "P75":      ps[75],
                "P95":      ps[95],
                "Calidad":  fiabilidad,
            })
        return pd.DataFrame(resultados)

    fmt_tabla = {
        "Mediana": lambda x: formato_latino(x) + " d",
        "Media":   lambda x: formato_latino(x) + " d",
        "P5":      lambda x: formato_latino(x) + " d",
        "P25":     lambda x: formato_latino(x) + " d",
        "P75":     lambda x: formato_latino(x) + " d",
        "P95":     lambda x: formato_latino(x) + " d",
        "n":       lambda x: formato_latino(x, 0),
    }

    def render_tabla_con_calidad(df_stats, id_col):
        dict_cal = df_stats.set_index(id_col)['Calidad'].to_dict()
        df_stats[id_col] = df_stats[id_col].apply(
            lambda x: (
                f'<span title="{dict_cal.get(x,"")}" style="cursor:help;'
                f'border-bottom:1px dotted {P_CORAL};color:{P_CORAL};">{x}</span>'
                if str(dict_cal.get(x, "")).startswith("⚠") else x
            )
        )
        df_stats.drop(columns=['Calidad'], inplace=True)
        mostrar_tabla_html(df_stats.style.hide(axis="index").format(fmt_tabla))
        mostrar_nota_outliers()

    # -- Sección 1: Por Variante -------------------------------------------
    st.markdown("#### Tiempos totales por variante de proceso")
    st.caption(
        f"Duración total (suma de todas las etapas) por caso, agrupada por variante. "
        f"Solo variantes con ≥ {N_MIN_VALIDO} casos."
    )

    stats_var = calcular_estadisticas(df_var, 'Nombre_Variante', 'Duracion_Total', 'Variante')
    stats_var_validas = stats_var[stats_var['n'] >= N_MIN_VALIDO].sort_values('n', ascending=False)
    n_excluidas = len(stats_var) - len(stats_var_validas)

    if n_excluidas > 0:
        st.caption(f"ℹ {n_excluidas} variante(s) excluida(s) por tener menos de {N_MIN_VALIDO} casos.")

    if not stats_var_validas.empty:
        diccionario_rutas_t2 = df_var.set_index('Nombre_Variante')['Ruta'].to_dict()
        dict_cal_v = stats_var_validas.set_index('Variante')['Calidad'].to_dict()
        stats_var_validas = stats_var_validas.copy()
        stats_var_validas['Variante'] = stats_var_validas['Variante'].apply(
            lambda v: (
                f'<span title="Ruta: {diccionario_rutas_t2.get(v,"")} — {dict_cal_v.get(v,"")}"'
                f' style="cursor:help;border-bottom:1px dotted {P_CORAL};color:{P_CORAL};">{v}</span>'
                if str(dict_cal_v.get(v, "")).startswith("⚠") else
                f'<span title="Ruta: {diccionario_rutas_t2.get(v,"")}"'
                f' style="cursor:help;border-bottom:1px dotted #aaa;">{v}</span>'
            )
        )
        stats_var_validas.drop(columns=['Calidad'], inplace=True)
        mostrar_tabla_html(stats_var_validas.style.hide(axis="index").format(fmt_tabla))
        mostrar_nota_outliers()
    else:
        st.warning(f"No hay variantes con al menos {N_MIN_VALIDO} casos.")

    st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)

    # -- Sección 2: Tiempos por etapa (colapsable) -------------------------
    lbl_etapa = "▼  Tiempos por etapa" if st.session_state.exp_etapa else "▶  Tiempos por etapa"
    if st.button(lbl_etapa, key="btn_exp_etapa", use_container_width=True):
        st.session_state.exp_etapa = not st.session_state.exp_etapa
        st.rerun()
    if st.session_state.exp_etapa:
        st.caption(
            "Días de permanencia en cada etapa: desde el inicio de la etapa "
            "hasta el inicio de la siguiente."
        )
        df_etapas = df_trans[
            (df_trans['Origen'] != 'Inicio proceso') &
            (df_trans['Destino'] != 'Fin proceso')
        ]
        stats_etapas = calcular_estadisticas(df_etapas, 'Origen', 'Duracion', 'Etapa')
        if not stats_etapas.empty:
            render_tabla_con_calidad(stats_etapas, 'Etapa')
        else:
            st.info("Sin datos de etapas.")

    # -- Sección 3: Tiempos por recurso (colapsable) -----------------------
    lbl_rec = "▼  Tiempos por recurso" if st.session_state.exp_rec else "▶  Tiempos por recurso"
    if st.button(lbl_rec, key="btn_exp_rec", use_container_width=True):
        st.session_state.exp_rec = not st.session_state.exp_rec
        st.rerun()
    if st.session_state.exp_rec:
        st.caption("Tiempo promedio que cada recurso demora en completar las etapas asignadas.")
        df_rec_t2 = df_trans[df_trans['Recurso_Origen'] != 'Sistema']
        stats_rec = calcular_estadisticas(df_rec_t2, 'Recurso_Origen', 'Duracion', 'Recurso')
        if not stats_rec.empty:
            render_tabla_con_calidad(stats_rec, 'Recurso')
        else:
            st.info("No se encontraron recursos en los datos.")

    # -- Nota metodológica (colapsable) ------------------------------------
    lbl_met = "▼  Nota metodológica" if st.session_state.exp_metodo else "▶  Nota metodológica"
    if st.button(lbl_met, key="btn_exp_metodo", use_container_width=True):
        st.session_state.exp_metodo = not st.session_state.exp_metodo
        st.rerun()
    if st.session_state.exp_metodo:
        st.markdown(f"""
            <div style="font-size:13px;font-family:Arial,sans-serif;line-height:1.8;
                        background:#f9fafb;border:1px solid {P_BORDER};
                        border-radius:6px;padding:14px 18px;margin-top:4px;">
            <b>Sobre los estimadores presentados</b><br>
            • <b>Mediana (P50)</b>: estimador central preferido para tiempos de proceso
              debido a la asimetría positiva característica de estas distribuciones.
              Es más robusta ante valores extremos que la media aritmética.<br>
            • <b>P5 / P25 / P75 / P95</b>: percentiles empíricos calculados directamente
              de los datos históricos, sin suponer ninguna distribución estadística subyacente.<br>
            • <b>Media</b>: incluida como referencia, pero puede sobreestimar la duración
              típica en presencia de casos extremos (colas largas).<br>
            • <b>Detección de atípicos</b>: método IQR (1,5 × rango intercuartílico).
              Los valores atípicos se señalan en la tabla pero no se eliminan del análisis.<br>
            • <b>Umbral mínimo</b>: grupos con menos de {N_MIN_VALIDO} casos se excluyen
              o marcan como poco fiables. Con n &lt; 10, los percentiles extremos (P5/P95)
              coinciden prácticamente con el mínimo y máximo observados.<br>
            • El <b>tiempo por etapa</b> es el sojourn time: días transcurridos desde
              el inicio de la etapa hasta el inicio de la siguiente.
            </div>
        """, unsafe_allow_html=True)