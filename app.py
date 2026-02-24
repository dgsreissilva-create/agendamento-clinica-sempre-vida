import streamlit as st
import pandas as pd
import datetime as dt_lib
from supabase import create_client

# --- CONFIGURAÇÃO DO SUPABASE ---
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

st.set_page_config(page_title="Clínica Sempre Vida", layout="wide")

# --- MENU LATERAL ---
st.sidebar.title("🏥 Sistema Clínico")
menu = st.sidebar.radio("Navegação", [
    "1. Cadastro de Médicos", 
    "2. Abertura de Agenda", 
    "3. Marcar Consulta",
    "4. Relatório de Agendamentos"
])

# --- TELA 1: CADASTRO DE MÉDICOS ---
if menu == "1. Cadastro de Médicos":
    st.header("👨S⚕️ Cadastro de Médicos")
    especialidades_lista = ["Cardiologia", "Clinica", "Dermatologia", "Endocrinologia", "Fonoaudiologia", "Ginecologia", "Neurologia", "Oftalmologia", "Ortopedia", "Pediatria", "Psicologia"]
    
    with st.form("form_medicos", clear_on_submit=True):
        nome = st.text_input("Nome do Médico")
        especialidade = st.selectbox("Especialidade", especialidades_lista)
        unidade = st.selectbox("Unidade", ["Praça 7 - Rua Carijos", "Praça 7 - Rua Rio de Janeiro", "Eldorado"])
        
        if st.form_submit_button("Salvar Médico"):
            if nome:
                supabase.table("MEDICOS").insert({"nome": nome, "especialidade": especialidade, "unidade": unidade}).execute()
                st.success(f"Médico {nome} cadastrado!")
            else:
                st.warning("Insira o nome.")

# --- TELA 2: ABERTURA DE AGENDA ---
elif menu == "2. Abertura de Agenda":
    st.header("🏪 Abertura de Agenda")
    try:
        res_med = supabase.table("MEDICOS").select("*").execute()
        if res_med.data:
            opcoes = {f"{m['nome']} ({m['especialidade']})": m['id'] for m in res_med.data}
            selecao = st.selectbox("Selecione o Médico:", list(opcoes.keys()))
            
            col1, col2 = st.columns(2)
            data_age = col1.date_input("Data", format="DD/MM/YYYY")
            hora_ini = col2.time_input("Início", value=dt_lib.time(8, 0))
            
            qtd = st.number_input("Qtd de Consultas", min_value=1, value=10)
            intervalo = st.number_input("Intervalo (min)", min_value=5, value=20)

            if st.button("Gerar Agenda"):
                vagas = []
                ponto = dt_lib.datetime.combine(data_age, hora_ini)
                for i in range(int(qtd)):
                    h = ponto + dt_lib.timedelta(minutes=i * int(intervalo))
                    vagas.append({"medico_id": opcoes[selecao], "data_hora": h.isoformat(), "status": "Livre"})
                supabase.table("CONSULTAS").insert(vagas).execute()
                st.success("Agenda Gerada!")
        else:
            st.warning("Cadastre um médico primeiro.")
    except Exception as e:
        st.error(f"Erro na Tela 2: {e}")

# --- TELA 3: MARCAÇÃO DE CONSULTA ---
elif menu == "3. Marcar Consulta":
    st.header("📅 Marcar Consulta")
    try:
        res = supabase.table("CONSULTAS").select(", MEDICOS()").eq("status", "Livre").execute()
        if res.data:
            dados = []
            for r in res.data:
                m = r.get('MEDICOS') or r.get('medicos')
                if m:
                    dt = pd.to_datetime(r['data_hora'])
                    dados.append({
                        'id': r['id'], 'unidade': m['unidade'], 'medico': m['nome'],
                        'especialidade': m['especialidade'], 'horario': dt.strftime('%d/%m/%Y %H:%M')
                    })
            if dados:
                df = pd.DataFrame(dados)
                u = st.selectbox("Unidade", sorted(df['unidade'].unique()))
                df = df[df['unidade'] == u]
                m = st.selectbox("Médico", sorted(df['medico'].unique()))
                df = df[df['medico'] == m]
                h = st.selectbox("Horário", df['horario'].tolist())
                
                with st.form("f_marcar"):
                    nome_p = st.text_input("Seu Nome")
                    tel_p = st.text_input("WhatsApp")
                    if st.form_submit_button("Confirmar"):
                        id_v = df[df['horario'] == h].iloc[0]['id']
                        supabase.table("CONSULTAS").update({"paciente_nome": nome_p, "paciente_telefone": tel_p, "status": "Marcada"}).eq("id", id_v).execute()
                        st.success("Marcado!")
        else:
            st.info("Sem horários livres.")
    except Exception as e:
        st.error(f"Erro na Tela 3: {e}")

# --- TELA 4: RELATÓRIO ---
elif menu == "4. Relatório de Agendamentos":
    st.header("📋 Relatório Geral")
    try:
        res = supabase.table("CONSULTAS").select(", MEDICOS()").execute()
        if res.data:
            relat = []
            for r in res.data:
                m = r.get('MEDICOS') or r.get('medicos')
                dt = pd.to_datetime(r['data_hora'])
                relat.append({
                    "Data/Hora": dt.strftime('%d/%m/%Y %H:%M'),
                    "Médico": m['nome'] if m else "N/I",
                    "Paciente": r.get('paciente_nome', '-'),
                    "Telefone": r.get('paciente_telefone', '-'),
                    "Status": r.get('status')
                })
            st.table(pd.DataFrame(relat))
    except Exception as e:
        st.error(f"Erro na Tela 4: {e}")
