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
        return ["Pç 7 Rua Carijos 424 SL 2213", "Eldorado Av Jose Faria da Rocha 4408 2 and"]

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
        # Puxamos as vagas e médicos separadamente para cruzar no código (Link Direto)
        res_v = supabase.table("CONSULTAS").select("*").eq("status", "Livre").limit(3000).execute()
        res_m = supabase.table("MEDICOS").select("*").execute()
        
        if res_v.data and res_m.data:
            df_v = pd.DataFrame(res_v.data)
            df_m = pd.DataFrame(res_m.data)
            
            # O MERGE garante o vínculo correto entre ID da consulta e ID do médico
            df_final = pd.merge(df_v, df_m, left_on="medico_id", right_on="id")
            
            if not df_final.empty:
                # Padronização de strings para evitar erros de busca
                df_final['unidade'] = df_final['unidade'].astype(str).str.strip()
                df_final['especialidade'] = df_final['especialidade'].astype(str).str.strip()
                df_final['horario_txt'] = pd.to_datetime(df_final['data_hora']).dt.strftime('%d/%m/%Y às %H:%M')
                
                c1, c2 = st.columns(2)
                with c1:
                    u_sel = st.selectbox("1️⃣ Unidade", ["Selecione..."] + sorted(df_final['unidade'].unique().tolist()))
                    if u_sel != "Selecione...":
                        df_f = df_final[df_final['unidade'] == u_sel]
                        e_sel = st.selectbox("2️⃣ Especialidade", ["Selecione..."] + sorted(df_f['especialidade'].unique().tolist()))
                    else: e_sel = "Selecione..."
                with c2:
                    if e_sel != "Selecione..." and u_sel != "Selecione...":
                        df_f = df_f[df_f['especialidade'] == e_sel]
                        m_sel = st.selectbox("3️⃣ Médico", ["Selecione..."] + sorted(df_f['nome'].unique().tolist()))
                        if m_sel != "Selecione...":
                            df_f = df_f[df_f['nome'] == m_sel]
                            h_sel = st.selectbox("4️⃣ Horário", ["Selecione..."] + df_f['horario_txt'].tolist())
                        else: h_sel = "Selecione..."
                    else: m_sel = h_sel = "Selecione..."

                if "Selecione" not in f"{u_sel}{e_sel}{m_sel}{h_sel}":
                    id_vaga = df_f[df_f['horario_txt'] == h_sel].iloc[0]['id_x']
                    with st.form("f_agendar"):
                        fn, fs = st.text_input("Nome"), st.text_input("Sobrenome")
                        wt, cv = st.text_input("WhatsApp"), st.text_input("Convênio")
                        if st.form_submit_button("Confirmar Agendamento"):
                            if fn and wt:
                                supabase.table("CONSULTAS").update({"paciente_nome": fn, "paciente_sobrenome": fs, "paciente_telefone": wt, "paciente_convenio": cv, "status": "Marcada"}).eq("id", id_vaga).execute()
                                st.success("✅ Agendado!"); st.balloons(); st.rerun()
            else: st.warning("Existem horários livres com IDs antigos. Use o SQL Editor para limpar.")
        else: st.info("Sem horários disponíveis.")
    except Exception as e: st.error(f"Erro: {e}")

else:
    if verificar_senha():
        lista_u = buscar_unidades_db()
        esp_lista = sorted(["Cardiologia", "Clinica", "Dermatologia", "Endocrinologia", "Fonoaudiologia", "Ginecologia", "Nefrologia", "Neurologia", "Neuropsicologia", "Nutricionista", "ODONTOLOGIA", "Oftalmologia", "Ortopedia", "Pediatria", "Pneumologia", "Psicologia", "Psiquiatria", "Urologia"])

        if menu == "2. Abertura de Agenda":
            st.header("🏪 Abertura de Agenda")
            res_m = supabase.table("MEDICOS").select("*").execute()
            if res_m.data:
                med_dict = {f"{m['nome']} ({m['especialidade']})": m['id'] for m in res_m.data}
                sel = st.selectbox("Selecione o Médico", list(med_dict.keys()))
                c1, c2, c3 = st.columns(3)
                d, hi, hf = c1.date_input("Data"), c2.time_input("Início"), c3.time_input("Fim")
                if st.button("Gerar Grade"):
                    v = []
                    t, f = dt_lib.datetime.combine(d, hi), dt_lib.datetime.combine(d, hf)
                    while t < f:
                        v.append({"medico_id": med_dict[sel], "data_hora": t.isoformat(), "status": "Livre"})
                        t += dt_lib.timedelta(minutes=20)
                    supabase.table("CONSULTAS").insert(v).execute()
                    st.success("✅ Grade criada para o ID correto!")

        elif menu == "9. Editar Cadastro de Médico":
            st.header("📝 Editar Médico")
            res_m = supabase.table("MEDICOS").select("*").execute()
            if res_m.data:
                med_edit = {f"{m['nome']} ({m['especialidade']})": m for m in res_m.data}
                sel_m = st.selectbox("Médico:", ["Selecione..."] + list(med_edit.keys()))
                if sel_m != "Selecione...":
                    m_at = med_edit[sel_m]
                    with st.form("ed_f"):
                        novo_n = st.text_input("Nome", value=m_at['nome'])
                        nova_e = st.selectbox("Especialidade", esp_lista, index=esp_lista.index(m_at['especialidade']) if m_at['especialidade'] in esp_lista else 0)
                        nova_u = st.selectbox("Unidade", lista_u, index=lista_u.index(m_at['unidade']) if m_at['unidade'] in lista_u else 0)
                        if st.form_submit_button("Atualizar"):
                            supabase.table("MEDICOS").update({"nome": novo_n.upper(), "especialidade": nova_e, "unidade": nova_u}).eq("id", m_at['id']).execute()
                            st.success("Atualizado!"); st.rerun()
