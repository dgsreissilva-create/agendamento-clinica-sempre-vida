import streamlit as st
import pandas as pd
import datetime as dt_lib
from supabase import create_client

# --- 1. CONFIGURAÇÕES INICIAIS ---
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

st.set_page_config(page_title="Clínica Sempre Vida", layout="wide")

# --- SEGURANÇA ---
SENHA_ACESSO = "8484" 

# --- 2. MENU LATERAL ---
st.sidebar.title("🏥 Gestão Clínica")
menu = st.sidebar.radio("Navegação", [
    "1. Cadastro de Médicos", 
    "2. Abertura de Agenda", 
    "3. Marcar Consulta",
    "4. Relatório de Agendamentos",
    "5. Cancelar Consulta",
    "6. Excluir Grade Aberta",
    "7. Excluir Cadastro de Médico",
    "8. Relatório Gerencial"
], index=2)

# Função de validação de senha
def verificar_senha():
    if "autenticado" not in st.session_state:
        st.session_state["autenticado"] = False
    
    if not st.session_state["autenticado"]:
        with st.container():
            st.subheader("🔒 Área Restrita")
            senha_digitada = st.text_input("Digite a senha administrativa:", type="password")
            if st.button("Liberar Acesso"):
                if senha_digitada == SENHA_ACESSO:
                    st.session_state["autenticado"] = True
                    st.rerun()
                else:
                    st.error("Senha incorreta!")
        return False
    return True

# --- 3. LÓGICA DAS TELAS ---

# TELA 3 (ABERTA AO PÚBLICO)
if menu == "3. Marcar Consulta":
    st.header("📅 Agendamento de Consultas")
    try:
        # AJUSTE 1: Aumentado o limite para 4000 para garantir que pegue médicos novos
        res_vagas = supabase.table("CONSULTAS").select("*, MEDICOS(*)").eq("status", "Livre").limit(4000).execute()
        if res_vagas.data:
            vagas_limpas = []
            for r in res_vagas.data:
                m = r.get('MEDICOS') or r.get('medicos')
                if m:
                    dt = pd.to_datetime(r['data_hora'])
                    vagas_limpas.append({
                        'id': r['id'], 'unidade': str(m.get('unidade', 'N/I')).strip(),
                        'especialidade': str(m.get('especialidade', 'N/I')).strip(),
                        'medico': str(m.get('nome', 'N/I')).strip(),
                        'display_horario': dt.strftime('%d/%m/%Y às %H:%M'),
                        'sort': r['data_hora']
                    })
            df_f = pd.DataFrame(vagas_limpas).sort_values(by='sort')

            c1, c2 = st.columns(2)
            with c1:
                u_sel = st.selectbox("1️⃣ Unidade", ["Selecione..."] + sorted(df_f['unidade'].unique().tolist()))
                if u_sel != "Selecione...":
                    df_filtered = df_f[df_f['unidade'] == u_sel]
                    e_sel = st.selectbox("2️⃣ Especialidade", ["Selecione..."] + sorted(df_filtered['especialidade'].unique().tolist()))
                else:
                    e_sel = "Selecione..."
            with c2:
                if e_sel != "Selecione..." and u_sel != "Selecione...":
                    df_filtered = df_filtered[df_filtered['especialidade'] == e_sel]
                    m_sel = st.selectbox("3️⃣ Médico", ["Selecione..."] + sorted(df_filtered['medico'].unique().tolist()))
                    if m_sel != "Selecione...":
                        df_filtered = df_filtered[df_filtered['medico'] == m_sel]
                        h_sel = st.selectbox("4️⃣ Horário", ["Selecione..."] + df_filtered['display_horario'].tolist())
                    else:
                        h_sel = "Selecione..."
                else:
                    m_sel = h_sel = "Selecione..."

            if "Selecione" not in f"{u_sel}{e_sel}{m_sel}{h_sel}":
                id_vaga = df_filtered[df_filtered['display_horario'] == h_sel].iloc[0]['id']
                with st.form("form_agendar"):
                    f1, f2 = st.columns(2)
                    pn = f1.text_input("Nome")
                    ps = f1.text_input("Sobrenome")
                    pt = f2.text_input("WhatsApp")
                    pc = f2.text_input("Convênio")
                    if st.form_submit_button("Confirmar Agendamento"):
                        if pn and pt:
                            supabase.table("CONSULTAS").update({
                                "paciente_nome": pn, "paciente_sobrenome": ps, 
                                "paciente_telefone": pt, "paciente_convenio": pc, 
                                "status": "Marcada"
                            }).eq("id", id_vaga).execute()
                            st.success("✅ Agendado!")
                            st.balloons()
                            st.rerun()
                        else: st.error("Por favor, preencha Nome e WhatsApp.")
        else: st.info("Nenhum horário livre no momento.")
    except Exception as e: st.error(f"Erro ao carregar agenda: {e}")

# TELAS ADMINISTRATIVAS (PROTEGIDAS)
else:
    if verificar_senha():
        if st.sidebar.button("🔒 Sair do Painel Adm"):
            st.session_state["autenticado"] = False
            st.rerun()

        if menu == "1. Cadastro de Médicos":
            st.header("👨‍⚕️ Cadastro de Médicos")
            especialidades = ["Cardiologia", "Clinica", "Dermatologia", "Endocrinologia", "Endocrinologia - Diabete e Tireoide", "Fonoaudiologia", "Ginecologia", "Nefrologia", "Neurologia", "Neuropsicologia", "Nutricionista", "ODONTOLOGIA", "Oftalmologia", "Ortopedia", "Otorrinolaringologia", "Pediatria", "Pneumologia", "Psicologia", "Psiquiatria", "Urologia"]
            with st.form("f_med"):
                n = st.text_input("Nome do Médico")
                e = st.selectbox("Especialidade", sorted(especialidades))
                u = st.selectbox("Unidade", [
                    "Pç 7 Rua Carijos 424 SL 2213", "Pç 7 Rua Rio de Janeiro 462 SL 303", 
                    "Eldorado Av Jose Faria da Rocha 4408 2 and", "Eldorado Av Jose Faria da Rocha 5959"
                ])
                if st.form_submit_button("Salvar Médico"):
                    supabase.table("MEDICOS").insert({"nome": n.strip(), "especialidade": e, "unidade": u}).execute()
                    st.success("Médico Cadastrado!")

        elif menu == "2. Abertura de Agenda":
            st.header("🏪 Abertura de Agenda")
            res = supabase.table("MEDICOS").select("*").execute()
            if res.data:
                # AJUSTE 2: Garantir que o dicionário use o ID correto para gravação
                op = {f"{m['nome']} ({m['especialidade']}) - {m['unidade']}": m['id'] for m in res.data}
                sel = st.selectbox("Selecione o Médico e Unidade", list(op.keys()))
                c1, c2, c3 = st.columns(3)
                d = c1.date_input("Data", format="DD/MM/YYYY")
                h_ini = c2.time_input("Hora de Início", value=dt_lib.time(8, 0))
                h_fim = c3.time_input("Hora Final", value=dt_lib.time(18, 0))
                i = st.number_input("Intervalo (minutos)", 5, 120, 20)
                if st.button("Gerar Grade"):
