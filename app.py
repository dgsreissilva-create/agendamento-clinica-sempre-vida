import streamlit as st
import pandas as pd
import datetime as dt_lib
from supabase import create_client

# --- CONFIGURAÇÃO DO SUPABASE ---
# Verifique se estas variáveis estão corretas no seu código original
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

st.set_page_config(page_title="Clínica Sempre Vida", layout="wide")

# --- MENU LATERAL ---
st.sidebar.title("🏥 Sistema de Agendamento")
menu = st.sidebar.radio("Navegação", [
    "1. Cadastro de Médicos", 
    "2. Abertura de Agenda", 
    "3. Marcar Consulta"
])

# --- TELA 1: CADASTRO DE MÉDICOS ---
if menu == "1. Cadastro de Médicos":
    st.header("👨‍⚕️ Cadastro de Médicos")
    
    especialidades_lista = [
        "Cardiologia", "Clinica", "Dermatologia", "Endocrinologia - Diabete e Tireoide",
        "Fonoaudiologia", "Ginecologia", "Neurologia", "Neuropsicologia",
        "ODONTOLOGIA - DENTISTA", "Oftalmologia", "Ortopedia", 
        "Otorrinolaringologia", "Pediatria", "Pneumologia", "Psicologia"
    ]
    
    with st.form("form_medicos", clear_on_submit=True):
        nome = st.text_input("Nome do Médico")
        especialidade = st.selectbox("Especialidade", especialidades_lista)
        unidade = st.selectbox("Unidade", ["Praça 7 - Rua Carijos", "Praça 7 - Rua Rio de Janeiro", "Eldorado"])
        
        if st.form_submit_button("Salvar Médico"):
            if nome:
                try:
                    supabase.table("MEDICOS").insert({
                        "nome": nome, "especialidade": especialidade, "unidade": unidade
                    }).execute()
                    st.success(f"Médico {nome} cadastrado com sucesso!")
                except Exception as e:
                    st.error(f"Erro ao salvar: {e}")
            else:
                st.warning("Por favor, insira o nome do médico.")

# --- TELA 2: ABERTURA DE AGENDA ---
elif menu == "2. Abertura de Agenda":
    st.header("🏪 Abertura de Agenda Médica")
    try:
        res_med = supabase.table("MEDICOS").select("*").execute()
        if res_med.data:
            opcoes = {f"{m.get('nome')} ({m.get('especialidade')})": m.get('id') for m in res_med.data}
            escolha = st.selectbox("Selecione o Médico:", list(opcoes.keys()))
            id_medico_vinc = opcoes[escolha]

            st.markdown("---")
            col1, col2 = st.columns(2)
            data_age = col1.date_input("Data do Atendimento", format="DD/MM/YYYY")
            hora_ini = col2.time_input("Horário de Início", value=dt_lib.time(8, 0))
            
            c3, c4 = st.columns(2)
            qtd = c3.number_input("Quantidade de Vagas", min_value=1, value=10)
            int_min = c4.number_input("Intervalo (minutos)", min_value=5, value=20)

            if st.button("Gerar e Salvar Agenda"):
                lista_vagas = []
                ponto_inicio = dt_lib.datetime.combine(data_age, hora_ini)
                for i in range(int(qtd)):
                    horario_vaga = ponto_inicio + dt_lib.timedelta(minutes=i * int(int_min))
                    lista_vagas.append({
                        "medico_id": id_medico_vinc,
                        "data_hora": horario_vaga.isoformat(),
                        "status": "Livre"
                    })
                supabase.table("CONSULTAS").insert(lista_vagas).execute()
                st.success(f"✅ Agenda gerada para {escolha}!")
                st.balloons()
        else:
            st.warning("⚠️ Nenhum médico cadastrado. Vá na Tela 1.")
    except Exception as e:
        st.error(f"Erro ao carregar tela: {e}")

# --- TELA 3: MARCAÇÃO DE CONSULTA ---
elif menu == "3. Marcar Consulta":
    st.header("📅 Agendamento de Consultas")
    try:
        res_vagas = supabase.table("CONSULTAS").select(", MEDICOS()").eq("status", "Livre").execute()
        if res_vagas.data:
            vagas_limpas = []
            for r in res_vagas.data:
                m = r.get('MEDICOS') or r.get('medicos')
                if m and isinstance(m, dict):
                    dt = pd.to_datetime(r['data_hora'])
                    vagas_limpas.append({
                        'id': r['id'],
                        'unidade': m.get('unidade', 'N/I'),
                        'especialidade': m.get('especialidade', 'N/I'),
                        'medico': m.get('nome', 'N/I'),
                        'label_filtro': dt.strftime('%d/%m/%Y às %H:%M'),
                        'sort': r['data_hora']
                    })
            if vagas_limpas:
                df = pd.DataFrame(vagas_limpas).sort_values(by='sort')
                c1, c2 = st.columns(2)
                with c1:
                    u_sel = st.selectbox("🏥 Unidade", sorted(df['unidade'].unique()))
                    df = df[df['unidade'] == u_sel]
                    e_sel = st.selectbox("🩺 Especialidade", sorted(df['especialidade'].unique()))
                    df = df[df['especialidade'] == e_sel]
                with c2:
                    m_sel = st.selectbox("👨‍⚕️ Médico", sorted(df['medico'].unique()))
                    df = df[df['medico'] == m_sel]
                    h_sel = st.selectbox("⏰ Horário", df['label_filtro'].tolist())
                
                id_final = df[df['label_filtro'] == h_sel].iloc[0]['id']
                with st.form("form_final"):
                    st.write(f"📝 Agendando com: {m_sel} ({h_sel})")
                    c_f1, c_f2 = st.columns(2)
                    p_n = c_f1.text_input("Nome")
                    p_t = c_f2.text_input("WhatsApp")
                    if st.form_submit_button("Finalizar Agendamento"):
                        if p_n and p_t:
                            supabase.table("CONSULTAS").update({"paciente_nome": p_n, "paciente_telefone": p_t, "status": "Marcada"}).eq("id", id_final).execute()
                            st.success("✅ Consulta marcada!")
                            st.balloons()
            else:
                st.warning("🔎 Sem horários vinculados a médicos.")
        else:
            st.info("🔎 Não há horários livres.")
    except Exception as e:
        st.error(f"Erro: {e}")
