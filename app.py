import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from streamlit_js_eval import streamlit_js_eval
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import re

# Configuração da página
st.set_page_config(page_title="Mapeamento RMC", layout="wide")

# Inicialização de estados para controlar os formulários
if 'form_aberto' not in st.session_state:
    st.session_state.form_aberto = None  # Pode ser 'automatico', 'manual' ou None

def fechar_formularios():
    st.session_state.form_aberto = None

# Função para validar coordenadas (Regex)
def validar_coordenadas(lat, lon):
    try:
        l_val = float(lat)
        n_val = float(lon)
        # Verifica se estão dentro de faixas globais reais
        if -90 <= l_val <= 90 and -180 <= n_val <= 180:
            return True
        return False
    except:
        return False

st.title("📍 Sistema de Mapeamento RMC")

# Conexão GSheets
conn = st.connection("gsheets", type=GSheetsConnection)
df_existente = conn.read(ttl=0)

# --- CAPTURA DE LOCALIZAÇÃO AUTOMÁTICA ---
loc_auto = streamlit_js_eval(js_expressions="navigator.geolocation.getCurrentPosition(pos => { window.parent.postMessage({type: 'location', pos: pos.coords}, '*') });", key="Location")

# --- BOTÕES DE ESCOLHA ---
col1, col2, col3 = st.columns([1, 1, 1])
with col1:
    if st.button("➕ Adicionar ponto na minha localidade"):
        st.session_state.form_aberto = 'automatico'
with col2:
    if st.button("🔍 Adicionar ponto em outro local"):
        st.session_state.form_aberto = 'manual'
with col3:
    if st.button("❌ Cancelar / Fechar"):
        fechar_formularios()

# --- ÁREA DO MAPA ---
st.subheader("Visualização em Tempo Real")
centro_mapa = [-22.9064, -47.0616] # Centro RMC padrão
zoom = 12

# Se GPS ativo, foca no usuário
if loc_auto and st.session_state.form_aberto == 'automatico':
    centro_mapa = [loc_auto['latitude'], loc_auto['longitude']]
    zoom = 16

m = folium.Map(location=centro_mapa, zoom_start=zoom)

# Plotar pontos já existentes da planilha
for i, row in df_existente.iterrows():
    if pd.notnull(row['latitude']):
        folium.Marker(
            [row['latitude'], row['longitude']],
            popup=f"Empresa: {row['empresa']}",
            icon=folium.Icon(color="red")
        ).add_to(m)

# Marcador temporário para inserção manual
lat_manual, lon_manual = None, None
if st.session_state.form_aberto == 'manual':
    st.info("Digite as coordenadas abaixo para visualizar o ponto de interrogação no mapa.")

# Exibir Mapa
st_folium(m, width=800, height=450, key="mapa_principal")

# --- FORMULÁRIO 1: AUTOMÁTICO ---
if st.session_state.form_aberto == 'automatico':
    if not loc_auto:
        st.warning("Aguardando sinal do GPS...")
    else:
        with st.form("form_auto"):
            st.write("### Cadastro Automático (GPS)")
            st.write(f"Sua posição: `{loc_auto['latitude']}, {loc_auto['longitude']}`")
            empresa = st.text_input("Nome da Empresa")
            cat = st.selectbox("Categoria", ["Municipal", "Intermunicipal", "Outro"])
            obs = st.text_area("Observação")
            
            if st.form_submit_button("Confirmar Cadastro"):
                novo = pd.DataFrame([{"data_hora": datetime.now().strftime("%d/%m/%Y %H:%M:%S"), "latitude": loc_auto['latitude'], "longitude": loc_auto['longitude'], "categoria": cat, "empresa": empresa, "obs": obs}])
                conn.update(data=pd.concat([df_existente, novo], ignore_index=True))
                st.success("Cadastrado!")
                fechar_formularios()
                st.rerun()

# --- FORMULÁRIO 2: MANUAL ---
if st.session_state.form_aberto == 'manual':
    with st.container():
        st.write("### Cadastro por Endereço/Coordenadas")
        rua_input = st.text_input("Nome da Rua")
        lat_input = st.text_input("Latitude (Ex: -22.915)")
        lon_input = st.text_input("Longitude (Ex: -47.256)")
        
        # Validação em tempo real para mostrar no mapa
        if lat_input and lon_input:
            if validar_coordenadas(lat_input, lon_input):
                st.success("Coordenada Válida! O ponto '?' apareceria aqui.")
                # Nota: Para atualizar o mapa com o '?' instantaneamente, 
                # seria necessário um re-processamento do componente folium.
            else:
                st.error("Coordenadas Inválidas. Use o formato decimal (ex: -22.123).")

        with st.form("form_manual"):
            empresa_m = st.text_input("Nome da Empresa")
            confirmacao = st.checkbox("Você confirma que este ponto realmente existe no local informado?")
            
            if st.form_submit_button("Finalizar Cadastro"):
                if validar_coordenadas(lat_input, lon_input) and confirmacao:
                    novo = pd.DataFrame([{"data_hora": datetime.now().strftime("%d/%m/%Y %H:%M:%S"), "latitude": float(lat_input), "longitude": float(lon_input), "categoria": "Manual", "empresa": empresa_m, "obs": rua_input}])
                    conn.update(data=pd.concat([df_existente, novo], ignore_index=True))
                    st.balloons()
                    fechar_formularios()
                    st.rerun()
                else:
                    st.error("Verifique as coordenadas e marque a confirmação de existência.")
