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
        # Puxamos as duas tabelas e fazemos o cruzamento (JOIN) manual para garantir que apareça
        v_res = supabase.table("CONSULTAS").select("*").eq("status", "Livre").execute()
        m_res = supabase.table("MEDICOS").select("*").execute()
        
        if v_res.data and m_res.data:
            df_v = pd.DataFrame(v_res.data)
            df_m = pd.DataFrame(m_res.data)
            
            # Cruzamento de dados pelo ID do médico
            df_unido = pd.merge(df_v, df_m, left_on="medico_id", right_on="id")
            
            if not df_unido.empty:
                df_unido['unidade'] = df_unido['unidade'].astype(str).str.strip()
                df_unido['especialidade'] = df_unido['especialidade'].astype(str).str.strip().upper()
                df_unido['horario'] = pd.to_datetime(df_unido['data_hora']).dt.strftime('%d/%m/%Y às %H:%M')
                
                c1, c2 = st.columns(2)
                with c1:
                    u_list = sorted(df_unido['unidade'].unique().tolist())
                    u_sel = st.selectbox("1️⃣ Unidade", ["Selecione..."] + u_list)
                    if u_sel != "Selecione...":
                        df_f = df_unido[df_unido['unidade'] == u_sel]
                        e_sel = st.selectbox("2️⃣ Especialidade", ["Selecione..."] + sorted(df_f['especialidade'].unique().tolist()))
                    else: e_sel = "Selecione..."
                with c2:
                    if e_sel != "Selecione..." and u_sel != "Selecione...":
                        df_f = df_f[df_f['especialidade'] == e_sel]
                        m_sel = st.selectbox("3️⃣ Médico", ["Selecione..."] + sorted(df_f['nome'].unique().tolist()))
                        if m_sel != "Selecione...":
                            df_f = df_f[df_f['nome'] == m_sel]
                            h_sel = st.selectbox("4️⃣ Horário", ["Selecione..."] + df_f['horario'].tolist())
                        else: h_sel = "Selecione..."
                    else: m_sel = h_sel = "Selecione..."

                if "Selecione" not in f"{u_sel}{e_sel}{m_sel}{h_sel}":
                    id_vaga = df_f[df_f['horario'] == h_sel].iloc[0]['id_x']
                    with st.form("agendar"):
                        n, s = st.text_input("Nome"), st.text_input("Sobrenome")
                        w, c = st.text_input("WhatsApp"), st.text_input("Convênio")
                        if st.form_submit_button("Confirmar"):
                            supabase.table("CONSULTAS").update({"paciente_nome": n, "paciente_sobrenome": s, "paciente_telefone": w, "paciente_convenio": c, "status": "Marcada"}).eq("id", id_vaga).execute()
                            st.success("✅ Agendado!"); st.balloons()
            else: st.warning("Vagas encontradas, mas sem médicos ativos. Vá em 'Excluir Grade Aberta' e limpe tudo, depois reabra.")
        else: st.info("Sem vagas livres.")
    except Exception as e: st.error(f"Erro: {e}")

else:
    if verificar_senha():
        if menu == "1. Cadastro de Médicos":
            st.header("👨‍⚕️ Cadastro")
            esp_lista = ["CARDIOLOGIA", "CLINICA", "DERMATOLOGIA", "ENDOCRINOLOGIA", "FONOAUDIOLOGIA", "GINECOLOGIA", "NEUROLOGIA", "NUTRICIONISTA", "ODONTOLOGIA", "OFTALMOLOGIA", "ORTOPEDIA", "PEDIATRIA", "PSICOLOGIA", "PSIQUIATRIA", "UROLOGIA"]
            with st.form("f_med"):
                n = st.text_input("Nome")
                e = st.selectbox("Especialidade", sorted(esp_lista))
                u = st.selectbox("Unidade", ["Pç 7 Rua Carijos 424 SL 2213", "Pç 7 Rua Rio de Janeiro 462 SL 303", "Eldorado Av Jose Faria da Rocha 4408 2 and", "Eldorado Av Jose Faria da Rocha 5959"])
                if st.form_submit_button("Salvar"):
                    supabase.table("MEDICOS").insert({"nome": n.upper(), "especialidade": e, "unidade": u}).execute()
                    st.success("Médico Cadastrado!")

        elif menu == "2. Abertura de Agenda":
            st.header("🏪 Abertura de Agenda")
            res_m = supabase.table("MEDICOS").select("*").execute()
            if res_m.data:
                med_dict = {f"{m['nome']} ({m['especialidade']})": m['id'] for m in res_m.data}
                sel = st.selectbox("Médico", list(med_dict.keys()))
                c1, c2, c3 = st.columns(3)
                d = c1.date_input("Data")
                h_i, h_f = c2.time_input("Início"), c3.time_input("Fim")
                i = st.number_input("Intervalo (min)", 5, 120, 20)
                if st.button("Gerar Grade"):
                    v = []
                    t, f = dt_lib.datetime.combine(d, h_i), dt_lib.datetime.combine(d, h_f)
                    while t < f:
                        v.append({"medico_id": med_dict[sel], "data_hora": t.isoformat(), "status": "Livre"})
                        t += dt_lib.timedelta(minutes=i)
                    supabase.table("CONSULTAS").insert(v).execute()
                    st.success("Grade Criada!")

        elif menu == "4. Relatório de Agendamentos":
            st.header("📋 Relatório")
            res = supabase.table("CONSULTAS").select("*, MEDICOS(*)").order("data_hora", desc=True).limit(200).execute()
            if res.data:
                df = pd.DataFrame([{"Data": pd.to_datetime(r['data_hora']).strftime('%d/%m/%Y %H:%M'), "Médico": (r.get('MEDICOS') or {}).get('nome', 'N/I'), "Unidade": (r.get('MEDICOS') or {}).get('unidade', '-'), "Status": r['status']} for r in res.data])
                st.table(df)

        elif menu == "6. Excluir Grade Aberta":
            st.header("🗑️ Limpeza de Sistema")
            st.warning("Use esta tela para apagar grades 'órfãs' (como a da Ana Paula que está com ID errado).")
            res = supabase.table("CONSULTAS").select("*").eq("status", "Livre").execute()
            if res.data:
                df_e = pd.DataFrame([{'id': r['id'], 'info': f"ID {r['id']} | MedID {r['medico_id']} | Data {r['data_hora']}"} for r in res.data])
                sel = st.multiselect("Selecione para apagar:", df_e['info'].tolist())
                if st.button("Apagar Selecionados"):
                    ids = df_e[df_e['info'].isin(sel)]['id'].tolist()
                    supabase.table("CONSULTAS").delete().in_("id", ids).execute()
                    st.rerun()
