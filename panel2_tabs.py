import streamlit as st

import panel3_mapa
import panel3_estadisticas
import panel3_diagnostico
import panel3_pronostico

from panel1_header import TABS

P_TEAL   = "#84DCC6"
P_MINT   = "#A5FFD6"
P_DARK   = "#1f2937"

# Espaciado parametrizable
DISTANCIA_BOTONES_TITULO = 25 

def render():
    # ── Sidebar ───────────────────────────────────────────────────────────
    st.sidebar.markdown(
        f"<div style='font-size:11px;color:var(--text-color); opacity: 0.7; margin-bottom:4px;"
        f"font-family:Arial;'>{st.session_state.periodo_fechas}</div>",
        unsafe_allow_html=True,
    )
    st.sidebar.markdown("---")
    if st.sidebar.button("Cargar nuevos archivos", use_container_width=True):
        st.session_state.datos_procesados = False
        st.rerun()

    if "tab_idx" not in st.session_state:
        st.session_state.tab_idx = 0

    idx = st.session_state.tab_idx

    # ── Estilos CSS Theme-Aware ───────────────────────────────────────────
    st.markdown(
        f"""
        <style>
            /* 🎯 BOTÓN ACTIVO */
            [data-testid="stHorizontalBlock"]:first-of-type button[data-testid="baseButton-primary"] {{
                background-color: {P_MINT} !important;
                color: {P_DARK} !important; /* Siempre oscuro para contraste con el verde claro */
                font-weight: 700 !important;
                border: 1px solid {P_TEAL} !important;
                border-radius: 6px !important;
            }}
            
            /* ⚪ BOTONES INACTIVOS */
            [data-testid="stHorizontalBlock"]:first-of-type button[data-testid="baseButton-secondary"] {{
                background-color: transparent !important;
                color: var(--text-color) !important;
                font-weight: 500 !important;
                border: 1px solid var(--secondary-background-color) !important;
                border-radius: 6px !important;
            }}
            
            /* Efecto Hover inactivos */
            [data-testid="stHorizontalBlock"]:first-of-type button[data-testid="baseButton-secondary"]:hover {{
                border-color: {P_TEAL} !important;
                color: {P_TEAL} !important;
                background-color: var(--secondary-background-color) !important;
            }}
        </style>
        """,
        unsafe_allow_html=True
    )

    # ── Renderizado de la fila de botones ────────────────────────────────
    cols = st.columns(len(TABS))
    for i, (col, nombre) in enumerate(zip(cols, TABS)):
        with col:
            tipo_boton = "primary" if i == idx else "secondary"
            if st.button(nombre, key=f"tab_{i}", use_container_width=True, type=tipo_boton):
                st.session_state.tab_idx = i
                st.rerun()

    # ── Espaciador ────────────────────────────────────────────────────────
    st.markdown(f"<div style='height: {DISTANCIA_BOTONES_TITULO}px;'></div>", unsafe_allow_html=True)

    # ── Enrutamiento ──────────────────────────────────────────────────────
    if idx == 0: panel3_mapa.render()
    elif idx == 1: panel3_estadisticas.render()
    elif idx == 2: panel3_diagnostico.render()
    elif idx == 3: panel3_pronostico.render()