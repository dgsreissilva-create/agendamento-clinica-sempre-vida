import streamlit as st
from supabase import create_client
import pandas as pd

# LINHA 5 e 6: Colocamos os dados direto aqui para não ter erro de 'Key'
URL = "https://mxsuvjgwpqzhaqbzrvdq.supabase.co"
KEY = "sb_publishable_08qbHGfKbBb8ljAHb7ckuQ_mp161ThN"

# Conexão
supabase = create_client(URL, KEY)

st.set_page_config(page_title="Agenda Clínica", layout="wide")

# Interface simples
st.title("🏥 Agenda Clínica Sempre Vida")
nome = st.text_input("Nome do Paciente")
tel = st.text_input("WhatsApp")

if st.button("Salvar Cadastro"):
    if nome:
        supabase.table("PACIENTES").insert({"nome_completo": nome, "telefone": tel}).execute()
        st.success(f"✅ {nome} cadastrado!")
    else:
        st.error("Digite o nome!")

if st.checkbox("Ver Agenda"):
    res = supabase.table("PACIENTES").select("*").execute()
    if res.data:
        st.table(pd.DataFrame(res.data))
