import streamlit as st
from supabase import create_client
import pandas as pd
from datetime import datetime, timedelta

# --- CONFIGURAÇÃO DE CONEXÃO ---
URL_S = "https://mxsuvjgwpqzhaqbzrvdq.supabase.co"
KEY_S = "sb_publishable_O8qbHGfKbBb8ljAHb7ckuQ_mp16IThN"
supabase = create_client(URL_S, KEY_S)

st.set_page_config(page_title="Gestão Sempre Vida", layout="wide", page_icon="🏥")

# --- SISTEMA DE LOGIN ---
if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False

with st.sidebar:
    st.title("🏥 Menu Administrativo")
    if not st.session_state["autenticado"]:
        senha = st.text_input("Digite a Senha Admin", type="password")
        if st.button("Acessar Sistema"):
            if senha == "1234":
                st.session_state["autenticado"] = True
                st.rerun()
            else:
                st.error("Senha incorreta!")
    else:
        if st.button("Sair (Logout)"):
            st.session_state["autenticado"] = False
            st.rerun()

# Definir qual menu mostrar
if st.session_state["autenticado"]:
    menu = st.sidebar.radio("Navegação:", [
        "1. Cadastro de Médicos", 
        "2. Abrir Agenda", 
        "3. Marcar Consulta", 
        "4. Relatório de Consultas"
    ])
else:
    menu = "3. Marcar Consulta"  # Única tela que o paciente vê

# --- TELA 1: CADASTRO DE MÉDICOS ---
if menu == "1. Cadastro de Médicos":
    st.header("👨‍⚕️ Cadastro de Médicos / Especialidade / Unidade")
    with st.form("form_medicos", clear_on_submit=True):
        nome = st.text_input("Nome do Médico")
        especialidade = st.selectbox("Especialidade", ["Clínico Geral", "Cardiologia", "Ginecologia", "Ortopedia", "Pediatria", "Oftalmologia", "Dermatologia", "Otorrinolaringologia", "Endocrinologia", "Endocrinologia - Diabete e Tireoide", "Fonoaudiologia", "Neuropsicologia", "Neurologia", "Nefrologia", "Pneumologia", "Psicologia", "ODONTOLOGIA"])
        unidade = st.selectbox("Unidade", ["Praça 7 - Rua Carijos", "Praça 7 - Rua Rio de Janeiro", "Eldorado"])
        
        if st.form_submit_button("Salvar Médico"):
            if nome:
                supabase.table("MEDICOS").insert({
                    "nome": nome, "especialidade": especialidade, "unidade": unidade
                }).execute()
                st.success(f"Médico {nome} cadastrado com sucesso!")
            else:
                st.warning("Por favor, insira o nome do médico.")

# --- TELA 2: ABERTURA DE AGENDA (INTERVALOS) ---
elif menu == "2. Abrir Agenda":
    st.header("⏳ Abertura de Agenda por Intervalos")
    
    # Busca médicos e trata possíveis erros de conexão ou tabela vazia
    try:
        medicos_res = supabase.table("MEDICOS").select("*").execute()
        
        # Correção da lógica para evitar erro na linha 55:
        if medicos_res.data and len(medicos_res.data) > 0:
            lista_medicos = {m['nome']: m['id'] for m in medicos_res.data}
            med_escolhido = st.selectbox("Selecione o Médico", list(lista_medicos.keys()))
            
            col1, col2 = st.columns(2)
            data_atend = col1.date_input("Data do Atendimento", format="DD/MM/YYYY")
            hora_inicio = col1.time_input("Horário de Início")
            intervalo = col2.number_input("Duração de cada consulta (minutos)", value=20)
            total_horas = col2.slider("Total de horas de trabalho", 1, 10, 4)

            if st.button("Gerar Grade de Horários"):
                inicio_dt = datetime.combine(data_atend, hora_inicio)
                vagas = []
                # Gera as vagas com base no intervalo escolhido
                for i in range(0, int(total_horas * 60), int(intervalo)):
                    vaga_hora = inicio_dt + timedelta(minutes=i)
                    vagas.append({
                        "medico_id": lista_medicos[med_escolhido],
                        "data_hora": vaga_hora.isoformat(),
                        "status": "Livre"
                    })
                
                supabase.table("CONSULTAS").insert(vagas).execute()
                st.success(f"Agenda gerada com sucesso para {med_escolhido}!")
        else:
            st.info("⚠️ Nenhum médico encontrado. Cadastre um médico na Tela 1 antes de abrir a agenda.")
            
    except Exception as e:
        st.error(f"Erro ao acessar o banco de dados: {e}")
        

# --- TELA 3: MARCAÇÃO DE CONSULTA (PÚBLICA) ---

# --- TELA 3: MARCAÇÃO DE CONSULTA ---
elif menu == "3. Marcar Consulta":
    st.header("📅 Agendamento de Consultas")
    
    try:
        # Busca horários e médicos
        res_vagas = supabase.table("CONSULTAS").select(", MEDICOS()").eq("status", "Livre").execute()
        
        if res_vagas.data:
            vagas_validadas = []
            for r in res_vagas.data:
                # Segurança contra o erro NoneType visto nos prints
                med = r.get('MEDICOS') or r.get('medicos')
                if med and isinstance(med, dict):
                    dt = pd.to_datetime(r['data_hora'])
                    vagas_validadas.append({
                        'id': r['id'],
                        'unidade': med.get('unidade', 'N/I'),
                        'especialidade': med.get('especialidade', 'N/I'),
                        'medico': med.get('nome', 'N/I'),
                        'display_hora': dt.strftime('%d/%m/%Y às %H:%M'),
                        'data_sort': r['data_hora']
                    })
            
            if vagas_validadas:
                df = pd.DataFrame(vagas_validadas).sort_values(by='data_sort')
                
                # Filtros Sequenciais
                c1, c2 = st.columns(2)
                with c1:
                    sel_unidade = st.selectbox("🏥 1. Escolha a Unidade", sorted(df['unidade'].unique()))
                    df = df[df['unidade'] == sel_unidade]
                    sel_esp = st.selectbox("🩺 2. Escolha a Especialidade", sorted(df['especialidade'].unique()))
                    df = df[df['especialidade'] == sel_esp]
                with c2:
                    sel_med = st.selectbox("👨‍⚕️ 3. Escolha o Médico", sorted(df['medico'].unique()))
                    df = df[df['medico'] == sel_med]
                    sel_hora = st.selectbox("⏰ 4. Escolha o Horário", df['display_hora'].tolist())

                id_vaga = df[df['display_hora'] == sel_hora].iloc[0]['id']

                with st.form("finalizar"):
                    st.write(f"✅ Agendando com: *{sel_med}*")
                    col_a, col_b = st.columns(2)
                    n = col_a.text_input("Nome")
                    t = col_b.text_input("WhatsApp")
                    if st.form_submit_button("Confirmar Agendamento"):
                        if n and t:
                            supabase.table("CONSULTAS").update({"paciente_nome": n, "paciente_telefone": t, "status": "Marcada"}).eq("id", id_vaga).execute()
                            st.success("Agendado com sucesso!")
                            st.balloons()
            else:
                st.warning("Encontramos horários, mas eles não estão vinculados a médicos válidos.")
        else:
            st.info("Não há horários livres no momento.")
    except Exception as e:
        st.error(f"Erro de conexão: {e}")

# --- TELA 4: RELATÓRIO ---
# --- TELA 4: RELATÓRIO (CONFIRMAÇÃO DE CONSULTAS) ---
elif menu == "4. Relatório de Consultas":
    st.header("📋 Relatório Geral (Ordem Cronológica)")
    
    # Busca consultas que NÃO estão livres (Marcadas ou Confirmadas)
    try:
        res_relatorio = supabase.table("CONSULTAS").select(", MEDICOS()").neq("status", "Livre").execute()
        
        if res_relatorio.data and len(res_relatorio.data) > 0:
            dados = []
            for r in res_relatorio.data:
                # CORREÇÃO: Busca segura dos dados do médico (trata maiúsculas/minúsculas)
                medico = r.get('MEDICOS') or r.get('medicos')
                nome_medico = medico.get('nome', 'Não informado') if medico else 'Médico excluído'
                unidade_medico = medico.get('unidade', 'Não informada') if medico else 'N/A'
                
                dados.append({
                    "Data/Hora": r.get('data_hora'),
                    "Médico": nome_medico,
                    "Unidade": unidade_medico,
                    "Paciente": f"{r.get('paciente_nome', '')} {r.get('paciente_sobrenome', '')}".strip(),
                    "Telefone": r.get('paciente_telefone', 'N/A'),
                    "Convênio": r.get('paciente_convenio', 'Particular')
                })
            
            # Criar DataFrame e ordenar
            df_final = pd.DataFrame(dados)
            if not df_final.empty:
                st.dataframe(df_final.sort_values(by="Data/Hora"), use_container_width=True)
            else:
                st.info("Nenhuma consulta processada para exibição.")
                
        else:
            st.info("Nenhuma consulta agendada encontrada no sistema.")
            
    except Exception as e:
        st.error(f"Erro ao carregar o relatório: {e}")
