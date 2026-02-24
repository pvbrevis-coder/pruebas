import streamlit as st

import panel3_mapa
import panel3_estadisticas
import panel3_diagnostico
import panel3_pronostico

from panel1_header import TABS

P_TEAL   = "#84DCC6"
P_MINT   = "#A5FFD6"
P_DARK   = "#1f2937"
P_GRAY   = "#6b7280"
P_BORDER = "#e5e7eb"

# =========================================================================
# PARÁMETRO DE ESPACIADO
# =========================================================================
# Ajusta este número (en píxeles) para separar la botonera del título inferior
DISTANCIA_BOTONES_TITULO = 10 
# =========================================================================


def render():
    # ── Sidebar ───────────────────────────────────────────────────────────
    st.sidebar.markdown(
        f"<div style='font-size:11px;color:#9ca3af;margin-bottom:4px;"
        f"font-family:Arial;'>{st.session_state.periodo_fechas}</div>",
        unsafe_allow_html=True,
    )
    st.sidebar.markdown("---")
    if st.sidebar.button("Cargar nuevos archivos", use_container_width=True):
        st.session_state.datos_procesados = False
        st.rerun()

    # ── Estado de la pestaña activa ───────────────────────────────────────
    if "tab_idx" not in st.session_state:
        st.session_state.tab_idx = 0

    idx = st.session_state.tab_idx

    # ── Estilos CSS Dinámicos para Primary (Activo) y Secondary (Inactivos) ──
    st.markdown(
        f"""
        <style>
            /* BOTÓN ACTIVO (Capturado por el tipo Primary) */
            [data-testid="stHorizontalBlock"]:first-of-type button[data-testid="baseButton-primary"] {{
                background-color: {P_MINT} !important;
                color: {P_DARK} !important;
                font-weight: 700 !important;
                border: 1px solid {P_TEAL} !important;
                border-radius: 6px !important;
                box-shadow: 0px 2px 4px rgba(0,0,0,0.08) !important;
            }}
            
            /* BOTONES INACTIVOS (Capturados por el tipo Secondary) */
            [data-testid="stHorizontalBlock"]:first-of-type button[data-testid="baseButton-secondary"] {{
                background-color: #ffffff !important;
                color: {P_GRAY} !important;
                font-weight: 500 !important;
                border: 1px solid {P_BORDER} !important;
                border-radius: 6px !important;
            }}
            
            /* Efecto Hover solo para los inactivos */
            [data-testid="stHorizontalBlock"]:first-of-type button[data-testid="baseButton-secondary"]:hover {{
                border-color: {P_TEAL} !important;
                color: {P_TEAL} !important;
                background-color: #f9fafb !important;
            }}
        </style>
        """,
        unsafe_allow_html=True
    )

    # ── Fila de botones usando la asignación dinámica de tipo ────────────────
    cols = st.columns(len(TABS))
    for i, (col, nombre) in enumerate(zip(cols, TABS)):
        with col:
            # Asignamos tipo 'primary' solo al botón seleccionado
            tipo_boton = "primary" if i == idx else "secondary"
            
            if st.button(nombre, key=f"tab_{i}", use_container_width=True, type=tipo_boton):
                st.session_state.tab_idx = i
                st.rerun()

    # ── Espaciador Parametrizable ─────────────────────────────────────────
    st.markdown(
        f"<div style='height: {DISTANCIA_BOTONES_TITULO}px;'></div>",
        unsafe_allow_html=True,
    )

    # ── Enrutamiento al Panel 3 ───────────────────────────────────────────
    if idx == 0:
        panel3_mapa.render()
    elif idx == 1:
        panel3_estadisticas.render()
    elif idx == 2:
        panel3_diagnostico.render()
    elif idx == 3:
        panel3_pronostico.render()