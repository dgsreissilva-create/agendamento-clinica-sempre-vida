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

# --- FUNÇÃO MESTRE: BUSCAR UNIDADES DIRETAMENTE DO BANCO ---
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

# TELA 3 - AGENDAMENTO COM LINK DIRETO AO BANCO
if menu == "3. Marcar Consulta":
    st.header("📅 Agendamento de Consultas")
    try:
        # BUSCA 1: Pegamos as vagas livres
        res_vagas = supabase.table("CONSULTAS").select("*").eq("status", "Livre").limit(3000).execute()
        # BUSCA 2: Pegamos os médicos cadastrados (O LINK DIRETO QUE VOCÊ PEDIU)
        res_medicos = supabase.table("MEDICOS").select("*").execute()
        
        if res_vagas.data and res_medicos.data:
            df_vagas = pd.DataFrame(res_vagas.data)
            df_medicos = pd.DataFrame(res_medicos.data)
            
            # Unimos as duas tabelas pelo ID do médico (O "Link" perfeito)
            df_final = pd.merge(df_vagas, df_medicos, left_on="medico_id", right_on="id")
            
            if not df_final.empty:
                # Padronização para os filtros
                df_final['unidade'] = df_final['unidade'].astype(str).strip()
                df_final['especialidade'] = df_final['especialidade'].astype(str).upper().strip()
                
                c1, c2 = st.columns(2)
                with c1:
                    # Filtro 1: Unidade (Lincado ao banco)
                    u_sel = st.selectbox("1️⃣ Escolha a Unidade", ["Selecione..."] + sorted(df_final['unidade'].unique().tolist()))
                    
                    if u_sel != "Selecione...":
                        df_u = df_final[df_final['unidade'] == u_sel]
                        # Filtro 2: Especialidade (Lincado ao banco)
                        e_sel = st.selectbox("2️⃣ Escolha a Especialidade", ["Selecione..."] + sorted(df_u['especialidade'].unique().tolist()))
                    else: e_sel = "Selecione..."

                with c2:
                    if e_sel != "Selecione..." and u_sel != "Selecione...":
                        df_e = df_u[df_u['especialidade'] == e_sel]
                        # Filtro 3: Nome do Médico (Lincado ao banco)
                        m_sel = st.selectbox("3️⃣ Escolha o Médico", ["Selecione..."] + sorted(df_e['nome'].unique().tolist()))
                        
                        if m_sel != "Selecione...":
                            df_m = df_e[df_e['nome'] == m_sel]
                            # Filtro 4: Horários disponíveis para este médico
                            h_lista = pd.to_datetime(df_m['data_hora']).dt.strftime('%d/%m/%Y às %H:%M').tolist()
                            h_sel = st.selectbox("4️⃣ Escolha o Horário", ["Selecione..."] + h_lista)
                        else: h_sel = "Selecione..."
                    else: m_sel = h_sel = "Selecione..."

                if "Selecione" not in f"{u_sel}{e_sel}{m_sel}{h_sel}":
                    # Pega o ID da vaga (id_x é o ID da tabela CONSULTAS após o merge)
                    id_vaga = df_m.iloc[h_lista.index(h_sel)]['id_x']
                    
                    with st.form("f_agendar"):
                        f1, f2 = st.columns(2)
                        pn, ps = f1.text_input("Nome"), f1.text_input("Sobrenome")
                        pt, pc = f2.text_input("WhatsApp"), f2.text_input("Convênio")
                        if st.form_submit_button("Confirmar Agendamento"):
                            if pn and pt:
                                supabase.table("CONSULTAS").update({
                                    "paciente_nome": pn, "paciente_sobrenome": ps, 
                                    "paciente_telefone": pt, "paciente_convenio": pc, 
                                    "status": "Marcada"
                                }).eq("id", id_vaga).execute()
                                st.success("✅ Agendado com sucesso!"); st.balloons()
                                st.rerun()
            else: st.warning("Existem horários, mas eles não estão vinculados a médicos ativos.")
        else: st.info("Não há vagas disponíveis no momento.")
    except Exception as e: st.error(f"Erro ao carregar dados: {e}")

# TELAS ADMINISTRATIVAS
else:
    if verificar_senha():
        lista_u = buscar_unidades_db()
        esp_lista = sorted(["Cardiologia", "Clinica", "Dermatologia", "Endocrinologia", "Fonoaudiologia", "Ginecologia", "Nefrologia", "Neurologia", "Neuropsicologia", "Nutricionista", "ODONTOLOGIA", "Oftalmologia", "Ortopedia", "Pediatria", "Pneumologia", "Psicologia", "Psiquiatria", "Urologia"])

        if menu == "1. Cadastro de Médicos":
            st.header("👨‍⚕️ Cadastro")
            with st.form("f_med"):
                n = st.text_input("Nome")
                e = st.selectbox("Especialidade", esp_lista)
                u = st.selectbox("Un
