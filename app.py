import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from streamlit_js_eval import streamlit_js_eval
from streamlit_gsheets import GSheetsConnection
import sqlite3

# 1. Configuração de Página e Responsividade
st.set_page_config(page_title="Mapeamento RMC", layout="wide")

st.markdown("""
    <style>
    .main { padding: 0rem; }
    div.stButton > button { width: 100%; border-radius: 8px; height: 3.5em; background-color: #f0f2f6; }
    </style>
    """, unsafe_allow_html=True)

# Inicialização de estado para o formulário
if 'form_tipo' not in st.session_state:
    st.session_state.form_tipo = None

st.title("📍 Sistema de Mapeamento RMC")

# 2. Conexões de Dados
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=0)
def carregar_dados():
    # Planilha (Pontos Novos - Vermelhos)
    try:
        df_planilha = conn.read(ttl=0)
    except:
        df_planilha = pd.DataFrame()
    
    # Arquivo DB (Pontos Fixos - Verdes)
    try:
        db_conn = sqlite3.connect('transporte_integrado.db')
        df_fixos = pd.read_sql_query("SELECT * FROM pontos", db_conn)
        db_conn.close()
    except:
        df_fixos = pd.DataFrame()
        
    return df_planilha, df_fixos

df_planilha, df_fixos = carregar_dados()

# 3. Captura Constante da Localização (GPS)
# Esta função roda assim que a página abre
loc = streamlit_js_eval(js_expressions="navigator.geolocation.getCurrentPosition(pos => { window.parent.postMessage({type: 'location', pos: pos.coords}, '*') });", key="Location")

# --- LÓGICA DO MAPA ---
# Se estiver no formulário manual, o mapa foca no que for digitado. 
# Caso contrário, foca sempre no usuário ou no centro da RMC.
centro_mapa = [-22.9064, -47.0616] 
zoom_atual = 12

if loc:
    centro_mapa = [loc['latitude'], loc['longitude']]
    zoom_atual = 15

m = folium.Map(location=centro_mapa, zoom_start=zoom_atual, control_scale=True)

# A) Mostrar SUA LOCALIZAÇÃO (Pino azul com pulso)
if loc:
    folium.Marker(
        [loc['latitude'], loc['longitude']],
        tooltip="Sua Localização Atual",
        icon=folium.Icon(color="blue", icon="user", prefix="fa")
    ).add_to(m)
    # Círculo azul em volta para destacar
    folium.Circle([loc['latitude'], loc['longitude']], radius=50, color="blue", fill=True, fill_opacity=0.2).add_to(m)

# B) PONTOS DA PLANILHA (Círculos Vermelhos)
for _, row in df_planilha.iterrows():
    if pd.notnull(row['latitude']) and pd.notnull(row['longitude']):
        folium.CircleMarker(
            location=[row['latitude'], row['longitude']],
            radius=6,
            color="red",
            fill=True,
            fill_color="red",
            fill_opacity=0.7,
            popup=f"Empresa: {row['empresa']}"
        ).add_to(m)

# C) PONTOS DO ARQUIVO DB (Círculos Verdes)
for _, row in df_fixos.iterrows():
    if pd.notnull(row['latitude']) and pd.notnull(row['longitude']):
        folium.CircleMarker(
            location=[row['latitude'], row['longitude']],
            radius=6,
            color="green",
            fill=True,
            fill_color="green",
            fill_opacity=0.7,
            popup=row.get('nome_ponto', 'Ponto de Ônibus')
        ).add_to(m)

# EXIBIÇÃO DO MAPA (Topo da página)
st_folium(m, width="100%", height=450)

# --- BOTÕES (Abaixo do mapa) ---
st.write("---")
col1, col2 = st.columns(2)

with col1:
    if st.button("➕ Cadastrar Ponto Aqui"):
        st.session_state.form_tipo = "auto"
with col2:
    if st.button("🔍 Digitar Local Diferente"):
        st.session_state.form_tipo = "manual"

# --- FORMULÁRIOS ---
if st.session_state.form_tipo == "auto" and loc:
    with st.expander("📝 Confirmar Cadastro no Local Atual", expanded=True):
        st.write(f"Coordenadas: `{loc['latitude']}, {loc['longitude']}`")
        empresa = st.text_input("Nome da Empresa")
        if st.button("Salvar na Planilha"):
            # Lógica de salvar...
            st.success("Ponto salvo com sucesso!")
            st.session_state.form_tipo = None
            st.rerun()

if st.session_state.form_tipo == "manual":
    with st.expander("📝 Digitar Coordenadas Manuais", expanded=True):
        st.warning("Ao digitar aqui, o mapa acima focará no novo endereço.")
        rua = st.text_input("Rua/Referência")
        lat_manual = st.text_input("Latitude")
        lon_manual = st.text_input("Longitude")
        if st.button("Validar e Salvar"):
            # Lógica de salvar manual...
            st.session_state.form_tipo = None
            st.rerun()

if st.session_state.form_tipo:
    if st.button("❌ Cancelar"):
        st.session_state.form_tipo = None
        st.rerun()
