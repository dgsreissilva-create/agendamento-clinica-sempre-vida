import streamlit as st
import pandas as pd
import datetime as dt_lib
from supabase import create_client

# --- 1. CONFIGURAÇÕES INICIAIS ---
# Certifique-se de que SUPABASE_URL e SUPABASE_KEY estão corretos no seu Secrets
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

if menu == "3. Marcar Consulta":
    st.header("📅 Agendamento de Consultas")
    try:
        # Aumentamos o limite para 5000 para garantir que pegue todas as grades
        res_vagas = supabase.table("CONSULTAS").select("*, MEDICOS(*)").eq("status", "Livre").limit(5000).execute()
        
        if res_vagas.data:
            vagas_limpas = []
            for r in res_vagas.data:
                m = r.get('MEDICOS') or r.get('medicos')
                if m:
                    dt = pd.to_datetime(r['data_hora'])
                    vagas_limpas.append({
                        'id': r['id'], 
                        'unidade': str(m.get('unidade', 'N/I')).strip(),
                        'especialidade': str(m.get('especialidade', 'N/I')).strip().upper(),
                        'medico': str(m.get('nome', 'N/I')).strip(),
                        'display_horario': dt.strftime('%d/%m/%Y às %H:%M'),
                        'sort': r['data_hora']
                    })
            df_f = pd.DataFrame(vagas_limpas).sort_values(by='sort')

            c1, c2 = st.columns(2)
            with c1:
                u_sel = st.selectbox("1️⃣ Unidade", ["Selecione..."] + sorted(df_f['unidade'].unique().tolist()))
                if u_sel != "Selecione...":
                    df_u = df_f[df_f['unidade'] == u_sel]
                    e_sel = st.selectbox("2️⃣ Especialidade", ["Selecione..."] + sorted(df_u['especialidade'].unique().tolist()))
                else: e_sel = "Selecione..."

            with c2:
                if e_sel != "Selecione..." and u_sel != "Selecione...":
                    df_e = df_u[df_u['especialidade'] == e_sel]
                    m_sel = st.selectbox("3️⃣ Médico", ["Selecione..."] + sorted(df_e['medico'].unique().tolist()))
                    if m_sel != "Selecione...":
                        df_m = df_e[df_e['medico'] == m_sel]
                        h_sel = st.selectbox("4️⃣ Horário", ["Selecione..."] + df_m['display_horario'].tolist())
                    else: h_sel = "Selecione..."
                else: m_sel = h_sel = "Selecione..."

            if "Selecione" not in f"{u_sel}{e_sel}{m_sel}{h_sel}":
                id_vaga = df_m[df_m['display_horario'] == h_sel].iloc[0]['id']
                with st.form("form_agendar"):
                    f1, f2 = st.columns(2)
                    pn, ps = f1.text_input("Nome"), f1.text_input("Sobrenome")
                    pt, pc = f2.text_input("WhatsApp"), f2.text_input("Convênio")
                    if st.form_submit_button("Confirmar Agendamento"):
                        if pn and pt:
                            supabase.table("CONSULTAS").update({"paciente_nome": pn, "paciente_sobrenome": ps, "paciente_telefone": pt, "paciente_convenio": pc, "status": "Marcada"}).eq("id", id_vaga).execute()
                            st.success("✅ Agendado!"); st.balloons()
                        else: st.error("Preencha Nome e WhatsApp.")
        else:
            st.info("Nenhuma vaga livre encontrada no banco de dados.")
    except Exception as e:
        st.error(f"Erro ao carregar agendamentos: {e}")

else:
    if verificar_senha():
        if st.sidebar.button("🔒 Sair do Painel Adm"):
            st.session_state["autenticado"] = False
            st.rerun()

        if menu == "1. Cadastro de Médicos":
            st.header("👨‍⚕️ Cadastro")
            esp_opcoes = ["CARDIOLOGIA", "CLINICA", "DERMATOLOGIA", "ENDOCRINOLOGIA", "FONOAUDIOLOGIA", "GINECOLOGIA", "NEFROLOGIA", "NEUROLOGIA", "NUTRICIONISTA", "ODONTOLOGIA", "OFTALMOLOGIA", "ORTOPEDIA", "OTORRINOLARINGOLOGIA", "PEDIATRIA", "PNEUMOLOGIA", "PSICOLOGIA", "PSIQUIATRIA", "UROLOGIA"]
            with st.form("f_med"):
                n = st.text_input("Nome do Médico")
                e = st.selectbox("Especialidade", sorted(esp_opcoes))
                u = st.selectbox("Unidade", ["Pç 7 Rua Carijos 424 SL 2213", "Pç 7 Rua Rio de Janeiro 462 SL 303", "Eldorado Av Jose Faria da Rocha 4408 2 and", "Eldorado Av Jose Faria da Rocha 5959"])
                if st.form_submit_button("Salvar Médico"):
                    try:
                        supabase.table("MEDICOS").insert({"nome": n, "especialidade": e, "unidade": u}).execute()
                        st.success("Médico Cadastrado!")
                    except Exception as err:
                        st.error(f"Erro ao cadastrar médico: {err}")

        elif menu == "2. Abertura de Agenda":
            st.header("🏪 Abertura de Agenda")
            res_m = supabase.table("MEDICOS").select("*").execute()
            if res_m.data:
                # Mapeamento do médico para o ID
                op = {f"{m['nome']} ({m['especialidade']})": m['id'] for m in res_m.data}
                sel = st.selectbox("Selecione o Médico", list(op.keys()))
                c1, c2, c3 = st.columns(3)
                d = c1.date_input("Data", format="DD/MM/YYYY")
                h_i = c2.time_input("Início", value=dt_lib.time(8, 0))
                h_f = c3.time_input("Final", value=dt_lib.time(18, 0))
                i = st.number_input("Intervalo (min)", 5, 120, 20)
                
                if st.button("Gerar Grade agora"):
                    vagas = []
                    t = dt_lib.datetime.combine(d, h_i)
                    f = dt_lib.datetime.combine(d, h_f)
                    id_medico = op[sel]
                    
                    while t < f:
                        vagas.append({"medico_id": id_medico, "data_hora": t.isoformat(), "status": "Livre"})
                        t += dt_lib.timedelta(minutes=i)
                    
                    try:
                        # Tenta inserir e força o retorno dos dados
                        resultado = supabase.table("CONSULTAS").insert(vagas).execute()
                        if resultado.data:
                            st.success(f"✅ SUCESSO! {len(vagas)} horários criados para {sel}.")
                            st.balloons()
                        else:
                            st.error("O banco não retornou erro, mas também não gravou os dados. Verifique as colunas.")
                    except Exception as e_db:
                        st.error(f"❌ ERRO AO GRAVAR NO BANCO: {e_db}")
                        st.info("Verifique se na tabela CONSULTAS a coluna chama 'medico_id' (com o tipo igual ao ID da tabela médicos).")
            else:
                st.warning("Nenhum médico encontrado no cadastro.")

        elif menu == "4. Relatório de Agendamentos":
            st.header("📋 Relatório Completo")
            # Puxamos tudo (Livre e Marcado) para conferência
            res = supabase.table("CONSULTAS").select("*, MEDICOS(*)").limit(5000).execute()
            if res.data:
                rel = []
                for idx, r in enumerate(res.data):
                    m = r.get('MEDICOS') or r.get('medicos') or {}
                    dt = pd.to_datetime(r['data_hora'])
                    pac = f"{r.get('paciente_nome','')} {r.get('paciente_sobrenome','')}".strip()
                    rel.append({
                        "Nº": idx+1, "Status": r['status'], "Data": dt.strftime('%d/%m/%Y %H:%M'), 
                        "Médico": m.get('nome', 'N/I'), "Unidade": m.get('unidade', '-'), "sort": r['data_hora']
                    })
                df_rel = pd.DataFrame(rel).sort_values(by="sort", ascending=False)
                st.dataframe(df_rel.drop(columns=["sort"]), use_container_width=True)
            else: st.info("Nenhum dado na tabela CONSULTAS.")

        elif menu == "5. Cancelar Consulta":
            st.header("🚫 Cancelar")
            res = supabase.table("CONSULTAS").select("*, MEDICOS(*)").eq("status", "Marcada").execute()
            if res.data:
                df_c = pd.DataFrame([{'id': r['id'], 'info': f"{r['paciente_nome']} | {r['data_hora']}"} for r in res.data])
                sel = st.selectbox("Escolha:", df_c['info'])
                if st.button("Confirmar"):
                    supabase.table("CONSULTAS").update({"status": "Livre", "paciente_nome": None, "paciente_sobrenome":None, "paciente_telefone":None}).eq("id", df_c[df_c['info']==sel].iloc[0]['id']).execute()
                    st.rerun()

        elif menu == "6. Excluir Grade Aberta":
            st.header("🗑️ Excluir")
            res = supabase.table("CONSULTAS").select("*, MEDICOS(*)").eq("status", "Livre").execute()
            if res.data:
                df_e = pd.DataFrame([{'id': r['id'], 'info': f"{r['data_hora']} - {r['MEDICOS']['nome']}"} for r in res.data])
                sel = st.multiselect("Selecione:", df_e['info'])
                if st.button("Excluir Permanente"):
                    ids = df_e[df_e['info'].isin(sel)]['id'].tolist()
                    supabase.table("CONSULTAS").delete().in_("id", ids).execute()
                    st.rerun()

        elif menu == "7. Excluir Cadastro de Médico":
            st.header("👨‍⚕️ Excluir Médico")
            res_m = supabase.table("MEDICOS").select("*").execute()
            if res_m.data:
                lista_m = {f"{m['nome']} ({m['especialidade']})": m['id'] for m in res_m.data}
                sel_m = st.selectbox("Médico:", ["Selecione..."] + list(lista_m.keys()))
                if sel_m != "Selecione..." and st.button("EXCLUIR"):
                    id_med = lista_m[sel_m]
                    supabase.table("CONSULTAS").delete().eq("medico_id", id_med).execute()
                    supabase.table("MEDICOS").delete().eq("id", id_med).execute()
                    st.rerun()

        elif menu == "8. Relatório Gerencial":
            st.header("📊 Gerencial")
            res_cons = supabase.table("CONSULTAS").select("*, MEDICOS(*)").execute()
            if res_cons.data:
                df = pd.DataFrame(res_cons.data)
                df['data_dt'] = pd.to_datetime(df['data_hora']).dt.date
                c1, c2 = st.columns(2)
                d_i, d_f = c1.date_input("De:", df['data_dt'].min()), c2.date_input("Até:", df['data_dt'].max())
                df_f = df[(df['data_dt'] >= d_i) & (df['data_dt'] <= d_f)]
                col1, col2 = st.columns(2)
                col1.metric("Agendadas", len(df_f[df_f['status'] == 'Marcada']))
                col2.metric("Livres", len(df_f[df_f['status'] == 'Livre']))
