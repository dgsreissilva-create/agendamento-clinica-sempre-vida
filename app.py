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
        especialidade = st.selectbox("Especialidade", ["Clínico Geral", "Cardiologia", "Ortopedia", "Pediatria", "Ginecologia"])
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
            data_atend = col1.date_input("Data do Atendimento")
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
        
# --- TELA 3: MARCAÇÃO DE CONSULTA ---
# --- TELA 3: MARCAÇÃO DE CONSULTA (PÚBLICA) ---

elif menu == "3. Marcar Consulta":
    st.header("📅 Agendamento de Consultas")
    
    # Busca horários livres trazendo os dados da tabela MEDICOS (o asterisco é essencial)
    res_vagas = supabase.table("CONSULTAS").select(", MEDICOS()").eq("status", "Livre").execute()
    
    if res_vagas.data and len(res_vagas.data) > 0:
        df_vagas = pd.DataFrame(res_vagas.data)
        
        try:
            # CORREÇÃO: Verifica se a chave MEDICOS existe (maiúscula ou minúscula)
            def formatar_exibicao(linha):
                # Tenta pegar os dados do médico independente da caixa das letras
                medico = linha.get('MEDICOS') or linha.get('medicos')
                if medico:
                    nome = medico.get('nome', 'Médico N/I')
                    unidade = medico.get('unidade', 'Unidade N/I')
                    return f"{nome} | {linha['data_hora']} | {unidade}"
                return f"Horário Avulso | {linha['data_hora']}"

            df_vagas['display'] = df_vagas.apply(formatar_exibicao, axis=1)
            
            vaga_sel = st.selectbox("Escolha o Médico e Horário", df_vagas['display'])
            id_vaga = df_vagas[df_vagas['display'] == vaga_sel]['id'].values[0]

            with st.form("form_paciente"):
                c1, c2 = st.columns(2)
                p_nome = c1.text_input("Nome")
                p_sobrenome = c1.text_input("Sobrenome")
                p_tel = c2.text_input("WhatsApp")
                p_conv = c2.text_input("Convênio")
                
                if st.form_submit_button("Confirmar Agendamento"):
                    if p_nome and p_tel:
                        supabase.table("CONSULTAS").update({
                            "paciente_nome": p_nome, 
                            "paciente_sobrenome": p_sobrenome,
                            "paciente_telefone": p_tel, 
                            "paciente_convenio": p_conv,
                            "status": "Marcada"
                        }).eq("id", id_vaga).execute()
                        st.success("Consulta marcada com sucesso!")
                        st.balloons()
                    else:
                        st.error("Nome e Telefone são obrigatórios!")
        except Exception as e:
            st.error(f"Erro ao processar lista de horários: {e}")
            # Log para te ajudar a debugar se o erro persistir
            st.write("Dados recebidos do banco:", res_vagas.data[0] if res_vagas.data else "Vazio")
    else:
        st.info("Não há horários livres disponíveis no momento.")
        
# --- TELA 4: RELATÓRIO ---
elif menu == "4. Relatório de Consultas":
    st.header("📋 Relatório Geral (Ordem Cronológica)")
    res_relatorio = supabase.table("CONSULTAS").select(", MEDICOS()").neq("status", "Livre").execute()
    
    if res_relatorio.data:
        dados = []
        for r in res_relatorio.data:
            dados.append({
                "Data/Hora": r['data_hora'],
                "Médico": r['MEDICOS']['nome'],
                "Unidade": r['MEDICOS']['unidade'],
                "Paciente": f"{r['paciente_nome']} {r['paciente_sobrenome']}",
                "Telefone": r['paciente_telefone'],
                "Convênio": r['paciente_convenio']
            })
        st.dataframe(pd.DataFrame(dados).sort_values(by="Data/Hora"), use_container_width=True)
    else:
        st.info("Nenhuma consulta agendada.")
