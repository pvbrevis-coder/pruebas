import streamlit as st

P_TEAL   = "#84DCC6"

# Lista de pestañas necesarias para que panel2_tabs.py pueda importarlas
TABS = [
    "Mapa de Proceso",
    "Análisis Estadístico",
    "Diagnóstico",
    "Pronóstico por Variante",
]

# Variable de altura por si alguna versión anterior de panel2_tabs la requiere
TOTAL_H = 84 

def render():
    st.markdown(f"""
    <style>
        .fixed-header {{
            position: fixed; top: 0; left: 0; width: 100%;
            background-color: #ffffff !important; /* BLANCO SÓLIDO (DÍA) */
            padding: 12px 30px;
            z-index: 9999999 !important; /* Z-index extremo para evitar superposición */
            border-bottom: 2px solid {P_TEAL};
            display: flex; align-items: center; gap: 12px;
        }}
        .header-dot {{
            width: 12px; height: 12px; border-radius: 50%;
            background: {P_TEAL}; flex-shrink: 0;
        }}
        .header-title {{
            margin: 0; font-size: 15px !important; font-weight: bold;
            color: #1f2937 !important;
            font-family: Arial, sans-serif !important;
        }}
        
        /* 🌙 MODO OSCURO AUTOMÁTICO */
        @media (prefers-color-scheme: dark) {{
            .fixed-header {{
                background-color: #0e1117 !important; /* GRIS OSCURO SÓLIDO (NOCHE) */
            }}
            .header-title {{
                color: #fafafa !important;
            }}
        }}
    </style>
    <div class="fixed-header">
        <div class="header-dot"></div>
        <div class="header-title">Monitor de Procesos — Análisis de Tiempos y Variantes</div>
    </div>
    """, unsafe_allow_html=True)