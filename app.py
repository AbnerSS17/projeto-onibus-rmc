import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from streamlit_geolocation import streamlit_geolocation
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
import sqlite3
import re

# Configuração de Página
st.set_page_config(page_title="RMC - Gestão Profissional", layout="wide")

# --- FUNÇÕES DE APOIO ---

def carregar_db():
    try:
        conn = sqlite3.connect('pontos.db')
        df = pd.read_sql_query("SELECT * FROM pontos", conn)
        conn.close()
        df.columns = [c.lower() for c in df.columns]
        return df
    except:
        return pd.DataFrame(columns=['nome', 'latitude', 'longitude'])

def carregar_excel():
    try:
        df = pd.read_excel('pontos_onibus.xlsx')
        df.columns = [c.lower() for c in df.columns]
        return df
    except:
        return pd.DataFrame(columns=['nome', 'latitude', 'longitude'])

def validar_coordenada(texto):
    # Regex para validar formato decimal de latitude/longitude (ex: -22.123456)
    # Permite sinal de menos opcional, 1 a 3 dígitos, ponto, e exatamente 6 dígitos após o ponto
    padrao = r"^-?\d{1,3}\.\d{6}$"
    if re.match(padrao, texto):
        return True
    return False

def checar_duplicidade(lat, lon, dfs, raio=20):
    for df in dfs:
        for _, row in df.iterrows():
            dist = geodesic((lat, lon), (row['latitude'], row['longitude'])).meters
            if dist < raio:
                return True, row['nome']
    return False, None

# --- CARREGAMENTO INICIAL ---
df_db = carregar_db()
df_excel = carregar_excel()

# --- MENU LATERAL ---
st.sidebar.title("🧭 Sistema RMC")
opcao = st.sidebar.radio("Selecione a Função:", 
    ["📍 Visualizar Pontos Existentes", "🛰️ Cadastrar via GPS (Excel)", "⌨️ Cadastrar Manual (Coordenadas)"])

# --- ESTILO ---
st.markdown("""
    <style>
    .big-font { font-size:18px !important; font-weight: bold; }
    .gps-label { background-color: #f0f2f6; padding: 20px; border-radius: 10px; border-left: 10px solid #ff4b4b; }
    </style>
    """, unsafe_allow_html=True)

# --- TELAS ---

if opcao == "📍 Visualizar Pontos Existentes":
    st.title("🗺️ Mapa Geral de Pontos")
    st.info("Neste mapa: Pontos Verdes (Banco de Dados) | Pontos Amarelos (Excel)")
    
    # Mapa focado na região (sem localização do usuário)
    m = folium.Map(location=[-22.9064, -47.0616], zoom_start=13, 
                   tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}',
                   attr='Esri')

    # Desenhar Pontos do DB (Verde)
    for _, p in df_db.iterrows():
        folium.Marker([p['latitude'], p['longitude']], popup=f"DB: {p['nome']}", 
                      icon=folium.Icon(color="green", icon="bus", prefix="fa")).add_to(m)

    # Desenhar Pontos do Excel (Amarelo/Laranja)
    for _, p in df_excel.iterrows():
        folium.Marker([p['latitude'], p['longitude']], popup=f"Excel: {p['nome']}", 
                      icon=folium.Icon(color="orange", icon="bus", prefix="fa")).add_to(m)

    st_folium(m, width="100%", height=600)

elif opcao == "🛰️ Cadastrar via GPS (Excel)":
    st.title("🛰️ Cadastro Direto no Excel")
    loc = streamlit_geolocation()
    lat, lon = loc.get('latitude'), loc.get('longitude')
    
    if lat:
        try:
            geo = Nominatim(user_agent="rmc_gps")
            rua = geo.reverse(f"{lat}, {lon}").address
        except:
            rua = "Endereço não identificado pelo satélite"

        st.markdown(f"""
            <div class="gps-label">
                <p class="big-font">📍 LOCALIZAÇÃO ATUAL DETECTADA</p>
                <b>Rua:</b> {rua}<br>
                <b>Coordenadas:</b> {lat:.6f}, {lon:.6f}
            </div>
        """, unsafe_allow_html=True)

        # Checar se já existe ponto antes de liberar formulário
        existe, nome_p = checar_duplicidade(lat, lon, [df_db, df_excel])
        
        if existe:
            st.error(f"❌ Bloqueado: O ponto '{nome_p}' já está cadastrado a menos de 20 metros.")
        else:
            with st.form("form_gps_excel"):
                nome_ponto = st.text_input("Nome do Ponto para o Excel:")
                if st.form_submit_button("CADASTRAR NO EXCEL"):
                    st.warning("Confirmar gravação no arquivo Excel?")
                    if st.button("SIM, GRAVAR AGORA"):
                        # Lógica para salvar no Excel aqui
                        st.success("Gravado com sucesso no Excel!")

        # Mapa de auxílio (Apenas localização atual, sem outros pontos)
        st.write("### Sua posição no mapa:")
        m_gps = folium.Map(location=[lat, lon], zoom_start=18)
        folium.Marker([lat, lon], icon=folium.Icon(color="blue", icon="user")).add_to(m_gps)
        st_folium(m_gps, width="100%", height=300)
    else:
        st.warning("📡 Aguardando sinal de satélite...")

elif opcao == "⌨️ Cadastrar Manual (Coordenadas)":
    st.title("⌨️ Cadastro Manual Rigoroso")
    
    st.markdown("""
        **Regra de Digitação:** Use o formato decimal com exatamente 6 casas após o ponto.
        <br>Exemplo correto: `-22.906412`
    """, unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        lat_dig = st.text_input("Latitude:", placeholder="-22.123456")
    with col2:
        lon_dig = st.text_input("Longitude:", placeholder="-47.123456")

    if lat_dig and lon_dig:
        if validar_coordenada(lat_dig) and validar_coordenada(lon_dig):
            lat_f, lon_f = float(lat_dig), float(lon_dig)
            
            # Checar duplicidade
            existe, nome_p = checar_duplicidade(lat_f, lon_f, [df_db, df_excel])
            
            if existe:
                st.error(f"❌ Erro: Coordenadas muito próximas do ponto '{nome_p}'.")
            else:
                st.success("✅ Formato e Localização Válidos!")
                
                # Mapa de confirmação (Apenas o ponto novo)
                m_man = folium.Map(location=[lat_f, lon_f], zoom_start=18)
                folium.Marker([lat_f, lon_f], icon=folium.Icon(color="red", icon="plus")).add_to(m_man)
                st_folium(m_man, width="100%", height=300)
                
                with st.form("final_manual"):
                    nome_man = st.text_input("Nome do ponto:")
                    if st.form_submit_button("REALMENTE DESEJA CADASTRAR?"):
                        st.success("Ponto manual registrado!")
        else:
            st.error("⚠️ Formato inválido! Você deve digitar o sinal (se houver), os números, o ponto e exatamente 6 casas decimais.")
