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
            senha_digitada = st.text_input("Senha:", type="password")
            if st.button("Liberar"):
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
        # BUSCA MANUAL PARA GARANTIR QUE TUDO APAREÇA
        res_vagas = supabase.table("CONSULTAS").select("*").eq("status", "Livre").limit(4000).execute()
        res_medicos = supabase.table("MEDICOS").select("*").execute()
        
        if res_vagas.data and res_medicos.data:
            df_v = pd.DataFrame(res_vagas.data)
            df_m = pd.DataFrame(res_medicos.data)
            
            # UNIMOS OS DADOS AQUI NO PYTHON (Merge manual)
            df_f = pd.merge(df_v, df_m, left_on="medico_id", right_on="id")
            
            if not df_f.empty:
                df_f['unidade'] = df_f['unidade'].astype(str).str.strip()
                df_f['especialidade'] = df_f['especialidade'].astype(str).str.strip()
                df_f['medico'] = df_f['nome'].astype(str).str.strip()
                df_f['horario'] = pd.to_datetime(df_f['data_hora']).dt.strftime('%d/%m/%Y às %H:%M')

                c1, c2 = st.columns(2)
                with c1:
                    u_list = sorted(df_f['unidade'].unique().tolist())
                    u_sel = st.selectbox("1️⃣ Unidade", ["Selecione..."] + u_list)
                    if u_sel != "Selecione...":
                        df_u = df_f[df_f['unidade'] == u_sel]
                        e_sel = st.selectbox("2️⃣ Especialidade", ["Selecione..."] + sorted(df_u['especialidade'].unique().tolist()))
                    else: e_sel = "Selecione..."
                with c2:
                    if e_sel != "Selecione..." and u_sel != "Selecione...":
                        df_e = df_u[df_u['especialidade'] == e_sel]
                        m_sel = st.selectbox("3️⃣ Médico", ["Selecione..."] + sorted(df_e['medico'].unique().tolist()))
                        if m_sel != "Selecione...":
                            df_m_final = df_e[df_e['medico'] == m_sel]
                            h_sel = st.selectbox("4️⃣ Horário", ["Selecione..."] + df_m_final['horario'].tolist())
                        else: h_sel = "Selecione..."
                    else: m_sel = h_sel = "Selecione..."

                if "Selecione" not in f"{u_sel}{e_sel}{m_sel}{h_sel}":
                    # id_x é o ID da tabela CONSULTAS após o merge
                    id_vaga = df_m_final[df_m_final['horario'] == h_sel].iloc[0]['id_x']
                    with st.form("agendar"):
                        n, s = st.text_input("Nome"), st.text_input("Sobrenome")
                        w, c = st.text_input("WhatsApp"), st.text_input("Convênio")
                        if st.form_submit_button("Confirmar"):
                            supabase.table("CONSULTAS").update({"paciente_nome": n, "paciente_sobrenome": s, "paciente_telefone": w, "paciente_convenio": c, "status": "Marcada"}).eq("id", id_vaga).execute()
                            st.success("✅ Agendado!"); st.balloons(); st.rerun()
            else: st.warning("Vagas livres sem médicos correspondentes.")
        else: st.info("Nenhuma vaga livre encontrada.")
    except Exception as e: st.error(f"Erro: {e}")

elif menu == "2. Abertura de Agenda":
    if verificar_senha():
        st.header("🏪 Abertura de Agenda")
        res_m = supabase.table("MEDICOS").select("*").execute()
        if res_m.data:
            op = {f"{m['nome']} ({m['especialidade']})": m['id'] for m in res_m.data}
            sel = st.selectbox("Selecione o Médico", list(op.keys()))
            c1, c2, c3 = st.columns(3)
            d = c1.date_input("Data")
            hi, hf = c2.time_input("Início", value=dt_lib.time(8,0)), c3.time_input("Fim", value=dt_lib.time(18,0))
            if st.button("Gerar Grade"):
                v = []
                t, f = dt_lib.datetime.combine(d, hi), dt_lib.datetime.combine(d, hf)
                while t < f:
                    v.append({"medico_id": int(op[sel]), "data_hora": t.isoformat(), "status": "Livre"})
                    t += dt_lib.timedelta(minutes=20)
                # Inserção explícita
                supabase.table("CONSULTAS").insert(v).execute()
                st.success(f"✅ Grade criada para ID {op[sel]}!")

elif menu == "4. Relatório de Agendamentos":
    st.header("📋 Relatório")
    # Busca manual também no relatório para evitar erros de relacionamento
    r_v = supabase.table("CONSULTAS").select("*").limit(1000).execute()
    r_m = supabase.table("MEDICOS").select("*").execute()
    if r_v.data and r_m.data:
        df_v = pd.DataFrame(r_v.data)
        df_m = pd.DataFrame(r_m.data)
        df_r = pd.merge(df_v, df_m, left_on="medico_id", right_on="id", how="left")
        df_r['Data'] = pd.to_datetime(df_r['data_hora']).dt.strftime('%d/%m/%Y %H:%M')
        st.dataframe(df_r[['Data', 'nome', 'status', 'paciente_nome']].sort_values('Data', ascending=False))
