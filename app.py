import streamlit as st
from supabase import create_client
import pandas as pd

# --- CONEXÃO COM O BANCO (O SEGREDO ESTÁ AQUI) ---
# O código busca exatamente os nomes que você salvou no Streamlit
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

st.set_page_config(page_title="Agenda Clínica Sempre Vida", layout="wide")

st.sidebar.title("🏥 Menu Clínica")
aba = st.sidebar.radio("Ir para:", ["👥 Cadastrar Paciente", "📊 Ver Agenda"])

# --- ABA 1: CADASTRO ---
if aba == "👥 Cadastrar Paciente":
    st.title("👥 Cadastro de Pacientes")
    with st.form("form_paciente", clear_on_submit=True):
        nome = st.text_input("Nome Completo")
        tel = st.text_input("WhatsApp")
        convenio = st.text_input("Convênio")
        
        if st.form_submit_button("Salvar no Banco"):
            if nome:
                supabase.table("PACIENTES").insert({
                    "nome_completo": nome, 
                    "telefone": tel, 
                    "convenio": convenio
                }).execute()
                st.success(f"✅ {nome} salvo com sucesso!")
            else:
                st.warning("⚠️ O nome é obrigatório.")

# --- ABA 2: AGENDA ---
elif aba == "📊 Ver Agenda":
    st.title("📋 Lista de Pacientes")
    # Busca os dados na tabela que você criou no SQL Editor
    res = supabase.table("PACIENTES").select("*").execute()
    
    if res.data:
        df = pd.DataFrame(res.data)
        # Remove a coluna ID da visualização para ficar mais limpo
        if 'id' in df.columns:
            df = df.drop(columns=['id', 'created_at'], errors='ignore')
        st.dataframe(df, use_container_width=True)
    else:
        st.info("Nenhum paciente cadastrado ainda.")
