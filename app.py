import streamlit as st
import pandas as pd
import datetime as dt_lib
from supabase import create_client

# --- 1. CONFIGURAÇÕES INICIAIS ---
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

st.set_page_config(page_title="Clínica Sempre Vida", layout="wide")

# --- CONFIGURAÇÃO DE SEGURANÇA ---
SENHA_ACESSO = "8484" 

# --- 2. MENU LATERAL ---
st.sidebar.title("🏥 Gestão Clínica")
# Definimos o índice 2 (Tela 3) como padrão para o paciente
menu = st.sidebar.radio("Navegação", [
    "1. Cadastro de Médicos", 
    "2. Abertura de Agenda", 
    "3. Marcar Consulta",
    "4. Relatório de Agendamentos",
    "5. Cancelar Consulta",
    "6. Excluir Grade Aberta"
], index=2)

# Função de validação de senha
def verificar_senha():
    if "autenticado" not in st.session_state:
        st.session_state["autenticado"] = False
    
    if not st.session_state["autenticado"]:
        with st.container():
            st.subheader("🔒 Área Restrita")
            senha_digitada = st.text_input("Digite a senha administrativa para acessar esta tela:", type="password")
            if st.button("Liberar Acesso"):
                if senha_digitada == SENHA_ACESSO:
                    st.session_state["autenticado"] = True
                    st.rerun()
                else:
                    st.error("Senha incorreta! Acesso negado.")
        return False
    return True

# --- LÓGICA DAS TELAS ---

# --- TELA 3: MARCAÇÃO DE CONSULTA (ABERTA AO PÚBLICO) ---
if menu == "3. Marcar Consulta":
    st.header("📅 Agendamento de Consultas")
    try:
        res_vagas = supabase.table("CONSULTAS").select("*, MEDICOS(*)").eq("status", "Livre").execute()
        if res_vagas.data:
            vagas_limpas = []
            for r in res_vagas.data:
                m = r.get('MEDICOS') or r.get('medicos')
                if m:
                    dt = pd.to_datetime(r['data_hora'])
                    vagas_limpas.append({
                        'id': r['id'], 'unidade': m.get('unidade', 'N/I'),
                        'especialidade': m.get('especialidade', 'N/I'),
                        'medico': m.get('nome', 'N/I'),
                        'display_horario': dt.strftime('%d/%m/%Y às %H:%M'),
                        'sort': r['data_hora']
                    })
            df_f = pd.DataFrame(vagas_limpas).sort_values(by='sort')

            c1, c2 = st.columns(2)
            with c1:
                u_sel = st.selectbox("1️⃣ Escolha a Unidade", ["Selecione a Unidade..."] + sorted(df_f['unidade'].unique().tolist()))
                if u_sel != "Selecione a Unidade...":
                    df_f = df_f[df_f['unidade'] == u_sel]
                    e_sel = st.selectbox("2️⃣ Escolha a Especialidade", ["Selecione a Especialidade..."] + sorted(df_f['especialidade'].unique().tolist()))
                else:
                    st.selectbox("2️⃣ Especialidade", ["Aguardando Unidade..."], disabled=True)
                    e_sel = "Selecione a Especialidade..."
            with c2:
                if e_sel != "Selecione a Especialidade..." and u_sel != "Selecione a Unidade...":
                    df_f = df_f[df_f['especialidade'] == e_sel]
                    m_sel = st.selectbox("3️⃣ Escolha o Médico", ["Selecione o Médico..."] + sorted(df_f['medico'].unique().tolist()))
                    if m_sel != "Selecione o Médico...":
                        df_f = df_f[df_f['medico'] == m_sel]
                        h_sel = st.selectbox("4️⃣ Escolha o Horário", ["Selecione o Horário..."] + df_f['display_horario'].tolist())
                    else:
                        st.selectbox("4️⃣ Horário", ["Aguardando Médico..."], disabled=True)
                        h_sel = "Selecione o Horário..."
                else:
                    st.selectbox("3️⃣ Médico", ["Aguardando Especialidade..."], disabled=True)
                    st.selectbox("4️⃣ Horário", ["Aguardando Médico..."], disabled=True)
                    m_sel = "Selecione o Médico..."
                    h_sel = "Selecione o Horário..."

            if "Selecione" not in f"{u_sel}{e_sel}{m_sel}{h_sel}":
                id_vaga = df_f[df_f['display_horario'] == h_sel].iloc[0]['id']
                st.divider()
                with st.form("form_publico"):
                    st.write(f"📝 Confirmando: **{m_sel}** em **{h_sel}**")
                    f1, f2 = st.columns(2)
                    p_n = f1.text_input("Seu Nome")
                    p_s = f1.text_input("Seu Sobrenome")
                    p_t = f2.text_input("WhatsApp com DDD")
                    p_c = f2.text_input("Convênio (Opcional)")
                    if st.form_submit_button("FINALIZAR AGENDAMENTO"):
                        if p_n and p_t:
                            supabase.table("CONSULTAS").update({
                                "paciente_nome": p_n, "paciente_sobrenome": p_s,
                                "paciente_telefone": p_t, "paciente_convenio": p_c,
                                "status": "Marcada"
                            }).eq("id", id_vaga).execute()
                            st.success("✅ Agendado com sucesso!")
                            st.balloons()
                        else:
                            st.error("⚠️ Nome e WhatsApp são obrigatórios.")
        else:
            st.info("🔎 Não há horários livres no momento.")
    except Exception as e:
        st.error(f"Erro técnico: {e}")

# --- TELAS ADMINISTRATIVAS (BLOQUEADAS COM SENHA 8484) ---
else:
    if verificar_senha():
        if st.sidebar.button("🔒 Sair do Painel Adm"):
            st.session_state["autenticado"] = False
            st.rerun()

        if menu == "1. Cadastro de Médicos":
            st.header("👨‍⚕️ Cadastro de Médicos")
            especialidades_lista = ["Cardiologia", "Clinica", "Dermatologia", "Endocrinologia - Diabete e Tireoide", "Fonoaudiologia", "Ginecologia", "Neurologia", "Neuropsicologia", "ODONTOLOGIA - DENTISTA", "Oftalmologia", "Ortopedia", "Otorrinolaringologia", "Pediatria", "Pneumologia", "Psicologia"]
            with st.form("f_med"):
                n = st.text_input("Nome do Médico")
                e = st.selectbox("Especialidade", especialidades_lista)
                u = st.selectbox("Unidade", ["Praça 7 - Rua Carijos", "Praça 7 - Rua Rio de Janeiro", "Eldorado"])
                if st.form_submit_button("Salvar Médico"):
                    supabase.table("MEDICOS").insert({"nome": n, "especialidade": e, "unidade": u}).execute()
                    st.success("Médico Cadastrado!")

        elif menu == "2. Abertura de Agenda":
            st.header("🏪 Abertura de Agenda")
            res = supabase.table("MEDICOS").select("*").execute()
            if res.data:
                op = {f"{m['nome']} ({m['especialidade']})": m['id'] for m in res.data}
                sel = st.selectbox("Médico", list(op.keys()))
                c1, c2 = st.columns(2)
                d = c1.date_input("Data", format="DD/MM/YYYY")
                h = c2.time_input("Hora Inicial")
                q = st.number_input("Vagas", 1, 50, 10)
                i = st.number_input("Minutos por vaga", 5, 60, 20)
                if st.button("Gerar Grade"):
                    vagas = []
                    inicio = dt_lib.datetime.combine(d, h)
                    for x in range(int(q)):
                        vagas.append({"medico_id": op[sel], "data_hora": (inicio + dt_lib.timedelta(minutes=x*i)).isoformat(), "status": "Livre"})
                    supabase.table("CONSULTAS").insert(vagas).execute()
                    st.success("Agenda Aberta no Banco!")

        elif menu == "4. Relatório de Agendamentos":
            st.header("📋 Relatório")
            res = supabase.table("CONSULTAS").select("*, MEDICOS(*)").execute()
            if res.data:
                relat = []
                for r in res.data:
                    m = r.get('MEDICOS') or r.get('medicos')
                    dt = pd.to_datetime(r['data_hora'])
                    relat.append({
                        "Data/Hora": dt.strftime('%d/%m/%Y %H:%M'),
                        "Médico": m['nome'] if m else "N/I",
                        "Paciente": f"{r.get('paciente_nome','')} {r.get('paciente_sobrenome','')}".strip() or "-",
                        "WhatsApp": r.get('paciente_telefone', '-'),
                        "Status": r['status']
                    })
                st.dataframe(pd.DataFrame(relat), use_container_width=True)

        elif menu == "5. Cancelar Consulta":
            st.header("🚫 Cancelar Agendamento")
            res = supabase.table("CONSULTAS").select("*, MEDICOS(*)").eq("status", "Marcada").execute()
            if res.data:
                df = pd.DataFrame([{'id': r['id'], 'info': f"{r['paciente_nome']} | {r['data_hora']}"} for r in res.data])
                sel = st.selectbox("Escolha a consulta para cancelar:", df['info'])
                if st.button("Confirmar Cancelamento"):
                    id_c = df[df['info'] == sel].iloc[0]['id']
                    supabase.table("CONSULTAS").update({"paciente_nome":None, "paciente_sobrenome":None, "paciente_telefone":None, "status":"Livre"}).eq("id", id_c).execute()
                    st.success("Cancelado!")
                    st.rerun()

        elif menu == "6. Excluir Grade Aberta":
            st.header("🗑️ Excluir Horários Livres")
            res = supabase.table("CONSULTAS").select("*, MEDICOS(*)").eq("status", "Livre").execute()
            if res.data:
                df = pd.DataFrame([{'id': r['id'], 'info': f"{pd.to_datetime(r['data_hora']).strftime('%d/%m/%Y %H:%M')} - {r['MEDICOS']['nome']}"} for r in res.data])
                sel = st.multiselect("Selecione os horários para apagar:", df['info'])
                if st.button("Excluir Permanente"):
                    ids = df[df['info'].isin(sel)]['id'].tolist()
                    supabase.table("CONSULTAS").delete().in_("id", ids).execute()
                    st.success("Removido do Banco!")
                    st.rerun()
