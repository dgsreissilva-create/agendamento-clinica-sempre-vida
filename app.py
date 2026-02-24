import streamlit as st
from supabase import create_client
import pandas as pd
from datetime import datetime, timedelta

# --- CONEXÃO DIRETA REVISADA ---
# Dica: Se o erro "Invalid API Key" persistir, pegue uma nova 'anon public key' no painel do Supabase.
URL_S = "https://mxsuvjgwpqzhaqbzrvdq.supabase.co"
KEY_S = "sb_publishable_08qbHGfKbBb8ljAHb7ckuQ_mp161ThN"
supabase = create_client(URL_S, KEY_S)

st.set_page_config(page_title="Agenda Clínica", layout="wide")

# --- LOGIN ---
if "logado" not in st.session_state: st.session_state["logado"] = False
with st.sidebar:
    st.title("🏥 Menu Clínica")
    if not st.session_state["logado"]:
        senha = st.text_input("Senha Admin", type="password")
        if st.button("Acessar"):
            if senha == "1234":
                st.session_state["logado"] = True
                st.rerun()
    else:
        if st.button("Sair"):
            st.session_state["logado"] = False
            st.rerun()

menu = st.sidebar.radio("Telas", ["Médicos", "Abrir Agenda", "Marcar Consulta"]) if st.session_state["logado"] else "Marcar Consulta"

# --- TELA MÉDICOS ---
if menu == "Médicos":
    st.header("👨‍⚕️ Cadastro de Médicos")
    with st.form("f_med"):
        nome = st.text_input("Nome do Médico")
        esp = st.selectbox("Especialidade", ["Clínico Geral", "Cardiologia", "Pediatria"])
        unid = st.selectbox("Unidade", ["Praça 7 - Rua Carijos", "Praça 7 - Rua Rio de Janeiro", "Eldorado"])
        if st.form_submit_button("Salvar Médico"):
            if nome:
                supabase.table("MEDICOS").insert({"nome": nome, "especialidade": esp, "unidade": unid}).execute()
                st.success("Médico cadastrado!")

# --- TELA ABRIR AGENDA ---
elif menu == "Abrir Agenda":
    st.header("⏳ Gerar Horários")
    m_data = supabase.table("MEDICOS").select("*").execute()
    if m_data.data:
        m_list = {m['nome']: m['id'] for m in m_data.data}
        sel = st.selectbox("Médico", list(m_list.keys()))
        data = st.date_input("Data")
        if st.button("Gerar Agenda (Início 08:00)"):
            inicio = datetime.combine(data, datetime.min.time()).replace(hour=8)
            vagas = [{"medico_id": m_list[sel], "data_hora": (inicio + timedelta(minutes=i*20)).isoformat(), "status": "Livre"} for i in range(10)]
            supabase.table("CONSULTAS").insert(vagas).execute()
            st.success("10 horários criados!")

# --- TELA MARCAR CONSULTA ---
elif menu == "Marcar Consulta":
    st.header("📅 Agendamento Online")
    res = supabase.table("CONSULTAS").select("*, MEDICOS(nome, unidade)").eq("status", "Livre").execute()
    if res.data:
        df = pd.DataFrame(res.data)
        df['op'] = df.apply(lambda x: f"{x['MEDICOS']['nome']} - {x['data_hora']}", axis=1)
        escolha = st.selectbox("Escolha sua Vaga", df['op'])
        v_id = df[df['op'] == escolha]['id'].values[0]
        with st.form("f_pac"):
            p_nome = st.text_input("Seu Nome")
            if st.form_submit_button("Confirmar Agendamento"):
                supabase.table("CONSULTAS").update({"paciente_nome": p_nome, "status": "Marcada"}).eq("id", v_id).execute()
                st.success("Consulta agendada!")
    else: st.info("Sem horários livres no momento.")
