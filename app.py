import streamlit as st
from streamlit_js_eval import get_geolocation
import folium
from streamlit_folium import st_folium
import sqlite3
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# 1. Configuração da Página
st.set_page_config(page_title="Cadastro de Pontos RMC", layout="wide")

# Interface Inicial
st.title("📍 Cadastro de Pontos em Tempo Real")
st.markdown("---")

# 2. Solicitação de GPS (Trava de Segurança)
loc = get_geolocation()

if not loc:
    st.warning("🛰️ Aguardando permissão de GPS... Por favor, autorize a localização no seu navegador para liberar o mapa.")
    st.stop()

# Coordenadas capturadas
lat_atual = loc['coords']['latitude']
lon_atual = loc['coords']['longitude']

st.success(f"✅ Localização capturada: {lat_atual:.6f}, {lon_atual:.6f}")

# 3. Mapa com Pontos Existentes (Lendo do .db)
def carregar_mapa():
    m = folium.Map(location=[lat_atual, lon_atual], zoom_start=17)
    
    # Marcador do Usuário (Azul)
    folium.Marker([lat_atual, lon_atual], tooltip="Você está aqui", icon=folium.Icon(color='blue', icon='user', prefix='fa')).add_to(m)
    
    # Tenta ler pontos antigos do arquivo .db
    try:
        conn = sqlite3.connect("transporte_integrado.db")
        query = "SELECT nome, latitude, longitude, categoria FROM pontos"
        df_db = pd.read_sql(query, conn)
        conn.close()
        
        for _, p in df_db.iterrows():
            folium.Marker(
                [p['latitude'], p['longitude']],
                popup=f"{p['nome']} ({p['categoria']})",
                icon=folium.Icon(color='green', icon='bus', prefix='fa')
            ).add_to(m)
    except:
        st.info("ℹ️ Nenhum ponto prévio carregado do banco .db local.")
        
    return m

st_folium(carregar_mapa(), width="100%", height=400)

# 4. Formulário de Cadastro (Salvando no Google Sheets)
st.subheader("📝 Novo Cadastro")

# Conexão com o Google Sheets (Configurada nos Secrets)
conn_gsheets = st.connection("gsheets", type=GSheetsConnection)

with st.form("meu_formulario"):
    categoria = st.selectbox("Categoria do Ponto", ["Municipal", "Híbrido"])
    empresa = st.text_input("Empresa (ex: SOU, EMTU, Fênix)")
    observacao = st.text_area("Observações/Linhas")
    
    botao_enviar = st.form_submit_button("Confirmar e Salvar")

    if botao_enviar:
        # Criar linha para a planilha
        nova_linha = pd.DataFrame([{
            "data_hora": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
            "latitude": lat_atual,
            "longitude": lon_atual,
            "categoria": categoria,
            "empresa": empresa,
            "obs": observacao
        }])
        
        try:
            # Lê os dados que já estão na planilha "db_pontos"
            dados_antigos = conn_gsheets.read()
            # Junta com o novo ponto
            dados_finais = pd.concat([dados_antigos, nova_linha], ignore_index=True)
            # Atualiza a planilha no Google Drive
            conn_gsheets.update(data=dados_finais)
            
            st.balloons()
            st.success("✅ Ponto registrado com sucesso na planilha!")
            
            # Botão extra para avisar no WhatsApp
            msg_whats = f"Novo ponto cadastrado! Lat: {lat_atual}, Lon: {lon_atual}. Empresa: {empresa}"
            link_wpp = f"https://wa.me/5519988922364?text={msg_whats}"
            st.markdown(f"📲 [Clique aqui para me avisar no WhatsApp]({link_wpp})")
            
        except Exception as e:
            st.error(f"❌ Erro ao salvar na planilha: {e}")
            st.info("Dica: Verifique se você configurou os Secrets no Streamlit e compartilhou a planilha com o robô.")