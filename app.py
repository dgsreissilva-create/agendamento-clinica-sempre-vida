import streamlit as st
from supabase import create_client

# O segredo é usar o mesmo nome que está no cofre (Secrets)
url = st.secrets["https://mxsuvjgwpqzhaqbzrvdq.supabase.co"]
key = st.secrets["sb_publishable_08qbHGfKbBb8ljAHb7ckuQ_mp161ThN"]
supabase = create_client(url, key)
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
