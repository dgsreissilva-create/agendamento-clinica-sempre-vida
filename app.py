import streamlit as st
from supabase import create_client
import pandas as pd

# --- CONEXÃO DIRETA (SEM SECRETS) ---
# Colocamos os dados reais aqui para o erro desaparecer na hora
URL_FIXA = "https://mxsuvjgwpqzhaqbzrvdq.supabase.co"
KEY_FIXA = "sb_publishable_08qbHGfKbBb8ljAHb7ckuQ_mp161ThN"

# Inicializa o banco de dados
try:
    supabase = create_client(URL_FIXA, KEY_FIXA)
except Exception as e:
    st.error(f"Erro ao conectar: {e}")

# --- INTERFACE ---
st.set_page_config(page_title="Clínica Sempre Vida", layout="wide")
st.title("🏥 Sistema de Agenda Clínica")

menu = st.sidebar.radio("Navegação", ["Cadastrar Paciente", "Ver Agenda"])

if menu == "Cadastrar Paciente":
    st.subheader("Novo Cadastro")
    with st.form("form_clinica", clear_on_submit=True):
        nome = st.text_input("Nome Completo")
        whatsapp = st.text_input("WhatsApp")
        convenio = st.text_input("Convênio")
        
        if st.form_submit_button("Salvar Paciente"):
            if nome:
                # Envia os dados para a tabela PACIENTES
                supabase.table("PACIENTES").insert({
                    "nome_completo": nome,
                    "telefone": whatsapp,
                    "convenio": convenio
                }).execute()
                st.success(f"✅ {nome} salvo com sucesso!")
            else:
                st.warning("O nome é obrigatório.")

elif menu == "Ver Agenda":
    st.subheader("Pacientes Agendados")
    res = supabase.table("PACIENTES").select("*").execute()
    if res.data:
        df = pd.DataFrame(res.data)
        # Mostra apenas as colunas principais
        st.dataframe(df[['nome_completo', 'telefone', 'convenio']], use_container_width=True)
    else:
        st.info("Nenhum paciente cadastrado.")
