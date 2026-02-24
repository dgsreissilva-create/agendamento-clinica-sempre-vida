import streamlit as st
from supabase import create_client
import pandas as pd
from datetime import datetime, timedelta

# --- CONEXÃO DIRETA ---
URL_S = "https://mxsuvjgwpqzhaqbzrvdq.supabase.co"
KEY_S = "sb_publishable_08qbHGfKbBb8ljAHb7ckuQ_mp161ThN"
supabase = create_client(URL_S, KEY_S)

st.set_page_config(page_title="Clínica Sempre Vida", layout="wide")

# --- LOGIN ---
if "logado" not in st.session_state: st.session_state["logado"] = False
with st.sidebar:
    st.title("🏥 Menu Clínica")
    if not st.session_state["logado"]:
        pwd = st.text_input("Senha Admin", type="password")
        if st.button("Acessar"):
            if pwd == "1234":
                st.session_state["logado"] = True
                st.rerun()
    else:
        if st.button("Sair"):
            st.session_state["logado"] = False
            st.rerun()

# Menu dinâmico
if st.session_state["logado"]:
    menu = st.sidebar.radio("Navegação", ["Médicos", "Abrir Agenda", "Marcar Consulta", "Relatório"])
else:
    menu = "Marcar Consulta"

# --- TELAS ---
if menu == "Médicos":
    st.header("👨‍⚕️ Cadastro de Médicos")
    with st.form("f1"):
        n = st.text_input("Nome")
        e = st.selectbox("Especialidade", ["Clínico Geral", "Pediatria", "Cardiologia"])
        u = st.selectbox("Unidade", ["Praça 7 - Rua Carijos", "Praça 7 - Rua Rio de Janeiro", "Eldorado"])
        if st.form_submit_button("Salvar"):
            supabase.table("MEDICOS").insert({"nome": n, "especialidade": e, "unidade": u}).execute()
            st.success("Cadastrado!")

elif menu == "Abrir Agenda":
    st.header("⏳ Gerar Horários")
    m_data = supabase.table("MEDICOS").select("*").execute()
    if m_data.data:
        m_list = {m['nome']: m['id'] for m in m_data.data}
        sel = st.selectbox("Médico", list(m_list.keys()))
        d = st.date_input("Data")
        h = st.time_input("Início")
        if st.button("Gerar 4 horas de agenda (20 min cada)"):
            inicio = datetime.combine(d, h)
            vagas = [{"medico_id": m_list[sel], "data_hora": (inicio + timedelta(minutes=i*20)).isoformat(), "status": "Livre"} for i in range(12)]
            supabase.table("CONSULTAS").insert(vagas).execute()
            st.success("Agenda aberta!")

elif menu == "Marcar Consulta":
    st.header("📅 Agendamento Online")
    # Busca simplificada para evitar o erro de API que apareceu no print
    res = supabase.table("CONSULTAS").select("*, MEDICOS(nome, unidade)").eq("status", "Livre").execute()
    if res.data:
        df = pd.DataFrame(res.data)
        df['op'] = df.apply(lambda x: f"{x['MEDICOS']['nome']} - {x['data_hora']} - {x['MEDICOS']['unidade']}", axis=1)
        escolha = st.selectbox("Horários Disponíveis", df['op'])
        idx = df[df['op'] == escolha]['id'].values[0]
        with st.form("f2"):
            nome_p = st.text_input("Seu Nome")
            tel_p = st.text_input("Seu WhatsApp")
            if st.form_submit_button("Confirmar Agendamento"):
                supabase.table("CONSULTAS").update({"paciente_nome": nome_p, "paciente_telefone": tel_p, "status": "Marcada"}).eq("id", idx).execute()
                st.success("Marcado!")
    else: st.info("Nenhum horário livre.")

elif menu == "Relatório":
    st.header("✅ Consultas Confirmadas")
    res = supabase.table("CONSULTAS").select("*, MEDICOS(nome)").neq("status", "Livre").execute()
    if res.data: st.write(pd.DataFrame(res.data))
