import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from streamlit_geolocation import streamlit_geolocation
from streamlit_autorefresh import st_autorefresh
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
import sqlite3

# 1. Configuração de Página e Estilo
st.set_page_config(page_title="RMC - Gestão de Pontos", layout="wide")

# CSS para melhorar a interface mobile
st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 10px; font-weight: bold; }
    .info-box { background-color: #f0f2f6; padding: 15px; border-radius: 10px; border-left: 5px solid #007bff; }
    </style>
    """, unsafe_allow_html=True)

# --- FUNÇÕES DE CARREGAMENTO E LOGICA ---

@st.cache_data(ttl=60)
def carregar_dados():
    """Carrega e padroniza os dados para evitar KeyError"""
    # Exemplo de dados. Substitua pela leitura do seu arquivo .db ou Excel.
    dados = [
        {"nome": "Ponto Exemplo 1", "latitude": -22.9060, "longitude": -47.0610},
        {"nome": "Ponto Exemplo 2", "latitude": -22.9070, "longitude": -47.0620}
    ]
    df = pd.DataFrame(dados)
    # Garante que as colunas tenham esses nomes exatos
    df.columns = [c.lower() for c in df.columns] 
    return df

def checar_proximidade(n_lat, n_lon, df, raio=20):
    """Verifica se já existe um ponto em um raio de X metros"""
    if df.empty: return False, None
    for _, row in df.iterrows():
        dist = geodesic((n_lat, n_lon), (row['latitude'], row['longitude'])).meters
        if dist < raio:
            return True, row['nome']
    return False, None

# --- CAPTURA DE SINAL GPS ---
# Ativado globalmente para ser usado em todas as telas
loc_data = streamlit_geolocation()
lat_u, lon_u = loc_data.get('latitude'), loc_data.get('longitude')
df_existente = carregar_dados()

# --- MENU LATERAL ---
st.sidebar.title("📍 Menu RMC")
menu = st.sidebar.radio("Navegação:", ["Visualizar Mapa", "Cadastrar Ponto (GPS)", "Cadastrar Ponto (Manual)"])

# --- TELAS DO SISTEMA ---

# 1. TELA DE VISUALIZAÇÃO (APENAS MAPA E PONTOS)
if menu == "Visualizar Mapa":
    st_autorefresh(interval=10000, key="map_refresh")
    st.title("🗺️ Mapa de Monitoramento")
    
    # Configuração do Mapa de Alta Qualidade (Esri World Street Map)
    centro = [lat_u, lon_u] if lat_u else [-22.9064, -47.0616]
    m = folium.Map(
        location=centro, 
        zoom_start=17 if lat_u else 13,
        tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}',
        attr='Esri'
    )

    # Marcador do Usuário (Azul)
    if lat_u:
        folium.Marker([lat_u, lon_u], tooltip="Sua Posição", icon=folium.Icon(color="blue", icon="user", prefix="fa")).add_to(m)

    # Marcadores dos Pontos Cadastrados (Verde)
    for _, p in df_existente.iterrows():
        folium.Marker(
            [p['latitude'], p['longitude']], 
            popup=p['nome'], 
            icon=folium.Icon(color="green", icon="bus", prefix="fa")
        ).add_to(m)

    st_folium(m, width="100%", height=550, key="main_map")

# 2. TELA DE CADASTRO GPS (SEM MAPA, APENAS TRAVA DE SEGURANÇA)
elif menu == "Cadastrar Ponto (GPS)":
    st.title("➕ Novo Ponto via GPS")
    if lat_u and lon_u:
        st.markdown(f"<div class='info-box'><b>Coordenadas Atuais:</b> {lat_u:.6f}, {lon_u:.6f}</div>", unsafe_allow_html=True)
        
        bloqueado, nome_vizinho = checar_proximidade(lat_u, lon_u, df_existente)
        
        if bloqueado:
            st.error(f"❌ Cadastro Negado: O ponto '{nome_vizinho}' já existe a menos de 20 metros deste local.")
        else:
            with st.form("save_gps"):
                novo_nome = st.text_input("Nome do Ponto de Ônibus:")
                if st.form_submit_button("SOLICITAR REGISTRO"):
                    st.warning(f"Deseja realmente salvar '{novo_nome}' nestas coordenadas?")
                    if st.button("✅ SIM, CONFIRMAR CADASTRO"):
                        # Inserir lógica de banco de dados aqui
                        st.success("Ponto enviado com sucesso!")
    else:
        st.warning("📡 Aguardando sinal de GPS estável...")

# 3. TELA DE CADASTRO MANUAL (COM MAPA DE CONFERÊNCIA)
elif menu == "Cadastrar Ponto (Manual)":
    st.title("🔍 Localizar e Cadastrar")
    
    with st.container():
        rua = st.text_input("Digite o endereço completo (Rua, Número, Cidade):")
        buscar = st.button("Verificar Localização")

        if rua and buscar:
            try:
                geo = Nominatim(user_agent="rmc_bus_app")
                res = geo.geocode(rua)
                if res:
                    bloqueado, nome_v = checar_proximidade(res.latitude, res.longitude, df_existente)
                    
                    if bloqueado:
                        st.error(f"❌ Impossível cadastrar: Já existe o ponto '{nome_v}' neste endereço.")
                    else:
                        st.success(f"Endereço validado: {res.latitude:.6f}, {res.longitude:.6f}")
                        
                        # Mapa para o usuário conferir se o ponto caiu no lugar certo
                        m_confirma = folium.Map(location=[res.latitude, res.longitude], zoom_start=18)
                        folium.Marker([res.latitude, res.longitude], icon=folium.Icon(color="red", icon="plus")).add_to(m_confirma)
                        st_folium(m_confirma, width="100%", height=300, key="manual_check")
                        
                        with st.form("save_manual"):
                            nome_m = st.text_input("Nome do ponto para o endereço acima:")
                            if st.form_submit_button("FINALIZAR CADASTRO"):
                                st.success(f"Ponto '{nome_m}' registrado com sucesso!")
                else:
                    st.error("Endereço não encontrado. Tente adicionar o nome da cidade.")
            except Exception as e:
                st.error(f"Erro no serviço de mapas: {e}")
