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
if "menu_escolhido" not in st.session_state:
    st.session_state["menu_escolhido"] = "3. Marcar Consulta"

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
            senha_digitada = st.text_input("Digite a senha administrativa:", type="password")
            if st.button("Liberar Acesso"):
                if senha_digitada == SENHA_ACESSO:
                    st.session_state["autenticado"] = True
                    st.rerun()
                else:
                    st.error("Senha incorreta!")
        return False
    return True

# --- LÓGICA DAS TELAS ---

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
                u_sel = st.selectbox("1️⃣ Unidade", ["Selecione..."] + sorted(df_f['unidade'].unique().tolist()))
                if u_sel != "Selecione...":
                    df_f = df_f[df_f['unidade'] == u_sel]
                    e_sel = st.selectbox("2️⃣ Especialidade", ["Selecione..."] + sorted(df_f['especialidade'].unique().tolist()))
                else:
                    st.selectbox("2️⃣ Especialidade", ["Aguardando..."], disabled=True)
                    e_sel = "Selecione..."
            with c2:
                if e_sel != "Selecione..." and u_sel != "Selecione...":
                    df_f = df_f[df_f['especialidade'] == e_sel]
                    m_sel = st.selectbox("3️⃣ Médico", ["Selecione..."] + sorted(df_f['medico'].unique().tolist()))
                    if m_sel != "Selecione...":
                        df_f = df_f[df_f['medico'] == m_sel]
                        h_sel = st.selectbox("4️⃣ Horário", ["Selecione..."] + df_f['display_horario'].tolist())
                    else:
                        st.selectbox("4️⃣ Horário", ["Aguardando..."], disabled=True)
                        h_sel = "Selecione..."
                else:
                    st.selectbox("3️⃣ Médico", ["Aguardando..."], disabled=True)
                    st.selectbox("4️⃣ Horário", ["Aguardando..."], disabled=True)
                    m_sel = "Selecione..."
                    h_sel = "Selecione..."

            if "Selecione" not in f"{u_sel}{e_sel}{m_sel}{h_sel}":
                id_vaga = df_f[df_f['display_horario'] == h_sel].iloc[0]['id']
                with st.form("form_p"):
                    f1, f2 = st.columns(2)
                    pn = f1.text_input("Nome")
                    ps = f1.text_input("Sobrenome")
                    pt = f2.text_input("WhatsApp")
                    pc = f2.text_input("Convênio")
                    if st.form_submit_button("AGENDAR"):
                        if pn and pt:
                            supabase.table("CONSULTAS").update({"paciente_nome": pn, "paciente_sobrenome": ps, "paciente_telefone": pt, "paciente_convenio": pc, "status": "Marcada"}).eq("id", id_vaga).execute()
                            st.success("✅ Agendado!")
                            st.balloons()
        else: st.info("Sem horários livres.")
    except Exception as e: st.error(f"Erro: {e}")

else:
    if verificar_senha():
        if st.sidebar.button("🔒 Sair do Painel Adm"):
            st.session_state["autenticado"] = False
            st.rerun()

        if menu == "1. Cadastro de Médicos":
            st.header("👨‍⚕️ Cadastro de Médicos")
            especialidades = ["Cardiologia", "Clinica", "Dermatologia", "Endocrinologia", "Fonoaudiologia", "Ginecologia", "Neurologia", "Neuropsicologia", "ODONTOLOGIA - DENTISTA", "Oftalmologia", "Ortopedia", "Otorrinolaringologia", "Pediatria", "Pneumologia", "Psicologia"]
            with st.form("f_med"):
                n = st.text_input("Nome do Médico")
                e = st.selectbox("Especialidade", especialidades)
                u = st.selectbox("Unidade", ["Praça 7 - Rua Carijos", "Praça 7 - Rua Rio de Janeiro", "Eldorado"])
                if st.form_submit_button("Salvar"):
                    supabase.table("MEDICOS").insert({"nome": n, "especialidade": e, "unidade": u}).execute()
                    st.success("Salvo!")

        elif menu == "2. Abertura de Agenda":
            st.header("🏪 Abertura de Agenda")
            res = supabase.table("MEDICOS").select("*").execute()
            if res.data:
                op = {f"{m['nome']} ({m['especialidade']})": m['id'] for m in res.data}
                sel = st.selectbox("Médico", list(op.keys()))
                c1, c2 = st.columns(2)
                d = c1.date_input("Data")
                h = c2.time_input("Início")
                q = st.number_input("Vagas", 1, 50, 10)
                i = st.number_input("Intervalo (min)", 5, 60, 20)
                if st.button("Gerar Grade"):
                    v = []
                    p = dt_lib.datetime.combine(d, h)
                    for idx in range(int(q)):
                        v.append({"medico_id": op[sel], "data_hora": (p + dt_lib.timedelta(minutes=idx*i)).isoformat(), "status": "Livre"})
                    supabase.table("CONSULTAS").insert(v).execute()
                    st.success("Grade Gerada!")

        elif menu == "4. Relatório de Agendamentos":
            st.header("📋 Relatório de Consultas")
            try:
                res = supabase.table("CONSULTAS").select("*, MEDICOS(*)").execute()
                if res.data:
                    relat_final = []
                    for i, r in enumerate(res.data):
                        m = r.get('MEDICOS') or r.get('medicos') or {}
                        dt = pd.to_datetime(r['data_hora'])
                        data_hora_br = dt.strftime('%d/%m/%Y %H:%M')
                        medico = m.get('nome', 'N/I')
                        especialidade = m.get('especialidade', '-')
                        unidade = m.get('unidade', '-')
                        paciente = f"{r.get('paciente_nome', '')} {r.get('paciente_sobrenome', '')}".strip()
                        telefone = str(r.get('paciente_telefone', ''))
                        
                        msg = f"Olá, você terá uma consulta com {medico} / {especialidade} / {data_hora_br} / {unidade}"
                        tel_limpo = ''.join(filter(str.isdigit, telefone))
                        link_wa = f"https://wa.me/55{tel_limpo}?text={msg.replace(' ', '%20')}" if tel_limpo else None
                        
                        relat_final.append({
                            "Nº": i + 1,
                            "Data/Hora": data_hora_br,
                            "Unidade": unidade,
                            "Médico": medico,
                            "Paciente": paciente if paciente else "Não informado",
                            "WhatsApp": link_wa
                        })
                    
                    df_relat = pd.DataFrame(relat_final)
                    st.dataframe(df_relat, column_config={"WhatsApp": st.column_config.LinkColumn("📱 Ação", display_text="Chamar no WhatsApp 🟢")}, use_container_width=True, hide_index=True)
                else: st.info("Nenhum registro encontrado.")
            except Exception as e: st.error(f"Erro no relatório: {e}")

        elif menu == "5. Cancelar Consulta":
            st.header("🚫 Cancelar Agendamento")
            res = supabase.table("CONSULTAS").select("*, MEDICOS(*)").eq("status", "Marcada").execute()
            if res.data:
                df = pd.DataFrame([{'id': r['id'], 'info': f"{r['paciente_nome']} | {r['data_hora']}"} for r in res.data])
                sel = st.selectbox("Consulta:", df['info'])
                if st.button("Confirmar"):
                    supabase.table("CONSULTAS").update({"paciente_nome":None, "paciente_sobrenome":None, "paciente_telefone":None, "status":"Livre"}).eq("id", df[df['info']==sel].iloc[0]['id']).execute()
                    st.success("Cancelado!"); st.rerun()

        elif menu == "6. Excluir Grade Aberta":
            st.header("🗑️ Excluir Horários Livres")
            res = supabase.table("CONSULTAS").select("*, MEDICOS(*)").eq("status", "Livre").execute()
            if res.data:
                df = pd.DataFrame([{'id': r['id'], 'info': f"{pd.to_datetime(r['data_hora']).strftime('%d/%m/%Y %H:%M')} - {r['MEDICOS']['nome']}"} for r in res.data])
                sel = st.multiselect("Horários:", df['info'])
                if st.button("Excluir"):
                    ids = df[df['info'].isin(sel)]['id'].tolist()
                    supabase.table("CONSULTAS").delete().in_("id", ids).execute()
                    st.success("Excluído!"); st.rerun()
