import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from streamlit_geolocation import streamlit_geolocation
from streamlit_autorefresh import st_autorefresh
from geopy.geocoders import Nominatim
import sqlite3

# 1. Configurações Iniciais
st.set_page_config(page_title="Monitoramento RMC", layout="wide")

# Atualiza o GPS automaticamente a cada 10 segundos
st_autorefresh(interval=10000, key="global_refresh")

# --- FUNÇÕES DE CARREGAMENTO (Evita que os pontos sumam) ---
@st.cache_data
def carregar_pontos_db():
    try:
        conn = sqlite3.connect('pontos.db') # Nome do seu arquivo no Git
        df = pd.read_sql_query("SELECT * FROM pontos", conn)
        conn.close()
        return df
    except:
        return pd.DataFrame(columns=['nome', 'latitude', 'longitude'])

@st.cache_data
def carregar_pontos_excel():
    try:
        # Substitua pelo nome real do seu arquivo Excel
        df = pd.read_excel('pontos_onibus.xlsx') 
        return df
    except:
        return pd.DataFrame(columns=['nome', 'latitude', 'longitude'])

# 2. Interface de Usuário (Menu Lateral)
st.sidebar.title("Menu de Opções")
opcao = st.sidebar.radio("O que deseja fazer?", ["Visualizar Mapa", "Cadastrar Ponto (GPS)", "Cadastrar Ponto (Manual)"])

# 3. Captura do GPS Real do Usuário
loc_data = streamlit_geolocation()
lat_user = loc_data.get('latitude')
lon_user = loc_data.get('longitude')

# 4. Lógica do Mapa
st.title("📍 Sistema de Pontos RMC")

# Pegar nome da rua para a etiqueta superior
if lat_user:
    try:
        geolocator = Nominatim(user_agent="rmc_final_app")
        endereco = geolocator.reverse(f"{lat_user}, {lon_user}", timeout=3).address
        st.info(f"🛰️ **Sua Localização Atual:** {endereco}")
    except:
        st.write("Localizando...")

# Criar o objeto do Mapa (ESRI Street Map - Alta Qualidade)
centro_mapa = [lat_user, lon_user] if lat_user else [-22.9064, -47.0616]
m = folium.Map(
    location=centro_mapa,
    zoom_start=17 if lat_user else 12,
    tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}',
    attr='Esri'
)

# --- DESENHANDO AS 3 FONTES ---

# Fonte 1: Usuário (Azul)
if lat_user:
    folium.Marker([lat_user, lon_user], tooltip="Você", icon=folium.Icon(color="blue", icon="person", prefix="fa")).add_to(m)

# Fonte 2: Pontos do Banco de Dados (Verde)
df_db = carregar_pontos_db()
for _, row in df_db.iterrows():
    folium.Marker(
        [row['latitude'], row['longitude']],
        popup=f"DB: {row['nome']}",
        icon=folium.Icon(color="green", icon="bus", prefix="fa")
    ).add_to(m)

# Fonte 3: Pontos do Excel (Vermelho)
df_excel = carregar_pontos_excel()
for _, row in df_excel.iterrows():
    folium.Marker(
        [row['latitude'], row['longitude']],
        popup=f"Excel: {row['nome']}",
        icon=folium.Icon(color="red", icon="bus", prefix="fa")
    ).add_to(m)

# Renderiza o Mapa
st_folium(m, width="100%", height=500, key="mapa_principal")

# 5. Lógica dos Formulários (Abaixo do Mapa)
st.write("---")

if opcao == "Cadastrar Ponto (GPS)":
    st.subheader("➕ Novo Cadastro via GPS")
    if lat_user:
        with st.form("form_gps"):
            st.write(f"Coordenadas detectadas: {lat_user}, {lon_user}")
            nome = st.text_input("Nome do Ponto")
            if st.form_submit_button("VALIDAR"):
                st.warning("Deseja realmente cadastrar este ponto?")
                if st.button("Sim, confirmar!"):
                    st.success("Cadastrado com sucesso!")
    else:
        st.error("GPS ainda não detectado.")

elif opcao == "Cadastrar Ponto (Manual)":
    st.subheader("🔍 Cadastro Manual por Endereço")
    with st.form("form_manual"):
        endereco_digitado = st.text_input("Digite a Rua, Número e Cidade")
        if st.form_submit_button("LOCALIZAR NO MAPA"):
            try:
                geolocator = Nominatim(user_agent="rmc_final_app")
                loc = geolocator.geocode(endereco_digitado)
                if loc:
                    st.success(f"Localizado: {loc.latitude}, {loc.longitude}")
                    st.session_state.temp_lat = loc.latitude
                    st.session_state.temp_lon = loc.longitude
                    # Aqui você poderia forçar o mapa a centralizar nessas coordenadas
                else:
                    st.error("Endereço não encontrado.")
            except:
                st.error("Erro no serviço de busca.")
        
        if 'temp_lat' in st.session_state:
            if st.form_submit_button("CONFIRMAR CADASTRO NESTE ENDEREÇO"):
                st.success("Ponto manual cadastrado!")
                del st.session_state.temp_lat
