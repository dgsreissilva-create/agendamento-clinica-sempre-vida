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
    "4. Relatório de Agendamentos",
    "5. Cancelar Consulta",
    "6. Excluir Grade Aberta"  # <--- ADICIONE ESTA LINHA AQUI
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

# --- TELA 3: MARCAÇÃO DE CONSULTA (COMPLETA COM CAMPOS EM BRANCO) ---
elif menu == "3. Marcar Consulta":
    st.header("📅 Agendamento de Consultas")
    
    try:
        # Busca no banco
        res_vagas = supabase.table("CONSULTAS").select("*, MEDICOS(*)").eq("status", "Livre").execute()
        
        if res_vagas.data and len(res_vagas.data) > 0:
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
                        'display_horario': dt.strftime('%d/%m/%Y às %H:%M'),
                        'sort': r['data_hora']
                    })
            
            df_final = pd.DataFrame(vagas_limpas).sort_values(by='sort')

            # --- FILTROS EM CASCATA (INICIAM EM BRANCO) ---
            st.info("👋 Selecione as opções para encontrar sua consulta:")
            c1, c2 = st.columns(2)
            
            with c1:
                lista_unid = ["Selecione a Unidade..."] + sorted(df_final['unidade'].unique().tolist())
                u_sel = st.selectbox("1️⃣ Escolha a Unidade", lista_unid)
                
                if u_sel != "Selecione a Unidade...":
                    df_f = df_final[df_final['unidade'] == u_sel]
                    lista_esp = ["Selecione a Especialidade..."] + sorted(df_f['especialidade'].unique().tolist())
                    e_sel = st.selectbox("2️⃣ Escolha a Especialidade", lista_esp)
                else:
                    st.selectbox("2️⃣ Especialidade", ["Aguardando Unidade..."], disabled=True)
                    e_sel = "Selecione a Especialidade..."

            with c2:
                if e_sel != "Selecione a Especialidade..." and u_sel != "Selecione a Unidade...":
                    df_f = df_f[df_f['especialidade'] == e_sel]
                    lista_med = ["Selecione o Médico..."] + sorted(df_f['medico'].unique().tolist())
                    m_sel = st.selectbox("3️⃣ Escolha o Médico", lista_med)
                    
                    if m_sel != "Selecione o Médico...":
                        df_f = df_f[df_f['medico'] == m_sel]
                        lista_hora = ["Selecione o Horário..."] + df_f['display_horario'].tolist()
                        h_sel = st.selectbox("4️⃣ Escolha o Horário", lista_hora)
                    else:
                        st.selectbox("4️⃣ Horário", ["Aguardando Médico..."], disabled=True)
                        h_sel = "Selecione o Horário..."
                else:
                    st.selectbox("3️⃣ Médico", ["Aguardando Especialidade..."], disabled=True)
                    st.selectbox("4️⃣ Horário", ["Aguardando Médico..."], disabled=True)
                    m_sel = "Selecione o Médico..."
                    h_sel = "Selecione o Horário..."

            # --- FORMULÁRIO (SÓ APARECE SE TUDO FOR SELECIONADO) ---
            if "Selecione" not in f"{u_sel}{e_sel}{m_sel}{h_sel}":
                id_vaga = df_f[df_f['display_horario'] == h_sel].iloc[0]['id']
                st.markdown("---")
                with st.form("form_final_ok"):
                    st.write(f"📝 Confirmando: **{m_sel}** | **{h_sel}**")
                    f1, f2 = st.columns(2)
                    p_n = f1.text_input("Nome")
                    p_s = f1.text_input("Sobrenome")
                    p_t = f2.text_input("WhatsApp")
                    p_c = f2.text_input("Convênio")
                    
                    if st.form_submit_button("FINALIZAR AGENDAMENTO"):
                        if p_n and p_t:
                            supabase.table("CONSULTAS").update({
                                "paciente_nome": p_n, "paciente_sobrenome": p_s,
                                "paciente_telefone": p_t, "paciente_convenio": p_c,
                                "status": "Marcada"
                            }).eq("id", id_vaga).execute()
                            st.success("✅ Agendado com sucesso!")
                            st.balloons()
                        else:
                            st.error("⚠️ Nome e WhatsApp são obrigatórios.")
        else:
            st.info("🔎 No momento, não há horários livres disponíveis.")
    except Exception as e:
        st.error(f"Erro técnico: {e}")

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

# --- TELA 5: CANCELAMENTO DE CONSULTA ---
elif menu == "5. Cancelar Consulta":
    st.header("🚫 Cancelamento de Agendamentos")
    st.markdown("---")
    st.warning("Esta ação removerá os dados do paciente e tornará o horário disponível novamente na Tela 3.")

    try:
        # Busca apenas consultas que estão com status 'Marcada' para não listar horários vazios
        res = supabase.table("CONSULTAS").select("*, MEDICOS(*)").eq("status", "Marcada").execute()
        
        if res.data and len(res.data) > 0:
            dados_cancelar = []
            for r in res.data:
                m = r.get('MEDICOS') or r.get('medicos')
                dt = pd.to_datetime(r['data_hora'])
                
                # Criamos uma linha amigável para o usuário identificar a consulta
                paciente = f"{r.get('paciente_nome', '')} {r.get('paciente_sobrenome', '')}".strip()
                medico = m.get('nome', 'N/I')
                info = f"📅 {dt.strftime('%d/%m/%Y %H:%M')} | 👤 Paciente: {paciente} | 👨‍⚕️ Dr(a): {medico}"
                
                dados_cancelar.append({
                    'id': r['id'],
                    'info_completa': info
                })
            
            df_cancelar = pd.DataFrame(dados_cancelar)
            
            # Campo de seleção para o administrador/paciente escolher qual consulta cancelar
            st.subheader("Selecione o agendamento:")
            escolha_cancelar = st.selectbox("Consultas Marcadas:", ["Selecione um agendamento..."] + df_cancelar['info_completa'].tolist())
            
            if escolha_cancelar != "Selecione um agendamento...":
                id_para_cancelar = df_cancelar[df_cancelar['info_completa'] == escolha_cancelar].iloc[0]['id']

                # Botão de confirmação com cor de destaque (vermelho)
                if st.button("🔴 CONFIRMAR CANCELAMENTO DEFINITIVO"):
                    # O código limpa os campos do paciente e volta o status para 'Livre'
                    supabase.table("CONSULTAS").update({
                        "paciente_nome": None,
                        "paciente_sobrenome": None,
                        "paciente_telefone": None,
                        "paciente_convenio": None,
                        "status": "Livre"
                    }).eq("id", id_para_cancelar).execute()
                    
                    st.success("✨ Sucesso! O horário foi liberado e os dados do paciente foram removidos.")
                    st.balloons()
                    # O comando rerun faz a lista de cancelamento se atualizar na hora
                    st.rerun()
        else:
            st.info("🔎 No momento, não há nenhuma consulta marcada no sistema para ser cancelada.")
            
    except Exception as e:
        st.error(f"Ocorreu um erro ao processar o cancelamento: {e}")

# --- TELA 6: EXCLUIR GRADE ABERTA (CANCELAR ABERTURA) ---
elif menu == "6. Excluir Grade Aberta":
    st.header("🗑️ Excluir Horários Disponíveis")
    st.markdown("---")
    st.info("Esta tela permite apagar horários que estão **Livres**. Horários já marcados por pacientes não aparecem aqui.")

    try:
        # Busca apenas horários com status 'Livre'
        res = supabase.table("CONSULTAS").select("*, MEDICOS(*)").eq("status", "Livre").execute()
        
        if res.data and len(res.data) > 0:
            vagas_excluir = []
            for r in res.data:
                m = r.get('MEDICOS') or r.get('medicos')
                dt = pd.to_datetime(r['data_hora'])
                
                # Criamos a linha para identificação
                medico = m.get('nome', 'N/I')
                especialidade = m.get('especialidade', 'N/I')
                info = f"📅 {dt.strftime('%d/%m/%Y %H:%M')} | Médico: {medico} ({especialidade})"
                
                vagas_excluir.append({
                    'id': r['id'],
                    'info_completa': info
                })
            
            df_vagas = pd.DataFrame(vagas_excluir)
            
            st.subheader("Selecione os horários para apagar:")
            # Usamos multiselect para você poder apagar vários de uma vez só
            selecionados = st.multiselect("Horários Livres no Sistema:", df_vagas['info_completa'].tolist())
            
            if selecionados:
                ids_para_deletar = df_vagas[df_vagas['info_completa'].isin(selecionados)]['id'].tolist()

                if st.button("🗑️ EXCLUIR HORÁRIOS SELECIONADOS"):
                    # Deleta permanentemente as linhas do banco de dados
                    supabase.table("CONSULTAS").delete().in_("id", ids_para_deletar).execute()
                    
                    st.success(f"✅ {len(ids_para_deletar)} horário(s) removido(s) com sucesso!")
                    st.rerun()
        else:
            st.info("🔎 Não há horários 'Livres' para excluir.")
            
    except Exception as e:
        st.error(f"Erro ao processar exclusão: {e}")
