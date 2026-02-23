import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import streamlit.components.v1 as components
import statistics
import re
import base64

# ==========================================
# PALETA: PEACHY SUNRISE
# ==========================================
P_TEAL     = "#84DCC6"   # primario / positivo / inicio
P_MINT     = "#A5FFD6"   # secundario / banda P10-P90
P_SALMON   = "#FFA69E"   # moderado / alerta media
P_CORAL    = "#FF686B"   # crítico / fin / alta variabilidad
P_DARK     = "#1f2937"   # texto principal
P_MID      = "#374151"   # texto secundario
P_GRAY     = "#6b7280"   # texto terciario
P_LIGHTBG  = "#f9fafb"   # fondo tarjetas
P_BORDER   = "#e5e7eb"   # bordes neutros
# Escala de calor nodos (mín → máx)
P_HEAT = ["#E1E1E1", "#fde8e7", P_SALMON, "#ff9292", P_CORAL]
# Escala recursos (frío → caliente)
P_REC  = [P_MINT, P_TEAL, "#5aab9a"]

# ==========================================
# 1. CONFIGURACIÓN Y ESTILOS GLOBALES
# ==========================================
st.set_page_config(page_title="Monitor de Procesos", layout="wide")

st.markdown(f"""
    <style>
        header[data-testid="stHeader"] {{ display: none !important; }}
        div[data-testid="stToolbar"] {{ display: none !important; }}
        * {{ font-family: 'Arial', sans-serif !important; }}
        .fixed-header {{
            position: fixed; top: 0; left: 0; width: 100%;
            background: #ffffff; padding: 12px 30px;
            z-index: 999999; border-bottom: 2px solid {P_TEAL};
            display: flex; align-items: center; gap: 12px;
        }}
        .header-dot {{
            width: 12px; height: 12px; border-radius: 50%;
            background: {P_TEAL}; flex-shrink: 0;
        }}
        .header-title {{
            margin: 0; font-size: 15px !important; font-weight: bold;
            color: {P_DARK}; font-family: Arial, sans-serif !important;
        }}
        .block-container {{ margin-top: 40px; }}
        a.header-anchor,
        [data-testid="stMarkdownContainer"] h1 a,
        [data-testid="stMarkdownContainer"] h2 a,
        [data-testid="stMarkdownContainer"] h3 a,
        [data-testid="stMarkdownContainer"] h4 a,
        .st-emotion-cache-16twljr a {{ display: none !important; }}
        .tabla-arial {{
            width: 100%; border-collapse: collapse;
            font-family: Arial, sans-serif !important;
            font-size: 13px; color: #333; margin-bottom: 0.5rem;
        }}
        .tabla-arial th {{
            background-color: #f8f9fa; border-bottom: 2px solid {P_TEAL};
            padding: 10px 14px; text-align: center; font-weight: bold;
        }}
        .tabla-arial td {{
            border-bottom: 1px solid #dee2e6; padding: 9px 14px;
            text-align: center;
        }}
        .tabla-arial tr:hover {{ background-color: #f6fffe; }}
        .nota-outliers {{
            font-size: 12px; color: #666; font-style: italic;
            margin-bottom: 1rem; text-align: right;
        }}
        div[data-testid="metric-container"] > div:first-child {{
            font-size: 12px !important; color: {P_GRAY} !important;
        }}
        div[data-testid="metric-container"] > div:last-child {{
            font-size: 22px !important; font-weight: bold !important;
            color: {P_DARK} !important;
        }}
        /* ── Botones colapsables custom ─────────────────────────────────── */
        [data-testid="stMainBlockContainer"] button[data-testid="baseButton-secondary"] {{
            background: #f8f9fa !important;
            border: 1px solid {P_BORDER} !important;
            border-radius: 6px !important;
            color: {P_DARK} !important;
            font-size: 14px !important;
            font-weight: 600 !important;
            text-align: left !important;
            padding: 10px 16px !important;
            margin-top: 6px !important;
            justify-content: flex-start !important;
        }}
        [data-testid="stMainBlockContainer"] button[data-testid="baseButton-secondary"]:hover {{
            background: #f0faf8 !important;
            border-color: {P_TEAL} !important;
            color: {P_TEAL} !important;
        }}
        /* ── Tabs fijas ──────────────────────────────────────────────────
           position:sticky requiere overflow:visible en TODA la cadena
           entre el scroll-container y el tablist.
           Cubrimos todos los contenedores posibles de Streamlit. ───── */
        section[data-testid="stMain"] > div,
        div[data-testid="stMainBlockContainer"],
        div[data-testid="block-container"],
        div[data-testid="stVerticalBlock"],
        div[data-testid="stTabs"],
        div[data-testid="stTabs"] > div,
        div[data-testid="stTabs"] > div > div {{
            overflow: visible !important;
        }}
        [role="tablist"] {{
            position: sticky !important;
            top: 44px !important;
            z-index: 99998 !important;
            background: white !important;
            border-bottom: 1px solid {P_BORDER} !important;
            padding-bottom: 2px !important;
        }}
    </style>
    <div class="fixed-header">
        <div class="header-dot"></div>
        <div class="header-title">Monitor de Procesos — Análisis de Tiempos y Variantes</div>
    </div>
""", unsafe_allow_html=True)


def formato_latino(numero, decimales=1):
    if pd.isna(numero): return "0"
    if decimales == 0:
        formateado = f"{int(numero):,}"
    else:
        formateado = f"{numero:,.{decimales}f}"
    return formateado.replace(',', 'X').replace('.', ',').replace('X', '.')


# ==========================================
# RENDERIZADOR MERMAID (con doble clic)
# ==========================================
def render_mermaid(code: str, node_data: dict = None, tiene_heuristico: bool = False):
    import json as _json
    b64_code = base64.b64encode(code.encode('utf-8')).decode('utf-8')
    node_data_js = _json.dumps(node_data or {}, ensure_ascii=False)

    leyenda_reproceso = ""
    if tiene_heuristico:
        leyenda_reproceso = f"""
            <span style="display:inline-block;width:25px;border-top:2px dashed {P_CORAL};margin:0 5px;"></span> Reproceso confirmado (orden definido)
            <span style="display:inline-block;width:25px;border-top:2px dashed #aaa;margin:0 5px;margin-left:12px;"></span> Reproceso inferido (heurístico)
        """
    else:
        leyenda_reproceso = f"""
            <span style="display:inline-block;width:25px;border-top:2px dashed {P_CORAL};margin:0 5px;"></span> Reproceso
        """

    html_content = f"""
    <!DOCTYPE html><html><head><meta charset="utf-8">
    <style>
        body {{ margin:0; padding:0; display:flex; justify-content:center;
               font-family:Arial,sans-serif; position:relative; }}
        #graphDiv {{ width:100%; height:100%; display:flex; justify-content:center;
                    align-items:center; padding-top:20px; }}
        .mermaidTooltip {{
            position:absolute !important; text-align:left !important;
            min-width:150px !important; padding:10px 15px !important;
            font-family:Arial,sans-serif !important; font-size:13px !important;
            background-color:{P_DARK} !important; color:#fff !important;
            border-radius:6px !important; pointer-events:none !important;
            z-index:999999 !important; box-shadow:0 4px 10px rgba(0,0,0,0.3) !important;
            transition:opacity 0.1s ease !important; line-height:1.6 !important;
            white-space:nowrap !important;
        }}
        #nodeModal {{
            display:none; position:fixed; top:0; left:0; width:100%; height:100%;
            background:rgba(0,0,0,0.45); z-index:9999999;
            justify-content:center; align-items:center;
        }}
        #nodeModal.open {{ display:flex; }}
        #modalBox {{
            background:#fff; border-radius:10px;
            box-shadow:0 8px 32px rgba(0,0,0,0.25);
            width:700px; max-width:95vw; max-height:80vh;
            display:flex; flex-direction:column;
            font-family:Arial,sans-serif; overflow:hidden;
        }}
        #modalHeader {{
            background:{P_DARK}; color:#fff; padding:14px 20px;
            display:flex; justify-content:space-between; align-items:center; flex-shrink:0;
        }}
        #modalTitle {{ font-size:15px; font-weight:bold; margin:0; }}
        #modalSubtitle {{ font-size:12px; color:#9ca3af; margin:2px 0 0 0; }}
        #modalClose {{
            background:none; border:none; color:#fff;
            font-size:22px; cursor:pointer; line-height:1; padding:0 4px;
        }}
        #modalClose:hover {{ color:{P_SALMON}; }}
        #modalBody {{ overflow-y:auto; flex:1; padding:0; }}
        #modalTable {{ width:100%; border-collapse:collapse; font-size:13px; }}
        #modalTable thead th {{
            background:#f8f9fa; border-bottom:2px solid {P_TEAL};
            padding:10px 14px; text-align:left; font-weight:bold; color:{P_MID};
            position:sticky; top:0; z-index:10;
        }}
        #modalTable tbody td {{ padding:8px 14px; border-bottom:1px solid #f0f0f0; color:{P_MID}; }}
        #modalTable tbody tr:hover {{ background:#f6fffe; }}
        #modalFooter {{
            padding:10px 20px; font-size:12px; color:{P_GRAY};
            border-top:1px solid {P_BORDER}; flex-shrink:0; background:#fafafa;
        }}
    </style>
    </head>
    <body>
        <div id="graphDiv">Generando mapa de proceso...</div>
        <div id="nodeModal">
            <div id="modalBox">
                <div id="modalHeader">
                    <div>
                        <p id="modalTitle">Etapa</p>
                        <p id="modalSubtitle"></p>
                    </div>
                    <button id="modalClose" title="Cerrar">&#10005;</button>
                </div>
                <div id="modalBody">
                    <table id="modalTable">
                        <thead><tr>
                            <th>ID Caso</th><th>Fecha de ingreso</th>
                            <th>Recurso</th><th>D&#237;as en etapa</th>
                        </tr></thead>
                        <tbody id="modalTableBody"></tbody>
                    </table>
                </div>
                <div id="modalFooter"></div>
            </div>
        </div>
        <script type="module">
            window.noAction = function() {{ return false; }};
            const NODE_DATA = {node_data_js};
            import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
            mermaid.initialize({{
                startOnLoad:false, theme:'default', fontFamily:'Arial',
                securityLevel:'loose', flowchart:{{ arrowMarkerAbsolute:true }}
            }});
            const modal=document.getElementById('nodeModal'),
                  mTitle=document.getElementById('modalTitle'),
                  mSub=document.getElementById('modalSubtitle'),
                  mBody=document.getElementById('modalTableBody'),
                  mFooter=document.getElementById('modalFooter'),
                  mClose=document.getElementById('modalClose');
            function openModal(stateName) {{
                const rows=NODE_DATA[stateName];
                if(!rows||rows.length===0) return;
                mTitle.textContent=stateName;
                mSub.textContent=rows.length+' caso'+(rows.length!==1?'s':'')+' pasan por esta etapa';
                mFooter.textContent='Total: '+rows.length+' registro'+(rows.length!==1?'s':'')+'.';
                mBody.innerHTML='';
                rows.forEach(function(r){{
                    var tr=document.createElement('tr');
                    tr.innerHTML='<td>'+(r.id||'\u2014')+'</td>'
                        +'<td>'+(r.fecha||'\u2014')+'</td>'
                        +'<td>'+(r.recurso||'\u2014')+'</td>'
                        +'<td style="text-align:center;">'+(r.duracion!==undefined?r.duracion:'\u2014')+'</td>';
                    mBody.appendChild(tr);
                }});
                modal.classList.add('open');
            }}
            mClose.addEventListener('click',function(){{modal.classList.remove('open');}});
            modal.addEventListener('click',function(e){{if(e.target===modal)modal.classList.remove('open');}});
            document.addEventListener('keydown',function(e){{if(e.key==='Escape')modal.classList.remove('open');}});
            try {{
                const b64="{b64_code}";
                const graphDefinition=decodeURIComponent(escape(window.atob(b64)));
                mermaid.render('mermaid-svg',graphDefinition).then((result)=>{{
                    document.getElementById('graphDiv').innerHTML=result.svg;
                    if(result.bindFunctions) result.bindFunctions(document.getElementById('graphDiv'));
                    var EXCLUIDOS=['Inicio proceso','Fin proceso'];
                    document.querySelectorAll('.node').forEach(function(nodeEl){{
                        var labelEl=nodeEl.querySelector('span')||nodeEl.querySelector('p')||nodeEl.querySelector('text');
                        if(!labelEl) return;
                        var label=labelEl.textContent.trim();
                        if(EXCLUIDOS.indexOf(label)!==-1) return;
                        if(!NODE_DATA[label]) return;
                        nodeEl.style.cursor='pointer';
                        nodeEl.title='Doble clic para ver casos';
                        nodeEl.addEventListener('dblclick',function(e){{
                            e.stopPropagation(); openModal(label);
                        }});
                    }});
                }}).catch((error)=>{{
                    document.getElementById('graphDiv').innerHTML="<div style='color:red;'><b>Error:</b> "+error.message+"</div>";
                }});
            }} catch(e) {{
                document.getElementById('graphDiv').innerHTML="<div style='color:red;'>Error decodificando el gr\u00e1fico.</div>";
            }}
            setInterval(function(){{
                var tooltips=document.getElementsByClassName('mermaidTooltip');
                for(var i=0;i<tooltips.length;i++){{
                    var tt=tooltips[i];
                    if(tt.textContent.includes('<br>')) tt.innerHTML=tt.textContent.split('<br>').join('<br>');
                }}
                var paths=document.querySelectorAll('path[marker-end]');
                paths.forEach(function(path){{
                    var strokeColor=path.style.stroke||path.getAttribute('stroke');
                    if(strokeColor&&strokeColor!=='none'){{
                        var markerId=path.getAttribute('marker-end');
                        if(markerId&&!markerId.includes('_custom_')){{
                            var id=markerId.replace('url(','').replace(')','').replace(/[\"\']/g,'');
                            if(id.includes('#')) id=id.substring(id.indexOf('#'));
                            var marker=document.querySelector(id);
                            if(marker){{
                                var colorSafe=strokeColor.replace(/[^a-zA-Z0-9]/g,'');
                                var newId=id.substring(1)+'_custom_'+colorSafe;
                                if(!document.getElementById(newId)){{
                                    var newMarker=marker.cloneNode(true);
                                    newMarker.id=newId;
                                    newMarker.querySelectorAll('path').forEach(function(mp){{
                                        mp.style.fill=strokeColor; mp.style.stroke='none';
                                    }});
                                    marker.parentNode.appendChild(newMarker);
                                }}
                                path.setAttribute('marker-end','url(#'+newId+')');
                            }}
                        }}
                    }}
                }});
            }},50);
        </script>
    </body></html>
    """
    components.html(html_content, height=750, scrolling=True)


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


def bloque_info(color_borde, color_fondo, texto_html):
    """Bloque de alerta/info con paleta unificada."""
    st.markdown(
        f'<div style="background:{color_fondo};border-left:4px solid {color_borde};'
        f'padding:10px 14px;border-radius:6px;font-size:13px;font-family:Arial,sans-serif;">'
        f'{texto_html}</div>',
        unsafe_allow_html=True
    )



# ==========================================
# 2. VARIABLES DE SESIÓN
# ==========================================
if 'datos_procesados' not in st.session_state: st.session_state.datos_procesados = False
if 'df_transiciones'  not in st.session_state: st.session_state.df_transiciones  = None
if 'df_variantes'     not in st.session_state: st.session_state.df_variantes      = None
if 'dict_orden'       not in st.session_state: st.session_state.dict_orden        = {}
if 'periodo_fechas'   not in st.session_state: st.session_state.periodo_fechas    = ""
if 'tiene_est_orden'  not in st.session_state: st.session_state.tiene_est_orden   = False
# Colapsables custom (sin dependencia de Material Icons)
if 'exp_etapa'  not in st.session_state: st.session_state.exp_etapa  = False
if 'exp_rec'    not in st.session_state: st.session_state.exp_rec    = False
if 'exp_metodo' not in st.session_state: st.session_state.exp_metodo = False

# ==========================================
# 3. PANTALLA 1: CARGA DE DATOS
# ==========================================
if not st.session_state.datos_procesados:
    st.info("Sube los archivos CSV para comenzar el análisis.")
    col1, col2 = st.columns(2)
    with col1: archivo_log = st.file_uploader("1. Log principal (eventos)", type=['csv'])
    with col2: archivo_est = st.file_uploader("2. Maestro de estados", type=['csv'])

    if archivo_log and archivo_est:
        try:
            with st.spinner("Procesando datos y modelando procesos..."):
                df_log = pd.read_csv(archivo_log, sep=None, engine='python',
                                     on_bad_lines='skip', encoding='utf-8-sig')
                df_est = pd.read_csv(archivo_est, sep=None, engine='python',
                                     on_bad_lines='skip', encoding='utf-8-sig')

                col_responsable = (
                    'RECURSO'     if 'RECURSO'     in df_log.columns else
                    'RESPONSABLE' if 'RESPONSABLE' in df_log.columns else None
                )

                tiene_est_orden = ('ESTADO' in df_est.columns and 'EST_ORDEN' in df_est.columns)
                dict_orden = {'Inicio proceso': -9999, 'Fin proceso': 9999}
                if tiene_est_orden:
                    for _, r in df_est.dropna(subset=['ESTADO', 'EST_ORDEN']).iterrows():
                        val_str = str(r['EST_ORDEN']).strip()
                        try:
                            orden_val = float(val_str)
                        except ValueError:
                            m = re.search(r'\d+', val_str)
                            orden_val = float(m.group()) if m else 9999
                        dict_orden[str(r['ESTADO']).strip()] = orden_val

                st.session_state.dict_orden      = dict_orden
                st.session_state.tiene_est_orden = tiene_est_orden

                df_log['FECHA_ESTADO'] = pd.to_datetime(
                    df_log['FECHA_ESTADO'], format='mixed', dayfirst=True, errors='coerce'
                )
                fechas_validas = df_log['FECHA_ESTADO'].dropna()
                if not fechas_validas.empty:
                    fecha_min = fechas_validas.min().strftime('%d-%m-%Y')
                    fecha_max = fechas_validas.max().strftime('%d-%m-%Y')
                    st.session_state.periodo_fechas = f"Período {fecha_min} – {fecha_max}"
                else:
                    st.session_state.periodo_fechas = "Período no disponible"

                # Merge sin requerir EST_ORDEN
                cols_merge = ['ESTADO']
                if tiene_est_orden:
                    cols_merge.append('EST_ORDEN')
                df = df_log.merge(df_est[cols_merge], on='ESTADO', how='left')
                df = df.sort_values(['ID', 'FECHA_ESTADO'])

                transiciones = []
                for case_id, group in df.groupby('ID'):
                    estados = ['Inicio proceso'] + group['ESTADO'].tolist() + ['Fin proceso']
                    fechas  = ([group['FECHA_ESTADO'].min()]
                               + group['FECHA_ESTADO'].tolist()
                               + [group['FECHA_ESTADO'].max()])
                    recursos_lista = (group[col_responsable].tolist()
                                      if col_responsable else ['Desconocido'] * len(group))
                    recursos = ['Sistema'] + recursos_lista + ['Sistema']
                    for i in range(len(estados) - 1):
                        duracion = ((fechas[i+1] - fechas[i]).days
                                    if pd.notnull(fechas[i+1]) and pd.notnull(fechas[i]) else 0)
                        transiciones.append({
                            'ID': case_id, 'Origen': estados[i], 'Destino': estados[i+1],
                            'Fecha_Inicio': fechas[i],
                            'Duracion': duracion, 'Recurso_Origen': recursos[i]
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
                df_var['Ruta_Tooltip']    = df_var['Ruta'].apply(
                    lambda x: x.replace(' -> ', '<br>&#8627; ')
                )

                df_trans = df_trans.merge(
                    df_var[['ID', 'Nombre_Variante', 'Ruta']], on='ID', how='left'
                )

                st.session_state.df_transiciones = df_trans
                st.session_state.df_variantes    = df_var
                st.session_state.datos_procesados = True
                st.rerun()
        except Exception as e:
            st.error(f"Error al procesar: {e}")

# ==========================================
# 4. PANTALLA 2: PESTAÑAS
# ==========================================
if st.session_state.datos_procesados:
    df_trans       = st.session_state.df_transiciones
    df_var         = st.session_state.df_variantes
    dict_orden     = st.session_state.dict_orden
    periodo_fechas = st.session_state.periodo_fechas
    tiene_est_orden = st.session_state.tiene_est_orden

    if st.sidebar.button("Cargar nuevos archivos"):
        st.session_state.datos_procesados = False
        st.rerun()

    tab1, tab2, tab3, tab4 = st.tabs([
        "Mapa de Proceso",
        "Análisis Estadístico",
        "Diagnóstico",
        "Pronóstico por Variante"
    ])

    # Inyectar fixes de JS: expander _arrow_right y tabs sticky
    # ──────────────────────────────────────────────
    # PESTAÑA 1: MAPA DE PROCESO
    # ──────────────────────────────────────────────
    with tab1:
        # Barra de controles horizontal compacta
        ctrl1, ctrl2, ctrl3 = st.columns([2, 2, 6])
        with ctrl1:
            metrica_grafo = st.radio(
                "Métrica en flechas:",
                ["Frecuencia (Casos)", "Tiempo promedio (Días)"],
                horizontal=False
            )
        with ctrl2:
            resaltar_cuellos = st.checkbox("Resaltar cuellos de botella", value=False)
            st.caption("Colorea nodos según tiempo de permanencia")

        st.markdown("---")

        col_grafo, col_panel = st.columns([7, 3])

        with col_panel:
            with st.container(height=780):
                var_counts = (df_var
                              .groupby(['Nombre_Variante', 'Ruta_Tooltip', 'Ruta'])
                              .size().reset_index(name='Frecuencia'))
                var_counts['Orden'] = (var_counts['Nombre_Variante']
                                       .str.replace('Var ', '').astype(int))
                var_counts = var_counts.sort_values('Orden', ascending=False)
                total_casos_proceso = var_counts['Frecuencia'].sum()
                var_counts['Porcentaje']     = (var_counts['Frecuencia'] / total_casos_proceso) * 100
                var_counts['Porcentaje_Txt'] = var_counts['Porcentaje'].apply(
                    lambda x: formato_latino(x, 1) + "%"
                )

                fig = px.bar(
                    var_counts.tail(15),
                    x='Frecuencia', y='Nombre_Variante', orientation='h',
                    title="Variantes de proceso (clic para filtrar)",
                    text='Porcentaje_Txt',
                    custom_data=['Nombre_Variante', 'Ruta_Tooltip', 'Ruta', 'Porcentaje_Txt'],
                    color_discrete_sequence=[P_TEAL]
                )
                fig.update_traces(
                    textposition='outside', cliponaxis=False,
                    hovertemplate=(
                        "<b>%{y}</b><br>Casos: %{x} (%{customdata[3]})"
                        "<br><br><b>Ruta:</b><br>%{customdata[1]}<extra></extra>"
                    )
                )
                fig.update_layout(
                    height=720, font=dict(family="Arial"),
                    margin=dict(l=0, r=50, t=40, b=60),
                    hoverlabel=dict(align="left", font_family="Arial",
                                   bgcolor="white", font_size=13),
                    yaxis_title=None,
                    plot_bgcolor='white', paper_bgcolor='white'
                )
                seleccion = st.plotly_chart(
                    fig, on_select="rerun", selection_mode="points",
                    use_container_width=True
                )
                variante_seleccionada = None
                if (seleccion and seleccion.get("selection")
                        and seleccion["selection"].get("points")):
                    variante_seleccionada = seleccion["selection"]["points"][0]["customdata"][0]
                    st.success(f"Filtrando: **{variante_seleccionada}** — "
                               "Clic en área vacía para quitar filtro.")

        with col_grafo:
            st.subheader("Mapa de proceso")
            st.caption(f"**{periodo_fechas}**")

            df_grafo = (df_trans[df_trans['Nombre_Variante'] == variante_seleccionada]
                        if variante_seleccionada else df_trans)

            edges_stats = df_grafo.groupby(['Origen', 'Destino']).agg(
                Frecuencia=('ID', 'count'), Tiempo_Promedio=('Duracion', 'mean')
            ).reset_index()

            if edges_stats.empty:
                st.warning("No hay suficientes datos para dibujar el mapa con esta selección.")
            else:
                node_stats = df_grafo.groupby('Origen').agg(
                    Casos=('ID', 'count'),
                    Tiempo_Promedio=('Duracion', 'mean'),
                    Mediana=('Duracion', 'median')
                ).fillna(0).to_dict('index')

                min_t = max_t = rango_t = 0
                tiempos_validos = []
                if resaltar_cuellos:
                    tiempos_validos = [
                        v['Tiempo_Promedio'] for k, v in node_stats.items()
                        if v['Tiempo_Promedio'] > 0
                        and k not in ["Inicio proceso", "Fin proceso"]
                    ]
                    if tiempos_validos:
                        min_t   = min(tiempos_validos)
                        max_t   = max(tiempos_validos)
                        rango_t = max_t - min_t

                nodos_unicos = list(set(
                    edges_stats['Origen'].tolist() + edges_stats['Destino'].tolist()
                ))
                mapa_nodos = {nodo: f"N{i}" for i, nodo in enumerate(nodos_unicos)}

                mermaid_code = "flowchart TD\n"

                def sort_nodes(item):
                    if item[0] == "Inicio proceso": return 0
                    if item[0] == "Fin proceso":    return 2
                    return 1

                nodos_ordenados = sorted(mapa_nodos.items(), key=sort_nodes)

                for nombre_real, nodo_id in nodos_ordenados:
                    nombre_limpio = re.sub(
                        r'[^a-zA-Z0-9 áéíóúÁÉÍÓÚñÑ.,_-]', ' ', str(nombre_real)
                    ).strip() or "Etapa_Desconocida"

                    mermaid_code += f'    {nodo_id}(["{nombre_limpio}"])\n'

                    color_fondo = "#e5e7eb"; color_texto = "#000"
                    color_borde = "#9ca3af"; ancho_borde = "1px"

                    if nombre_real == "Inicio proceso":
                        color_fondo, color_borde, ancho_borde = "transparent", P_TEAL, "2px"
                    elif nombre_real == "Fin proceso":
                        color_fondo, color_borde, ancho_borde = "transparent", P_CORAL, "2px"
                    elif resaltar_cuellos and nombre_real in node_stats and tiempos_validos:
                        t_prom = node_stats[nombre_real]['Tiempo_Promedio']
                        if t_prom > 0:
                            if rango_t == 0:
                                color_fondo = P_HEAT[0]; color_texto = "#000"
                            else:
                                idx = int(round(4 * (t_prom - min_t) / rango_t))
                                idx = max(0, min(4, idx))
                                colores = [
                                    (P_HEAT[0], "#000"), (P_HEAT[1], "#000"),
                                    (P_HEAT[2], "#000"), (P_HEAT[3], "#000"),
                                    (P_HEAT[4], "#fff")
                                ]
                                color_fondo, color_texto = colores[idx]

                    mermaid_code += (
                        f'    style {nodo_id} fill:{color_fondo},'
                        f'stroke:{color_borde},stroke-width:{ancho_borde},color:{color_texto}\n'
                    )

                    if nombre_real in node_stats and nombre_real not in ["Inicio proceso", "Fin proceso"]:
                        datos = node_stats[nombre_real]
                        texto_tooltip = (
                            f"Casos: {int(datos['Casos'])}<br>"
                            f"Promedio: {formato_latino(datos['Tiempo_Promedio'])} días<br>"
                            f"Mediana: {formato_latino(datos['Mediana'])} días"
                        )
                        mermaid_code += f'    click {nodo_id} call noAction() "{texto_tooltip}"\n'
                    elif nombre_real == "Fin proceso":
                        mermaid_code += f'    click {nodo_id} call noAction() "Fin del flujo"\n'
                    elif nombre_real == "Inicio proceso":
                        mermaid_code += f'    click {nodo_id} call noAction() "Inicio del flujo"\n'

                max_frecuencia = edges_stats['Frecuencia'].max() or 1
                estilos_flechas = ""
                tiene_heuristico = False

                for idx, (_, row) in enumerate(edges_stats.iterrows()):
                    origen  = row['Origen']
                    destino = row['Destino']
                    freq    = row['Frecuencia']
                    tiempo  = row['Tiempo_Promedio']

                    is_rework = False
                    rework_confirmado = False
                    if origen == destino:
                        is_rework = True
                        rework_confirmado = tiene_est_orden
                    else:
                        o_order = dict_orden.get(str(origen).strip())
                        d_order = dict_orden.get(str(destino).strip())
                        if o_order is not None and d_order is not None:
                            if d_order < o_order:
                                is_rework = True
                                rework_confirmado = tiene_est_orden
                        else:
                            freq_bwd = edges_stats[
                                (edges_stats['Origen'] == destino) &
                                (edges_stats['Destino'] == origen)
                            ]['Frecuencia'].sum()
                            if freq_bwd > freq:
                                is_rework = True
                                rework_confirmado = False
                                tiene_heuristico  = True

                    if is_rework:
                        color_linea = P_CORAL if rework_confirmado else "#aaaaaa"
                        dash_style  = ",stroke-dasharray: 5 5"
                    else:
                        color_linea = "slategray"
                        dash_style  = ""

                    label = (f"{formato_latino(tiempo)} días" if "Tiempo" in metrica_grafo
                             else f"{formato_latino(freq, 0)} casos")
                    mermaid_code += f'    {mapa_nodos[origen]} -->|"{label}"| {mapa_nodos[destino]}\n'
                    grosor = int(round(2.0 + (freq / max_frecuencia) * 4.0))
                    estilos_flechas += (
                        f'    linkStyle {idx} '
                        f'stroke-width:{grosor}px,stroke:{color_linea}{dash_style}\n'
                    )

                mermaid_code += estilos_flechas

                # Datos popup por nodo
                node_data_popup = {}
                for nombre_real in nodos_unicos:
                    if nombre_real in ["Inicio proceso", "Fin proceso"]:
                        continue
                    df_nodo = df_grafo[df_grafo['Origen'] == nombre_real][
                        ['ID', 'Fecha_Inicio', 'Recurso_Origen', 'Duracion']
                    ].copy()
                    df_nodo['Fecha_Inicio'] = pd.to_datetime(
                        df_nodo['Fecha_Inicio'], errors='coerce'
                    ).dt.strftime('%d-%m-%Y').fillna('—')
                    df_nodo = df_nodo.sort_values('Fecha_Inicio')
                    node_data_popup[nombre_real] = [
                        {
                            'id':       str(r['ID']),
                            'fecha':    str(r['Fecha_Inicio']),
                            'recurso':  str(r['Recurso_Origen']),
                            'duracion': int(r['Duracion']) if pd.notnull(r['Duracion']) else 0
                        }
                        for _, r in df_nodo.iterrows()
                    ]

                render_mermaid(mermaid_code, node_data=node_data_popup,
                               tiene_heuristico=tiene_heuristico)

                # Leyenda dinámica según tipo de reproceso
                rework_leyenda_items = ""
                if tiene_heuristico and tiene_est_orden:
                    rework_leyenda_items = (
                        f'<span style="display:inline-block;width:25px;border-top:2px dashed {P_CORAL};'
                        f'margin-left:5px;"></span> Reproceso (orden definido) &nbsp;&nbsp;'
                        f'<span style="display:inline-block;width:25px;border-top:2px dashed #aaa;'
                        f'margin-left:5px;"></span> Reproceso (inferido)'
                    )
                else:
                    rework_leyenda_items = (
                        f'<span style="display:inline-block;width:25px;border-top:2px dashed {P_CORAL};'
                        f'margin-left:5px;"></span> Reproceso'
                    )

                heat_swatches = "".join([
                    f'<span style="display:inline-block;width:14px;height:14px;'
                    f'background:{c};border:1px solid #ccc;border-radius:3px;"></span>'
                    for c in P_HEAT
                ])

                st.markdown(f"""
                    <div style="display:flex;flex-wrap:wrap;justify-content:center;
                                align-items:center;gap:20px;font-family:Arial,sans-serif;
                                font-size:13px;margin-top:15px;padding:12px;
                                background:#f8f9fa;border-radius:8px;border:1px solid {P_BORDER};">
                        <div style="display:flex;align-items:center;gap:5px;">
                            <b>Flujo:</b>
                            <span style="display:inline-block;width:25px;border-top:2px solid slategray;
                                         margin-left:5px;"></span> Normal &nbsp;
                            {rework_leyenda_items}
                        </div>
                        <div style="display:flex;align-items:center;gap:5px;margin-left:15px;">
                            <b>Tiempo etapa:</b>
                            <span style="margin-left:5px;margin-right:3px;">Mín</span>
                            {heat_swatches}
                            <span style="margin-left:3px;">Máx</span>
                        </div>
                        <div style="font-size:12px;color:{P_GRAY};">
                            Doble clic sobre una etapa para ver los casos asociados
                        </div>
                    </div>
                """, unsafe_allow_html=True)

    # ──────────────────────────────────────────────
    # PESTAÑA 2: ANÁLISIS ESTADÍSTICO
    # ──────────────────────────────────────────────
    with tab2:
        st.subheader("Análisis Estadístico de Tiempos")
        st.caption(
            f"Distribución de duraciones históricas por recurso, etapa y variante. "
            f"{periodo_fechas}."
        )

        _, col_conf = st.columns([4, 1])
        with col_conf:
            confianza_input = st.number_input(
                "Nivel de confianza (%)", min_value=50, max_value=99, value=95, step=1
            )

        N_MIN_VALIDO = 10  # umbral mínimo elevado a 10

        def calcular_estadisticas(df_agrupado, col_agrupacion, col_valor, rename_col):
            """Calcula percentiles empíricos y detecta outliers. Sin supuestos de normalidad."""
            resultados = []
            for grupo, datos in df_agrupado.groupby(col_agrupacion):
                valores = datos[col_valor].dropna().values
                n = len(valores)
                if n == 0:
                    continue

                media  = np.mean(valores)
                mediana = np.median(valores)

                ps = {}
                for p in [5, 25, 75, 95]:
                    sorted_v = np.sort(valores)
                    idx_f    = (p / 100) * (len(sorted_v) - 1)
                    lo, hi   = int(np.floor(idx_f)), int(np.ceil(idx_f))
                    ps[p]    = sorted_v[lo] + (sorted_v[hi] - sorted_v[lo]) * (idx_f - lo)

                q1, q3   = ps[25], ps[75]
                iqr      = q3 - q1
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
                    rename_col:    grupo,
                    "n":           n,
                    "Mediana":     mediana,
                    "Media":       media,
                    "P5":          ps[5],
                    "P25":         ps[25],
                    "P75":         ps[75],
                    "P95":         ps[95],
                    "Calidad":     fiabilidad,
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

        # -- Sección 1: Por Variante (visible por defecto — más accionable) ---
        st.markdown(f"#### Tiempos totales por variante de proceso")
        st.caption(
            f"Duración total (suma de todas las etapas) por caso, agrupada por variante. "
            f"Solo variantes con ≥ {N_MIN_VALIDO} casos."
        )

        stats_var = calcular_estadisticas(df_var, 'Nombre_Variante', 'Duracion_Total', 'Variante')
        stats_var_validas = (stats_var[stats_var['n'] >= N_MIN_VALIDO]
                             .sort_values('n', ascending=False))
        n_excluidas = len(stats_var) - len(stats_var_validas)

        if n_excluidas > 0:
            st.caption(f"ℹ {n_excluidas} variante(s) excluida(s) por tener menos de {N_MIN_VALIDO} casos.")

        if not stats_var_validas.empty:
            diccionario_rutas_t2 = df_var.set_index('Nombre_Variante')['Ruta'].to_dict()
            dict_cal_v  = stats_var_validas.set_index('Variante')['Calidad'].to_dict()
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

        # -- Sección 2: Tiempos por etapa (colapsable custom) ------------------
        lbl_etapa = "Tiempos por etapa" if st.session_state.exp_etapa else "Tiempos por etapa"
        if st.button(lbl_etapa, key="btn_exp_etapa", use_container_width=True):
            st.session_state.exp_etapa = not st.session_state.exp_etapa
            st.rerun()
        if st.session_state.exp_etapa:
            with st.container():
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

        # -- Sección 3: Tiempos por recurso (colapsable custom) ----------------
        lbl_rec = "Tiempos por recurso" if st.session_state.exp_rec else "Tiempos por recurso"
        if st.button(lbl_rec, key="btn_exp_rec", use_container_width=True):
            st.session_state.exp_rec = not st.session_state.exp_rec
            st.rerun()
        if st.session_state.exp_rec:
            with st.container():
                st.caption(
                    "Tiempo promedio que cada recurso demora en completar las etapas asignadas."
                )
                df_rec_t2 = df_trans[df_trans['Recurso_Origen'] != 'Sistema']
                stats_rec  = calcular_estadisticas(df_rec_t2, 'Recurso_Origen', 'Duracion', 'Recurso')
                if not stats_rec.empty:
                    render_tabla_con_calidad(stats_rec, 'Recurso')
                else:
                    st.info("No se encontraron recursos en los datos.")

        # -- Nota metodológica (colapsable custom) -----------------------------
        lbl_met = "Nota metodológica" if st.session_state.exp_metodo else "Nota metodológica"
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

    # ──────────────────────────────────────────────
    # PESTAÑA 3: DIAGNÓSTICO
    # ──────────────────────────────────────────────
    with tab3:
        st.markdown("### Diagnóstico")
        st.caption("Diagnóstico at-a-glance para la toma de decisiones. Basado en el universo completo de casos cargados.")

        N_MIN_RESUMEN = 5
        z_resumen = statistics.NormalDist().inv_cdf((1 + 95 / 100) / 2)

        df_etapas_res = df_trans[
            (df_trans['Origen'] != 'Inicio proceso') &
            (df_trans['Destino'] != 'Fin proceso')
        ]
        etapa_stats = (df_etapas_res.groupby('Origen')
                       .agg(Promedio=('Duracion', 'mean'), Casos=('ID', 'count'))
                       .reset_index().rename(columns={'Origen': 'Etapa'}))
        etapa_stats = etapa_stats[etapa_stats['Promedio'] > 0].sort_values('Promedio', ascending=False)

        def pred_variante(valores, z):
            n = len(valores)
            if n < N_MIN_RESUMEN:
                return None, None, None
            media  = np.mean(valores)
            std    = np.std(valores, ddof=1) if n > 1 else 0.0
            margen = z * std * np.sqrt(1 + 1/n)
            return media, max(0, media - margen), media + margen

        pronostico_rows = []
        diccionario_rutas_res = df_var.set_index('Nombre_Variante')['Ruta'].to_dict()
        for var, grp in df_var.groupby('Nombre_Variante'):
            vals = grp['Duracion_Total'].dropna().values
            media, li, ls = pred_variante(vals, z_resumen)
            if media is not None:
                pronostico_rows.append({
                    'Variante': var,
                    'Ruta':     diccionario_rutas_res.get(var, ''),
                    'Casos':    len(vals),
                    'Promedio': media,
                    'Li95':     li,
                    'Ls95':     ls,
                })
        df_pronostico = (pd.DataFrame(pronostico_rows)
                         .sort_values('Casos', ascending=False).head(5)
                         if pronostico_rows else pd.DataFrame())

        col_cb, col_rec = st.columns(2)

        with col_cb:
            st.markdown("#### ① Cuellos de botella por etapa")
            st.caption("Etapas ordenadas por tiempo de permanencia promedio.")

            if not etapa_stats.empty:
                etapa_stats['Casos_txt']    = etapa_stats['Casos'].apply(lambda x: formato_latino(x, 0))
                etapa_stats['Promedio_txt'] = etapa_stats['Promedio'].apply(lambda x: formato_latino(x, 1))

                fig_cb = px.bar(
                    etapa_stats,
                    x='Promedio', y='Etapa', orientation='h',
                    color='Promedio',
                    color_continuous_scale=["#E1E1E1", P_SALMON, P_CORAL],
                    text=etapa_stats['Promedio'].apply(lambda x: f"{formato_latino(x)} días"),
                    custom_data=['Casos_txt', 'Promedio_txt'],
                    labels={'Promedio': 'Días promedio', 'Etapa': ''},
                )
                fig_cb.update_traces(
                    textposition='outside', cliponaxis=False,
                    hovertemplate=(
                        "<b>%{y}</b><br>Promedio: %{customdata[1]} días<br>"
                        "Casos: %{customdata[0]}<extra></extra>"
                    )
                )
                fig_cb.update_layout(
                    height=380, font=dict(family="Arial", size=13),
                    coloraxis_showscale=False,
                    margin=dict(l=10, r=60, t=10, b=40),
                    yaxis=dict(categoryorder='total ascending'),
                    xaxis_title="Días promedio de permanencia",
                    xaxis=dict(rangemode='tozero'),
                    plot_bgcolor='white', paper_bgcolor='white'
                )
                st.plotly_chart(fig_cb, use_container_width=True)

                peor = etapa_stats.iloc[0]
                bloque_info(
                    P_CORAL, "#fff4f4",
                    f"<b>⚠ Mayor cuello de botella:</b> {peor['Etapa']}<br>"
                    f"Promedio de <b>{formato_latino(peor['Promedio'])} días</b> "
                    f"· {formato_latino(peor['Casos'], 0)} casos"
                )
            else:
                st.info("Sin datos suficientes para calcular cuellos de botella.")

        with col_rec:
            st.markdown("#### ② Recursos con sobrecarga")
            st.caption("Cada punto es un recurso. Eje Y: tiempo promedio por etapa. Tamaño: volumen de etapas procesadas.")

            df_recursos_res = df_trans[df_trans['Recurso_Origen'] != 'Sistema']
            recurso_stats = (df_recursos_res.groupby('Recurso_Origen')
                             .agg(Promedio=('Duracion', 'mean'), Casos=('ID', 'count'))
                             .reset_index().rename(columns={'Recurso_Origen': 'Recurso'}))

            if not recurso_stats.empty:
                recurso_stats['Promedio_txt'] = recurso_stats['Promedio'].apply(lambda x: formato_latino(x, 1))
                recurso_stats['Casos_txt']    = recurso_stats['Casos'].apply(lambda x: formato_latino(x, 0))

                fig_rec = px.scatter(
                    recurso_stats,
                    x='Recurso', y='Promedio',
                    size='Casos',
                    color='Promedio',
                    color_continuous_scale=[P_MINT, P_TEAL, "#5aab9a"],
                    size_max=60,
                    text='Recurso',
                    custom_data=['Casos_txt', 'Promedio_txt'],
                    labels={'Promedio': 'Tiempo promedio (días)', 'Recurso': ''},
                )
                fig_rec.update_traces(
                    textposition='top center',
                    hovertemplate=(
                        "<b>%{x}</b><br>Tiempo promedio: %{customdata[1]} días<br>"
                        "Etapas procesadas: %{customdata[0]}<extra></extra>"
                    )
                )
                fig_rec.update_layout(
                    height=380, font=dict(family="Arial", size=13),
                    coloraxis_showscale=False,
                    margin=dict(l=10, r=30, t=10, b=60),
                    xaxis=dict(showticklabels=False),
                    yaxis_title="Tiempo promedio de procesamiento (días)",
                    yaxis=dict(rangemode='tozero'),
                    plot_bgcolor='white', paper_bgcolor='white'
                )
                st.plotly_chart(fig_rec, use_container_width=True)

                # Criterio robusto: crítico = alto tiempo AND alto volumen
                p75_tiempo = recurso_stats['Promedio'].quantile(0.75)
                med_casos  = recurso_stats['Casos'].median()
                candidatos = recurso_stats[
                    (recurso_stats['Promedio'] > p75_tiempo) &
                    (recurso_stats['Casos']    > med_casos)
                ]
                if not candidatos.empty:
                    peor_r       = candidatos.sort_values('Promedio', ascending=False).iloc[0]
                    criterio_txt = "alto tiempo (>P75) y alto volumen (>mediana)"
                else:
                    peor_r       = recurso_stats.sort_values('Promedio', ascending=False).iloc[0]
                    criterio_txt = "mayor tiempo promedio"

                bloque_info(
                    P_TEAL, "#f0faf8",
                    f"<b>⚠ Recurso más crítico:</b> {peor_r['Recurso']}<br>"
                    f"Promedio de <b>{formato_latino(peor_r['Promedio'])} días</b> "
                    f"· {formato_latino(peor_r['Casos'], 0)} etapas procesadas<br>"
                    f"<span style='font-size:11px;color:{P_GRAY};'>Criterio: {criterio_txt}</span>"
                )
            else:
                st.info("Sin datos de recursos para analizar.")

        st.markdown("<br>", unsafe_allow_html=True)

        # ── Pronóstico Top 5 ──────────────────────────────────────────────────
        st.markdown("#### ③ Pronóstico para casos futuros (Top 5 variantes)")
        st.caption("Estimación de duración total para un caso nuevo según la variante de proceso. Intervalo de predicción al 95% de confianza.")

        if not df_pronostico.empty:
            total_casos_resumen = len(df_var)
            df_pronostico['Pct']         = (df_pronostico['Casos'] / total_casos_resumen) * 100
            df_pronostico['Promedio_txt'] = df_pronostico['Promedio'].apply(lambda x: formato_latino(x, 1))
            df_pronostico['Li95_txt']     = df_pronostico['Li95'].apply(lambda x: formato_latino(x, 1))
            df_pronostico['Ls95_txt']     = df_pronostico['Ls95'].apply(lambda x: formato_latino(x, 1))
            df_pronostico['Casos_txt']    = df_pronostico['Casos'].apply(lambda x: formato_latino(x, 0))
            df_pronostico['Label_Casos']  = df_pronostico.apply(
                lambda r: f"{r['Casos_txt']} ({formato_latino(r['Pct'], 1)}%)", axis=1
            )

            fig_pron = px.scatter(
                df_pronostico,
                x='Variante', y='Promedio',
                error_y=df_pronostico['Ls95'] - df_pronostico['Promedio'],
                error_y_minus=df_pronostico['Promedio'] - df_pronostico['Li95'],
                text='Label_Casos',
                size='Casos', size_max=30,
                color_discrete_sequence=[P_TEAL],
                custom_data=['Li95_txt', 'Ls95_txt', 'Casos_txt', 'Promedio_txt'],
                labels={'Promedio': 'Días (promedio)', 'Variante': ''},
            )
            fig_pron.update_traces(
                textposition='middle right',
                hovertemplate=(
                    "<b>%{x}</b><br>"
                    "Promedio: %{customdata[3]} días<br>"
                    "Intervalo 95%: %{customdata[0]} – %{customdata[1]} días<br>"
                    "Casos: %{customdata[2]}<extra></extra>"
                )
            )
            for _, row in df_pronostico.iterrows():
                for y_val, txt in [(row['Ls95'], formato_latino(row['Ls95'], 1)),
                                   (row['Li95'], formato_latino(row['Li95'], 1))]:
                    fig_pron.add_annotation(
                        x=row['Variante'], y=y_val,
                        text=txt, showarrow=False,
                        xanchor='left', yanchor='middle', xshift=8,
                        font=dict(size=11, color=P_TEAL)
                    )
            fig_pron.update_layout(
                height=350, font=dict(family="Arial", size=13),
                margin=dict(l=10, r=80, t=20, b=60),
                yaxis_title="Duración estimada (días)",
                yaxis=dict(rangemode='tozero'),
                plot_bgcolor='white', paper_bgcolor='white'
            )
            st.plotly_chart(fig_pron, use_container_width=True)

            tabla_pron = df_pronostico[['Variante', 'Casos', 'Promedio', 'Li95', 'Ls95']].copy()
            tabla_pron.columns = ['Variante', 'Casos', 'Promedio', 'Límite Inf. (95%)', 'Límite Sup. (95%)']
            tabla_pron['Variante'] = tabla_pron['Variante'].apply(
                lambda v: f'<span title="{diccionario_rutas_res.get(v, "")}" '
                          f'style="cursor:help;border-bottom:1px dotted #888;">{v}</span>'
            )
            fmt_pron = {
                'Promedio':           lambda x: formato_latino(x) + " días",
                'Límite Inf. (95%)':  lambda x: formato_latino(x) + " días",
                'Límite Sup. (95%)':  lambda x: formato_latino(x) + " días",
                'Casos':              lambda x: formato_latino(x, 0),
            }
            mostrar_tabla_html(tabla_pron.style.hide(axis="index").format(fmt_pron))
        else:
            st.info(f"No hay variantes con al menos {N_MIN_RESUMEN} casos para generar pronósticos.")

    # ──────────────────────────────────────────────
    # PESTAÑA 4: PRONÓSTICO POR VARIANTE
    # ──────────────────────────────────────────────
    with tab4:
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
            logs  = np.log(np.maximum(0.01, valores))
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
                    metodo  = "lognormal"
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
        N_MIN_PRON = 10  # umbral elevado a 10
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
        else:
            max_dias_pron = max(v['p90'] for v in variantes_stats) * 1.10

            def riesgo_variante(st_v):
                cv = ((st_v['p90'] - st_v['p10']) / st_v['p50']
                      if st_v['p50'] > 0 else 99)
                if st_v['p50'] <= 10 and cv < 1.2: return "bajo"
                if st_v['p50'] <= 20 and cv < 1.8: return "medio"
                return "alto"

            # Paleta actualizada
            RIESGO_CFG = {
                "bajo":  {"label": "Predecible",        "border": P_TEAL,   "text": "#1a6b5a"},
                "medio": {"label": "Moderado",          "border": P_SALMON, "text": "#7a3030"},
                "alto":  {"label": "Alta variabilidad", "border": P_CORAL,  "text": "#7a1515"},
            }

            # Filtro por nivel de riesgo
            todos_niveles = sorted(
                set(riesgo_variante(v) for v in variantes_stats),
                key=lambda x: {"bajo": 0, "medio": 1, "alto": 2}[x]
            )
            label_map = {"bajo": "Predecible", "medio": "Moderado", "alto": "Alta variabilidad"}
            opciones   = ["Todos"] + [label_map[n] for n in todos_niveles]
            filtro_lbl = st.selectbox("Filtrar por nivel de variabilidad:", opciones, index=0)
            filtro_inv = {v: k for k, v in label_map.items()}
            filtro_key = None if filtro_lbl == "Todos" else filtro_inv.get(filtro_lbl)

            variantes_filtradas = [
                v for v in variantes_stats
                if filtro_key is None or riesgo_variante(v) == filtro_key
            ]

            if not variantes_filtradas:
                st.info("No hay variantes con ese nivel de variabilidad.")
            else:
                # ── HTML de todas las tarjetas en un solo iframe ──────────────
                cards_inner = ""
                for i_v, st_v in enumerate(variantes_filtradas):
                    r    = riesgo_variante(st_v)
                    cfg  = RIESGO_CFG[r]
                    var  = st_v['variante']
                    p10, p25, p50, p75, p90 = (
                        st_v['p10'], st_v['p25'], st_v['p50'], st_v['p75'], st_v['p90']
                    )
                    n_casos  = st_v['n']
                    pct_txt  = formato_latino(st_v['pct'], 1)
                    ruta_txt = st_v['ruta']
                    nota_txt = (st_v['nota_metodo']
                                .replace("'", "&#39;").replace('"', "&quot;"))
                    cid = f"card_{i_v}"

                    pb10 = min(100, (p10 / max_dias_pron) * 100)
                    pb25 = min(100, (p25 / max_dias_pron) * 100)
                    pb50 = min(100, (p50 / max_dias_pron) * 100)
                    pb75 = min(100, (p75 / max_dias_pron) * 100)
                    pb90 = min(100, (p90 / max_dias_pron) * 100)
                    w80  = max(0, pb90 - pb10)
                    w50  = max(0, pb75 - pb25)

                    # Colores narrativa alineados con paleta
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

                n_cards = len(variantes_filtradas)
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

