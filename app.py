import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from streamlit_js_eval import streamlit_js_eval
from streamlit_gsheets import GSheetsConnection
import sqlite3

# 1. Configuração de Página e Estilo Responsivo
st.set_page_config(page_title="Mapeamento RMC", layout="wide")

# CSS para botões grandes no celular
st.markdown("""
    <style>
    .main { padding: 0rem; }
    div.stButton > button { width: 100%; border-radius: 10px; height: 3.5em; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# Inicialização de estados
if 'form_aberto' not in st.session_state:
    st.session_state.form_aberto = None

st.title("📍 Sistema de Mapeamento RMC")

# 2. Captura de Localização (ESTE BLOCO DEVE VIR ANTES DO MAPA)
# Força a requisição do GPS assim que a página abre
loc = streamlit_js_eval(js_expressions="navigator.geolocation.getCurrentPosition(pos => { window.parent.postMessage({type: 'location', pos: pos.coords}, '*') });", key="Location")

# 3. Conexões de Dados
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=0)
def carregar_dados():
    try:
        df_p = conn.read(ttl=0)
    except:
        df_p = pd.DataFrame()
    try:
        db_conn = sqlite3.connect('transporte_integrado.db')
        df_f = pd.read_sql_query("SELECT * FROM pontos", db_conn)
        db_conn.close()
    except:
        df_f = pd.DataFrame()
    return df_p, df_f

df_planilha, df_fixos = carregar_dados()

# --- LÓGICA DE FOCO DO MAPA ---
# Centro padrão (Campinas) caso o GPS ainda não tenha carregado
centro_mapa = [-22.9064, -47.0616]
zoom_atual = 12

# SE o GPS retornar a localização, o mapa FOCA nela automaticamente
if loc:
    centro_mapa = [loc['latitude'], loc['longitude']]
    zoom_atual = 16  # Zoom mais próximo para ver a rua
    st.success(f"Sinal de GPS Ativo: {loc['latitude']:.4f}, {loc['longitude']:.4f}")

# EXCEÇÃO: Se o usuário estiver digitando manualmente, o foco muda apenas se ele preencher a lat/lon
# Caso contrário, o GPS continua mandando no foco.

# 4. Construção do Mapa
m = folium.Map(location=centro_mapa, zoom_start=zoom_atual, control_scale=True)

# A) SUA LOCALIZAÇÃO (Ponto Azul com Ícone de Usuário)
if loc:
    folium.Marker(
        location=[loc['latitude'], loc['longitude']],
        tooltip="Sua Posição",
        icon=folium.Icon(color="blue", icon="user", prefix="fa")
    ).add_to(m)
    # Círculo de precisão azul
    folium.Circle([loc['latitude'], loc['longitude']], radius=40, color="blue", fill=True, fill_opacity=0.1).add_to(m)

# B) PONTOS DA PLANILHA (Círculos Vermelhos)
for _, row in df_planilha.iterrows():
    if pd.notnull(row['latitude']):
        folium.CircleMarker(
            location=[row['latitude'], row['longitude']],
            radius=7, color="red", fill=True, fill_color="red", fill_opacity=0.8,
            popup=f"Empresa: {row['empresa']}"
        ).add_to(m)

# C) PONTOS DO ARQUIVO DB (Círculos Verdes)
for _, row in df_fixos.iterrows():
    if pd.notnull(row['latitude']):
        folium.CircleMarker(
            location=[row['latitude'], row['longitude']],
            radius=5, color="green", fill=True, fill_color="green", fill_opacity=0.6,
            popup=row.get('nome_ponto', 'Ponto de Ônibus')
        ).add_to(m)

# Exibe o Mapa Responsivo
st_folium(m, width="100%", height=450, key="mapa_dinamico")

# --- BOTÕES DE AÇÃO (ABAIXO DO MAPA) ---
st.write("---")
col1, col2 = st.columns(2)

with col1:
    if st.button("➕ Ponto no Local Atual"):
        st.session_state.form_aberto = "auto"
with col2:
    if st.button("🔍 Ponto em Outro Local"):
        st.session_state.form_aberto = "manual"

# --- FORMULÁRIOS ---
if st.session_state.form_aberto == "auto" and loc:
    with st.container():
        st.info("Cadastrando ponto na sua posição atual.")
        # Campos de input aqui...
        if st.button("Confirmar Salva"):
            st.session_state.form_aberto = None
            st.rerun()

if st.session_state.form_aberto == "manual":
    with st.container():
        st.warning("O foco do mapa sairá do seu GPS enquanto você digita.")
        # Inputs manuais aqui...
        if st.button("Voltar ao GPS"):
            st.session_state.form_aberto = None
            st.rerun()
