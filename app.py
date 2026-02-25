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
                            supabase.table("CONSULTAS").update({"paciente_nome": pn, "paciente_sobrenome": ps, "paciente_telefone": pt, "paciente_convenio": pc, "status": "Marcada"}).eq("id", id_vaga).execute()
                            st.success("✅ Agendado!")
                            st.balloons()
        else:
            st.info("Nenhum horário livre no momento.")
    except Exception as e:
        st.error(f"Erro: {e}")

# TELAS ADMINISTRATIVAS (PROTEGIDAS)
else:
    if verificar_senha():
        if st.sidebar.button("🔒 Sair do Painel Adm"):
            st.session_state["autenticado"] = False
            st.rerun()

        if menu == "1. Cadastro de Médicos":
            st.header("👨‍⚕️ Cadastro de Médicos")
            especialidades = ["Cardiologia", "Clinica", "Dermatologia", "Endocrinologia", "Endocrinologia - Diabete e Tireoide", "Fonoaudiologia", "Ginecologia", "Nefrologia", "Neurologia", "Neuropsicologia", "ODONTOLOGIA", "Oftalmologia", "Ortopedia", "Otorrinolaringologia", "Pediatria", "Pneumologia", "Psicologia"]
            with st.form("f_med"):
                n = st.text_input("Nome do Médico")
                e = st.selectbox("Especialidade", especialidades)
                u = st.selectbox("Unidade", ["Praça 7 - Rua Carijos 424 - SALA 2213", "Praça 7 - Rua Rio de Janeiro 462 - SALA 303", "Eldorado - Av. Jose Faria da Rocha 4408 - 2 andar", "Eldorado - Av. Jose Faria da Rocha 5959"])
                if st.form_submit_button("Salvar Médico"):
                    supabase.table("MEDICOS").insert({"nome": n, "especialidade": e, "unidade": u}).execute()
                    st.success("Médico Cadastrado com Sucesso!")

        elif menu == "2. Abertura de Agenda":
            st.header("🏪 Abertura de Agenda")
            res = supabase.table("MEDICOS").select("*").execute()
            if res.data:
                op = {f"{m['nome']} ({m['especialidade']}) - {m['unidade']}": m['id'] for m in res.data}
                sel = st.selectbox("Selecione o Médico e Unidade", list(op.keys()))
                c1, c2 = st.columns(2)
                d = c1.date_input("Data", format="DD/MM/YYYY")
                h = c2.time_input("Hora de Início")
                q = st.number_input("Quantidade de Vagas", 1, 50, 10)
                i = st.number_input("Intervalo (minutos)", 5, 60, 20)
                if st.button("Gerar Grade de Horários"):
                    vagas_list = []
                    p_inicio = dt_lib.datetime.combine(d, h)
                    for x in range(int(q)):
                        vagas_list.append({"medico_id": op[sel], "data_hora": (p_inicio + dt_lib.timedelta(minutes=x*i)).isoformat(), "status": "Livre"})
                    supabase.table("CONSULTAS").insert(vagas_list).execute()
                    st.success(f"✅ Agenda criada para o dia {d.strftime('%d/%m/%Y')}!")

        elif menu == "4. Relatório de Agendamentos":
            st.header("📋 Relatório de Consultas")
            try:
                res = supabase.table("CONSULTAS").select("*, MEDICOS(*)").execute()
                if res.data:
                    relat = []
                    for idx, r in enumerate(res.data):
                        m = r.get('MEDICOS') or r.get('medicos') or {}
                        dt = pd.to_datetime(r['data_hora'])
                        data_br = dt.strftime('%d/%m/%Y %H:%M')
                        med, esp, uni = m.get('nome','N/I'), m.get('especialidade','-'), m.get('unidade','-')
                        pac = f"{r.get('paciente_nome','')} {r.get('paciente_sobrenome','')}".strip()
                        tel = str(r.get('paciente_telefone', ''))
                        msg = f"Olá, Gentileza Confirmar consulta {med} / {esp} / {data_br} / {uni}"
                        tel_limpo = ''.join(filter(str.isdigit, tel))
                        link = f"https://wa.me/55{tel_limpo}?text={msg.replace(' ', '%20')}" if tel_limpo else None
                        relat.append({"Nº": idx+1, "Data/Hora": data_br, "Unidade": uni, "Médico": med, "Paciente": pac if pac else "Livre", "WhatsApp": link, "Confirmado": False, "sort": r['data_hora']})
                    df = pd.DataFrame(relat).sort_values(by="sort")
                    st.data_editor(df.drop(columns=["sort"]), column_config={"WhatsApp": st.column_config.LinkColumn("📱 Ação", display_text="Enviar 🟢"), "Confirmado": st.column_config.CheckboxColumn("OK?")}, use_container_width=True, hide_index=True)
                else: st.info("Nenhum registro encontrado.")
            except Exception as e: st.error(f"Erro no relatório: {e}")

        elif menu == "5. Cancelar Consulta":
            st.header("🚫 Cancelar Agendamento")
            try:
                res = supabase.table("CONSULTAS").select("*, MEDICOS(*)").eq("status", "Marcada").execute()
                if res.data:
                    lista_c = []
                    for r in res.data:
                        m = r.get('MEDICOS') or r.get('medicos') or {}
                        pac = f"{r.get('paciente_nome', '')} {r.get('paciente_sobrenome', '')}".strip()
                        dt = pd.to_datetime(r['data_hora']).strftime('%d/%m/%Y %H:%M')
                        lista_c.append({'id': r['id'], 'info': f"{pac} | {dt} | Dr(a): {m.get('nome')}"})
                    df_c = pd.DataFrame(lista_c)
                    busca = st.text_input("🔍 Buscar Paciente pelo Nome:", "")
                    df_f = df_c[df_c['info'].str.contains(busca, case=False)]
                    sel = st.selectbox("Selecione para cancelar:", ["Selecione..."] + df_f['info'].tolist())
                    if sel != "Selecione..." and st.button("Confirmar Cancelamento"):
                        id_v = df_f[df_f['info'] == sel].iloc[0]['id']
                        supabase.table("CONSULTAS").update({"paciente_nome":None, "paciente_sobrenome":None, "paciente_telefone":None, "status":"Livre"}).eq("id", id_v).execute()
                        st.success("Consulta Cancelada e horário liberado!"); st.rerun()
                else: st.info("Sem consultas marcadas para cancelar.")
            except Exception as e: st.error(f"Erro: {e}")

        elif menu == "6. Excluir Grade Aberta":
            st.header("🗑️ Excluir Horários Livres")
            res = supabase.table("CONSULTAS").select("*, MEDICOS(*)").eq("status", "Livre").execute()
            if res.data:
                df_e = pd.DataFrame([{'id': r['id'], 'info': f"{pd.to_datetime(r['data_hora']).strftime('%d/%m/%Y %H:%M')} - {r['MEDICOS']['nome']}"} for r in res.data])
                sel_e = st.multiselect("Selecione os horários para excluir permanentemente:", df_e['info'].tolist())
                if st.button("Excluir Permanente"):
                    ids_e = df_e[df_e['info'].isin(sel_e)]['id'].tolist()
                    supabase.table("CONSULTAS").delete().in_("id", ids_e).execute()
                    st.success(f"{len(ids_e)} horários excluídos com sucesso!"); st.rerun()
