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

# FUNÇÃO DE PAGINAÇÃO
def buscar_todos(tabela, select_str="*", filtros=None):
    page_size = 1000
    offset = 0
    dados = []
    while True:
        query = supabase.table(tabela).select(select_str).range(offset, offset + page_size - 1)
        if filtros:
            for f in filtros: query = query.eq(f[0], f[1])
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
    if "autenticado" not in st.session_state: st.session_state["autenticado"] = False
    if not st.session_state["autenticado"]:
        st.subheader("🔒 Área Restrita")
        senha_digitada = st.text_input("Senha Administrativa:", type="password", key="pwd_main")
        if st.button("Liberar Acesso"):
            if senha_digitada == SENHA_ACESSO:
                st.session_state["autenticado"] = True
                st.rerun()
            else: st.error("Senha incorreta!")
        return False
    return True

# --- 3. LÓGICA DAS TELAS ---


# TELA 1 - CADASTRO (ATUALIZADA COM TODAS AS ESPECIALIDADES)
if menu == "1. Cadastro de Médicos":
    if verificar_senha():
        st.header("👨‍⚕️ Cadastro de Médicos")
        with st.form("f_med"):
            n = st.text_input("Nome do Médico")
            
            # LISTA COMPLETA E ATUALIZADA (LINHA 64)
            lista_especialidades = sorted([
                "Cardiologia", "Clinica", "Dermatologia", "Endocrinologia", 
                "Endocrinologia - Diabete e Tireoide", "Fonoaudiologia", "Ginecologia", 
                "Nefrologia", "Neurologia", "Neuropsicologia", "Nutricionista", 
                "ODONTOLOGIA", "Oftalmologia", "Ortopedia", "Otorrinolaringologia", 
                "Pediatria", "Pneumologia", "Psicologia", "Psiquiatria", "Urologia"
            ])
            
            e = st.selectbox("Especialidade", lista_especialidades)
            
            u = st.selectbox("Unidade", [
                "Pç 7 Rua Carijos 424 SL 2213", 
                "Pç 7 Rua Rio de Janeiro 462 SL 303", 
                "Eldorado Av Jose Faria da Rocha 4408 2 and"
            ])
            
            if st.form_submit_button("Salvar"):
                if n:
                    supabase.table("MEDICOS").insert({
                        "nome": n.upper(), 
                        "especialidade": e, 
                        "unidade": u
                    }).execute()
                    st.success(f"Médico {n.upper()} cadastrado com sucesso!")
                else:
                    st.error("Por favor, digite o nome do médico.")



# TELA 2 - ABERTURA (AJUSTE FINO: ORDEM ALFABÉTICA)
elif menu == "2. Abertura de Agenda":
    if verificar_senha():
        st.header("🏪 Abertura de Agenda")
        medicos = buscar_todos("MEDICOS")
        if medicos:
            df_meds = pd.DataFrame(medicos)
            
            # 1. Seleciona a Unidade
            u_filtro = st.selectbox("Selecione a Unidade para filtrar médicos:", sorted(df_meds['unidade'].unique().tolist()))
            
            # 2. Filtra e Ordena os médicos por nome (A-Z)
            df_filtrado = df_meds[df_meds['unidade'] == u_filtro].sort_values(by='nome')
            
            # 3. Monta as opções já ordenadas
            op = {f"{m['nome']} ({m['especialidade']})": m['id'] for _, m in df_filtrado.iterrows()}
            
            sel = st.selectbox("Médico Disponível nesta Unidade (Ordem Alfabética)", list(op.keys()))
            
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
                st.success(f"✅ Grade criada com sucesso!")




# TELA 3 - MARCAR CONSULTA (MOSTRA TODOS MÉDICOS)

elif menu == "3. Marcar Consulta":
    st.header("📅 Agendamento de Consultas")

    if "bloqueio" not in st.session_state:
        st.session_state.bloqueio = False

    # 🔹 1️⃣ BUSCA TODOS OS MÉDICOS
    medicos_res = supabase.table("MEDICOS").select("*").execute()
    medicos = medicos_res.data

    if medicos:

        df_med = pd.DataFrame(medicos)

        # 1. Unidade
        u_sel = st.selectbox(
            "1. Escolha a Unidade",
            sorted(df_med['unidade'].unique())
        )
        df_u = df_med[df_med['unidade'] == u_sel]

        # 2. Especialidade
        esp_sel = st.selectbox(
            "2. Escolha a Especialidade",
            sorted(df_u['especialidade'].unique())
        )
        df_esp = df_u[df_u['especialidade'] == esp_sel]

        # 3. Médico
        m_sel = st.selectbox(
            "3. Escolha o Médico",
            sorted(df_esp['nome'].unique())
        )

        medico_id = df_esp[df_esp['nome'] == m_sel].iloc[0]['id']

        # 🔹 2️⃣ BUSCA HORÁRIOS LIVRES APENAS DO MÉDICO SELECIONADO
        consultas_res = supabase.table("CONSULTAS") \
            .select("*") \
            .eq("medico_id", medico_id) \
            .eq("status", "Livre") \
            .order("data_hora") \
            .execute()

        consultas = consultas_res.data

        if consultas:

            horarios = []
            for c in consultas:
                dt = pd.to_datetime(c['data_hora'])
                horarios.append({
                    "id": c['id'],
                    "display": dt.strftime('%d/%m/%Y %H:%M')
                })

            df_h = pd.DataFrame(horarios)

            h_sel = st.selectbox(
                "4. Escolha o Horário",
                df_h['display'].tolist()
            )

            id_vaga = df_h[df_h['display'] == h_sel].iloc[0]['id']

            with st.form("form_paciente", clear_on_submit=True):

                c1, c2 = st.columns(2)
                pn = c1.text_input("Nome")
                ps = c1.text_input("Sobrenome")
                pt = c2.text_input("WhatsApp")
                pc = c2.text_input("Convênio")

                submit = st.form_submit_button("Finalizar Agendamento")

                if submit:

                    if st.session_state.bloqueio:
                        st.warning("⏳ Processando...")
                        st.stop()

                    if pn and pt:

                        st.session_state.bloqueio = True

                        resposta = supabase.table("CONSULTAS") \
                            .update({
                                "paciente_nome": pn,
                                "paciente_sobrenome": ps,
                                "paciente_telefone": pt,
                                "paciente_convenio": pc,
                                "status": "Marcada"
                            }) \
                            .eq("id", id_vaga) \
                            .eq("status", "Livre") \
                            .execute()

                        if resposta.data and len(resposta.data) > 0:
                            st.success("✅ Agendada com sucesso!")
                            st.session_state.bloqueio = False
                            st.rerun()
                        else:
                            st.session_state.bloqueio = False
                            st.error("⚠️ Horário ocupado. Escolha outro.")
                            st.rerun()
                    else:
                        st.warning("⚠️ Nome e WhatsApp são obrigatórios!")

        else:
            st.info("Este médico não possui horários livres no momento.")

    else:
        st.error("Nenhum médico cadastrado.")









# TELA 5 - CANCELAR CONSULTA
elif menu == "5. Cancelar Consulta":
    if verificar_senha():
        st.header("🚫 Cancelar Consulta")
        dados = buscar_todos("CONSULTAS", filtros=[("status", "Marcada")])
        if dados:
            op = {f"{r['paciente_nome']} | {r['data_hora']}": r['id'] for r in dados}
            sel = st.selectbox("Selecione o agendamento para cancelar:", list(op.keys()))
            if st.button("Confirmar Cancelamento"):
                supabase.table("CONSULTAS").update({"status": "Livre", "paciente_nome": None, "paciente_telefone": None}).eq("id", op[sel]).execute()
                st.success("Cancelado!"); st.rerun()



# TELA 6 - EXCLUIR GRADE ABERTA (AJUSTE: NOME + DATA + UNIDADE)
elif menu == "6. Excluir Grade Aberta":
    if verificar_senha():
        st.header("🗑️ Remover Horários Livres (Futuro)")
        
        # Puxa as vagas livres com os dados dos médicos
        dados = buscar_todos("CONSULTAS", "*, MEDICOS(*)", filtros=[("status", "Livre")])
        
        if dados:
            agora = dt_lib.datetime.now().replace(tzinfo=None)
            lista_futura = []
            
            for r in dados:
                dt_vaga = pd.to_datetime(r['data_hora']).replace(tzinfo=None)
                
                # Filtro para mostrar apenas o que for de agora para frente
                if dt_vaga >= agora:
                    m = r.get('MEDICOS') or r.get('medicos') or {}
                    m_nome = m.get('nome', 'Médico N/I')
                    m_unidade = m.get('unidade', 'Unidade N/I')
                    
                    # Formatação solicitada: NOME | DATA HORÁRIO | UNIDADE
                    texto_exibicao = f"{m_nome} | {dt_vaga.strftime('%d/%m/%Y %H:%M')} | {m_unidade}"
                    
                    lista_futura.append({
                        'id': r['id'], 
                        'info': texto_exibicao
                    })
            
            if lista_futura:
                df_ex = pd.DataFrame(lista_futura)
                # O multiselect agora mostrará o nome, data e a unidade à direita
                sel = st.multiselect("Selecione os horários para remover:", df_ex['info'].tolist())
                
                if st.button("Excluir Horários Selecionados"):
                    ids_para_excluir = df_ex[df_ex['info'].isin(sel)]['id'].tolist()
                    if ids_para_excluir:
                        supabase.table("CONSULTAS").delete().in_("id", ids_para_excluir).execute()
                        st.success(f"✅ Removido com sucesso!")
                        st.rerun()
            else:
                st.info("Não há horários livres futuros para exibir.")
        else:
            st.info("Nenhuma grade aberta encontrada.")



# TELA 7 - EXCLUIR CADASTRO DE MÉDICO (CORRIGIDA COM BUSCA TOTAL)
elif menu == "7. Excluir Cadastro de Médico":
    if verificar_senha():
        st.header("👨‍⚕️ Remover Cadastro de Médico")
        
        # AJUSTE FINO: Usando a função de paginação para garantir que busque TODOS os médicos
        meds = buscar_todos("MEDICOS")
        
        if meds:
            # Transformando em DataFrame para ordenar de A a Z por nome
            df_m = pd.DataFrame(meds).sort_values('nome')
            
            # Criando o dicionário de opções para o seletor
            op = {f"{r['nome']} ({r['especialidade']}) - {r['unidade']}": r['id'] for _, r in df_m.iterrows()}
            
            sel = st.selectbox("Escolha o médico para remover permanentemente:", list(op.keys()))
            
            st.warning(f"⚠️ Atenção: Ao excluir o cadastro de {sel}, você não poderá reverter esta ação.")
            
            if st.button("CONFIRMAR EXCLUSÃO PERMANENTE"):
                try:
                    supabase.table("MEDICOS").delete().eq("id", op[sel]).execute()
                    st.success(f"O cadastro de {sel} foi removido com sucesso!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao excluir: {e}")
        else:
            st.info("Não foram encontrados médicos cadastrados no banco de dados.")





# =========================================================
# TELA 8 - RELATÓRIO GERENCIAL (FOCO EM DATAS FUTURAS)
# CORRIGIDO NOS INDICADORES
# =========================================================

elif menu == "8. Relatório Gerencial":

    if verificar_senha():

        st.header("📊 Resumo de Ocupação por Dia")

        dados_consultas = buscar_todos("CONSULTAS")
        dados_medicos = buscar_todos("MEDICOS")

        if dados_consultas:

            df = pd.DataFrame(dados_consultas)

            # 🔒 Segurança de dados
            df = df[df['data_hora'].notna()].copy()
            df['data_dt'] = pd.to_datetime(df['data_hora'], errors='coerce').dt.date
            df = df[df['data_dt'].notna()]

            hoje_dt = dt_lib.datetime.now().date()
            ontem_dt = hoje_dt - dt_lib.timedelta(days=1)
            ante_dt = hoje_dt - dt_lib.timedelta(days=2)

            # =========================================================
            # 🔹 RESUMO COMPLETO CORRIGIDO
            # =========================================================

            resumo_completo = (
                df.groupby('data_dt')
                .agg(
                    Total_Vagas=('id', 'count'),
                    Agendados=('status', lambda x: (x == 'Marcada').sum())
                )
                .reset_index()
            )

            # =========================================================
            # 🔹 PARTE 1 - TABELA FUTURA (INALTERADA VISUALMENTE)
            # =========================================================

            resumo_futuro = resumo_completo[resumo_completo['data_dt'] >= hoje_dt].copy()
            resumo_futuro = resumo_futuro.sort_values('data_dt', ascending=True)
            resumo_futuro['Data'] = resumo_futuro['data_dt'].apply(lambda x: x.strftime('%d/%m/%Y'))

            st.write("### Ocupação Diária (Hoje e Futuro)")

            if not resumo_futuro.empty:
                st.dataframe(
                    resumo_futuro[['Data', 'Total_Vagas', 'Agendados']],
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.info("Não há grades abertas para datas futuras.")

            # =========================================================
            # 🔹 PARTE 2 - MÉDICOS SEM GRADE FUTURA (INALTERADO)
            # =========================================================

            st.divider()
            st.subheader("⚠️ Médicos sem Grade Aberta (Futuro)")

            if dados_medicos:

                df_meds = pd.DataFrame(dados_medicos)
                df_futuro_consultas = df[df['data_dt'] >= hoje_dt]
                ids_com_grade = df_futuro_consultas['medico_id'].unique()
                meds_sem_grade = df_meds[~df_meds['id'].isin(ids_com_grade)]

                if not meds_sem_grade.empty:
                    meds_sem_grade = meds_sem_grade.sort_values('nome')
                    st.dataframe(
                        meds_sem_grade[['nome', 'especialidade', 'unidade']],
                        use_container_width=True,
                        hide_index=True
                    )
                else:
                    st.success("✅ Todos os médicos possuem grades futuras.")

            # =========================================================
            # 🔹 PARTE 3 - INDICADORES CORRIGIDOS
            # =========================================================

            st.divider()
            st.subheader("📈 Comparativo de Desempenho")

            def get_agendados(data):
                filtro = df[df['data_dt'] == data]
                return int((filtro['status'] == 'Marcada').sum())

            def get_vagas(data):
                filtro = df[df['data_dt'] == data]
                return int(len(filtro))

            # 🔹 PACIENTES AGENDADOS
            st.write("**Pacientes Agendados:**")
            a1, a2, a3 = st.columns(3)

            a1.metric(f"Hoje ({hoje_dt.strftime('%d/%m')})", get_agendados(hoje_dt))
            a2.metric(f"Ontem ({ontem_dt.strftime('%d/%m')})", get_agendados(ontem_dt))
            a3.metric(f"Anteontem ({ante_dt.strftime('%d/%m')})", get_agendados(ante_dt))

            # 🔹 GRADES ABERTAS
            st.write("**Grades Abertas (Total):**")
            g1, g2, g3 = st.columns(3)

            g1.metric(f"Hoje ({hoje_dt.strftime('%d/%m')})", get_vagas(hoje_dt))
            g2.metric(f"Ontem ({ontem_dt.strftime('%d/%m')})", get_vagas(ontem_dt))
            g3.metric(f"Anteontem ({ante_dt.strftime('%d/%m')})", get_vagas(ante_dt))

            # =========================================================
            # 🔹 TOTAL GERAL (INALTERADO VISUAL)
            # =========================================================

            st.divider()
            c1, c2 = st.columns(2)

            c1.metric("Total Geral de Vagas (Sistema)", len(df))
            c2.metric("Total Geral Agendado", len(df[df['status'] == 'Marcada']))
