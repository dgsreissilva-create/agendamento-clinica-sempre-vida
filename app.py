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

# ==============================
# FUNÇÃO PARA BUSCAR TODOS REGISTROS (PAGINAÇÃO)
# ==============================
def buscar_todos(tabela, select_str="*", filtros=None):
    page_size = 1000
    offset = 0
    dados = []
    while True:
        query = supabase.table(tabela).select(select_str).range(offset, offset + page_size - 1)
        if filtros:
            for f in filtros:
                query = query.eq(f[0], f[1])
        res = query.execute()
        if not res.data:
            break
        dados.extend(res.data)
        if len(res.data) < page_size:
            break
        offset += page_size
    return dados

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
            senha_digitada = st.text_input("Digite a senha administrativa:", type="password", key="senha_adm")
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
        dados = buscar_todos("CONSULTAS", "*, MEDICOS(*)", filtros=[("status", "Livre")])
        if dados:
            vagas_limpas = []
            for r in dados:
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
                df_u = df_f[df_f['unidade'] == u_sel]
                with c2:
                    e_sel = st.selectbox("2️⃣ Especialidade", ["Selecione..."] + sorted(df_u['especialidade'].unique().tolist()))
                
                if e_sel != "Selecione...":
                    df_e = df_u[df_u['especialidade'] == e_sel]
                    m_sel = st.selectbox("3️⃣ Médico", ["Selecione..."] + sorted(df_e['medico'].unique().tolist()))
                    
                    if m_sel != "Selecione...":
                        df_m = df_e[df_e['medico'] == m_sel]
                        h_sel = st.selectbox("4️⃣ Horário", ["Selecione..."] + df_m['display_horario'].tolist())
                        
                        if h_sel != "Selecione...":
                            id_vaga = df_m[df_m['display_horario'] == h_sel].iloc[0]['id']
                            with st.form("form_agendar"):
                                pn, ps = st.text_input("Nome"), st.text_input("Sobrenome")
                                pt, pc = st.text_input("WhatsApp"), st.text_input("Convênio")
                                if st.form_submit_button("Confirmar Agendamento"):
                                    if pn and pt:
                                        supabase.table("CONSULTAS").update({
                                            "paciente_nome": pn, "paciente_sobrenome": ps, 
                                            "paciente_telefone": pt, "paciente_convenio": pc, "status": "Marcada"
                                        }).eq("id", id_vaga).execute()
                                        st.success("✅ Agendado!"); st.balloons(); st.rerun()
        else: st.info("Nenhum horário livre disponível.")
    except Exception as e: st.error(f"Erro: {e}")

# TELAS QUE EXIGEM SENHA
else:
    if verificar_senha():
        if st.sidebar.button("🔒 Sair do Painel"):
            st.session_state["autenticado"] = False
            st.rerun()

        if menu == "1. Cadastro de Médicos":
            st.header("👨‍⚕️ Cadastro")
            esp = sorted(["Cardiologia", "Clinica", "Ginecologia", "Neurologia", "Nutricionista", "ODONTOLOGIA", "Ortopedia", "Psicologia", "Psiquiatria"])
            with st.form("f_med"):
                n = st.text_input("Nome")
                e = st.selectbox("Especialidade", esp)
                u = st.selectbox("Unidade", ["Pç 7 Rua Carijos 424 SL 2213", "Eldorado Av Jose Faria da Rocha 4408 2 and"])
                if st.form_submit_button("Salvar"):
                    supabase.table("MEDICOS").insert({"nome": n.upper(), "especialidade": e, "unidade": u}).execute()
                    st.success("Médico Salvo!")

        elif menu == "2. Abertura de Agenda":
            st.header("🏪 Abertura")
            meds = buscar_todos("MEDICOS")
            if meds:
                op = {f"{m['nome']} ({m['especialidade']})": m['id'] for m in meds}
                sel = st.selectbox("Médico", list(op.keys()))
                d = st.date_input("Data")
                hi, hf = st.time_input("Início", value=dt_lib.time(8,0)), st.time_input("Fim", value=dt_lib.time(18,0))
                if st.button("Gerar Grade"):
                    vagas = []
                    t, fim = dt_lib.datetime.combine(d, hi), dt_lib.datetime.combine(d, hf)
                    while t < fim:
                        vagas.append({"medico_id": op[sel], "data_hora": t.isoformat(), "status": "Livre"})
                        t += dt_lib.timedelta(minutes=20)
                    supabase.table("CONSULTAS").insert(vagas).execute()
                    st.success("Grade Criada!")

        elif menu == "4. Relatório de Agendamentos":
            st.header("📋 Relatório")
            dados = buscar_todos("CONSULTAS", "*, MEDICOS(*)")
            if dados:
                df = pd.DataFrame([{"Data": pd.to_datetime(r['data_hora']).strftime('%d/%m/%Y %H:%M'), "Médico": (r.get('MEDICOS') or {}).get('nome'), "Paciente": r.get('paciente_nome'), "Status": r['status']} for r in dados])
                st.dataframe(df, use_container_width=True)

        elif menu == "5. Cancelar Consulta":
            st.header("🚫 Cancelar")
            dados = buscar_todos("CONSULTAS", filtros=[("status", "Marcada")])
            if dados:
                op = {f"{r['paciente_nome']} | {r['data_hora']}": r['id'] for r in dados}
                sel = st.selectbox("Selecione:", ["Selecione..."] + list(op.keys()))
                if sel != "Selecione..." and st.button("Confirmar"):
                    supabase.table("CONSULTAS").update({"status": "Livre", "paciente_nome": None}).eq("id", op[sel]).execute()
                    st.success("Cancelado!")

        elif menu == "6. Excluir Grade Aberta":
            st.header("🗑️ Excluir Horários Livres")
            dados = buscar_todos("CONSULTAS", filtros=[("status", "Livre")])
            if dados:
                df = pd.DataFrame([{"id": r['id'], "info": f"{r['data_hora']}"} for r in dados])
                sel = st.multiselect("Selecione:", df['info'].tolist())
                if st.button("Remover"):
                    ids = df[df['info'].isin(sel)]['id'].tolist()
                    supabase.table("CONSULTAS").delete().in_("id", ids).execute()
                    st.success("Removido!")

        elif menu == "7. Excluir Cadastro de Médico":
            st.header("👨‍⚕️ Remover Médico")
            meds = buscar_todos("MEDICOS")
            if meds:
                op = {m['nome']: m['id'] for m in meds}
                sel = st.selectbox("Médico:", ["Selecione..."] + list(op.keys()))
                if sel != "Selecione..." and st.button("Excluir"):
                    supabase.table("MEDICOS").delete().eq("id", op[sel]).execute()
                    st.success("Removido!")

        elif menu == "8. Relatório Gerencial":
            st.header("📊 Performance")
            dados = buscar_todos("CONSULTAS")
            if dados:
                df = pd.DataFrame(dados)
                st.metric("Total de Vagas", len(df))
                st.metric("Agendados", len(df[df['status'] == 'Marcada']))
