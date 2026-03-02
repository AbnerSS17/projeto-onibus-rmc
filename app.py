import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from streamlit_js_eval import streamlit_js_eval
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import sqlite3

# 1. Configuração de Responsividade e Página
st.set_page_config(
    page_title="Mapeamento RMC", 
    layout="wide", # Ajusta o conteúdo à largura da tela
    initial_sidebar_state="collapsed"
)

# CSS para forçar o mapa a ocupar bem a tela do celular
st.markdown("""
    <style>
    .main > div { padding-top: 1rem; }
    iframe { width: 100% !important; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

if 'form_aberto' not in st.session_state:
    st.session_state.form_aberto = None

def fechar_formularios():
    st.session_state.form_aberto = None

st.title("📍 Sistema de Mapeamento RMC")

# --- CONEXÕES DE DADOS ---
# Banco 1: Google Sheets (Novos pontos)
conn = st.connection("gsheets", type=GSheetsConnection)
df_planilha = conn.read(ttl=0)

# Banco 2: SQLite (Pontos de ônibus fixos)
def carregar_pontos_fixos():
    try:
        conn_db = sqlite3.connect('transporte_integrado.db')
        query = "SELECT latitude, longitude, nome_ponto FROM pontos" # Ajuste o nome da tabela/colunas se necessário
        df = pd.read_sql_query(query, conn_db)
        conn_db.close()
        return df
    except:
        return pd.DataFrame()

df_fixos = carregar_pontos_fixos()

# --- LOCALIZAÇÃO GPS ---
loc_auto = streamlit_js_eval(js_expressions="navigator.geolocation.getCurrentPosition(pos => { window.parent.postMessage({type: 'location', pos: pos.coords}, '*') });", key="Location")

# --- ÁREA DO MAPA (TOPO) ---
st.subheader("Visualização em Tempo Real")
centro = [-22.9064, -47.0616]
if loc_auto:
    centro = [loc_auto['latitude'], loc_auto['longitude']]

m = folium.Map(location=centro, zoom_start=14, control_scale=True)

# Plotar Pontos Fixos (Azul - do arquivo .db)
for i, row in df_fixos.iterrows():
    folium.CircleMarker(
        location=[row['latitude'], row['longitude']],
        radius=5,
        color="blue",
        fill=True,
        popup=row.get('nome_ponto', 'Ponto de Ônibus')
    ).add_to(m)

# Plotar Pontos da Planilha (Vermelho - Novos cadastros)
for i, row in df_planilha.iterrows():
    if pd.notnull(row['latitude']):
        folium.Marker(
            [row['latitude'], row['longitude']],
            popup=f"Empresa: {row['empresa']}",
            icon=folium.Icon(color="red", icon="info-sign")
        ).add_to(m)

# Exibição do Mapa Responsivo
st_folium(m, width="100%", height=450, key="mapa_rmc")

# --- BOTÕES DE AÇÃO (ABAIXO DO MAPA) ---
st.divider()
col1, col2 = st.columns(2)
with col1:
    if st.button("➕ Ponto Aqui (GPS)", use_container_width=True):
        st.session_state.form_aberto = 'automatico'
with col2:
    if st.button("🔍 Ponto Manual", use_container_width=True):
        st.session_state.form_aberto = 'manual'

if st.session_state.form_aberto:
    if st.button("❌ Fechar Formulário", use_container_width=True):
        fechar_formularios()

# --- FORMULÁRIOS (APARECEM NO RODAPÉ) ---
if st.session_state.form_aberto == 'automatico':
    with st.form("form_auto"):
        st.write("### Cadastro via GPS")
        empresa = st.text_input("Empresa")
        cat = st.selectbox("Categoria", ["Municipal", "Intermunicipal"])
        if st.form_submit_button("Salvar Agora"):
            # Lógica de salvamento (concat e update) aqui...
            st.success("Salvo!")
            fechar_formularios()
            st.rerun()

if st.session_state.form_aberto == 'manual':
    with st.form("form_manual"):
        st.write("### Cadastro Manual")
        lat_in = st.text_input("Latitude")
        lon_in = st.text_input("Longitude")
        confirm = st.checkbox("Confirmo que o ponto existe")
        if st.form_submit_button("Salvar Manual"):
            # Lógica de salvamento aqui...
            fechar_formularios()
            st.rerun()
