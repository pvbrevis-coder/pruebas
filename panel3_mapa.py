import streamlit as st
import pandas as pd
import plotly.express as px
import streamlit.components.v1 as components
import base64
import json
import re

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
P_BORDER = "#e5e7eb"
P_HEAT   = ["#E1E1E1", "#fde8e7", P_SALMON, "#ff9292", P_CORAL]


def formato_latino(numero, decimales=1):
    if pd.isna(numero): return "0"
    if decimales == 0:
        formateado = f"{int(numero):,}"
    else:
        formateado = f"{numero:,.{decimales}f}"
    return formateado.replace(',', 'X').replace('.', ',').replace('X', '.')


def render_mermaid(code: str, node_data: dict = None, node_stats: dict = None, tiene_heuristico: bool = False):
    b64_code = base64.b64encode(code.encode('utf-8')).decode('utf-8')
    node_data_js = json.dumps(node_data or {}, ensure_ascii=False)
    node_stats_js = json.dumps(node_stats or {}, ensure_ascii=False)

    if tiene_heuristico:
        leyenda_reproceso = (
            f'<span style="display:inline-block;width:25px;border-top:2px dashed {P_CORAL};margin:0 5px;"></span> Reproceso confirmado'
            f'<span style="display:inline-block;width:25px;border-top:2px dashed #aaa;margin:0 5px;margin-left:12px;"></span> Reproceso heurístico'
        )
    else:
        leyenda_reproceso = f'<span style="display:inline-block;width:25px;border-top:2px dashed {P_CORAL};margin:0 5px;"></span> Reproceso'

    html_content = f"""
    <!DOCTYPE html><html><head><meta charset="utf-8">
    <style>
        /* CSS Base (Día) */
        body {{ margin:0; padding:0; display:flex; justify-content:center; font-family:Arial; position:relative; color: #1f2937; }}
        #graphDiv {{ width:100%; height:100%; display:flex; justify-content:center; align-items:center; padding-top:20px; }}
        
        /* Modal y Tablas Base */
        #nodeModal {{ display:none; position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.45); z-index:9999999; justify-content:center; align-items:center; }}
        #nodeModal.open {{ display:flex; }}
        #modalBox {{ background:#fff; border-radius:10px; box-shadow:0 8px 32px rgba(0,0,0,0.25); width:700px; max-width:95vw; max-height:80vh; display:flex; flex-direction:column; overflow:hidden; }}
        #modalHeader {{ background:#1f2937; color:#fff; padding:14px 20px; display:flex; justify-content:space-between; align-items:center; }}
        #modalTitle {{ font-size:15px; font-weight:bold; margin:0; }}
        #modalSubtitle {{ font-size:12px; color:#9ca3af; margin:2px 0 0 0; }}
        #modalClose {{ background:none; border:none; color:#fff; font-size:22px; cursor:pointer; line-height:1; }}
        #modalBody {{ overflow-y:auto; flex:1; padding:0; }}
        #modalTable {{ width:100%; border-collapse:collapse; font-size:13px; }}
        #modalTable thead th {{ background:#f8f9fa; border-bottom:2px solid {P_TEAL}; padding:10px 14px; text-align:left; color:#374151; position:sticky; top:0; z-index:10; }}
        #modalTable tbody td {{ padding:8px 14px; border-bottom:1px solid #f0f0f0; }}
        #modalTable tbody tr:hover {{ background:#f6fffe; }}
        #modalFooter {{ padding:10px 20px; font-size:12px; color:#6b7280; border-top:1px solid #e5e7eb; background:#fafafa; }}

        /* 💡 ESTE ES EL NUEVO TOOLTIP CUSTOM Y ELEGANTE */
        #customTooltip {{
            position: absolute;
            background: rgba(31, 41, 55, 0.95); /* Color oscuro semi-transparente */
            color: #ffffff;
            padding: 10px 14px;
            border-radius: 6px;
            font-size: 13px;
            pointer-events: none; /* Para que el ratón no interfiera con él */
            z-index: 9999999;
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
            opacity: 0;
            transition: opacity 0.1s ease;
            white-space: nowrap;
            line-height: 1.5;
        }}

        /* 🌙 MODO OSCURO AUTOMÁTICO */
        @media (prefers-color-scheme: dark) {{
            body {{ color: #fafafa; }}
            #modalBox {{ background: #262730; }}
            #modalHeader {{ background: #0e1117; color: #fafafa; }}
            #modalTable thead th {{ background: #0e1117; color: #fafafa; }}
            #modalTable tbody td {{ border-bottom: 1px solid #333; }}
            #modalTable tbody tr:hover {{ background: rgba(132,220,198,0.1); }}
            #modalFooter {{ background: #0e1117; border-top: 1px solid #333; color: #aaa; }}
            #customTooltip {{ background: #262730; border: 1px solid #444; }}
        }}
    </style>
    </head>
    <body>
        <div id="graphDiv">Generando mapa de proceso...</div>
        <div id="customTooltip"></div>
        
        <div id="nodeModal"><div id="modalBox">
            <div id="modalHeader"><div><p id="modalTitle"></p><p id="modalSubtitle"></p></div><button id="modalClose" title="Cerrar">&#10005;</button></div>
            <div id="modalBody"><table id="modalTable">
                <thead><tr><th>ID Caso</th><th>Fecha</th><th>Recurso</th><th>Días</th></tr></thead>
                <tbody id="modalTableBody"></tbody>
            </table></div>
            <div id="modalFooter"></div>
        </div></div>
        <script type="module">
            window.noAction = function() {{ return false; }};
            const NODE_DATA = {node_data_js};
            const NODE_STATS = {node_stats_js};
            const tooltip = document.getElementById('customTooltip');
            
            import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
            mermaid.initialize({{ startOnLoad:false, theme:'base', fontFamily:'Arial', securityLevel:'loose', flowchart:{{ arrowMarkerAbsolute:true }} }});
            
            const modal=document.getElementById('nodeModal'), mT=document.getElementById('modalTitle'), mS=document.getElementById('modalSubtitle'), mB=document.getElementById('modalTableBody'), mF=document.getElementById('modalFooter'), mC=document.getElementById('modalClose');
            function openModal(name) {{
                const rows=NODE_DATA[name]; if(!rows||rows.length===0) return;
                mT.textContent=name; mS.textContent=rows.length+' casos'; mF.textContent='Total: '+rows.length;
                mB.innerHTML='';
                rows.forEach(r=>{{ mB.innerHTML+=`<tr><td>${{r.id||'-'}}</td><td>${{r.fecha||'-'}}</td><td>${{r.recurso||'-'}}</td><td style="text-align:center;">${{r.duracion!==undefined?r.duracion:'-'}}</td></tr>`; }});
                modal.classList.add('open');
            }}
            mC.onclick=()=>modal.classList.remove('open');
            modal.addEventListener('click', e => {{ if(e.target === modal) modal.classList.remove('open'); }});
            document.addEventListener('keydown', e => {{ if(e.key === 'Escape') modal.classList.remove('open'); }});
            
            try {{
                mermaid.render('mermaid-svg', decodeURIComponent(escape(window.atob("{b64_code}")))).then(r=>{{
                    document.getElementById('graphDiv').innerHTML=r.svg;
                    
                    // 💡 LÓGICA DEL TOOLTIP JAVASCRIPT CUSTOM
                    document.querySelectorAll('.node').forEach(n=>{{
                        const lblEl=n.querySelector('span')||n.querySelector('p')||n.querySelector('text');
                        if(!lblEl) return;
                        const lbl=lblEl.textContent.trim();
                        
                        // Eliminar title nativo si Mermaid lo agregó para evitar duplicados
                        const titleEl = n.querySelector('title');
                        if(titleEl) titleEl.remove();

                        if(NODE_DATA[lbl]){{ 
                            n.style.cursor='pointer'; 
                            n.ondblclick=e=>{{ e.stopPropagation(); tooltip.style.opacity = 0; openModal(lbl); }}; 
                            
                            if(NODE_STATS[lbl]) {{
                                n.onmouseenter = e => {{
                                    const n_stat = NODE_STATS[lbl];
                                    // Usamos doble llave para escapar la interpolación de Javascript del f-string de Python
                                    tooltip.innerHTML = `Casos: ${{n_stat.casos}}<br>Promedio: ${{n_stat.promedio}} días<br>Mediana: ${{n_stat.mediana}} días<br><hr style="margin:8px 0; border:none; border-top:1px solid #4b5563;"><span style="color:#84DCC6;"> Doble clic para ver registros</span>`;
                                    tooltip.style.opacity = 1;
                                }};
                                n.onmousemove = e => {{
                                    tooltip.style.left = (e.pageX + 15) + 'px';
                                    tooltip.style.top = (e.pageY + 15) + 'px';
                                }};
                                n.onmouseleave = () => tooltip.style.opacity = 0;
                            }}
                        }} else if (lbl === "Inicio proceso" || lbl === "Fin proceso") {{
                            n.onmouseenter = e => {{
                                tooltip.innerHTML = lbl === "Inicio proceso" ? "Inicio del flujo" : "Fin del flujo";
                                tooltip.style.opacity = 1;
                            }};
                            n.onmousemove = e => {{
                                tooltip.style.left = (e.pageX + 15) + 'px';
                                tooltip.style.top = (e.pageY + 15) + 'px';
                            }};
                            n.onmouseleave = () => tooltip.style.opacity = 0;
                        }}
                    }});
                }});
            }} catch(e) {{ document.getElementById('graphDiv').innerHTML="<div style='color:red;'>Error gráfico</div>"; }}
            
            // Script para colorear flechas SVG en Mermaid
            setInterval(function(){{
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


# ==========================================
# FUNCIÓN PRINCIPAL
# ==========================================
def render():
    df_trans        = st.session_state.df_transiciones
    df_var          = st.session_state.df_variantes
    dict_orden      = st.session_state.dict_orden
    periodo_fechas  = st.session_state.periodo_fechas
    tiene_est_orden = st.session_state.tiene_est_orden

    # Layout principal: gráfico izquierda, panel derecha
    col_grafo, col_panel = st.columns([7, 3])

    # ── Panel derecho: controles + gráfico de variantes ──────────────────
    with col_panel:
        st.write("**Visualización del Mapa**")
        
        # Un solo radiobutton con las 3 opciones agrupadas verticalmente
        modo_mapa = st.radio(
            "Opciones de visualización:",
            [
                "Frecuencia (Casos)", 
                "Tiempo promedio (Días)", 
                "Resaltar cuellos de botella"
            ],
            horizontal=False,
            label_visibility="collapsed",
            key="radio_modo_mapa"
        )

        # Mapeamos la selección a las variables lógicas
        if modo_mapa == "Frecuencia (Casos)":
            metrica_grafo = "Frecuencia (Casos)"
            resaltar_cuellos = False
        elif modo_mapa == "Tiempo promedio (Días)":
            metrica_grafo = "Tiempo promedio (Días)"
            resaltar_cuellos = False
        else: # "Resaltar cuellos de botella"
            metrica_grafo = "Tiempo promedio (Días)"
            resaltar_cuellos = True
            
        st.markdown("<div style='height:15px'></div>", unsafe_allow_html=True)

        # Gráfico de variantes
        with st.container(height=680):
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
                title="Variantes del proceso (clic para filtrar)",
                text='Porcentaje_Txt',
                custom_data=['Nombre_Variante', 'Ruta_Tooltip', 'Ruta', 'Porcentaje_Txt'],
                color_discrete_sequence=[P_TEAL]
            )
            # El tooltip de Plotly SI soporta <br> porque es HTML nativo de plotly
            fig.update_traces(
                textposition='outside', cliponaxis=False,
                hovertemplate=(
                    "<b>%{y}</b><br>Casos: %{x} (%{customdata[3]})"
                    "<br><br><b>Ruta:</b><br>%{customdata[1]}<extra></extra>"
                )
            )
            fig.update_layout(
                height=630, font=dict(family="Arial"),
                margin=dict(l=0, r=50, t=40, b=40),
                yaxis_title=None,
                plot_bgcolor='rgba(0,0,0,0)', 
                paper_bgcolor='rgba(0,0,0,0)'
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

    # ── Columna izquierda: mapa ───────────────────────────────────────────
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

            for nombre_real, nodo_id in sorted(mapa_nodos.items(), key=sort_nodes):
                nombre_limpio = re.sub(
                    r'[^a-zA-Z0-9 áéíóúÁÉÍÓÚñÑ.,_-]', ' ', str(nombre_real)
                ).strip() or "Etapa_Desconocida"

                mermaid_code += f'    {nodo_id}(["{nombre_limpio}"])\n'

                color_fondo, color_texto, color_borde, ancho_borde = "#e5e7eb", "#000", "#9ca3af", "1px"

                if nombre_real == "Inicio proceso":
                    color_fondo, color_texto, color_borde, ancho_borde = "#ffffff", "#000000", P_TEAL, "2px"
                elif nombre_real == "Fin proceso":
                    color_fondo, color_texto, color_borde, ancho_borde = "#ffffff", "#000000", P_CORAL, "2px"
                elif resaltar_cuellos and nombre_real in node_stats and rango_t > 0:
                    t_prom = node_stats[nombre_real]['Tiempo_Promedio']
                    if t_prom > 0:
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

                # 💡 Ahora Mermaid solo crea el nodo clicable SIN agregarle tooltip. El JS se encarga del tooltip.
                if nombre_real in node_stats and nombre_real not in ["Inicio proceso", "Fin proceso"]:
                    mermaid_code += f'    click {nodo_id} call noAction()\n'
                elif nombre_real == "Fin proceso":
                    mermaid_code += f'    click {nodo_id} call noAction()\n'
                elif nombre_real == "Inicio proceso":
                    mermaid_code += f'    click {nodo_id} call noAction()\n'

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

            # Preparamos los diccionarios que Javascript leerá (Modal y Tooltips)
            node_data_popup = {}
            node_stats_popup = {}
            
            for nombre_real in nodos_unicos:
                if nombre_real in ["Inicio proceso", "Fin proceso"]:
                    continue
                # Datos para la tabla del Doble Clic
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
                
                # Datos para el Tooltip flotante (Hover)
                if nombre_real in node_stats:
                    node_stats_popup[nombre_real] = {
                        'casos': int(node_stats[nombre_real]['Casos']),
                        'promedio': formato_latino(node_stats[nombre_real]['Tiempo_Promedio']),
                        'mediana': formato_latino(node_stats[nombre_real]['Mediana'])
                    }

            # Llamamos a la función de renderizado inyectando los datos para JS
            render_mermaid(mermaid_code, node_data=node_data_popup, node_stats=node_stats_popup, tiene_heuristico=tiene_heuristico)

            # Leyenda
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
                            background:var(--secondary-background-color); border-radius:8px;">
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
                    <div style="font-size:12px;opacity:0.8;">
                        Doble clic sobre una etapa para ver los casos asociados
                    </div>
                </div>
            """, unsafe_allow_html=True)