import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from streamlit_js_eval import streamlit_js_eval
from streamlit_gsheets import GSheetsConnection
import sqlite3

# 1. Configuração de Página Responsiva
st.set_page_config(page_title="Mapeamento RMC", layout="wide")

# Estilo CSS para melhorar a visualização no celular
st.markdown("""
    <style>
    .reportview-container .main .block-container { padding-top: 1rem; }
    .stAlert { margin-top: 10px; border-radius: 10px; }
    div.stButton > button { width: 100%; border-radius: 10px; height: 3.5em; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# 2. Captura de Localização (GPS) - ESSENCIAL NO TOPO
# Esta linha solicita permissão e captura as coordenadas do navegador
loc = streamlit_js_eval(js_expressions="navigator.geolocation.getCurrentPosition(pos => { window.parent.postMessage({type: 'location', pos: pos.coords}, '*') });", key="Location")

st.title("📍 Sistema de Mapeamento RMC")

# 3. Etiqueta de Texto com Localização (Acima do Mapa)
if loc:
    lat_atual = loc['latitude']
    lon_atual = loc['longitude']
    
    # Exibe uma etiqueta de sucesso com os dados capturados
    st.success(f"✅ **Sua Localização Atual:**\n\n**Latitude:** {lat_atual:.6f} | **Longitude:** {lon_atual:.6f}")
    st.info("💡 *Dica: O nome da rua aparecerá no marcador azul dentro do mapa.*")
else:
    st.warning("📡 Aguardando sinal de GPS... Certifique-se de que a localização está permitida no seu navegador.")

# 4. Conexões de Dados
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=0)
def carregar_dados_completos():
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

df_planilha, df_fixos = carregar_dados_completos()

# --- LÓGICA DE FOCO E CONSTRUÇÃO DO MAPA ---
centro_mapa = [-22.9064, -47.0616] # Centro RMC padrão
zoom_inicial = 12

if loc:
    centro_mapa = [loc['latitude'], loc['longitude']]
    zoom_inicial = 16 # Zoom aproximado para foco no usuário

m = folium.Map(location=centro_mapa, zoom_start=zoom_inicial, control_scale=True)

# A) Marcador da Sua Localização (Azul)
if loc:
    folium.Marker(
        [loc['latitude'], loc['longitude']],
        popup="Você está aqui",
        tooltip="Sua Posição Real",
        icon=folium.Icon(color="blue", icon="user", prefix="fa")
    ).add_to(m)
    # Círculo de precisão
    folium.Circle([loc['latitude'], loc['longitude']], radius=30, color="blue", fill=True, fill_opacity=0.2).add_to(m)

# B) Marcadores da Planilha Excel (Círculos Vermelhos)
for _, row in df_planilha.iterrows():
    if pd.notnull(row['latitude']) and pd.notnull(row['longitude']):
        folium.CircleMarker(
            location=[row['latitude'], row['longitude']],
            radius=7, color="red", fill=True, fill_color="red", fill_opacity=0.8,
            popup=f"Empresa: {row['empresa']}"
        ).add_to(m)

# C) Marcadores do Arquivo DB (Círculos Verdes)
for _, row in df_fixos.iterrows():
    if pd.notnull(row['latitude']) and pd.notnull(row['longitude']):
        folium.CircleMarker(
            location=[row['latitude'], row['longitude']],
            radius=5, color="green", fill=True, fill_color="green", fill_opacity=0.6,
            popup=row.get('nome_ponto', 'Ponto de Ônibus')
        ).add_to(m)

# 5. Exibição do Mapa (Responsivo)
st_folium(m, width="100%", height=450, key="mapa_final")

# 6. Botões de Cadastro (Abaixo do Mapa)
st.write("---")
col1, col2 = st.columns(2)
with col1:
    if st.button("➕ Cadastrar Ponto Aqui"):
        st.session_state.form = "auto"
with col2:
    if st.button("🔍 Digitar Local"):
        st.session_state.form = "manual"
