import streamlit as st
from supabase import create_client
import pandas as pd
from datetime import datetime

# Conexão Direta
URL_S = "https://mxsuvjgwpqzhaqbzrvdq.supabase.co"
KEY_S = "sb_publishable_08qbHGfKbBb8ljAHb7ckuQ_mp161ThN"
supabase = create_client(URL_S, KEY_S)

st.set_page_config(page_title="Gestão Clínica Sempre Vida", layout="wide")

# --- MENU LATERAL ---
st.sidebar.title("🏥 Sistema Sempre Vida")
menu = st.sidebar.radio("Selecione a Tela:", [
    "📅 Abrir Agenda (Médico)", 
    "👥 Cadastro de Pacientes", 
    "📋 Ver Agenda Geral"
])

# --- TELA 1: ABRIR AGENDA (MÉDICO) ---
if menu == "📅 Abrir Agenda (Médico)":
    st.header("⚙️ Abertura de Disponibilidade Médica")
    
    with st.form("form_abrir_agenda"):
        col1, col2 = st.columns(2)
        with col1:
            medico = st.text_input("Nome do Médico")
            especialidade = st.selectbox("Especialidade", ["Clínico Geral", "Cardiologia", "Ortopedia", "Pediatria", "Ginecologia"])
        
        with col2:
            unidade = st.selectbox("Unidade", [
                "Praça 7 - Rua Carijós", 
                "Praça 7 - Rua Rio de Janeiro", 
                "Eldorado"
            ])
            data_hora = st.datetime_input("Data e Horário da Disponibilidade", value=datetime.now())

        if st.form_submit_button("Liberar Horário para Pacientes"):
            if medico:
                supabase.table("AGENDA_DISPONIVEL").insert({
                    "medico": medico,
                    "especialidade": especialidade,
                    "unidade": unidade,
                    "data_hora": data_hora.isoformat(),
                    "status": "Livre"
                }).execute()
                st.success(f"✅ Agenda aberta para Dr(a). {medico} na unidade {unidade}!")
            else:
                st.error("Por favor, preencha o nome do médico.")

# --- TELA 2: CADASTRO DE PACIENTES ---
elif menu == "👥 Cadastro de Pacientes":
    st.header("👥 Cadastro de Paciente")
    with st.form("cad_paciente", clear_on_submit=True):
        nome = st.text_input("Nome do Paciente")
        tel = st.text_input("WhatsApp")
        if st.form_submit_button("Salvar Paciente"):
            supabase.table("PACIENTES").insert({"nome_completo": nome, "telefone": tel}).execute()
            st.success("Paciente cadastrado!")

# --- TELA 3: VER AGENDA GERAL ---
elif menu == "📋 Ver Agenda Geral":
    st.header("📋 Horários Disponíveis e Pacientes")
    
    st.subheader("👨‍⚕️ Horários Liberados pelos Médicos")
    res_agenda = supabase.table("AGENDA_DISPONIVEL").select("*").execute()
    if res_agenda.data:
        st.dataframe(pd.DataFrame(res_agenda.data)[["medico", "especialidade", "unidade", "data_hora", "status"]], use_container_width=True)
    
    st.divider()
    
    st.subheader("👥 Lista de Pacientes")
    res_pacientes = supabase.table("PACIENTES").select("*").execute()
    if res_pacientes.data:
        st.dataframe(pd.DataFrame(res_pacientes.data)[["nome_completo", "telefone"]], use_container_width=True)
