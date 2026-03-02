import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from streamlit_js_eval import streamlit_js_eval
from streamlit_gsheets import GSheetsConnection
import sqlite3

# 1. Configuração de Página Responsiva
st.set_page_config(page_title="Mapeamento RMC", layout="wide")

# CSS para dispositivos móveis
st.markdown("""<style> .main { padding: 0rem; } div.stButton > button { width: 100%; border-radius: 5px; height: 3em; } </style>""", unsafe_allow_html=True)

st.title("📍 Sistema de Mapeamento RMC")

# 2. Carregar Dados (Planilha e Banco Local)
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=0)
def carregar_todos_dados():
    # Dados da Planilha
    try:
        df_planilha = conn.read(ttl=0)
    except:
        df_planilha = pd.DataFrame()
    
    # Dados do SQLite (.db)
    try:
        db_conn = sqlite3.connect('transporte_integrado.db')
        df_fixos = pd.read_sql_query("SELECT * FROM pontos", db_conn)
        db_conn.close()
    except:
        df_fixos = pd.DataFrame()
        
    return df_planilha, df_fixos

df_planilha, df_fixos = carregar_todos_dados()

# 3. Captura de Localização
loc = streamlit_js_eval(js_expressions="navigator.geolocation.getCurrentPosition(pos => { window.parent.postMessage({type: 'location', pos: pos.coords}, '*') });", key="Location")

# --- MAPA NO TOPO ---
# Centraliza em Campinas caso o GPS demore a responder
centro_mapa = [-22.9064, -47.0616]
if loc:
    centro_mapa = [loc['latitude'], loc['longitude']]

m = folium.Map(location=centro_mapa, zoom_start=13)

# Adicionar sua localização (Pino Azul)
if loc:
    folium.Marker(centro_mapa, tooltip="Você está aqui", icon=folium.Icon(color="blue", icon="user", prefix="fa")).add_to(m)

# Adicionar pontos da Planilha (Pinos Vermelhos)
for _, row in df_planilha.iterrows():
    if pd.notnull(row['latitude']) and pd.notnull(row['longitude']):
        folium.Marker([row['latitude'], row['longitude']], popup=f"Empresa: {row['empresa']}", icon=folium.Icon(color="red")).add_to(m)

# Adicionar pontos de ônibus do arquivo .db (Círculos Verdes)
for _, row in df_fixos.iterrows():
    if pd.notnull(row['latitude']) and pd.notnull(row['longitude']):
        folium.CircleMarker([row['latitude'], row['longitude']], radius=4, color="green", fill=True).add_to(m)

# Exibição do Mapa
st_folium(m, width="100%", height=400)

# --- BOTÕES NA PARTE DE BAIXO ---
st.write("---")
col1, col2 = st.columns(2)

with col1:
    btn_gps = st.button("➕ Ponto na Localização Atual")
with col2:
    btn_manual = st.button("🔍 Digitar Coordenadas")

# Lógica para mostrar formulários após os botões
if btn_gps:
    st.session_state.form = "gps"
if btn_manual:
    st.session_state.form = "manual"

# Formulário aparece aqui (embaixo dos botões)
if "form" in st.session_state:
    with st.container():
        st.info(f"Editando: {st.session_state.form}")
        # Campos do formulário...
        if st.button("Fechar"):
            del st.session_state.form
            st.rerun()
