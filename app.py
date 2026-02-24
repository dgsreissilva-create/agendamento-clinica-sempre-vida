import streamlit as st
from supabase import create_client
import pandas as pd
from datetime import datetime, timedelta

# --- CONEXÃO DIRETA REVISADA ---
URL_S = "https://mxsuvjgwpqzhaqbzrvdq.supabase.co"
KEY_S = "sb_publishable_08qbHGfKbBb8ljAHb7ckuQ_mp161ThN"
supabase = create_client(URL_S, KEY_S)

st.set_page_config(page_title="Clínica Sempre Vida", layout="wide", page_icon="🏥")

# --- CONFIGURAÇÃO DE SEGURANÇA ---
SENHA_ADMIN = "1234" # Altere sua senha administrativa aqui

if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False

# --- BARRA LATERAL ---
st.sidebar.image("https://cdn-icons-png.flaticon.com/512/387/387561.png", width=100)
st.sidebar.title("Menu Clínica")

# Lógica de Login na Sidebar
if not st.session_state["autenticado"]:
    with st.sidebar.expander("🔐 Área Restrita (Adm)"):
        pwd = st.text_input("Senha", type="password")
        if st.button("Acessar"):
            if pwd == SENHA_ADMIN:
                st.session_state["autenticado"] = True
                st.rerun()
            else:
                st.error("Senha incorreta")

# Definição de telas visíveis
if st.session_state["autenticado"]:
    menu = st.sidebar.radio("Navegação", [
        "1 - Cadastro de Médicos", 
        "2 - Abertura de Agenda", 
        "3 - Marcação de Consulta", 
        "4 - Confirmação de Consultas"
    ])
    if st.sidebar.button("Sair"):
        st.session_state["autenticado"] = False
        st.rerun()
else:
    menu = "3 - Marcação de Consulta" # Única tela visível para o público
    st.sidebar.info("Acesse a área restrita para gerenciar médicos e agendas.")

# --- TELA 1: CADASTRO DE MÉDICOS ---
if menu == "1 - Cadastro de Médicos":
    st.header("👨‍⚕️ Cadastro de Equipe Médica")
    with st.form("form_med"):
        col1, col2 = st.columns(2)
        nome = col1.text_input("Nome do Médico")
        esp = col2.selectbox("Especialidade", ["Clínico Geral", "Cardiologia", "Pediatria", "Ginecologia", "Ortopedia", "Oftalmologia"])
        unidade = st.selectbox("Unidade de Atendimento", ["Praça 7 - Rua Carijos", "Praça 7 - Rua Rio de Janeiro", "Eldorado"])
        if st.form_submit_button("Cadastrar Médico"):
            if nome:
                supabase.table("MEDICOS").insert({"nome": nome, "especialidade": esp, "unidade": unidade}).execute()
                st.success("Médico cadastrado com sucesso!")
            else: st.warning("Informe o nome.")

# --- TELA 2: ABERTURA DE AGENDA ---
elif menu == "2 - Abertura de Agenda":
    st.header("⏳ Gerador de Grade de Horários")
    res_m = supabase.table("MEDICOS").select("*").execute()
    if res_m.data:
        m_dict = {m['nome']: m['id'] for m in res_m.data}
        escolha_m = st.selectbox("Selecione o Médico", list(m_dict.keys()))
        
        c1, c2, c3 = st.columns(3)
        data = c1.date_input("Data do Atendimento")
        hora = c2.time_input("Horário de Início")
        intervalo = c3.number_input("Minutos por consulta", value=20)
        horas_total = st.slider("Duração do turno (horas)", 1, 12, 4)

        if st.button("Gerar Horários na Agenda"):
            inicio = datetime.combine(data, hora)
            vagas = []
            for i in range(0, int(horas_total * 60), int(intervalo)):
                vagas.append({
                    "medico_id": m_dict[escolha_m],
                    "data_hora": (inicio + timedelta(minutes=i)).isoformat(),
                    "status": "Livre"
                })
            supabase.table("CONSULTAS").insert(vagas).execute()
            st.success(f"Foram criadas {len(vagas)} vagas para o médico selecionado!")
    else: st.warning("Nenhum médico cadastrado.")

# --- TELA 3: MARCAÇÃO DE CONSULTA (PÚBLICA) ---
elif menu == "3 - Marcação de Consulta":
    st.header("📅 Agendamento Online")
    # Busca horários livres com dados dos médicos (Inner Join)
    res_v = supabase.table("CONSULTAS").select(", MEDICOS()").eq("status", "Livre").execute()
    
    if res_v.data:
        df_v = pd.DataFrame(res_v.data)
        # Formata data para exibição
        df_v['exibir'] = df_v.apply(lambda x: f"{x['MEDICOS']['nome']} ({x['MEDICOS']['especialidade']}) - {x['data_hora']} - {x['MEDICOS']['unidade']}", axis=1)
        
        vaga_selecionada = st.selectbox("Escolha um horário disponível", df_v['exibir'])
        id_selecionado = df_v[df_v['exibir'] == vaga_selecionada]['id'].values[0]

        with st.form("form_pac"):
            col1, col2 = st.columns(2)
            n = col1.text_input("Nome")
            s = col1.text_input("Sobrenome")
            t = col2.text_input("WhatsApp (com DDD)")
            c = col2.text_input("Convênio")
            if st.form_submit_button("Confirmar Agendamento"):
                if n and t:
                    supabase.table("CONSULTAS").update({
                        "paciente_nome": n, "paciente_sobrenome": s, "paciente_telefone": t,
                        "paciente_convenio": c, "status": "Marcada"
                    }).eq("id", id_selecionado).execute()
                    st.balloons()
                    st.success("Consulta marcada! Compareça com 15 min de antecedência.")
                else: st.error("Nome e Telefone são obrigatórios.")
    else: st.info("Não há horários disponíveis no momento. Tente mais tarde.")

# --- TELA 4: CONFIRMAÇÃO DE CONSULTAS (ADM) ---
elif menu == "4 - Confirmação de Consultas":
    st.header("✅ Consultas Agendadas")
    res_f = supabase.table("CONSULTAS").select(", MEDICOS()").neq("status", "Livre").execute()
    if res_f.data:
        lista = []
        for r in res_f.data:
            lista.append({
                "Data/Hora": r['data_hora'],
                "Médico": r['MEDICOS']['nome'],
                "Unidade": r['MEDICOS']['unidade'],
                "Paciente": f"{r['paciente_nome']} {r['paciente_sobrenome']}",
                "WhatsApp": r['paciente_telefone'],
                "Convênio": r['paciente_convenio']
            })
        df_final = pd.DataFrame(lista).sort_values(by="Data/Hora")
        st.dataframe(df_final, use_container_width=True)
    else: st.info("Nenhuma consulta marcada no sistema.")
