import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from streamlit_geolocation import streamlit_geolocation
from geopy.geocoders import Nominatim
import sqlite3

# 1. Configuração de Página
st.set_page_config(page_title="Mapeamento RMC Pro", layout="wide")

# --- AUTO-REFRESH (Faz o GPS atualizar a cada 10 segundos) ---
if "count" not in st.session_state:
    st.session_state.count = 0

# Estilo Visual Customizado
st.markdown("""
    <style>
    .reportview-container { background: #f0f2f6; }
    .stMetric { background: white; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
    div.stButton > button { width: 100%; height: 3.5em; font-weight: bold; border-radius: 12px; }
    .rua-badge { background-color: #007bff; color: white; padding: 10px; border-radius: 8px; font-weight: bold; margin-bottom: 10px; }
    </style>
    """, unsafe_allow_html=True)

# 2. Captura de GPS (O componente precisa estar no topo)
# Ele retorna um dicionário com lat, lon, altitude, etc.
location = streamlit_geolocation()

# Inicializa variáveis de localização
lat_atual = location.get('latitude')
lon_atual = location.get('longitude')

# Função para pegar o nome da rua (Geocoding Reverso)
def get_street_name(lat, lon):
    try:
        geolocator = Nominatim(user_agent="rmc_bus_app")
        loc = geolocator.reverse(f"{lat}, {lon}", timeout=3)
        address = loc.raw.get('address', {})
        rua = address.get('road', 'Rua não identificada')
        numero = address.get('house_number', '')
        return f"{rua}, {numero}".strip(", ")
    except:
        return "Buscando endereço..."

# 3. Cabeçalho Dinâmico (Etiqueta em Tempo Real)
if lat_atual and lon_atual:
    nome_rua = get_street_name(lat_atual, lon_atual)
    st.markdown(f"""
        <div class="rua-badge">
            📍 LOCALIZAÇÃO ATUAL: {nome_rua}<br>
            <small>Coordenadas: {lat_atual:.6f} | {lon_atual:.6f}</small>
        </div>
    """, unsafe_allow_html=True)
else:
    st.warning("📡 Tentando conectar ao GPS... Certifique-se de que o acesso à localização está permitido no navegador.")

# 4. Lógica do Mapa
# Usando o mapa 'OpenStreetMap' que é o melhor para detalhes de ruas/pontos
centro = [lat_atual, lon_atual] if lat_atual else [-22.9064, -47.0616]
zoom = 18 if lat_atual else 12 # Zoom 18 é ideal para ver a calçada

m = folium.Map(location=centro, zoom_start=zoom, tiles="OpenStreetMap")

# A) Marcador do Usuário (O "Ponto Azul" que se move)
if lat_atual:
    folium.Marker(
        [lat_atual, lon_atual],
        popup="Você está aqui",
        icon=folium.Icon(color="blue", icon="person", prefix="fa")
    ).add_to(m)
    # Círculo de precisão
    folium.Circle([lat_atual, lon_atual], radius=20, color="blue", fill=True, fill_opacity=0.1).add_to(m)

# B) Simulando Pontos de Ônibus Fixos (Verdes)
# Aqui você integraria com seu banco de dados
pontos_teste = [
    {"nome": "Ponto Central 1", "lat": -22.9060, "lon": -47.0610},
    {"nome": "Parada Shopping", "lat": -22.9070, "lon": -47.0620}
]

for p in pontos_teste:
    folium.Marker(
        [p['lat'], p['lon']],
        icon=folium.Icon(color="green", icon="bus", prefix="fa"),
        popup=p['nome']
    ).add_to(m)

# 5. Exibição do Mapa
st_folium(m, width="100%", height=450, key="mapa_movel")

# 6. Botões de Ação e Cadastro
st.write("---")
c1, c2 = st.columns(2)

with c1:
    if st.button("➕ Cadastrar Ponto no GPS Atual"):
        st.session_state.tipo_cadastro = "gps"

with c2:
    if st.button("🔍 Digitar Coordenadas"):
        st.session_state.tipo_cadastro = "manual"

# 7. Formulários de Confirmação
if "tipo_cadastro" in st.session_state:
    with st.container():
        st.write("### Confirmar Cadastro")
        
        if st.session_state.tipo_cadastro == "gps":
            if lat_atual:
                st.info(f"O ponto será fixado na sua rua atual: **{nome_rua}**")
                with st.form("confirm_gps"):
                    st.write(f"Latitude: {lat_atual} | Longitude: {lon_atual}")
                    nota = st.text_input("Nome do Ponto / Observação")
                    if st.form_submit_button("REALMENTE DESEJO CADASTRAR"):
                        # COMANDO SQL AQUI
                        st.success("Ponto registrado com sucesso!")
                        del st.session_state.tipo_cadastro
            else:
                st.error("GPS sem sinal. Não é possível cadastrar agora.")

        elif st.session_state.tipo_cadastro == "manual":
            with st.form("confirm_manual"):
                rua_input = st.text_input("Digite o endereço ou coordenadas")
                if st.form_submit_button("VERIFICAR E CADASTRAR"):
                    st.warning(f"Deseja realmente cadastrar o ponto em: {rua_input}?")
                    if st.button("SIM, CONFIRMAR"):
                        st.success("Ponto manual registrado!")

# Botão de refresh manual para forçar atualização se necessário
if st.button("🔄 Atualizar Minha Posição Agora"):
    st.rerun()
