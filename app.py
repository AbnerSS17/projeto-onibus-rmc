import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from streamlit_geolocation import streamlit_geolocation
from streamlit_gsheets import GSheetsConnection
from geopy.geocoders import Nominatim
import sqlite3

# 1. Configuração de Página
st.set_page_config(page_title="Monitoramento RMC", layout="wide")

# Inicialização de estados
if 'form' not in st.session_state:
    st.session_state.form = None
if 'confirmado' not in st.session_state:
    st.session_state.confirmado = False

# Estilo CSS para Mobile
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stButton>button { width: 100%; border-radius: 8px; height: 3em; background-color: #007bff; color: white; }
    .location-card { padding: 15px; background: white; border-radius: 10px; border-left: 5px solid #007bff; margin-bottom: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
    </style>
    """, unsafe_allow_html=True)

# 2. Captura de Localização e Endereço
st.subheader("🛰️ Rastreamento em Tempo Real")
location = streamlit_geolocation()

def obter_endereco(lat, lon):
    try:
        geolocator = Nominatim(user_agent="rmc_app")
        location = geolocator.reverse(f"{lat}, {lon}")
        return location.address.split(',')[0] + ", " + location.address.split(',')[1]
    except:
        return "Endereço não identificado"

lat_gps, lon_gps, endereco_atual = None, None, "Aguardando sinal..."

if location.get('latitude'):
    lat_gps = location['latitude']
    lon_gps = location['longitude']
    endereco_atual = obter_endereco(lat_gps, lon_gps)
    
    # Etiqueta de Localização Real-Time
    st.markdown(f"""
    <div class="location-card">
        <small>📍 VOCÊ ESTÁ EM:</small><br>
        <strong>{endereco_atual}</strong><br>
        <small>Coord: {lat_gps:.6f}, {lon_gps:.6f}</small>
    </div>
    """, unsafe_allow_html=True)

# 3. Conexão com Dados
@st.cache_data(ttl=60)
def carregar_dados():
    # Simulando carregamento (Substitua pelas suas conexões reais)
    df_p = pd.DataFrame(columns=['empresa', 'latitude', 'longitude']) # GSheets
    df_f = pd.DataFrame(columns=['nome_ponto', 'latitude', 'longitude']) # SQLite
    return df_p, df_f

df_planilha, df_fixos = carregar_dados()

# 4. Construção do Mapa
# "CartoDB Positron" é excelente para visualização urbana limpa
centro = [lat_gps, lon_gps] if lat_gps else [-22.9064, -47.0616]
m = folium.Map(location=centro, zoom_start=17 if lat_gps else 12, tiles="CartoDB positron")

# Marcador do Usuário
if lat_gps:
    folium.Marker(
        [lat_gps, lon_gps],
        icon=folium.Icon(color="blue", icon="street-view", prefix="fa"),
        tooltip="Sua Posição Atual"
    ).add_to(m)

# Desenhar Pontos de Ônibus (Verdes e Vermelhos) com ícone de Ônibus
for _, row in df_fixos.iterrows():
    folium.Marker(
        [row['latitude'], row['longitude']],
        icon=folium.Icon(color="green", icon="bus", prefix="fa"),
        popup=row.get('nome_ponto')
    ).add_to(m)

# 5. Exibição do Mapa
st_folium(m, width="100%", height=400, key="mapa_rmc")

# 6. Lógica de Cadastro
st.write("---")
col1, col2 = st.columns(2)

with col1:
    if st.button("➕ Cadastrar Ponto (GPS)"):
        st.session_state.form = "auto"
with col2:
    if st.button("🔍 Digitar Localização"):
        st.session_state.form = "manual"

# FORMULÁRIOS
if st.session_state.form == "auto":
    with st.form("form_gps"):
        st.info("O sistema usará sua posição exata agora.")
        st.text_input("Rua Atual", value=endereco_atual, disabled=True)
        st.text_input("Latitude", value=lat_gps, disabled=True)
        st.text_input("Longitude", value=lon_gps, disabled=True)
        nome_ponto = st.text_input("Nome/Número do Ponto")
        
        if st.form_submit_button("Validar Cadastro"):
            st.warning(f"Confirmar cadastro do ponto '{nome_ponto}' nesta localização?")
            if st.button("Sim, Realmente desejo cadastrar!"):
                # Lógica de salvar no DB aqui
                st.success("Ponto cadastrado com sucesso!")
                st.session_state.form = None

elif st.session_state.form == "manual":
    with st.form("form_manual"):
        st.subheader("Cadastro Manual")
        rua_input = st.text_input("Digite o nome da rua e cidade")
        lat_input = st.number_input("Latitude (opcional)", format="%.6f")
        lon_input = st.number_input("Longitude (opcional)", format="%.6f")
        
        btn_verificar = st.form_submit_button("Verificar no Mapa")
        
        if btn_verificar:
            # Aqui você adicionaria a lógica de mover o mapa para a rua digitada
            st.info(f"Buscando: {rua_input}... Se o ponto estiver correto, confirme abaixo.")
            
        if st.form_submit_button("Confirmar Cadastro Manual"):
             st.success("Solicitação enviada!")
