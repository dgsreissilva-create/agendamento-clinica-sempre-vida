mport streamlit as st
from supabase import create_client
import pandas as pd
from datetime import datetime, timedelta

# --- CONEXÃO REVISADA ---
# Se o erro de "Invalid API Key" continuar, você precisará pegar uma nova chave no Supabase
URL_S = "https://mxsuvjgwpqzhaqbzrvdq.supabase.co"
KEY_S = "sb_publishable_08qbHGfKbBb8ljAHb7ckuQ_mp161ThN"
supabase = create_client(URL_S, KEY_S)

st.set_page_config(page_title="Agenda Clínica", layout="wide")

# --- LOGIN SIMPLES ---
if "auth" not in st.session_state: st.session_state["auth"] = False
with st.sidebar:
    st.title("🏥 Menu")
    if not st.session_state["auth"]:
        p = st.text_input("Senha", type="password")
        if st.button("Entrar"):
            if p == "1234":
                st.session_state["auth"] = True
                st.rerun()
    else:
        if st.button("Sair"):
            st.session_state["auth"] = False
            st.rerun()

menu = st.sidebar.radio("Telas", ["Médicos", "Abrir Agenda", "Marcar Consulta"]) if st.session_state["auth"] else "Marcar Consulta"

# --- TELA MÉDICOS (A que estava dando erro) ---
if menu == "Médicos":
    st.header("👨‍⚕️ Cadastro de Médicos")
    with st.form("f_med"):
        nome = st.text_input("Nome")
        esp = st.selectbox("Especialidade", ["Clínico Geral", "Cardiologia", "Pediatria"])
        unid = st.selectbox("Unidade", ["Praça 7 - Rua Carijos", "Praça 7 - Rua Rio de Janeiro", "Eldorado"])
        if st.form_submit_button("Salvar"):
            if nome:
                try:
                    # Nomes das colunas devem ser idênticos ao SQL acima
                    supabase.table("MEDICOS").insert({
                        "nome": nome, 
                        "especialidade": esp, 
                        "unidade": unid
                    }).execute()
                    st.success("Médico salvo com sucesso!")
                except Exception as e:
                    st.error(f"Erro técnico: {e}")

elif menu == "Abrir Agenda":
    st.header("⏳ Abrir Horários")
    m = supabase.table("MEDICOS").select("*").execute()
    if m.data:
        m_id = {x['nome']: x['id'] for x in m.data}
        sel = st.selectbox("Médico", list(m_id.keys()))
        dt = st.date_input("Data")
        if st.button("Gerar 5 horários (Início 08:00)"):
            base = datetime.combine(dt, datetime.min.time()).replace(hour=8)
            vagas = [{"medico_id": m_id[sel], "data_hora": (base + timedelta(minutes=i*30)).isoformat(), "status": "Livre"} for i in range(5)]
            supabase.table("CONSULTAS").insert(vagas).execute()
            st.success("Agenda aberta!")

elif menu == "Marcar Consulta":
    st.header("📅 Agendamento Online")
    res = supabase.table("CONSULTAS").select("*, MEDICOS(nome, unidade)").eq("status", "Livre").execute()
    if res.data:
        df = pd.DataFrame(res.data)
        # Ajuste para evitar erro se a tabela MEDICOS estiver vazia no retorno
        df['op'] = df.apply(lambda x: f"{x['MEDICOS']['nome']} - {x['data_hora']}", axis=1)
        sel_vaga = st.selectbox("Vagas", df['op'])
        v_id = df[df['op'] == sel_vaga]['id'].values[0]
        with st.form("f_pac"):
            p_nome = st.text_input("Seu Nome")
            if st.form_submit_button("Confirmar"):
                supabase.table("CONSULTAS").update({"paciente_nome": p_nome, "status": "Marcada"}).eq("id", v_id).execute()
                st.success("Agendado!")
