import streamlit as st
from supabase import create_client
import pandas as pd
from datetime import datetime, timedelta
import os

# =============================
# CONFIGURAÇÃO
# =============================

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_SERVICE_ROLE_KEY"]
ADMIN_PASSWORD = st.secrets["ADMIN_PASSWORD"]

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

st.set_page_config(page_title="Clínica Sempre Vida", layout="wide")

if "auth" not in st.session_state:
    st.session_state.auth = False

# =============================
# SIDEBAR
# =============================

st.sidebar.title("🏥 Clínica Sempre Vida")

if not st.session_state.auth:
    with st.sidebar.expander("🔐 Área Administrativa"):
        senha = st.text_input("Senha", type="password")
        if st.button("Entrar"):
            if senha == ADMIN_PASSWORD:
                st.session_state.auth = True
                st.rerun()
            else:
                st.error("Senha incorreta")

if st.session_state.auth:
    menu = st.sidebar.radio("Menu", [
        "1 - Cadastro de Médicos",
        "2 - Abertura de Agenda",
        "3 - Marcação de Consulta",
        "4 - Consultas Marcadas"
    ])
    if st.sidebar.button("Sair"):
        st.session_state.auth = False
        st.rerun()
else:
    menu = "3 - Marcação de Consulta"
    st.sidebar.info("Login necessário para área administrativa")

# =============================
# 1 - CADASTRO MÉDICOS
# =============================

if menu == "1 - Cadastro de Médicos":

    st.header("Cadastro de Médicos")

    with st.form("form_medico"):
        nome = st.text_input("Nome do Médico")
        especialidade = st.text_input("Especialidade")
        unidade = st.text_input("Unidade")

        if st.form_submit_button("Cadastrar"):
            if nome and especialidade and unidade:
                supabase.table("MEDICOS").insert({
                    "nome": nome,
                    "especialidade": especialidade,
                    "unidade": unidade
                }).execute()
                st.success("Médico cadastrado com sucesso")
            else:
                st.warning("Preencha todos os campos")

# =============================
# 2 - ABERTURA DE AGENDA
# =============================

elif menu == "2 - Abertura de Agenda":

    st.header("Gerar Horários")

    medicos = supabase.table("MEDICOS").select("*").execute()

    if medicos.data:

        dict_med = {m["nome"]: m["id"] for m in medicos.data}

        medico = st.selectbox("Selecione o Médico", dict_med.keys())
        data = st.date_input("Data")
        hora_inicio = st.time_input("Hora Inicial")
        intervalo = st.number_input("Intervalo (minutos)", 5, 120, 20)
        duracao = st.slider("Duração do turno (horas)", 1, 12, 4)

        if st.button("Gerar Agenda"):

            inicio = datetime.combine(data, hora_inicio)
            fim = inicio + timedelta(hours=duracao)

            # Verifica duplicidade
            existe = supabase.table("CONSULTAS") \
                .select("id") \
                .eq("medico_id", dict_med[medico]) \
                .gte("data_hora", inicio.isoformat()) \
                .lte("data_hora", fim.isoformat()) \
                .execute()

            if existe.data:
                st.warning("Já existe agenda nesse período.")
            else:
                vagas = []
                atual = inicio

                while atual < fim:
                    vagas.append({
                        "medico_id": dict_med[medico],
                        "data_hora": atual.isoformat(),
                        "status": "Livre"
                    })
                    atual += timedelta(minutes=intervalo)

                supabase.table("CONSULTAS").insert(vagas).execute()
                st.success(f"{len(vagas)} horários criados com sucesso")

    else:
        st.warning("Nenhum médico cadastrado")

# =============================
# 3 - MARCAÇÃO DE CONSULTA
# =============================

elif menu == "3 - Marcação de Consulta":

    st.header("Agendamento Online")

    consultas = supabase.table("CONSULTAS") \
        .select("*, MEDICOS(*)") \
        .eq("status", "Livre") \
        .order("data_hora") \
        .execute()

    if consultas.data:

        df = pd.DataFrame(consultas.data)
        df["data_formatada"] = pd.to_datetime(df["data_hora"]).dt.strftime("%d/%m/%Y %H:%M")

        df["descricao"] = df.apply(
            lambda x: f"{x['MEDICOS']['nome']} | "
                      f"{x['MEDICOS']['especialidade']} | "
                      f"{x['MEDICOS']['unidade']} | "
                      f"{x['data_formatada']}",
            axis=1
        )

        escolha = st.selectbox("Escolha o horário", df["descricao"])
        id_consulta = df[df["descricao"] == escolha]["id"].values[0]

        with st.form("form_paciente"):
            nome = st.text_input("Nome")
            sobrenome = st.text_input("Sobrenome")
            telefone = st.text_input("Telefone")
            convenio = st.text_input("Convênio")

            if st.form_submit_button("Confirmar Agendamento"):
                if nome and telefone:

                    supabase.table("CONSULTAS") \
                        .update({
                            "paciente_nome": nome,
                            "paciente_sobrenome": sobrenome,
                            "paciente_telefone": telefone,
                            "paciente_convenio": convenio,
                            "status": "Marcada"
                        }) \
                        .eq("id", id_consulta) \
                        .execute()

                    st.success("Consulta marcada com sucesso")
                    st.rerun()
                else:
                    st.error("Nome e telefone são obrigatórios")

    else:
        st.info("Não há horários disponíveis")

# =============================
# 4 - CONSULTAS MARCADAS
# =============================

elif menu == "4 - Consultas Marcadas":

    st.header("Consultas Agendadas")

    consultas = supabase.table("CONSULTAS") \
        .select("*, MEDICOS(*)") \
        .neq("status", "Livre") \
        .order("data_hora") \
        .execute()

    if consultas.data:

        dados = []

        for c in consultas.data:
            dados.append({
                "Data/Hora": pd.to_datetime(c["data_hora"]).strftime("%d/%m/%Y %H:%M"),
                "Médico": c["MEDICOS"]["nome"],
                "Especialidade": c["MEDICOS"]["especialidade"],
                "Unidade": c["MEDICOS"]["unidade"],
                "Paciente": f"{c['paciente_nome']} {c['paciente_sobrenome']}",
                "Telefone": c["paciente_telefone"],
                "Convênio": c["paciente_convenio"],
                "Status": c["status"]
            })

        df_final = pd.DataFrame(dados)
        st.dataframe(df_final, use_container_width=True)

    else:
        st.info("Nenhuma consulta marcada")
