import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from streamlit_geolocation import streamlit_geolocation
from streamlit_autorefresh import st_autorefresh # Novo: Atualização automática
from geopy.geocoders import Nominatim

# 1. Configuração e Auto-Refresh (Atualiza a cada 10 segundos)
st.set_page_config(page_title="Mapeamento RMC Pro", layout="wide")

# Faz o app recarregar automaticamente para ler o GPS novo
st_autorefresh(interval=10000, key="datarefresh") 

st.markdown("""
    <style>
    .rua-badge { background: #1E1E1E; color: #00FF00; padding: 15px; border-radius: 10px; 
                 font-family: monospace; border: 1px solid #333; margin-bottom: 15px; }
    div.stButton > button { border-radius: 20px; text-transform: uppercase; }
    </style>
    """, unsafe_allow_html=True)

# 2. Captura de Localização
location = streamlit_geolocation()
lat_atual = location.get('latitude')
lon_atual = location.get('longitude')

def obter_rua_detalhada(lat, lon):
    try:
        geolocator = Nominatim(user_agent="rmc_bus_prod")
        res = geolocator.reverse(f"{lat}, {lon}", timeout=3)
        return res.address
    except:
        return "Localizando via satélite..."

# 3. Painel de Informações Superior
if lat_atual:
    endereco = obter_rua_detalhada(lat_atual, lon_atual)
    st.markdown(f"""
        <div class="rua-badge">
            📡 GPS ATIVO (Atualização Automática)<br>
            📍 {endereco}<br>
            🌎 {lat_atual:.6f}, {lon_atual:.6f}
        </div>
    """, unsafe_allow_html=True)
else:
    st.info("🛰️ Aguardando sinal de GPS... Mantenha o navegador aberto.")

# 4. Configuração do Mapa com ESRI (Melhor que OpenStreetMap)
centro = [lat_atual, lon_atual] if lat_atual else [-22.9064, -47.0616]

m = folium.Map(
    location=centro, 
    zoom_start=18 if lat_atual else 13,
    tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}',
    attr='Esri'
)

# Marcador do Usuário (Sempre no topo)
if lat_atual:
    folium.Marker(
        [lat_atual, lon_atual],
        icon=folium.Icon(color="blue", icon="street-view", prefix="fa"),
        tooltip="Sua Posição"
    ).add_to(m)

# 5. Renderização do Mapa
st_folium(m, width="100%", height=500, key="mapa_v3")

# 6. Sistema de Cadastro com Confirmação
st.write("---")
if st.button("🚀 CADASTRAR PONTO NESTA LOCALIZAÇÃO"):
    if lat_atual:
        st.session_state.confirmar_save = True
    else:
        st.error("Erro: GPS não detectado.")

if st.session_state.get('confirmar_save'):
    with st.container():
        st.warning("⚠️ **CONFIRMAÇÃO FINAL**")
        st.write(f"Deseja salvar este ponto de ônibus em: **{endereco}**?")
        
        c1, c2 = st.columns(2)
        with c1:
            if st.button("✅ SIM, CONFIRMAR"):
                # AQUI ENTRA SEU CÓDIGO DE SALVAR NO SQLITE / GSHEETS
                st.success("PONTO CADASTRADO COM SUCESSO!")
                st.session_state.confirmar_save = False
        with c2:
            if st.button("❌ CANCELAR"):
                st.session_state.confirmar_save = False
