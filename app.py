import streamlit as st
from supabase import create_client
import pandas as pd

# Tenta pegar as chaves de qualquer jeito (Maiúsculo ou Minúsculo)
try:
    url = st.secrets.get("SUPABASE_URL") or st.secrets.get("supabase_url")
    key = st.secrets.get("SUPABASE_KEY") or st.secrets.get("supabase_key")
    
    if not url or not key:
        st.error("❌ Chaves não encontradas nos Secrets do Streamlit!")
        st.stop()
        
    supabase = create_client(url, key)
except Exception as e:
    st.error(f"❌ Erro de Conexão: {e}")
    st.stop()

st.set_page_config(page_title="Agenda Clínica", layout="wide")

# Interface
st.sidebar.title("🏥 Menu")
aba = st.sidebar.radio("Ir para:", ["Cadastrar", "Agenda"])

if aba == "Cadastrar":
    st.title("👥 Cadastro de Pacientes")
    with st.form("meu_form", clear_on_submit=True):
        nome = st.text_input("Nome")
        tel = st.text_input("WhatsApp")
        conv = st.text_input("Convênio")
        if st.form_submit_button("Salvar"):
            supabase.table("PACIENTES").insert({"nome_completo": nome, "telefone": tel, "convenio": conv}).execute()
            st.success("✅ Salvo!")

elif aba == "Agenda":
    st.title("📅 Agenda")
    dados = supabase.table("PACIENTES").select("*").execute()
    if dados.data:
        st.dataframe(pd.DataFrame(dados.data))
    else:
        st.info("Agenda vazia.")
