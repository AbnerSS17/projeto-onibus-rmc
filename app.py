import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from streamlit_geolocation import streamlit_geolocation
from streamlit_autorefresh import st_autorefresh
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
import sqlite3

# 1. Configurações e Estilo
st.set_page_config(page_title="RMC - Gestão de Pontos", layout="wide")
st_autorefresh(interval=10000, key="global_refresh")

# --- DATABASE / CARREGAMENTO ---
@st.cache_data(ttl=60)
def carregar_todos_pontos():
    # Aqui unificamos as fontes para checagem de proximidade
    # Simulação de dados (Substitua pela sua leitura de DB/Excel)
    pontos_existentes = [
        {"nome": "Ponto Exemplo 1", "lat": -22.9060, "lon": -47.0610},
        {"nome": "Ponto Exemplo 2", "lat": -22.9070, "lon": -47.0620}
    ]
    return pd.DataFrame(pontos_existentes)

df_pontos = carregar_todos_pontos()

def checar_duplicidade(nova_lat, nova_lon, dataframe, raio_metros=20):
    for _, ponto in dataframe.iterrows():
        distancia = geodesic((nova_lat, nova_lon), (ponto['latitude'], ponto['longitude'])).meters
        if distancia < raio_metros:
            return True, ponto['nome']
    return False, None

# --- CAPTURA DE GPS ---
loc_data = streamlit_geolocation()
lat_user, lon_user = loc_data.get('latitude'), loc_data.get('longitude')

# --- INTERFACE (MENU) ---
st.sidebar.title("📍 Menu de Opções")
opcao = st.sidebar.radio("Navegação:", ["Visualizar Mapa", "Cadastrar Ponto (GPS)", "Cadastrar Ponto (Manual)"])

# --- LÓGICA DE TELAS ---

# TELA 1: APENAS VISUALIZAÇÃO
if opcao == "Visualizar Mapa":
    st.title("🗺️ Mapa Integrado")
    centro = [lat_user, lon_user] if lat_user else [-22.9064, -47.0616]
    m = folium.Map(location=centro, zoom_start=17 if lat_user else 13, tiles='OpenStreetMap')
    
    if lat_user:
        folium.Marker([lat_user, lon_user], tooltip="Você", icon=folium.Icon(color="blue", icon="user", prefix="fa")).add_to(m)
    
    for _, p in df_pontos.iterrows():
        folium.Marker([p['lat'], p['lon']], popup=p['nome'], icon=folium.Icon(color="green", icon="bus", prefix="fa")).add_to(m)
    
    st_folium(m, width="100%", height=500, key="mapa_view")

# TELA 2: CADASTRO VIA GPS (Sem mapa de fundo, apenas dados)
elif opcao == "Cadastrar Ponto (GPS)":
    st.title("➕ Cadastro via GPS")
    if lat_user:
        st.success(f"Sinal de GPS estável em: {lat_user}, {lon_user}")
        
        # Checagem automática
        existe, nome_ponto = checar_duplicidade(lat_user, lon_user, df_pontos)
        
        if existe:
            st.error(f"❌ Não é permitido cadastrar aqui! Já existe o '{nome_ponto}' a menos de 20 metros.")
        else:
            with st.form("form_gps"):
                nome_novo = st.text_input("Nome do Novo Ponto")
                if st.form_submit_button("SOLICITAR CADASTRO"):
                    st.warning(f"Confirmar cadastro de '{nome_novo}'?")
                    if st.button("CONFIRMAR REALMENTE"):
                        st.balloons()
                        st.success("Ponto enviado para o banco de dados!")
    else:
        st.warning("📡 Aguardando sinal de GPS do seu dispositivo...")

# TELA 3: CADASTRO MANUAL (Busca por endereço)
elif opcao == "Cadastrar Ponto (Manual)":
    st.title("🔍 Cadastro por Endereço")
    with st.form("busca_manual"):
        endereco = st.text_input("Digite Endereço e Cidade")
        buscar = st.form_submit_button("Localizar no Mapa")
        
    if endereco and buscar:
        try:
            geolocator = Nominatim(user_agent="rmc_bus_app")
            loc = geolocator.geocode(endereco)
            if loc:
                existe, nome_ponto = checar_duplicidade(loc.latitude, loc.longitude, df_pontos)
                
                if existe:
                    st.error(f"❌ Localização inválida: O '{nome_ponto}' já ocupa este espaço.")
                else:
                    st.info(f"Ponto localizado: {loc.latitude}, {loc.longitude}")
                    m_manual = folium.Map(location=[loc.latitude, loc.longitude], zoom_start=18)
                    folium.Marker([loc.latitude, loc.longitude], icon=folium.Icon(color="red", icon="plus")).add_to(m_manual)
                    st_folium(m_manual, width="100%", height=300, key="mapa_manual")
                    
                    if st.button("CONFIRMAR CADASTRO MANUAL"):
                        st.success("Ponto manual registrado!")
            else:
                st.error("Endereço não encontrado.")
        except:
            st.error("Erro no serviço de mapas.")
