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
                    e_sel = "Selecione..."
            with c2:
                if e_sel != "Selecione..." and u_sel != "Selecione...":
                    df_f = df_f[df_f['especialidade'] == e_sel]
                    m_sel = st.selectbox("3️⃣ Médico", ["Selecione..."] + sorted(df_f['medico'].unique().tolist()))
                    if m_sel != "Selecione...":
                        df_f = df_f[df_f['medico'] == m_sel]
                        h_sel = st.selectbox("4️⃣ Horário", ["Selecione..."] + df_f['display_horario'].tolist())
                    else:
                        h_sel = "Selecione..."
                else:
                    m_sel = h_sel = "Selecione..."

            if "Selecione" not in f"{u_sel}{e_sel}{m_sel}{h_sel}":
                id_vaga = df_f[df_f['display_horario'] == h_sel].iloc[0]['id']
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
            especialidades = ["Cardiologia", "Clinica", "Dermatologia", "Endocrinologia", "Endocrinologia - Diabete e Tireoide", "Fonoaudiologia", "Ginecologia", "Nefrologia", "Neurologia", "Neuropsicologia", "ODONTOLOGIA", "Oftalmologia", "Ortopedia", "Otorrinolaringologia", "Pediatria", "Pneumologia", "Psicologia", "Psiquiatria", "Urologia"]
            with st.form("f_med"):
                n = st.text_input("Nome do Médico")
                e = st.selectbox("Especialidade", especialidades)
                u = st.selectbox("Unidade", [
                    "Pç 7 Rua Carijos 424 SL 2213", "Pç 7 Rua Rio de Janeiro 462 SL 303", 
                    "Eldorado Av Jose Faria da Rocha 4408 2 and", "Eldorado Av Jose Faria da Rocha 5959"
                ])
                if st.form_submit_button("Salvar Médico"):
                    supabase.table("MEDICOS").insert({"nome": n, "especialidade": e, "unidade": u}).execute()
                    st.success("Médico Cadastrado!")

        elif menu == "2. Abertura de Agenda":
            st.header("🏪 Abertura de Agenda")
            res = supabase.table("MEDICOS").select("*").execute()
            if res.data:
                op = {f"{m['nome']} ({m['especialidade']}) - {m['unidade']}": m['id'] for m in res.data}
                sel = st.selectbox("Selecione o Médico e Unidade", list(op.keys()))
                c1, c2, c3 = st.columns(3)
                d = c1.date_input("Data", format="DD/MM/YYYY")
                h_ini = c2.time_input("Hora de Início", value=dt_lib.time(8, 0))
                h_fim = c3.time_input("Hora Final", value=dt_lib.time(18, 0))
                i = st.number_input("Intervalo (minutos)", 5, 120, 20)
                if st.button("Gerar Grade"):
                    vagas_list = []
                    temp_dt = dt_lib.datetime.combine(d, h_ini)
                    fim_limite = dt_lib.datetime.combine(d, h_fim)
                    while temp_dt < fim_limite:
                        vagas_list.append({"medico_id": op[sel], "data_hora": temp_dt.isoformat(), "status": "Livre"})
                        temp_dt += dt_lib.timedelta(minutes=i)
                    if vagas_list:
                        supabase.table("CONSULTAS").insert(vagas_list).execute()
                        st.success(f"✅ {len(vagas_list)} horários criados!")

        elif menu == "4. Relatório de Agendamentos":
            st.header("📋 Relatório de Consultas")
            res = supabase.table("CONSULTAS").select("*, MEDICOS(*)").execute()
            if res.data:
                relat = []
                for idx, r in enumerate(res.data):
                    m = r.get('MEDICOS') or r.get('medicos') or {}
                    dt = pd.to_datetime(r['data_hora'])
                    pac = f"{r.get('paciente_nome','')} {r.get('paciente_sobrenome','')}".strip()
                    tel = ''.join(filter(str.isdigit, str(r.get('paciente_telefone', ''))))
                    msg = f"Olá, Gentileza Confirmar consulta Dr.(a) {m.get('nome')} / {m.get('especialidade')} / {dt.strftime('%d/%m/%Y %H:%M')} / {m.get('unidade')}"
                    link = f"https://wa.me/55{tel}?text={msg.replace(' ', '%20')}" if tel else None
                    relat.append({"Nº": idx+1, "Data": dt.strftime('%d/%m/%Y %H:%M'), "Médico": m.get('nome'), "Paciente": pac if pac else "Livre", "WhatsApp": link, "sort": r['data_hora']})
                st.data_editor(pd.DataFrame(relat).sort_values(by="sort").drop(columns=["sort"]), column_config={"WhatsApp": st.column_config.LinkColumn("📱 Ação", display_text="Enviar 🟢")}, use_container_width=True, hide_index=True)

        elif menu == "5. Cancelar Consulta":
            st.header("🚫 Cancelar Agendamento")
            res = supabase.table("CONSULTAS").select("*, MEDICOS(*)").eq("status", "Marcada").execute()
            if res.data:
                lista_c = [{'id': r['id'], 'info': f"{r.get('paciente_nome','')} | {pd.to_datetime(r['data_hora']).strftime('%d/%m/%Y %H:%M')}"} for r in res.data]
                df_c = pd.DataFrame(lista_c)
                sel = st.selectbox("Selecione para cancelar:", ["Selecione..."] + df_c['info'].tolist())
                if sel != "Selecione..." and st.button("Confirmar Cancelamento"):
                    id_v = df_c[df_c['info'] == sel].iloc[0]['id']
                    supabase.table("CONSULTAS").update({"paciente_nome":None, "paciente_sobrenome":None, "paciente_telefone":None, "status":"Livre"}).eq("id", id_v).execute()
                    st.success("Cancelado!"); st.rerun()

        elif menu == "6. Excluir Grade Aberta":
            st.header("🗑️ Excluir Horários Livres")
            res = supabase.table("CONSULTAS").select("*, MEDICOS(*)").eq("status", "Livre").execute()
            if res.data:
                df_e = pd.DataFrame([{'id': r['id'], 'info': f"{pd.to_datetime(r['data_hora']).strftime('%d/%m/%Y %H:%M')} - {r['MEDICOS']['nome']}"} for r in res.data])
                sel_e = st.multiselect("Selecione:", df_e['info'].tolist())
                if st.button("Excluir"):
                    ids_e = df_e[df_e['info'].isin(sel_e)]['id'].tolist()
                    supabase.table("CONSULTAS").delete().in_("id", ids_e).execute()
                    st.success("Excluído!"); st.rerun()

        elif menu == "7. Excluir Cadastro de Médico":
            st.header("👨‍⚕️ Excluir Médico")
            res_m = supabase.table("MEDICOS").select("*").execute()
            if res_m.data:
                lista_m = {f"{m['nome']} ({m['especialidade']})": m['id'] for m in res_m.data}
                sel_m = st.selectbox("Médico:", ["Selecione..."] + list(lista_m.keys()))
                if sel_m != "Selecione..." and st.button("EXCLUIR PERMANENTEMENTE"):
                    id_med = lista_m[sel_m]
                    supabase.table("CONSULTAS").delete().eq("medico_id", id_med).execute()
                    supabase.table("MEDICOS").delete().eq("id", id_med).execute()
                    st.success("Médico removido!"); st.rerun()

        elif menu == "8. Relatório Gerencial":
            st.header("📊 Relatório Gerencial de Performance")
            
            # 1. PEGAR DADOS
            res_cons = supabase.table("CONSULTAS").select("*, MEDICOS(*)").execute()
            res_meds = supabase.table("MEDICOS").select("*").execute()
            
            if res_cons.data:
                df = pd.DataFrame(res_cons.data)
                df['data_dt'] = pd.to_datetime(df['data_hora']).dt.date
                
                # FILTRO DE DATA
                c1, c2 = st.columns(2)
                d_ini = c1.date_input("De:", df['data_dt'].min())
                d_fim = c2.date_input("Até:", df['data_dt'].max())
                
                df_filt = df[(df['data_dt'] >= d_ini) & (df['data_dt'] <= d_fim)]
                
                # --- MÉTRICAS ---
                agendadas = df_filt[df_filt['status'] == 'Marcada']
                livres = df_filt[df_filt['status'] == 'Livre']
                
                col1, col2, col3 = st.columns(3)
                col1.metric("Consultas Agendadas", len(agendadas))
                col2.metric("Vagas Livres (Previstas)", len(livres))
                col3.metric("Total de Vagas Criadas", len(df_filt))
                
                st.divider()
                
                # --- AGENDADAS POR DATA ---
                st.subheader("📅 Consultas Agendadas por Data")
                if not agendadas.empty:
                    df_agg = agendadas.groupby('data_dt').size().reset_index(name='Quantidade')
                    df_agg.columns = ['Data', 'Total Agendado']
                    st.line_chart(df_agg.set_index('Data'))
                    st.table(df_agg)
                else: st.info("Sem consultas marcadas no período.")
                
                # --- MÉDICOS SEM AGENDA ---
                st.divider()
                st.subheader("⚠️ Médicos SEM Agendas Abertas (neste período)")
                medicos_com_agenda = df_filt['medico_id'].unique()
                meds_sem_agenda = [m for m in res_meds.data if m['id'] not in medicos_com_agenda]
                
                if meds_sem_agenda:
                    df_sem = pd.DataFrame(meds_sem_agenda)[['nome', 'especialidade', 'unidade']]
                    df_sem.columns = ['Médico', 'Especialidade', 'Unidade']
                    st.warning(f"Existem {len(meds_sem_agenda)} médicos sem horários configurados.")
                    st.dataframe(df_sem, use_container_width=True, hide_index=True)
                else: st.success("Todos os médicos possuem horários configurados!")
            else: st.info("Não há dados para gerar o relatório.")
