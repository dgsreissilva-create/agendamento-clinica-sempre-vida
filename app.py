import streamlit as st
import pandas as pd
import datetime as dt_lib
from supabase import create_client

# --- 1. CONFIGURAÇÕES INICIAIS ---
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

st.set_page_config(page_title="Clínica Sempre Vida", layout="wide")

# --- 2. MENU LATERAL ---
st.sidebar.title("🏥 Gestão Clínica")
menu = st.sidebar.radio("Navegação", [
    "1. Cadastro de Médicos", 
    "2. Abertura de Agenda", 
    "3. Marcar Consulta",
    "4. Relatório de Agendamentos"
])

# --- TELA 1: CADASTRO DE MÉDICOS ---
if menu == "1. Cadastro de Médicos":
    st.header("👨‍⚕️ Cadastro de Médicos e Especialidades")
    
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
                    st.success(f"✅ Médico {nome} cadastrado com sucesso!")
                except Exception as e:
                    st.error(f"Erro ao salvar: {e}")
            else:
                st.warning("⚠️ Digite o nome do médico.")

# --- TELA 2: ABERTURA DE AGENDA (GERAÇÃO PARA O BANCO) ---
elif menu == "2. Abertura de Agenda":
    st.header("🏪 Abertura de Agenda Médica")
    try:
        res_med = supabase.table("MEDICOS").select("*").execute()
        if res_med.data:
            opcoes = {f"{m['nome']} ({m['especialidade']})": m['id'] for m in res_med.data}
            escolha = st.selectbox("Selecione o Médico:", list(opcoes.keys()))
            id_medico_vinc = opcoes[escolha]

            st.divider()
            col1, col2 = st.columns(2)
            data_age = col1.date_input("Data do Atendimento", format="DD/MM/YYYY")
            hora_ini = col2.time_input("Horário de Início", value=dt_lib.time(8, 0))
            
            col3, col4 = st.columns(2)
            qtd = col3.number_input("Quantidade de Vagas", min_value=1, value=10)
            int_min = col4.number_input("Intervalo (minutos)", min_value=5, value=30)

            if st.button("Gerar e Salvar Grade"):
                vagas_batch = []
                ponto_partida = dt_lib.datetime.combine(data_age, hora_ini)
                for i in range(int(qtd)):
                    h_vaga = ponto_partida + dt_lib.timedelta(minutes=i * int(int_min))
                    vagas_batch.append({
                        "medico_id": id_medico_vinc, # Este ID conecta à tabela de Médicos
                        "data_hora": h_vaga.isoformat(),
                        "status": "Livre"
                    })
                # Salvando no banco de dados
                supabase.table("CONSULTAS").insert(vagas_batch).execute()
                st.success(f"✅ Agenda de {escolha} gerada e disponível para agendamento!")
                st.balloons()
        else:
            st.warning("⚠️ Cadastre um médico na Tela 1 primeiro.")
    except Exception as e:
        st.error(f"Erro ao gerar agenda: {e}")

# --- TELA 3: MARCAÇÃO DE CONSULTA (PUXANDO DO BANCO) ---
elif menu == "3. Marcar Consulta":
    st.header("📅 Agendamento de Consultas")
    try:
        # O asterisco (*) é fundamental para puxar todos os campos
        res_vagas = supabase.table("CONSULTAS").select("*, MEDICOS(*)").eq("status", "Livre").execute()
        
        if res_vagas.data:
            vagas_limpas = []
            for r in res_vagas.data:
                m = r.get('MEDICOS') or r.get('medicos')
                if m:
                    dt = pd.to_datetime(r['data_hora'])
                    vagas_limpas.append({
                        'id': r['id'],
                        'unidade': m.get('unidade', 'N/I'),
                        'especialidade': m.get('especialidade', 'N/I'),
                        'medico': m.get('nome', 'N/I'),
                        'horario_texto': dt.strftime('%d/%m/%Y às %H:%M'),
                        'sort': r['data_hora']
                    })
            
            if vagas_limpas:
                df = pd.DataFrame(vagas_limpas).sort_values(by='sort')
                
                c1, c2 = st.columns(2)
                with c1:
                    sel_unid = st.selectbox("🏥 1. Unidade", sorted(df['unidade'].unique()))
                    df = df[df['unidade'] == sel_unid]
                    sel_esp = st.selectbox("🩺 2. Especialidade", sorted(df['especialidade'].unique()))
                    df = df[df['especialidade'] == sel_esp]
                with c2:
                    sel_med = st.selectbox("👨‍⚕️ 3. Médico", sorted(df['medico'].unique()))
                    df = df[df['medico'] == sel_med]
                    sel_hora = st.selectbox("⏰ 4. Horário", df['horario_texto'].tolist())

                id_final = df[df['horario_texto'] == sel_hora].iloc[0]['id']

                with st.form("form_marcar"):
                    f1, f2 = st.columns(2)
                    p_nome = f1.text_input("Nome")
                    p_sobrenome = f1.text_input("Sobrenome")
                    p_tel = f2.text_input("WhatsApp")
                    p_conv = f2.text_input("Convênio")
                    
                    if st.form_submit_button("Confirmar Agendamento"):
                        if p_nome and p_tel:
                            supabase.table("CONSULTAS").update({
                                "paciente_nome": p_nome, "paciente_sobrenome": p_sobrenome,
                                "paciente_telefone": p_tel, "paciente_convenio": p_conv,
                                "status": "Marcada"
                            }).eq("id", id_final).execute()
                            st.success("✅ Consulta confirmada!")
                
        else:
            st.info("🔎 Não há horários disponíveis no momento. Gere horários na Tela 2.")
    except Exception as e:
        st.error(f"Erro ao carregar horários: {e}")

# --- TELA 4: RELATÓRIO ---
elif menu == "4. Relatório de Agendamentos":
    st.header("📋 Relatório Geral")
    try:
        res = supabase.table("CONSULTAS").select("*, MEDICOS(*)").execute()
        if res.data:
            relat = []
            for r in res.data:
                m = r.get('MEDICOS') or r.get('medicos')
                dt = pd.to_datetime(r['data_hora'])
                relat.append({
                    "Data/Hora": dt.strftime('%d/%m/%Y %H:%M'),
                    "Médico": m.get('nome', 'N/I') if m else "N/I",
                    "Paciente": f"{r.get('paciente_nome','')} {r.get('paciente_sobrenome','')}".strip() or "-",
                    "WhatsApp": r.get('paciente_telefone', '-'),
                    "Status": r.get('status')
                })
            st.dataframe(pd.DataFrame(relat), use_container_width=True)
    except Exception as e:
        st.error(f"Erro no relatório: {e}")
