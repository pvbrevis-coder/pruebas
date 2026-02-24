import streamlit as st

P_TEAL   = "#84DCC6"
P_DARK   = "#1f2937"
P_BORDER = "#e5e7eb"

TABS = [
    "Mapa de Proceso",
    "Análisis Estadístico",
    "Diagnóstico",
    "Pronóstico por Variante",
]

HEADER_H = 42   # altura de la barra de título (px)
TABBAR_H = 42   # altura de la barra de pestañas (px)
TOTAL_H  = HEADER_H + TABBAR_H  # altura total del bloque fijo


def render():
    st.markdown(f"""
    <style>
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
    </style>
    <div class="fixed-header">
        <div class="header-dot"></div>
        <div class="header-title">Monitor de Procesos — Análisis de Tiempos y Variantes</div>
    </div>
    """, unsafe_allow_html=True)