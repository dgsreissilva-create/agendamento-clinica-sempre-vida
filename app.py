import streamlit as st
import pandas as pd
import datetime as dt_lib
from supabase import create_client

# --- 1. CONFIGURAÇÕES INICIAIS ---
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

st.set_page_config(page_title="Clínica Sempre Vida", layout="wide")
SENHA_ACESSO = "8484" 

# ==============================
# FUNÇÃO DE PAGINAÇÃO (BUSCAR TODOS)
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
        if not res.data: break
        dados.extend(res.data)
        if len(res.data) < page_size: break
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

def verificar_senha():
    if "autenticado" not in st.session_state:
        st.session_state["autenticado"] = False
    if not st.session_state["autenticado"]:
        st.subheader("🔒 Área Restrita")
        senha_digitada = st.text_input("Senha Administrativa:", type="password")
        if st.button("Liberar Acesso"):
            if senha_digitada == SENHA_ACESSO:
                st.session_state["autenticado"] = True
                st.rerun()
            else: st.error("Senha incorreta!")
        return False
    return True

# --- 3. LÓGICA DAS TELAS ---

# TELA 1 - CADASTRO OK
if menu == "1. Cadastro de Médicos":
    if verificar_senha():
        st.header("👨‍⚕️ Cadastro de Médicos")
        with st.form("f_med"):
            n = st.text_input("Nome do Médico")
            e = st.selectbox("Especialidade", sorted(["Cardiologia", "Clinica", "Ginecologia", "Neurologia", "Nutricionista", "ODONTOLOGIA", "Ortopedia", "Psicologia", "Psiquiatria"]))
            u = st.selectbox("Unidade", ["Pç 7 Rua Carijos 424 SL 2213", "Pç 7 Rua Rio de Janeiro 462 SL 303", "Eldorado Av Jose Faria da Rocha 4408 2 and"])
            if st.form_submit_button("Salvar"):
                supabase.table("MEDICOS").insert({"nome": n.upper(), "especialidade": e, "unidade": u}).execute()
                st.success("Médico Cadastrado!")

# TELA 2 - ABERTURA (DATA BR E INTERVALO)
elif menu == "2. Abertura de Agenda":
    if verificar_senha():
        st.header("🏪 Abertura de Agenda")
        medicos = buscar_todos("MEDICOS")
        if medicos:
            op = {f"{m['nome']} ({m['especialidade']})": m['id'] for m in medicos}
            sel = st.selectbox("Médico", list(op.keys()))
            c1, c2, c3 = st.columns(3)
            d = c1.date_input("Data da Agenda", format="DD/MM/YYYY")
            hi = c2.time_input("Hora Início", value=dt_lib.time(8, 0))
            hf = c3.time_input("Hora Final", value=dt_lib.time(18, 0))
            inter = st.number_input("Intervalo (minutos)", 5, 120, 20)
            if st.button("Gerar Grade"):
                vagas = []
                t, fim = dt_lib.datetime.combine(d, hi), dt_lib.datetime.combine(d, hf)
                while t < fim:
                    vagas.append({"medico_id": op[sel], "data_hora": t.isoformat(), "status": "Livre"})
                    t += dt_lib.timedelta(minutes=inter)
                supabase.table("CONSULTAS").insert(vagas).execute()
                st.success(f"✅ {len(vagas)} horários criados!")

# TELA 3 - MARCAR CONSULTA (UNIDADE/MÉDICO)
elif menu == "3. Marcar Consulta":
    st.header("📅 Agendamento")
    dados = buscar_todos("CONSULTAS", "*, MEDICOS(*)", filtros=[("status", "Livre")])
    if dados:
        v_list = []
        for r in dados:
            m = r.get('MEDICOS') or r.get('medicos')
            if m:
                dt = pd.to_datetime(r['data_hora'])
                v_list.append({'id': r['id'], 'unidade': m['unidade'], 'especialidade': m['especialidade'], 'medico': m['nome'], 'display': dt.strftime('%d/%m/%Y %H:%M'), 'sort': r['data_hora']})
        df = pd.DataFrame(v_list).sort_values('sort')
        u_sel = st.selectbox("Selecione a Unidade", sorted(df['unidade'].unique()))
        df_u = df[df['unidade'] == u_sel]
        m_sel = st.selectbox("Selecione o Médico", sorted(df_u['medico'].unique()))
        df_m = df_u[df_u['medico'] == m_sel]
        h_sel = st.selectbox("Selecione o Horário", df_m['display'].tolist())
        id_vaga = df_m[df_m['display'] == h_sel].iloc[0]['id']
        with st.form("f_ag"):
            pn, ps, pt = st.text_input("Nome"), st.text_input("Sobrenome"), st.text_input("WhatsApp")
            if st.form_submit_button("Confirmar Agendamento"):
                if pn and pt:
                    supabase.table("CONSULTAS").update({"paciente_nome": pn, "paciente_sobrenome": ps, "paciente_telefone": pt, "status": "Marcada"}).eq("id", id_vaga).execute()
                    st.success("Agendado com Sucesso!"); st.rerun()

# TELA 4 - RELATÓRIO INTELIGENTE
elif menu == "4. Relatório de Agendamentos":
    if verificar_senha():
        st.header("📋 Relatório de Consultas")
        dados = buscar_todos("CONSULTAS", "*, MEDICOS(*)")
        if dados:
            agora = dt_lib.datetime.now()
            rel = []
            for r in dados:
                m = r.get('MEDICOS') or r.get('medicos') or {}
                dt = pd.to_datetime(r['data_hora'])
                if dt >= agora: # Somente para o futuro
                    pac = f"{r.get('paciente_nome','')} {r.get('paciente_sobrenome','')}".strip()
                    tel = ''.join(filter(str.isdigit, str(r.get('paciente_telefone', ''))))
                    msg = f"Olá, Gentileza Confirmar consulta Dr.(a) {m.get('nome')} / {m.get('especialidade')} / {dt.strftime('%d/%m/%Y %H:%M')} / {m.get('unidade')}"
                    link = f"https://wa.me/55{tel}?text={msg.replace(' ', '%20')}" if tel else None
                    rel.append({"Unidade": m.get('unidade'), "Data/Hora": dt, "Médico": m.get('nome'), "Paciente": pac if pac else "LIVRE", "WhatsApp": link, "Status": r['status'], "sort": r['data_hora']})
            df_r = pd.DataFrame(rel).sort_values(by=['Unidade', 'sort'])
            st.data_editor(df_r.drop(columns=['sort']), column_config={"WhatsApp": st.column_config.LinkColumn("📱 Confirmar", display_text="Enviar 🟢"), "Data/Hora": st.column_config.DatetimeColumn(format="DD/MM/YYYY HH:mm")}, use_container_width=True, hide_index=True)

# TELA 5 - CANCELAR OK
elif menu == "5. Cancelar Consulta":
    if verificar_senha():
        st.header("🚫 Cancelar Consulta")
        dados = buscar_todos("CONSULTAS", filtros=[("status", "Marcada")])
        if dados:
            op = {f"{r['paciente_nome']} - {r['data_hora']}": r['id'] for r in dados}
            sel = st.selectbox("Escolha o agendamento:", list(op.keys()))
            if st.button("Confirmar Cancelamento"):
                supabase.table("CONSULTAS").update({"status": "Livre", "paciente_nome": None, "paciente_telefone": None}).eq("id", op[sel]).execute()
                st.success("Cancelada!"); st.rerun()

# TELA 6 - EXCLUIR GRADE (NOME + DATA)
elif menu == "6. Excluir Grade Aberta":
    if verificar_senha():
        st.header("🗑️ Excluir Horários")
        dados = buscar_todos("CONSULTAS", "*, MEDICOS(*)", filtros=[("status", "Livre")])
        if dados:
            df_e = pd.DataFrame([{'id': r['id'], 'info': f"{r['MEDICOS']['nome']} | {pd.to_datetime(r['data_hora']).strftime('%d/%m/%Y %H:%M')}"} for r in dados])
            sel = st.multiselect("Selecione os horários:", df_e['info'].tolist())
            if st.button("Remover Selecionados"):
                ids = df_e[df_e['info'].isin(sel)]['id'].tolist()
                supabase.table("CONSULTAS").delete().in_("id", ids).execute()
                st.success("Removido!"); st.rerun()

# TELA 7 - EXCLUIR MÉDICO (ORDEM ALFABÉTICA)
elif menu == "7. Excluir Cadastro de Médico":
    if verificar_senha():
        st.header("👨‍⚕️ Remover Cadastro")
        meds = buscar_todos("MEDICOS")
        if meds:
            # Ordenação por ordem alfabética no nome
            df_m = pd.DataFrame(meds).sort_values('nome')
            op = {f"{r['nome']} ({r['especialidade']})": r['id'] for idx, r in df_m.iterrows()}
            sel = st.selectbox("Escolha o médico:", list(op.keys()))
            if st.button("EXCLUIR PERMANENTEMENTE"):
                supabase.table("MEDICOS").delete().eq("id", op[sel]).execute()
                st.success("Removido!"); st.rerun()

# TELA 8 - GERENCIAL (VAGAS E AGENDADOS POR DIA)
elif menu == "8. Relatório Gerencial":
    if verificar_senha():
        st.header("📊 Resumo Gerencial")
        dados = buscar_todos("CONSULTAS")
        if dados:
            df = pd.DataFrame(dados)
            df['dia'] = pd.to_datetime(df['data_hora']).dt.date
            resumo = df.groupby('dia').agg(Total_Vagas=('id', 'count'), Agendados=('status', lambda x: (x == 'Marcada').sum())).reset_index()
            st.write("### Ocupação por Dia")
            st.dataframe(resumo.sort_values('dia', ascending=False), use_container_width=True, hide_index=True)
            st.metric("Total Geral de Vagas", len(df))
            st.metric("Total Geral Agendado", len(df[df['status'] == 'Marcada']))
