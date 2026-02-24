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

# --- TELA 1: CADASTRO DE MÉDICOS (Funcional) ---
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

# --- TELA 2: ABERTURA DE AGENDA (Com Vínculo de ID) ---
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
                        "medico_id": id_medico_vinc,
                        "data_hora": h_vaga.isoformat(),
                        "status": "Livre"
                    })
                supabase.table("CONSULTAS").insert(vagas_batch).execute()
                st.success(f"✅ Agenda de {escolha} gerada!")
                st.balloons()
        else:
            st.warning("⚠️ Cadastre um médico na Tela 1 primeiro.")
    except Exception as e:
        st.error(f"Erro ao carregar médicos: {e}")

# --- TELA 3: MARCAÇÃO DE CONSULTA (4 Campos Separados) ---

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


# --- TELA 4: RELATÓRIO DE AGENDAMENTOS (Formato de Tabela) ---
elif menu == "4. Relatório de Agendamentos":
    st.header("📋 Relatório Geral de Consultas")
    try:
        res = supabase.table("CONSULTAS").select(", MEDICOS()").execute()
        if res.data:
            lista_relat = []
            for r in res.data:
                m = r.get('MEDICOS') or r.get('medicos')
                dt = pd.to_datetime(r['data_hora'])
                lista_relat.append({
                    "Data/Hora": dt.strftime('%d/%m/%Y %H:%M'),
                    "Unidade": m.get('unidade', '-') if m else "-",
                    "Médico": m.get('nome', 'N/I') if m else "N/I",
                    "Especialidade": m.get('especialidade', '-') if m else "-",
                    "Paciente": f"{r.get('paciente_nome', '')} {r.get('paciente_sobrenome', '')}".strip() or "-",
                    "WhatsApp": r.get('paciente_telefone', '-'),
                    "Convênio": r.get('paciente_convenio', '-'),
                    "Status": r.get('status')
                })
            st.dataframe(pd.DataFrame(lista_relat), use_container_width=True)
        else:
            st.info("Nenhum registro encontrado.")
    except Exception as e:
        st.error(f"Erro no relatório: {e}")
