import streamlit as st
from supabase import create_client
import pandas as pd

# --- CONEXÃO DIRETA (SEM SECRETS) ---
# Colocamos aqui para evitar o erro de KeyError
URL_DIRETA = "https://mxsuvjgwpqzhaqbzrvdq.supabase.co"
KEY_DIRETA = "sb_publishable_08qbHGfKbBb8ljAHb7ckuQ_mp161ThN"

try:
    supabase = create_client(URL_DIRETA, KEY_DIRETA)
except Exception as e:
    st.error(f"Erro na conexão: {e}")
    st.stop()

# --- CONFIGURAÇÃO DA TELA ---
st.set_page_config(page_title="Agenda Clínica Sempre Vida", layout="wide")

st.sidebar.title("🏥 Menu Clínica")
aba = st.sidebar.radio("Ir para:", ["👥 Cadastrar Paciente", "📊 Ver Agenda"])

# --- ABA 1: CADASTRO ---
if aba == "👥 Cadastrar Paciente":
    st.title("👥 Cadastro de Pacientes")
    with st.form("form_paciente", clear_on_submit=True):
        nome = st.text_input("Nome Completo")
        tel = st.text_input("WhatsApp")
        conv = st.text_input("Convênio")
        
        if st.form_submit_button("Salvar no Banco"):
            if nome:
                # Tenta inserir os dados na tabela PACIENTES
                supabase.table("PACIENTES").insert({
                    "nome_completo": nome, 
                    "telefone": tel, 
                    "convenio": conv
                }).execute()
                st.success(f"✅ {nome} cadastrado com sucesso!")
            else:
                st.warning("⚠️ O nome é obrigatório.")

# --- ABA 2: AGENDA ---
elif aba == "📊 Ver Agenda":
    st.title("📋 Lista de Pacientes")
    res = supabase.table("PACIENTES").select("*").execute()
    
    if res.data:
        df = pd.DataFrame(res.data)
        if 'id' in df.columns:
            df = df.drop(columns=['id', 'created_at'], errors='ignore')
        st.dataframe(df, use_container_width=True)
    else:
        st.info("Nenhum paciente cadastrado ainda.")
