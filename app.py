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

# --- FUNÇÃO PARA BUSCAR UNIDADES DIRETAMENTE DO BANCO ---
def buscar_unidades_db():
    try:
        res = supabase.table("UNIDADES").select("nome_unidade").execute()
        if res.data:
            return sorted([u['nome_unidade'] for u in res.data])
        return []
    except:
        return ["Pç 7 Rua Carijos 424 SL 2213", "Pç 7 Rua Rio de Janeiro 462 SL 303", 
                "Eldorado Av Jose Faria da Rocha 4408 2 and", "Eldorado Av Jose Faria da Rocha 5959"]

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
    "8. Relatório Gerencial",
    "9. Editar Cadastro de Médico"
], index=2)

def verificar_senha():
    if "autenticado" not in st.session_state:
        st.session_state["autenticado"] = False
    if not st.session_state["autenticado"]:
        with st.container():
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

if menu == "3. Marcar Consulta":
    st.header("📅 Agendamento de Consultas")
    try:
        # Busca vagas livres e médicos em tempo real
        res_vagas = supabase.table("CONSULTAS").select("*").eq("status", "Livre").limit(3000).execute()
        res_medicos = supabase.table("MEDICOS").select("*").execute()
        
        if res_vagas.data and res_medicos.data:
            df_v = pd.DataFrame(res_vagas.data)
            df_m = pd.DataFrame(res_medicos.data)
            
            # Cruzamento (Merge) para garantir que só apareçam médicos com grade e ativos
            df_final = pd.merge(df_v, df_m, left_on="medico_id", right_on="id")
            
            if not df_final.empty:
                c1, c2 = st.columns(2)
                with c1:
                    unidades_disponiveis = sorted(df_final['unidade'].unique().tolist())
                    u_sel = st.selectbox("1️⃣ Unidade", ["Selecione..."] + unidades_disponiveis)
                    
                    if u_sel != "Selecione...":
                        df_u = df_final[df_final['unidade'] == u_sel]
                        especialidades = sorted(df_u['especialidade'].unique().tolist())
                        e_sel = st.selectbox("2️⃣ Especialidade", ["Selecione..."] + especialidades)
                    else: e_sel = "Selecione..."

                with c2:
                    if e_sel != "Selecione..." and u_sel != "Selecione...":
                        df_e = df_u[df_u['especialidade'] == e_sel]
                        medicos = sorted(df_e['nome'].unique().tolist())
                        m_sel = st.selectbox("3️⃣ Médico", ["Selecione..."] + medicos)
                        
                        if m_sel != "Selecione...":
                            df_med_final = df_e[df_e['nome'] == m_sel]
                            horarios = pd.to_datetime(df_med_final['data_hora']).dt.strftime('%d/%m/%Y às %H:%M').tolist()
                            h_sel = st.selectbox("4️⃣ Horário", ["Selecione..."] + horarios)
                        else: h_sel = "Selecione..."
                    else: m_sel = h_sel = "Selecione..."

                if "Selecione" not in f"{u_sel}{e_sel}{m_sel}{h_sel}":
                    # Identifica o ID correto da consulta para atualizar
                    id_vaga = df_med_final.iloc[horarios.index(h_sel)]['id_x']
                    with st.form("f_agendar"):
                        fn, fs = st.text_input("Nome"), st.text_input("Sobrenome")
                        wt, cv = st.text_input("WhatsApp"), st.text_input("Convênio")
                        if st.form_submit_button("Confirmar Agendamento"):
                            if fn and wt:
                                supabase.table("CONSULTAS").update({
                                    "paciente_nome": fn, "paciente_sobrenome": fs, 
                                    "paciente_telefone": wt, "paciente_convenio": cv, 
                                    "status": "Marcada"
                                }).eq("id", id_vaga).execute()
                                st.success("✅ Agendado!"); st.balloons(); st.rerun()
                            else: st.error("Preencha Nome e WhatsApp.")
            else: st.warning("Grades encontradas, mas sem médicos ativos. Revise os cadastros.")
        else: st.info("Sem horários disponíveis.")
    except Exception as e: st.error(f"Erro: {e}")

else:
    if verificar_senha():
        lista_u = buscar_unidades_db()
        # Telas administrativas seguem o fluxo de cadastro e edição já configurados.
        if menu == "1. Cadastro de Médicos":
            st.header("👨‍⚕️ Cadastro")
            with st.form("f_med"):
                n = st.text_input("Nome")
                e = st.selectbox("Especialidade", ["Cardiologia", "Clinica", "Ginecologia", "Neurologia", "Nutricionista", "ODONTOLOGIA", "Ortopedia"])
                u = st.selectbox("Unidade", lista_u)
                if st.form_submit_button("Salvar"):
                    supabase.table("MEDICOS").insert({"nome": n.upper(), "especialidade": e, "unidade": u}).execute()
                    st.success("Salvo!")

        elif menu == "2. Abertura de Agenda":
            st.header("🏪 Abertura")
            res_m = supabase.table("MEDICOS").select("*").execute()
            if res_m.data:
                med_dict = {f"{m['nome']} ({m['especialidade']})": m['id'] for m in res_m.data}
                sel = st.selectbox("Médico", list(med_dict.keys()))
                c1, hi, hf = st.columns(3)
                d = c1.date_input("Data")
                if st.button("Gerar Grade"):
                    v = [{"medico_id": med_dict[sel], "data_hora": dt_lib.datetime.combine(d, hi.time_input("Início")).isoformat(), "status": "Livre"}]
                    supabase.table("CONSULTAS").insert(v).execute()
                    st.success("Criada!")
        
        # ... Outras telas seguem a lógica padrão conforme o sistema original.
