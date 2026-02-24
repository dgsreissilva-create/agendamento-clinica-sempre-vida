import streamlit as st
from supabase import create_client
import pandas as pd

# CONFIGURAÇÃO DE CONEXÃO DIRETA
URL_PROJETO = "https://mxsuvjgwpqzhaqbzrvdq.supabase.co"
KEY_PROJETO = "sb_publishable_08qbHGfKbBb8ljAHb7ckuQ_mp161ThN"

# Inicializa o cliente Supabase
@st.cache_resource
def init_connection():
    return create_client(URL_PROJETO, KEY_PROJETO)

supabase = init_connection()

# INTERFACE DO USUÁRIO
st.set_page_config(page_title="Clínica Sempre Vida", layout="centered")
st.title("🏥 Gestão de Pacientes - Clínica")

menu = st.sidebar.selectbox("Navegação", ["Cadastrar Novo", "Ver Agenda"])

if menu == "Cadastrar Novo":
    st.subheader("Formulário de Cadastro")
    with st.form("form_cadastro", clear_on_submit=True):
        nome = st.text_input("Nome do Paciente")
        whatsapp = st.text_input("WhatsApp")
        plano = st.text_input("Convênio")
        
        btn_salvar = st.form_submit_button("Finalizar Cadastro")
        
        if btn_salvar:
            if nome:
                try:
                    # Envia para a tabela PACIENTES
                    dados = {
                        "nome_completo": nome,
                        "telefone": whatsapp,
                        "convenio": plano
                    }
                    supabase.table("PACIENTES").insert(dados).execute()
                    st.success(f"✅ {nome} cadastrado com sucesso!")
                except Exception as e:
                    st.error(f"Erro ao salvar: {e}")
            else:
                st.warning("Por favor, preencha o nome.")

elif menu == "Ver Agenda":
    st.subheader("Lista de Pacientes Agendados")
    try:
        response = supabase.table("PACIENTES").select("*").execute()
        if response.data:
            df = pd.DataFrame(response.data)
            # Organiza as colunas para o usuário
            df = df[['nome_completo', 'telefone', 'convenio']]
            st.dataframe(df, use_container_width=True)
        else:
            st.info("Nenhum paciente encontrado.")
    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")
