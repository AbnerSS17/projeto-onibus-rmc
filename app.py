import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from streamlit_geolocation import streamlit_geolocation
from streamlit_autorefresh import st_autorefresh
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
import sqlite3
import os

# 1. Configuração de Página e Estilo
st.set_page_config(page_title="RMC - Gestão de Pontos", layout="wide")

# Força o app a recarregar para atualizar a posição do GPS no mapa
st_autorefresh(interval=10000, key="global_refresh")

# --- FUNÇÕES DE BANCO DE DADOS (CONEXÃO REAL) ---

def carregar_dados():
    """Lê os pontos do arquivo SQLite e da Planilha (se existirem)"""
    lista_pontos = []
    
    # Tentando ler do SQLite
    if os.path.exists('transporte_integrado.db'):
        try:
            conn = sqlite3.connect('transporte_integrado.db')
            df_db = pd.read_sql_query("SELECT * FROM pontos", conn)
            conn.close()
            # Padroniza colunas
            df_db.columns = [c.lower() for c in df_db.columns]
            lista_pontos.append(df_db)
        except Exception as e:
            st.error(f"Erro ao ler banco de dados: {e}")

    # Se não houver arquivos, retorna um DataFrame vazio com as colunas certas
    if not lista_pontos:
        return pd.DataFrame(columns=['nome', 'latitude', 'longitude'])
    
    return pd.concat(lista_pontos, ignore_index=True)

def salvar_ponto_db(nome, lat, lon):
    """Insere o novo ponto no arquivo SQLite"""
    try:
        conn = sqlite3.connect('transporte_integrado.db')
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE IF NOT EXISTS pontos (nome TEXT, latitude REAL, longitude REAL)")
        cursor.execute("INSERT INTO pontos (nome, latitude, longitude) VALUES (?, ?, ?)", (nome, lat, lon))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        st.error(f"Erro ao salvar: {e}")
        return False

# --- LÓGICA DE PROXIMIDADE ---
def checar_proximidade(n_lat, n_lon, df, raio=20):
    if df.empty: return False, None
    for _, row in df.iterrows():
        dist = geodesic((n_lat, n_lon), (row['latitude'], row['longitude'])).meters
        if dist < raio:
            return True, row.get('nome', 'Ponto sem nome')
    return False, None

# --- CAPTURA DE SINAL GPS ---
st.sidebar.markdown("### 🛰️ Status do GPS")
loc_data = streamlit_geolocation()
lat_u, lon_u = loc_data.get('latitude'), loc_data.get('longitude')

# Carrega os dados atualizados
df_existente = carregar_dados()

# --- MENU LATERAL ---
st.sidebar.title("📍 Menu RMC")
menu = st.sidebar.radio("Navegação:", ["Visualizar Mapa", "Cadastrar Ponto (GPS)", "Cadastrar Ponto (Manual)"])

# --- TELAS ---

if menu == "Visualizar Mapa":
    st.title("🗺️ Mapa de Monitoramento")
    
    if lat_u:
        st.success(f"Sinal de GPS Ativo")
    else:
        st.warning("Aguardando localização... Certifique-se de que o GPS do celular/PC está ligado.")

    # Configuração do Mapa Esri (Alta Qualidade)
    centro = [lat_u, lon_u] if lat_u else [-22.9064, -47.0616]
    m = folium.Map(
        location=centro, 
        zoom_start=18 if lat_u else 13,
        tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}',
        attr='Esri'
    )

    # Marcador do Usuário (Azul)
    if lat_u:
        folium.Marker(
            [lat_u, lon_u], 
            tooltip="Você está aqui", 
            icon=folium.Icon(color="blue", icon="street-view", prefix="fa")
        ).add_to(m)

    # Marcadores dos Pontos Cadastrados (Verde)
    for _, p in df_existente.iterrows():
        if pd.notnull(p['latitude']) and pd.notnull(p['longitude']):
            folium.Marker(
                [p['latitude'], p['longitude']], 
                popup=p.get('nome', 'Ponto'), 
                icon=folium.Icon(color="green", icon="bus", prefix="fa")
            ).add_to(m)

    st_folium(m, width="100%", height=550, key="main_map")

elif menu == "Cadastrar Ponto (GPS)":
    st.title("➕ Novo Ponto via GPS")
    if lat_u and lon_u:
        bloqueado, nome_vizinho = checar_proximidade(lat_u, lon_u, df_existente)
        
        if bloqueado:
            st.error(f"❌ Já existe o ponto '{nome_vizinho}' muito próximo daqui!")
        else:
            with st.form("save_gps"):
                novo_nome = st.text_input("Nome do Ponto:")
                submit = st.form_submit_button("CADASTRAR NESTA POSIÇÃO")
                if submit and novo_nome:
                    if salvar_ponto_db(novo_nome, lat_u, lon_u):
                        st.success("✅ Ponto gravado no banco de dados!")
                        st.cache_data.clear() # Limpa cache para mostrar no mapa imediatamente
    else:
        st.error("Sinal de GPS não encontrado. Não é possível cadastrar.")

elif menu == "Cadastrar Ponto (Manual)":
    st.title("🔍 Cadastro por Endereço")
    rua = st.text_input("Endereço (Rua, Número, Cidade):")
    if st.button("Localizar"):
        geo = Nominatim(user_agent="rmc_bus_app")
        res = geo.geocode(rua)
        if res:
            bloqueado, nome_v = checar_proximidade(res.latitude, res.longitude, df_existente)
            if bloqueado:
                st.error(f"❌ Localização ocupada por: {nome_v}")
            else:
                st.info(f"Localizado: {res.latitude}, {res.longitude}")
                m_manual = folium.Map(location=[res.latitude, res.longitude], zoom_start=18)
                folium.Marker([res.latitude, res.longitude], icon=folium.Icon(color="red", icon="plus")).add_to(m_manual)
                st_folium(m_manual, width="100%", height=300, key="manual_check")
                
                # Botão de salvamento manual simplificado
                nome_m = st.text_input("Confirme o nome para salvar:")
                if st.button("SALVAR PONTO MANUAL"):
                    if salvar_ponto_db(nome_m, res.latitude, res.longitude):
                        st.success("Salvo!")
                        st.cache_data.clear()
