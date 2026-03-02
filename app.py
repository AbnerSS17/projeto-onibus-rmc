import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from streamlit_js_eval import streamlit_js_eval
from streamlit_gsheets import GSheetsConnection
from datetime import datetime

# Configuração da página
st.set_page_config(page_title="Mapeamento RMC", layout="wide")

st.title("📍 Cadastro de Pontos em Tempo Real - RMC")

# 1. Conexão com o Google Sheets (Configurado nos Secrets)
conn = st.connection("gsheets", type=GSheetsConnection)

# 2. Função para ler dados da planilha (ttl=0 para tempo real)
def buscar_dados():
    return conn.read(ttl=0)

# 3. Captura de Localização via GPS do Navegador
loc = streamlit_js_eval(js_expressions="navigator.geolocation.getCurrentPosition(pos => { window.parent.postMessage({type: 'location', pos: pos.coords}, '*') });", key="Location")

if loc:
    lat = loc['latitude']
    lon = loc['longitude']
    st.success(f"Localização capturada: {lat}, {lon}")
    
    # --- MAPA DE VISUALIZAÇÃO ---
    st.subheader("Mapa de Pontos Cadastrados")
    
    # Criar o mapa centralizado na posição atual
    m = folium.Map(location=[lat, lon], zoom_start=15)
    
    # Adicionar marcador da posição atual (Azul)
    folium.Marker([lat, lon], tooltip="Você está aqui", icon=folium.Icon(color="blue")).add_to(m)
    
    # Ler pontos já cadastrados na planilha e adicionar ao mapa (Vermelhos)
    try:
        df_pontos = buscar_dados()
        for i, row in df_pontos.iterrows():
            # Verifica se há coordenadas válidas antes de criar o marcador
            if pd.notnull(row['latitude']) and pd.notnull(row['longitude']):
                folium.Marker(
                    [row['latitude'], row['longitude']],
                    popup=f"<b>Empresa:</b> {row['empresa']}<br><b>Obs:</b> {row['obs']}",
                    tooltip=f"{row['categoria']} - {row['data_hora']}",
                    icon=folium.Icon(color="red", icon="info-sign")
                ).add_to(m)
    except Exception as e:
        st.error(f"Erro ao carregar pontos existentes: {e}")

    # Exibir o mapa
    st_folium(m, width=800, height=450)

    # --- FORMULÁRIO DE CADASTRO ---
    st.divider()
    st.subheader("📝 Novo Cadastro")
    
    with st.form("form_ponto", clear_on_submit=True):
        categoria = st.selectbox("Categoria do Ponto", ["Municipal", "Intermunicipal", "Híbrido", "Outro"])
        empresa = st.text_input("Nome da Empresa")
        obs = st.text_area("Observações")
        
        submit = st.form_submit_button("Confirmar e Salvar na Planilha")
        
        if submit:
            # Criar novo registro
            novo_ponto = pd.DataFrame([{
                "data_hora": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                "latitude": lat,
                "longitude": lon,
                "categoria": categoria,
                "empresa": empresa,
                "obs": obs
            }])
            
            # Atualizar a planilha (lendo os dados atuais e concatenando)
            df_atualizado = pd.concat([df_pontos, novo_ponto], ignore_index=True)
            conn.update(data=df_atualizado)
            
            st.balloons()
            st.success("Ponto registrado com sucesso na planilha!")
            st.info("Atualize a página para ver o novo pino no mapa.")

else:
    st.warning("Aguardando permissão de GPS para carregar o mapa...")
    st.info("Se o GPS não carregar, verifique se o site tem permissão de localização no seu navegador.")
