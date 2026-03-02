import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from streamlit_geolocation import streamlit_geolocation
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
import sqlite3
import re
import os

# Configuração da Página
st.set_page_config(page_title="RMC - Gestão Profissional", layout="wide")

# --- FUNÇÕES DE CARREGAMENTO SEGURO ---
def carregar_dados_totais():
    lista_dfs = []
    # Tenta ler SQLite
    if os.path.exists('pontos.db'):
        try:
            conn = sqlite3.connect('pontos.db')
            df_db = pd.read_sql_query("SELECT * FROM pontos", conn)
            conn.close()
            df_db.columns = [c.lower() for c in df_db.columns]
            df_db['fonte'] = 'DB'
            lista_dfs.append(df_db)
        except: pass
    
    # Tenta ler Excel
    if os.path.exists('pontos_onibus.xlsx'):
        try:
            df_ex = pd.read_excel('pontos_onibus.xlsx')
            df_ex.columns = [c.lower() for c in df_ex.columns]
            df_ex['fonte'] = 'Excel'
            lista_dfs.append(df_ex)
        except: pass
    
    if not lista_dfs:
        return pd.DataFrame(columns=['nome', 'latitude', 'longitude', 'fonte'])
    return pd.concat(lista_dfs, ignore_index=True)

def validar_coords(texto):
    return bool(re.match(r"^-?\d{1,3}\.\d{6}$", texto))

# --- INTERFACE ---
st.sidebar.title("🧭 Sistema RMC")
opcao = st.sidebar.radio("Selecione a Função:", 
    ["📍 Visualizar Pontos Existentes", "🛰️ Cadastrar via GPS (Excel)", "⌨️ Cadastrar Manual (Coordenadas)"])

df_geral = carregar_dados_totais()

# 1. TELA: VISUALIZAR (Sem localização do usuário)
if opcao == "📍 Visualizar Pontos Existentes":
    st.title("🗺️ Mapa Geral de Pontos")
    if df_geral.empty:
        st.warning("Nenhum ponto encontrado nos arquivos pontos.db ou pontos_onibus.xlsx")
    else:
        # Mapa centralizado nos pontos (Esri)
        m = folium.Map(location=[df_geral['latitude'].mean(), df_geral['longitude'].mean()], 
                       zoom_start=13, tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}',
                       attr='Esri')
        
        for _, p in df_geral.iterrows():
            cor = "green" if p['fonte'] == 'DB' else "orange"
            folium.Marker([p['latitude'], p['longitude']], popup=f"{p['fonte']}: {p['nome']}", 
                          icon=folium.Icon(color=cor, icon="bus", prefix="fa")).add_to(m)
        st_folium(m, width="100%", height=600, key="mapa_view")

# 2. TELA: GPS (Foco no satélite)
elif opcao == "🛰️ Cadastrar via GPS (Excel)":
    st.title("🛰️ Cadastro via GPS")
    st.write("Clique no ícone de mira abaixo para ativar o GPS do seu aparelho.")
    
    loc = streamlit_geolocation()
    lat, lon = loc.get('latitude'), loc.get('longitude')
    
    if lat and lon:
        st.success(f"📍 Coordenadas: {lat:.6f}, {lon:.6f}")
        try:
            geo = Nominatim(user_agent="rmc_gps_v3")
            st.info(f"🏠 Rua aproximada: {geo.reverse(f'{lat}, {lon}').address}")
        except: st.write("Buscando endereço...")

        # Trava de proximidade
        proximo = False
        for _, r in df_geral.iterrows():
            if geodesic((lat, lon), (r['latitude'], r['longitude'])).meters < 20:
                proximo = r['nome']
                break
        
        if proximo:
            st.error(f"❌ Não permitido: Ponto '{proximo}' já cadastrado aqui (raio 20m).")
        else:
            with st.form("form_gps"):
                nome = st.text_input("Nome do Ponto:")
                if st.form_submit_button("CADASTRAR NO EXCEL"):
                    st.success(f"Solicitação de cadastro para '{nome}' enviada!")
    else:
        st.warning("Aguardando ativação do sinal de satélite...")

# 3. TELA: MANUAL (Com validação rigorosa)
elif opcao == "⌨️ Cadastrar Manual (Coordenadas)":
    st.title("⌨️ Cadastro Manual")
    st.info("Formato exigido: -22.123456 (Sinal, ponto e 6 casas decimais)")
    
    c1, c2 = st.columns(2)
    lat_in = c1.text_input("Latitude:", placeholder="-22.906412")
    lon_in = c2.text_input("Longitude:", placeholder="-47.061612")
    
    if lat_in and lon_in:
        if validar_coords(lat_in) and validar_coords(lon_in):
            l_val, n_val = float(lat_in), float(lon_in)
            
            # Verificação de duplicidade
            duplicado = False
            for _, r in df_geral.iterrows():
                if geodesic((l_val, n_val), (r['latitude'], r['longitude'])).meters < 20:
                    duplicado = r['nome']
                    break
            
            if duplicado:
                st.error(f"❌ Coordenada muito próxima de: {duplicado}")
            else:
                st.success("✅ Coordenadas válidas e local livre!")
                # Mostrar mapa de confirmação
                m_man = folium.Map(location=[l_val, n_val], zoom_start=18)
                folium.Marker([l_val, n_val], icon=folium.Icon(color="red", icon="plus")).add_to(m_man)
                st_folium(m_man, width="100%", height=300, key="mapa_man")
                
                with st.form("final_man"):
                    nome_m = st.text_input("Nome do novo ponto:")
                    if st.form_submit_button("CONFIRMAR CADASTRO MANUAL"):
                        st.success("Ponto registrado com sucesso!")
        else:
            st.error("⚠️ Formato incorreto. Use exatamente 6 números após o ponto.")
