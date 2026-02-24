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

# --- TELA 3: MARCAÇÃO DE CONSULTA (PÚBLICA) ---
elif menu == "3. Marcar Consulta":
    st.header("📅 Agendamento de Consultas")
    
    # Busca horários livres com dados detalhados
    res_vagas = supabase.table("CONSULTAS").select(", MEDICOS()").eq("status", "Livre").execute()
    
    if res_vagas.data and len(res_vagas.data) > 0:
        df_vagas = pd.DataFrame(res_vagas.data)
        
        # Tratamento de dados para facilitar os filtros
        def extrair_info(linha):
            med = linha.get('MEDICOS') or linha.get('medicos') or {}
            dt_obj = pd.to_datetime(linha['data_hora'])
            return pd.Series({
                'unid_nome': med.get('unidade', 'N/I'),
                'esp_nome': med.get('especialidade', 'N/I'),
                'med_nome': med.get('nome', 'N/I'),
                'dia_formatado': dt_obj.strftime('%d/%m/%Y'),
                'hora_formatada': dt_obj.strftime('%H:%M'),
                'timestamp': dt_obj
            })

        df_info = df_vagas.apply(extrair_info, axis=1)
        df_final = pd.concat([df_vagas, df_info], axis=1)

        st.info("👋 Olá! Selecione as opções abaixo para encontrar sua consulta:")

        # --- FILTROS SEQUENCIAIS ---
        c1, c2 = st.columns(2)
        with c1:
            lista_unidades = sorted(df_final['unid_nome'].unique())
            unidade_f = st.selectbox("1️⃣ Escolha a Unidade", lista_unidades)
            
            df_filtrado = df_final[df_final['unid_nome'] == unidade_f]
            lista_esps = sorted(df_filtrado['esp_nome'].unique())
            especialidade_f = st.selectbox("2️⃣ Escolha a Especialidade", lista_esps)

        with c2:
            df_filtrado = df_filtrado[df_filtrado['esp_nome'] == especialidade_f]
            lista_meds = sorted(df_filtrado['med_nome'].unique())
            medico_f = st.selectbox("3️⃣ Escolha o Médico", lista_meds)

            df_filtrado = df_filtrado[df_filtrado['med_nome'] == medico_f]
            # Criar opção combinada de Dia e Hora
            df_filtrado['horario_disp'] = df_filtrado['dia_formatado'] + " às " + df_filtrado['hora_formatada']
            horario_f = st.selectbox("4️⃣ Escolha o Dia e Horário", df_filtrado['horario_disp'].tolist())

        # Recuperar ID da vaga selecionada
        vaga_selecionada = df_filtrado[df_filtrado['horario_disp'] == horario_f].iloc[0]
        id_vaga = vaga_selecionada['id']

        # --- EXIBIÇÃO DO RESUMO ---
        st.markdown("### 📋 Resumo da sua Escolha")
        col_r1, col_r2, col_r3 = st.columns(3)
        col_r1.warning(f"*Unidade:*\n\n{unidade_f}")
        col_r2.warning(f"*Médico:*\n\n{medico_f}\n\n({especialidade_f})")
        col_r3.warning(f"*Data:*\n\n{horario_f}")

        # --- FORMULÁRIO FINAL ---
        with st.form("agendamento_final", clear_on_submit=True):
            st.write("🏃 *Quase lá! Preencha seus dados:*")
            col_f1, col_f2 = st.columns(2)
            p_nome = col_f1.text_input("Nome")
            p_sobre = col_f1.text_input("Sobrenome")
            p_tel = col_f2.text_input("WhatsApp (com DDD)")
            p_conv = col_f2.text_input("Convênio")
            
            if st.form_submit_button("FINALIZAR AGENDAMENTO"):
                if p_nome and p_tel:
                    try:
                        supabase.table("CONSULTAS").update({
                            "paciente_nome": p_nome, "paciente_sobrenome": p_sobre,
                            "paciente_telefone": p_tel, "paciente_convenio": p_conv,
                            "status": "Marcada"
                        }).eq("id", id_vaga).execute()
                        st.success("✨ Excelente! Sua consulta foi agendada com sucesso.")
                        st.balloons()
                    except Exception as e:
                        st.error(f"Erro ao salvar: {e}")
                else:
                    st.error("⚠️ Por favor, preencha pelo menos Nome e WhatsApp.")
    else:
        st.info("🔎 No momento, não temos horários livres para agendamento.")
        
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
