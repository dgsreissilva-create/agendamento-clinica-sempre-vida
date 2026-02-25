import streamlit as st
import pandas as pd
import datetime as dt_lib
from supabase import create_client

# --- 1. CONFIGURAÇÕES ---
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

st.set_page_config(page_title="Clínica Sempre Vida", layout="wide")

# --- SEGURANÇA ---
SENHA_ACESSO = "8484" 

def verificar_senha():
    if "autenticado" not in st.session_state:
        st.session_state["autenticado"] = False
    if not st.session_state["autenticado"]:
        with st.container():
            st.subheader("🔒 Área Administrativa")
            senha_digitada = st.text_input("Senha Adm:", type="password")
            if st.button("Acessar"):
                if senha_digitada == SENHA_ACESSO:
                    st.session_state["autenticado"] = True
                    st.rerun()
                else: st.error("Incorreta")
        return False
    return True

# --- MENU ---
menu = st.sidebar.radio("Navegação", ["Marcar Consulta", "Abertura de Agenda", "Relatório de Agendamentos", "Cadastro de Médicos"])

# --- TELA 3 (PÚBLICA) ---
if menu == "Marcar Consulta":
    st.header("📅 Agendamento")
    try:
        # Puxamos as duas tabelas separadas para não depender do relacionamento do banco
        v_res = supabase.table("CONSULTAS").select("*").eq("status", "Livre").limit(4000).execute()
        m_res = supabase.table("MEDICOS").select("*").execute()
        
        if v_res.data and m_res.data:
            df_v = pd.DataFrame(v_res.data)
            df_m = pd.DataFrame(m_res.data)
            # MERGE MANUAL: Isso linca o ID 63 (Ana Paula) ou ID 18 (Sergio) na hora
            df_f = pd.merge(df_v, df_m, left_on="medico_id", right_on="id")
            
            if not df_f.empty:
                u_sel = st.selectbox("Unidade", ["Selecione..."] + sorted(df_f['unidade'].unique().tolist()))
                if u_sel != "Selecione...":
                    df_u = df_f[df_f['unidade'] == u_sel]
                    e_sel = st.selectbox("Especialidade", ["Selecione..."] + sorted(df_u['especialidade'].unique().tolist()))
                    if e_sel != "Selecione...":
                        df_e = df_u[df_u['especialidade'] == e_sel]
                        m_sel = st.selectbox("Médico", ["Selecione..."] + sorted(df_e['nome'].unique().tolist()))
                        if m_sel != "Selecione...":
                            df_final = df_e[df_e['nome'] == m_sel]
                            df_final['hora'] = pd.to_datetime(df_final['data_hora']).dt.strftime('%d/%m/%Y %H:%M')
                            h_sel = st.selectbox("Horário", ["Selecione..."] + df_final['hora'].tolist())
                            
                            if h_sel != "Selecione...":
                                id_vaga = df_final[df_final['hora'] == h_sel].iloc[0]['id_x']
                                with st.form("ag"):
                                    n = st.text_input("Nome")
                                    w = st.text_input("WhatsApp")
                                    if st.form_submit_button("Confirmar"):
                                        supabase.table("CONSULTAS").update({"paciente_nome": n, "paciente_telefone": w, "status": "Marcada"}).eq("id", id_vaga).execute()
                                        st.success("✅ Marcado!"); st.rerun()
            else: st.warning("Vagas órfãs encontradas. Refaça a grade dos médicos novos.")
    except Exception as e: st.error(f"Erro: {e}")

# --- TELA 4 (RELATÓRIO) ---
elif menu == "Relatório de Agendamentos":
    st.header("📋 Relatório")
    v_res = supabase.table("CONSULTAS").select("*").limit(1000).execute()
    m_res = supabase.table("MEDICOS").select("*").execute()
    if v_res.data and m_res.data:
        df_v = pd.DataFrame(v_res.data)
        df_m = pd.DataFrame(m_res.data)
        df_r = pd.merge(df_v, df_m, left_on="medico_id", right_on="id", how="left")
        st.dataframe(df_r[['data_hora', 'nome', 'status', 'paciente_nome']].sort_values('data_hora', ascending=False))

# --- TELA 2 (ABERTURA) ---
elif menu == "Abertura de Agenda":
    if verificar_senha():
        st.header("🏪 Abertura de Agenda")
        res_m = supabase.table("MEDICOS").select("*").execute()
        if res_m.data:
            meds = {f"{m['nome']} ({m['especialidade']})": m['id'] for m in res_m.data}
            sel = st.selectbox("Médico", list(meds.keys()))
            d = st.date_input("Data")
            if st.button("Gerar 10 horários (Teste)"):
                vagas = []
                base_h = dt_lib.datetime.combine(d, dt_lib.time(8,0))
                for i in range(10):
                    vagas.append({"medico_id": int(meds[sel]), "data_hora": (base_h + dt_lib.timedelta(minutes=i*20)).isoformat(), "status": "Livre"})
                
                # INSERÇÃO COM CONFIRMAÇÃO VISUAL
                r = supabase.table("CONSULTAS").insert(vagas).execute()
                if r.data:
                    st.success(f"✅ Gravado no banco! Médico ID: {meds[sel]}")
                    st.write(r.data) # Isso vai mostrar se o banco realmente salvou
                else:
                    st.error("❌ O banco aceitou o comando, mas não salvou os dados. Verifique o RLS.")
