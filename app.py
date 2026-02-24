import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, time # <--- O segredo está aqui
from supabase import create_client

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
# --- TELA 2: ABERTURA DE AGENDA (CÓDIGO COMPLETO) ---
elif menu == "2. Abertura de Agenda":
    st.header("🏪 Abertura de Agenda Médica")
    
    try:
        # 1. Busca médicos cadastrados no banco
        res_medicos = supabase.table("MEDICOS").select("*").execute()
        
        if res_medicos.data and len(res_medicos.data) > 0:
            # Cria a lista de médicos para seleção
            opcoes_medicos = {f"{m['nome']} ({m['especialidade']})": m['id'] for m in res_medicos.data}
            selecao = st.selectbox("Selecione o Médico para gerar os horários:", list(opcoes_medicos.keys()))
            id_medico_vinc = opcoes_medicos[selecao]

            st.divider()
            
            # 2. Configuração dos horários
            col1, col2 = st.columns(2)
            data_agenda = col1.date_input("Qual o dia do atendimento?", format="DD/MM/YYYY")
            # Usa o time(8, 0) que agora está importado corretamente
            hora_inicio = col2.time_input("Horário da primeira consulta", value=time(8, 0)) 
            
            col3, col4 = st.columns(2)
            qtd_vagas = col3.number_input("Quantas consultas serão realizadas?", min_value=1, max_value=50, value=10)
            tempo_min = col4.number_input("Tempo de cada consulta (minutos)", min_value=5, max_value=120, value=20)

            st.divider()

            # 3. Botão de Processamento
            if st.button("Gerar Grade de Horários e Salvar"):
                novas_vagas = []
                # Ponto de partida: data + hora inicial escolhida
                momento_atual = datetime.combine(data_agenda, hora_inicio)
                
                for i in range(int(qtd_vagas)):
                    # Calcula o horário de cada vaga somando o intervalo
                    horario_vaga = momento_atual + timedelta(minutes=i * int(tempo_min))
                    
                    # Monta o registro com o médico vinculado corretamente
                    novas_vagas.append({
                        "medico_id": id_medico_vinc, # Vínculo fundamental para a Tela 3
                        "data_hora": horario_vaga.isoformat(),
                        "status": "Livre"
                    })
                
                # Insere no Supabase
                supabase.table("CONSULTAS").insert(novas_vagas).execute()
                
                st.success(f"✅ Sucesso! Foram gerados {qtd_vagas} horários para {selecao}.")
                st.balloons()
        else:
            st.warning("⚠️ Nenhum médico cadastrado no sistema. Vá até a Tela 1 para cadastrar.")
            
    except Exception as e:
        st.error(f"Erro ao carregar os dados: {e}")
        st.info("Dica: Verifique se você adicionou 'from datetime import time' no topo do código.")


# --- TELA 3: MARCAÇÃO DE CONSULTA (PÚBLICA) ---

# --- TELA 3: MARCAÇÃO DE CONSULTA (PÚBLICA) ---
elif menu == "3. Marcar Consulta":
    st.header("📅 Agendamento de Consultas")
    
    try:
        # Busca horários LIVRES e os MEDICOS vinculados
        res_vagas = supabase.table("CONSULTAS").select(", MEDICOS()").eq("status", "Livre").execute()
        
        if res_vagas.data and len(res_vagas.data) > 0:
            vagas_limpas = []
            for r in res_vagas.data:
                # Segurança: Garante que o médico existe
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

                st.info("👋 Selecione as opções abaixo para encontrar seu horário:")

                # --- FILTROS EM CASCATA ---
                c1, c2 = st.columns(2)
                
                with c1:
                    # 1. Unidade
                    op_unidade = sorted(df['unidade'].unique())
                    sel_unidade = st.selectbox("🏥 1. Escolha a Unidade", op_unidade)
                    df_unid = df[df['unidade'] == sel_unidade]
                    
                    # 2. Especialidade
                    op_esp = sorted(df_unid['especialidade'].unique())
                    sel_esp = st.selectbox("🩺 2. Escolha a Especialidade", op_esp)
                    df_esp = df_unid[df_unid['especialidade'] == sel_esp]

                with c2:
                    # 3. Médico
                    op_med = sorted(df_esp['medico'].unique())
                    sel_med = st.selectbox("👨‍⚕️ 3. Escolha o Médico", op_med)
                    df_med = df_esp[df_esp['medico'] == sel_med]
                    
                    # 4. Horário (Aqui usamos 'label_filtro' que é o nome correto agora)
                    op_hora = df_med['label_filtro'].tolist()
                    sel_hora = st.selectbox("⏰ 4. Escolha o Dia e Horário", op_hora)

                # Pega o ID para salvar usando a seleção final
                id_final = df_med[df_med['label_filtro'] == sel_hora].iloc[0]['id']

                st.markdown("---")
                
                # --- FORMULÁRIO FINAL ---
                with st.form("form_final_agendamento", clear_on_submit=True):
                    st.write(f"📝 *Confirmando:* {sel_med} | {sel_hora}")
                    c_f1, c_f2 = st.columns(2)
                    p_n = c_f1.text_input("Nome")
                    p_s = c_f1.text_input("Sobrenome")
                    p_t = c_f2.text_input("WhatsApp (com DDD)")
                    p_c = c_f2.text_input("Convênio")
                    
                    if st.form_submit_button("FINALIZAR AGENDAMENTO"):
                        if p_n and p_t:
                            try:
                                supabase.table("CONSULTAS").update({
                                    "paciente_nome": p_n, 
                                    "paciente_sobrenome": p_s,
                                    "paciente_telefone": p_t, 
                                    "paciente_convenio": p_c,
                                    "status": "Marcada"
                                }).eq("id", id_final).execute()
                                st.success("✅ Consulta agendada com sucesso!")
                                st.balloons()
                            except Exception as e:
                                st.error(f"Erro ao salvar: {e}")
                        else:
                            st.error("⚠️ Nome e WhatsApp são obrigatórios!")
            else:
                st.warning("🔎 Horários encontrados, mas sem vínculo com médicos. Gere novos horários na Tela 2.")
        else:
            st.info("🔎 Não há horários 'Livres' no sistema. Abra a agenda na Tela 2.")
            
    except Exception as e:
        st.error(f"Erro técnico: {e}")

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
