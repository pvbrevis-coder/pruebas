import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import statistics

# ==========================================
# PALETA
# ==========================================
P_TEAL   = "#84DCC6"
P_MINT   = "#A5FFD6"
P_SALMON = "#FFA69E"
P_CORAL  = "#FF686B"
P_GRAY   = "#6b7280"

def formato_latino(numero, decimales=1):
    if pd.isna(numero): return "0"
    if decimales == 0: formateado = f"{int(numero):,}"
    else: formateado = f"{numero:,.{decimales}f}"
    return formateado.replace(',', 'X').replace('.', ',').replace('X', '.')

def mostrar_tabla_html(styler):
    html = styler.to_html()
    html = html.replace('<table', '<table class="tabla-arial"')
    st.markdown(html, unsafe_allow_html=True)

def bloque_info(color_borde, bg_rgba, texto_html):
    st.markdown(
        f'<div style="background:{bg_rgba}; border-left:4px solid {color_borde}; color:var(--text-color); '
        f'padding:10px 14px;border-radius:6px;font-size:13px;">'
        f'{texto_html}</div>', unsafe_allow_html=True
    )

def render():
    df_trans = st.session_state.df_transiciones
    df_var   = st.session_state.df_variantes

    st.markdown("### Diagnóstico")
    st.caption("Diagnóstico at-a-glance para la toma de decisiones. Basado en el universo completo de casos cargados.")

    N_MIN_RESUMEN = 5
    z_resumen = statistics.NormalDist().inv_cdf((1 + 95 / 100) / 2)

    df_etapas_res = df_trans[(df_trans['Origen'] != 'Inicio proceso') & (df_trans['Destino'] != 'Fin proceso')]
    etapa_stats = df_etapas_res.groupby('Origen').agg(Promedio=('Duracion', 'mean'), Casos=('ID', 'count')).reset_index().rename(columns={'Origen': 'Etapa'})
    etapa_stats = etapa_stats[etapa_stats['Promedio'] > 0].sort_values('Promedio', ascending=False)

    def pred_variante(valores, z):
        n = len(valores)
        if n < N_MIN_RESUMEN: return None, None, None
        media = np.mean(valores)
        margen = z * (np.std(valores, ddof=1) if n > 1 else 0.0) * np.sqrt(1 + 1 / n)
        return media, max(0, media - margen), media + margen

    pronostico_rows = []
    diccionario_rutas_res = df_var.set_index('Nombre_Variante')['Ruta'].to_dict()
    for var, grp in df_var.groupby('Nombre_Variante'):
        vals = grp['Duracion_Total'].dropna().values
        media, li, ls = pred_variante(vals, z_resumen)
        if media is not None:
            pronostico_rows.append({'Variante': var, 'Ruta': diccionario_rutas_res.get(var, ''), 'Casos': len(vals), 'Promedio': media, 'Li95': li, 'Ls95': ls})
    df_pronostico = pd.DataFrame(pronostico_rows).sort_values('Casos', ascending=False).head(5) if pronostico_rows else pd.DataFrame()

    col_cb, col_rec = st.columns(2)

    with col_cb:
        st.markdown("#### ① Cuellos de botella por etapa")
        st.caption("Etapas ordenadas por tiempo de permanencia promedio.")

        if not etapa_stats.empty:
            etapa_stats['Casos_txt'] = etapa_stats['Casos'].apply(lambda x: formato_latino(x, 0))
            etapa_stats['Promedio_txt'] = etapa_stats['Promedio'].apply(lambda x: formato_latino(x, 1))

            fig_cb = px.bar(
                etapa_stats, x='Promedio', y='Etapa', orientation='h', color='Promedio',
                color_continuous_scale=["#E1E1E1", P_SALMON, P_CORAL],
                text=etapa_stats['Promedio'].apply(lambda x: f"{formato_latino(x)} días"),
                custom_data=['Casos_txt', 'Promedio_txt'], labels={'Promedio': 'Días promedio', 'Etapa': ''},
            )
            fig_cb.update_traces(textposition='outside', cliponaxis=False, hovertemplate="<b>%{y}</b><br>Promedio: %{customdata[1]} días<br>Casos: %{customdata[0]}<extra></extra>")
            fig_cb.update_layout(
                height=380, font=dict(family="Arial", size=13), coloraxis_showscale=False,
                margin=dict(l=10, r=60, t=10, b=40), yaxis=dict(categoryorder='total ascending'),
                xaxis_title="Días promedio de permanencia", xaxis=dict(rangemode='tozero'),
                plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)' # 👈 Transparente
            )
            st.plotly_chart(fig_cb, use_container_width=True)

            peor = etapa_stats.iloc[0]
            # Usamos RGBA para el fondo del bloque
            bloque_info(P_CORAL, "rgba(255, 104, 107, 0.1)", f"<b>⚠ Mayor cuello de botella:</b> {peor['Etapa']}<br>Promedio de <b>{formato_latino(peor['Promedio'])} días</b> · {formato_latino(peor['Casos'], 0)} casos")
        else: st.info("Sin datos suficientes.")

    with col_rec:
        st.markdown("#### ② Recursos con sobrecarga")
        st.caption("Eje Y: tiempo promedio. Tamaño: volumen de casos.")

        df_recursos_res = df_trans[df_trans['Recurso_Origen'] != 'Sistema']
        recurso_stats = df_recursos_res.groupby('Recurso_Origen').agg(Promedio=('Duracion', 'mean'), Casos=('ID', 'count')).reset_index().rename(columns={'Recurso_Origen': 'Recurso'})

        if not recurso_stats.empty:
            recurso_stats['Promedio_txt'] = recurso_stats['Promedio'].apply(lambda x: formato_latino(x, 1))
            recurso_stats['Casos_txt'] = recurso_stats['Casos'].apply(lambda x: formato_latino(x, 0))

            fig_rec = px.scatter(
                recurso_stats, x='Recurso', y='Promedio', size='Casos', color='Promedio',
                color_continuous_scale=[P_MINT, P_TEAL, "#5aab9a"], size_max=60, text='Recurso',
                custom_data=['Casos_txt', 'Promedio_txt'], labels={'Promedio': 'Tiempo promedio', 'Recurso': ''},
            )
            fig_rec.update_traces(textposition='top center', hovertemplate="<b>%{x}</b><br>Tiempo promedio: %{customdata[1]} días<br>Etapas: %{customdata[0]}<extra></extra>")
            fig_rec.update_layout(
                height=380, font=dict(family="Arial", size=13), coloraxis_showscale=False,
                margin=dict(l=10, r=30, t=10, b=60), xaxis=dict(showticklabels=False),
                yaxis_title="Tiempo promedio de procesamiento (días)", yaxis=dict(rangemode='tozero'),
                plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)' # 👈 Transparente
            )
            st.plotly_chart(fig_rec, use_container_width=True)

            candidatos = recurso_stats[(recurso_stats['Promedio'] > recurso_stats['Promedio'].quantile(0.75)) & (recurso_stats['Casos'] > recurso_stats['Casos'].median())]
            peor_r = candidatos.sort_values('Promedio', ascending=False).iloc[0] if not candidatos.empty else recurso_stats.sort_values('Promedio', ascending=False).iloc[0]
            
            # Usamos RGBA para el fondo del bloque
            bloque_info(P_TEAL, "rgba(132, 220, 198, 0.15)", f"<b>⚠ Recurso más crítico:</b> {peor_r['Recurso']}<br>Promedio de <b>{formato_latino(peor_r['Promedio'])} días</b> · {formato_latino(peor_r['Casos'], 0)} etapas")
        else: st.info("Sin datos de recursos.")

    st.markdown("#### ③ Pronóstico para casos futuros (Top 5 variantes)")
    st.caption("Estimación de duración total para un caso nuevo según la variante de proceso.")

    if not df_pronostico.empty:
        df_pronostico['Pct'] = (df_pronostico['Casos'] / len(df_var)) * 100
        df_pronostico['Label_Casos'] = df_pronostico.apply(lambda r: f"{formato_latino(r['Casos'], 0)} ({formato_latino(r['Pct'], 1)}%)", axis=1)

        fig_pron = px.scatter(
            df_pronostico, x='Variante', y='Promedio', error_y=df_pronostico['Ls95'] - df_pronostico['Promedio'], error_y_minus=df_pronostico['Promedio'] - df_pronostico['Li95'],
            text='Label_Casos', size='Casos', size_max=30, color_discrete_sequence=[P_TEAL],
            custom_data=[df_pronostico['Li95'].apply(lambda x: formato_latino(x, 1)), df_pronostico['Ls95'].apply(lambda x: formato_latino(x, 1)), df_pronostico['Casos'].apply(lambda x: formato_latino(x, 0)), df_pronostico['Promedio'].apply(lambda x: formato_latino(x, 1))],
            labels={'Promedio': 'Días (promedio)', 'Variante': ''},
        )
        fig_pron.update_traces(textposition='middle right', hovertemplate="<b>%{x}</b><br>Promedio: %{customdata[3]} días<br>Intervalo 95%: %{customdata[0]} – %{customdata[1]} días<br>Casos: %{customdata[2]}<extra></extra>")
        for _, row in df_pronostico.iterrows():
            for y_val, txt in [(row['Ls95'], formato_latino(row['Ls95'], 1)), (row['Li95'], formato_latino(row['Li95'], 1))]:
                fig_pron.add_annotation(x=row['Variante'], y=y_val, text=txt, showarrow=False, xanchor='left', yanchor='middle', xshift=8, font=dict(size=11, color=P_TEAL))
        fig_pron.update_layout(
            height=350, font=dict(family="Arial", size=13), margin=dict(l=10, r=80, t=20, b=60),
            yaxis_title="Duración estimada (días)", yaxis=dict(rangemode='tozero'),
            plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)' # 👈 Transparente
        )
        st.plotly_chart(fig_pron, use_container_width=True)

        tabla_pron = df_pronostico[['Variante', 'Casos', 'Promedio', 'Li95', 'Ls95']].copy()
        tabla_pron.columns = ['Variante', 'Casos', 'Promedio', 'Límite Inf. (95%)', 'Límite Sup. (95%)']
        tabla_pron['Variante'] = tabla_pron['Variante'].apply(lambda v: f'<span title="{diccionario_rutas_res.get(v, "")}" style="cursor:help;border-bottom:1px dotted #888;">{v}</span>')
        fmt_pron = {'Promedio': lambda x: formato_latino(x) + " días", 'Límite Inf. (95%)': lambda x: formato_latino(x) + " días", 'Límite Sup. (95%)': lambda x: formato_latino(x) + " días", 'Casos': lambda x: formato_latino(x, 0)}
        mostrar_tabla_html(tabla_pron.style.hide(axis="index").format(fmt_pron))