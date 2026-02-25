import streamlit as st
import pandas as pd
import datetime as dt_lib
from supabase import create_client

# ==============================
# CONFIGURAÇÕES INICIAIS
# ==============================
st.set_page_config(page_title="Clínica Sempre Vida", layout="wide")

url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

SENHA_ACESSO = "8484"

# ==============================
# FUNÇÃO GLOBAL PARA BUSCAR TODOS REGISTROS (REMOVE LIMITE 1000)
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


# ==============================
# CACHE DE DADOS
# ==============================
@st.cache_data(ttl=60)
def carregar_consultas():
    return buscar_todos("CONSULTAS", "*, MEDICOS(*)")

@st.cache_data(ttl=60)
def carregar_medicos():
    return buscar_todos("MEDICOS")


# ==============================
# MENU
# ==============================
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


# ==============================
# AUTENTICAÇÃO
# ==============================
def verificar_senha():
    if "autenticado" not in st.session_state:
        st.session_state["autenticado"] = False

    if not st.session_state["autenticado"]:
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


# ==============================
# TELA 3 - MARCAR CONSULTA
# ==============================
if menu == "3. Marcar Consulta":

    st.header("📅 Agendamento de Consultas")

    dados = buscar_todos("CONSULTAS", "*, MEDICOS(*)", filtros=[("status", "Livre")])

    if dados:

        vagas_limpas = []

        for r in dados:
            m = r.get('MEDICOS') or r.get('medicos')
            if m:
                dt = pd.to_datetime(r['data_hora'])
                vagas_limpas.append({
                    'id': r['id'],
                    'unidade': m.get('unidade'),
                    'especialidade': m.get('especialidade'),
                    'medico': m.get('nome'),
                    'display_horario': dt.strftime('%d/%m/%Y às %H:%M'),
                    'sort': r['data_hora']
                })

        df_f = pd.DataFrame(vagas_limpas).sort_values(by='sort')

        c1, c2 = st.columns(2)

        with c1:
            u_sel = st.selectbox("Unidade", sorted(df_f['unidade'].unique()))

        with c2:
            df_u = df_f[df_f['unidade'] == u_sel]
            e_sel = st.selectbox("Especialidade", sorted(df_u['especialidade'].unique()))

        df_e = df_u[df_u['especialidade'] == e_sel]
        m_sel = st.selectbox("Médico", sorted(df_e['medico'].unique()))

        df_m = df_e[df_e['medico'] == m_sel]
        h_sel = st.selectbox("Horário", df_m['display_horario'].tolist())

        id_vaga = df_m[df_m['display_horario'] == h_sel].iloc[0]['id']

        with st.form("form_agendar"):
            pn = st.text_input("Nome")
            ps = st.text_input("Sobrenome")
            pt = st.text_input("WhatsApp")
            pc = st.text_input("Convênio")

            if st.form_submit_button("Confirmar Agendamento"):
                if pn and pt:
                    supabase.table("CONSULTAS").update({
                        "paciente_nome": pn,
                        "paciente_sobrenome": ps,
                        "paciente_telefone": pt,
                        "paciente_convenio": pc,
                        "status": "Marcada"
                    }).eq("id", id_vaga).execute()

                    st.cache_data.clear()
                    st.success("Agendado com sucesso!")
                    st.rerun()
                else:
                    st.error("Preencha Nome e WhatsApp")

    else:
        st.info("Nenhuma vaga disponível.")


# ==============================
# TELAS ADMINISTRATIVAS
# ==============================
else:

    if verificar_senha():

        if menu == "1. Cadastro de Médicos":
            st.header("Cadastro de Médicos")

            with st.form("f_med"):
                n = st.text_input("Nome")
                e = st.text_input("Especialidade")
                u = st.text_input("Unidade")

                if st.form_submit_button("Salvar"):
                    supabase.table("MEDICOS").insert({
                        "nome": n,
                        "especialidade": e,
                        "unidade": u
                    }).execute()

                    st.cache_data.clear()
                    st.success("Médico cadastrado!")
                    st.rerun()


        elif menu == "2. Abertura de Agenda":
            st.header("Abertura de Agenda")

            medicos = carregar_medicos()

            if medicos:
                op = {f"{m['nome']} ({m['especialidade']})": m['id'] for m in medicos}
                sel = st.selectbox("Selecione o Médico", list(op.keys()))

                c1, c2, c3 = st.columns(3)

                d = c1.date_input("Data")
                h_ini = c2.time_input("Hora Início", value=dt_lib.time(8, 0))
                h_fim = c3.time_input("Hora Final", value=dt_lib.time(18, 0))

                intervalo = st.number_input("Intervalo (min)", 5, 120, 20)

                if st.button("Gerar Grade"):

                    vagas_list = []
                    temp_dt = dt_lib.datetime.combine(d, h_ini)
                    fim_limite = dt_lib.datetime.combine(d, h_fim)

                    while temp_dt < fim_limite:
                        vagas_list.append({
                            "medico_id": op[sel],
                            "data_hora": temp_dt.isoformat(),
                            "status": "Livre"
                        })
                        temp_dt += dt_lib.timedelta(minutes=intervalo)

                    if vagas_list:
                        supabase.table("CONSULTAS").insert(vagas_list).execute()
                        st.cache_data.clear()
                        st.success(f"{len(vagas_list)} horários criados!")
                        st.rerun()


        elif menu == "4. Relatório de Agendamentos":

            st.header("Relatório")

            dados = carregar_consultas()

            if dados:
                df = pd.DataFrame(dados)
                st.dataframe(df, use_container_width=True)
            else:
                st.info("Sem dados.")


        elif menu == "8. Relatório Gerencial":

            st.header("Relatório Gerencial")

            dados = carregar_consultas()

            if dados:
                df = pd.DataFrame(dados)
                df['data_dt'] = pd.to_datetime(df['data_hora']).dt.date

                agendadas = df[df['status'] == 'Marcada']
                livres = df[df['status'] == 'Livre']

                col1, col2, col3 = st.columns(3)
                col1.metric("Agendadas", len(agendadas))
                col2.metric("Livres", len(livres))
                col3.metric("Total", len(df))

            else:
                st.info("Sem dados.")
