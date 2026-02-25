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

def verificar_senha():
    if "autenticado" not in st.session_state:
        st.session_state["autenticado"] = False
    if not st.session_state["autenticado"]:
        with st.container():
            st.subheader("🔒 Área Restrita")
            senha_digitada = st.text_input("Senha Adm:", type="password")
            if st.button("Acessar"):
                if senha_digitada == SENHA_ACESSO:
                    st.session_state["autenticado"] = True
                    st.rerun()
                else: st.error("Incorreta")
        return False
    return True

# --- 3. LÓGICA DAS TELAS ---

if menu == "3. Marcar Consulta":
    st.header("📅 Agendamento de Consultas")
    try:
        # Puxa as vagas livres e os dados do médico em uma única consulta
        res = supabase.table("CONSULTAS").select("*, MEDICOS(*)").eq("status", "Livre").limit(3000).execute()
        
        if res.data and len(res.data) > 0:
            vagas_limpas = []
            for r in res.data:
                # Tentativa de pegar o médico (pode vir como 'MEDICOS' ou 'medicos')
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
            
            if not vagas_limpas:
                st.warning("Atenção: Existem horários livres, mas eles não estão vinculados a nenhum médico cadastrado.")
            else:
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
            st.info("Não há nenhuma grade aberta no sistema. Vá em 'Abertura de Agenda' primeiro.")
    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")

else:
    if verificar_senha():
        if st.sidebar.button("🔒 Sair"):
            st.session_state["autenticado"] = False
            st.rerun()

        if menu == "1. Cadastro de Médicos":
            st.header("👨‍⚕️ Cadastro")
            esp_lista = ["CARDIOLOGIA", "CLINICA", "DERMATOLOGIA", "ENDOCRINOLOGIA", "FONOAUDIOLOGIA", "GINECOLOGIA", "NEFROLOGIA", "NEUROLOGIA", "NUTRICIONISTA", "ODONTOLOGIA", "OFTALMOLOGIA", "ORTOPEDIA", "OTORRINOLARINGOLOGIA", "PEDIATRIA", "PNEUMOLOGIA", "PSICOLOGIA", "PSIQUIATRIA", "UROLOGIA"]
            with st.form("f_med"):
                n = st.text_input("Nome")
                e = st.selectbox("Especialidade", sorted(esp_lista))
                u = st.selectbox("Unidade", ["Pç 7 Rua Carijos 424 SL 2213", "Pç 7 Rua Rio de Janeiro 462 SL 303", "Eldorado Av Jose Faria da Rocha 4408 2 and", "Eldorado Av Jose Faria da Rocha 5959"])
                if st.form_submit_button("Salvar Médico"):
                    supabase.table("MEDICOS").insert({"nome": n, "especialidade": e, "unidade": u}).execute()
                    st.success("Cadastrado!")

        elif menu == "2. Abertura de Agenda":
            st.header("🏪 Abertura de Agenda")
            res_m = supabase.table("MEDICOS").select("*").execute()
            if res_m.data:
                med_list = {f"{m['nome']} ({m['especialidade']})": m['id'] for m in res_m.data}
                sel_med = st.selectbox("Selecione o Médico", list(med_list.keys()))
                c1, c2, c3 = st.columns(3)
                d = c1.date_input("Data", format="DD/MM/YYYY")
                h_i = c2.time_input("Início", value=dt_lib.time(8, 0))
                h_f = c3.time_input("Fim", value=dt_lib.time(18, 0))
                i = st.number_input("Intervalo (min)", 5, 120, 20)
                
                if st.button("Gerar Grade agora"):
                    vagas = []
                    t = dt_lib.datetime.combine(d, h_i)
                    f = dt_lib.datetime.combine(d, h_f)
                    while t < f:
                        vagas.append({"medico_id": med_list[sel_med], "data_hora": t.isoformat(), "status": "Livre"})
                        t += dt_lib.timedelta(minutes=i)
                    
                    try:
                        # LOG DE ENVIO
                        st.write(f"Tentando gravar {len(vagas)} horários para o ID de médico: {med_list[sel_med]}")
                        resp = supabase.table("CONSULTAS").insert(vagas).execute()
                        if resp.data:
                            st.success(f"✅ Sucesso! Vá para a Tela 3 ou 4 para conferir.")
                        else:
                            st.error("O banco não gravou. Verifique se a coluna na tabela CONSULTAS se chama 'medico_id'.")
                    except Exception as e:
                        st.error(f"Erro na gravação: {e}")
            else: st.warning("Cadastre um médico primeiro.")

        elif menu == "4. Relatório de Agendamentos":
            st.header("📋 Relatório Completo")
            # Mostra as últimas 200 linhas de tudo o que está no banco
            res = supabase.table("CONSULTAS").select("*, MEDICOS(*)").order("data_hora", desc=True).limit(200).execute()
            if res.data:
                st.dataframe(pd.DataFrame(res.data), use_container_width=True)
            else: st.info("Tabela CONSULTAS está vazia.")

        elif menu == "7. Excluir Cadastro de Médico":
            st.header("Excluir Médico")
            res_m = supabase.table("MEDICOS").select("*").execute()
            if res_m.data:
                m_del = {f"{m['nome']}": m['id'] for m in res_m.data}
                sel = st.selectbox("Médico:", list(m_del.keys()))
                if st.button("Excluir"):
                    supabase.table("CONSULTAS").delete().eq("medico_id", m_del[sel]).execute()
                    supabase.table("MEDICOS").delete().eq("id", m_del[sel]).execute()
                    st.success("Removido"); st.rerun()
