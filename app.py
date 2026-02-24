import streamlit as st
from supabase import create_client
import pandas as pd

# Chaves diretas para eliminar erros de 'Secrets'
URL_S = "https://mxsuvjgwpqzhaqbzrvdq.supabase.co"
KEY_S = "sb_publishable_08qbHGfKbBb8ljAHb7ckuQ_mp161ThN"

# Conexão Robusta
try:
    supabase = create_client(URL_S, KEY_S)
except Exception as e:
    st.error(f"Erro na conexão com o banco: {e}")

# Configuração da Página
st.set_page_config(page_title="Clínica Sempre Vida", layout="wide")

# Menu Lateral
st.sidebar.title("🏥 Gestão Clínica")
opcao = st.sidebar.radio("Navegar:", ["Cadastrar Paciente", "Agenda de Clientes"])

# --- CADASTRO ---
if opcao == "Cadastrar Paciente":
    st.header("📋 Cadastro de Novo Paciente")
    
    with st.form("meu_formulario", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            nome = st.text_input("Nome Completo")
            whats = st.text_input("WhatsApp / Telefone")
        with col2:
            plano = st.text_input("Convênio / Plano")
        
        enviar = st.form_submit_button("Salvar Paciente")
        
        if enviar:
            if nome:
                try:
                    # O nome das chaves aqui DEVE ser igual ao do SQL
                    supabase.table("PACIENTES").insert({
                        "nome_completo": nome,
                        "telefone": whats,
                        "convenio": plano
                    }).execute()
                    st.success(f"✨ {nome} cadastrado com sucesso!")
                except Exception as error:
                    st.error(f"Erro ao salvar: {error}")
            else:
                st.warning("⚠️ O campo 'Nome' é obrigatório.")

# --- AGENDA ---
elif opcao == "Agenda de Clientes":
    st.header("📅 Pacientes Cadastrados")
    
    try:
        dados = supabase.table("PACIENTES").select("*").execute()
        if dados.data:
            df = pd.DataFrame(dados.data)
            # Seleciona apenas as colunas importantes para exibir
            colunas_exibir = ["nome_completo", "telefone", "convenio"]
            st.dataframe(df[colunas_exibir], use_container_width=True)
        else:
            st.info("Nenhum registro encontrado no banco.")
    except Exception as e:
        st.error(f"Erro ao carregar a agenda: {e}")
