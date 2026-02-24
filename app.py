import streamlit as st
from supabase import create_client
import pandas as pd

# CONFIGURAÇÕES DE ACESSO DIRETO (Substitui os Secrets)
URL_DB = "https://mxsuvjgwpqzhaqbzrvdq.supabase.co"
KEY_DB = "sb_publishable_O8qbHGfKbBb8ljAHb7ckuQ_mp16IThN"

# Conexão com o Supabase
try:
    supabase = create_client(URL_DB, KEY_DB)
except Exception as e:
    st.error(f"Erro de conexão: {e}")

# Configuração da Interface
st.set_page_config(page_title="Clínica Sempre Vida", layout="centered")

st.sidebar.title("🏥 Gestão Clínica")
aba = st.sidebar.radio("Navegar para:", ["Cadastrar Paciente", "Ver Agenda"])

# --- FORMULÁRIO DE CADASTRO ---
if aba == "Cadastrar Paciente":
    st.title("👥 Cadastro de Paciente")
    
    with st.form("form_clinica", clear_on_submit=True):
        nome = st.text_input("Nome Completo")
        whatsapp = st.text_input("Telemóvel / WhatsApp")
        plano = st.text_input("Convênio ou Plano de Saúde")
        
        btn_salvar = st.form_submit_button("Salvar Registro")
        
        if btn_salvar:
            if nome:
                try:
                    # Inserção no banco de dados
                    supabase.table("PACIENTES").insert({
                        "nome_completo": nome,
                        "telefone": whatsapp,
                        "convenio": plano
                    }).execute()
                    st.success(f"✅ {nome} foi guardado com sucesso!")
                except Exception as err:
                    st.error(f"Erro ao guardar dados: {err}")
            else:
                st.warning("⚠️ O campo Nome é obrigatório.")

# --- VISUALIZAÇÃO DA AGENDA ---
elif aba == "Ver Agenda":
    st.title("📋 Lista de Pacientes")
    
    try:
        resultado = supabase.table("PACIENTES").select("*").execute()
        if resultado.data:
            df = pd.DataFrame(resultado.data)
            # Mostra apenas as colunas relevantes
            colunas = ["nome_completo", "telefone", "convenio"]
            st.dataframe(df[colunas], use_container_width=True)
        else:
            st.info("Ainda não existem pacientes cadastrados.")
    except Exception as e:
        st.error(f"Erro ao carregar agenda: {e}")
