import streamlit as st
from supabase import create_client
import pandas as pd

# O segredo é usar EXATAMENTE o que você escreveu nos Secrets
# Se lá você escreveu SUPABASE_URL, aqui tem que ser igual
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

st.set_page_config(page_title="Agenda Clínica Sempre Vida", layout="wide")
except Exception as e:
    st.error("Erro nas chaves de conexão. Verifique os Secrets!")
    st.stop()

st.title("🏥 Agenda Clínica Sempre Vida")

aba = st.sidebar.radio("Navegação", ["Cadastrar Paciente", "Ver Agenda"])

if aba == "Cadastrar Paciente":
    with st.form("form_paciente", clear_on_submit=True):
        nome = st.text_input("Nome Completo")
        tel = st.text_input("WhatsApp")
        conv = st.text_input("Convênio")
        if st.form_submit_button("Salvar"):
            if nome:
                supabase.table("PACIENTES").insert({"nome_completo": nome, "telefone": tel, "convenio": conv}).execute()
                st.success(f"{nome} cadastrado com sucesso!")

elif aba == "Ver Agenda":
    res = supabase.table("PACIENTES").select("*").execute()
    if res.data:
        st.dataframe(pd.DataFrame(res.data))
