import streamlit as st
import pandas as pd
import re

import panel1_header
import panel2_tabs

# ==========================================
# 1. CONFIGURACIÓN Y ESTILOS GLOBALES
# ==========================================
st.set_page_config(page_title="Monitor de Procesos", layout="wide")

P_TEAL   = "#84DCC6"
P_CORAL  = "#FF686B"

# CSS Theme-Aware (Compatible con Modo Oscuro)
st.markdown(f"""
    <style>
        header[data-testid="stHeader"] {{ display: none !important; }}
        div[data-testid="stToolbar"] {{ display: none !important; }}
        * {{ font-family: 'Arial', sans-serif !important; }}

        .block-container {{
            margin-top: 0 !important;
            padding-top: 8px !important;
            padding-bottom: 2rem !important;
        }}
        a.header-anchor, [data-testid="stMarkdownContainer"] h1 a {{ display: none !important; }}
        
        /* Tablas que se adaptan al modo oscuro */
        .tabla-arial {{
            width: 100%; border-collapse: collapse;
            font-size: 13px; margin-bottom: 0.5rem;
            color: var(--text-color);
        }}
        .tabla-arial th {{
            background-color: var(--secondary-background-color); 
            border-bottom: 2px solid {P_TEAL};
            padding: 10px 14px; text-align: center; font-weight: bold;
        }}
        .tabla-arial td {{
            border-bottom: 1px solid var(--secondary-background-color); 
            padding: 9px 14px; text-align: center;
        }}
        .tabla-arial tr:hover {{ 
            background-color: rgba(132, 220, 198, 0.1); /* Turquesa al 10% de opacidad */
        }}
        
        .nota-outliers {{
            font-size: 12px; color: var(--text-color); opacity: 0.7; font-style: italic;
            margin-bottom: 1rem; text-align: right;
        }}
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. VARIABLES DE SESIÓN GLOBALES
# ==========================================
if 'datos_procesados' not in st.session_state: st.session_state.datos_procesados = False
if 'df_transiciones'  not in st.session_state: st.session_state.df_transiciones  = None
if 'df_variantes'     not in st.session_state: st.session_state.df_variantes      = None
if 'dict_orden'       not in st.session_state: st.session_state.dict_orden        = {}
if 'periodo_fechas'   not in st.session_state: st.session_state.periodo_fechas    = ""
if 'tiene_est_orden'  not in st.session_state: st.session_state.tiene_est_orden   = False
if 'exp_etapa'        not in st.session_state: st.session_state.exp_etapa         = False
if 'exp_rec'          not in st.session_state: st.session_state.exp_rec           = False
if 'exp_metodo'       not in st.session_state: st.session_state.exp_metodo        = False

panel1_header.render()

# ==========================================
# 3. LÓGICA DE CARGA DE DATOS
# ==========================================
if not st.session_state.datos_procesados:
    st.info("Sube los archivos CSV para comenzar el análisis.")
    col1, col2 = st.columns(2)
    with col1: archivo_log = st.file_uploader("1. Log principal (eventos)", type=['csv'])
    with col2: archivo_est = st.file_uploader("2. Maestro de estados", type=['csv'])

    if archivo_log and archivo_est:
        try:
            with st.spinner("Procesando datos y modelando procesos..."):
                df_log = pd.read_csv(archivo_log, sep=None, engine='python', on_bad_lines='skip', encoding='utf-8-sig')
                df_est = pd.read_csv(archivo_est, sep=None, engine='python', on_bad_lines='skip', encoding='utf-8-sig')

                col_responsable = ('RECURSO' if 'RECURSO' in df_log.columns else 'RESPONSABLE' if 'RESPONSABLE' in df_log.columns else None)
                tiene_est_orden = ('ESTADO' in df_est.columns and 'EST_ORDEN' in df_est.columns)
                dict_orden = {'Inicio proceso': -9999, 'Fin proceso': 9999}
                if tiene_est_orden:
                    for _, r in df_est.dropna(subset=['ESTADO', 'EST_ORDEN']).iterrows():
                        val_str = str(r['EST_ORDEN']).strip()
                        try: orden_val = float(val_str)
                        except ValueError:
                            m = re.search(r'\d+', val_str)
                            orden_val = float(m.group()) if m else 9999
                        dict_orden[str(r['ESTADO']).strip()] = orden_val

                st.session_state.dict_orden      = dict_orden
                st.session_state.tiene_est_orden = tiene_est_orden

                df_log['FECHA_ESTADO'] = pd.to_datetime(df_log['FECHA_ESTADO'], format='mixed', dayfirst=True, errors='coerce')
                fechas_validas = df_log['FECHA_ESTADO'].dropna()
                if not fechas_validas.empty:
                    st.session_state.periodo_fechas = f"Período {fechas_validas.min().strftime('%d-%m-%Y')} – {fechas_validas.max().strftime('%d-%m-%Y')}"
                else:
                    st.session_state.periodo_fechas = "Período no disponible"

                cols_merge = ['ESTADO']
                if tiene_est_orden: cols_merge.append('EST_ORDEN')
                df = df_log.merge(df_est[cols_merge], on='ESTADO', how='left')
                df = df.sort_values(['ID', 'FECHA_ESTADO'])

                transiciones = []
                for case_id, group in df.groupby('ID'):
                    estados = ['Inicio proceso'] + group['ESTADO'].tolist() + ['Fin proceso']
                    fechas  = ([group['FECHA_ESTADO'].min()] + group['FECHA_ESTADO'].tolist() + [group['FECHA_ESTADO'].max()])
                    recursos_lista = (group[col_responsable].tolist() if col_responsable else ['Desconocido'] * len(group))
                    recursos = ['Sistema'] + recursos_lista + ['Sistema']
                    for i in range(len(estados) - 1):
                        duracion = ((fechas[i+1] - fechas[i]).days if pd.notnull(fechas[i+1]) and pd.notnull(fechas[i]) else 0)
                        transiciones.append({
                            'ID': case_id, 'Origen': estados[i], 'Destino': estados[i+1],
                            'Fecha_Inicio': fechas[i], 'Duracion': duracion, 'Recurso_Origen': recursos[i]
                        })

                df_trans = pd.DataFrame(transiciones)

                df_var = df_trans.groupby('ID').agg(
                    Ruta=('Destino', lambda x: ' -> '.join([s for s in x if s != 'Fin proceso'])),
                    Duracion_Total=('Duracion', 'sum'),
                    Fecha_Inicio_Caso=('Fecha_Inicio', 'min')
                ).reset_index()

                frecuencias = df_var['Ruta'].value_counts().reset_index()
                frecuencias.columns = ['Ruta', 'Frecuencia']
                mapeo_variantes = {row['Ruta']: f"Var {i+1}" for i, row in frecuencias.iterrows()}
                df_var['Nombre_Variante'] = df_var['Ruta'].map(mapeo_variantes)
                df_var['Ruta_Tooltip']    = df_var['Ruta'].apply(lambda x: x.replace(' -> ', '<br>&#8627; '))

                df_trans = df_trans.merge(df_var[['ID', 'Nombre_Variante', 'Ruta']], on='ID', how='left')

                st.session_state.df_transiciones = df_trans
                st.session_state.df_variantes    = df_var
                st.session_state.datos_procesados = True
                st.rerun()

        except Exception as e:
            st.error(f"Error al procesar: {e}")
else:
    panel2_tabs.render()