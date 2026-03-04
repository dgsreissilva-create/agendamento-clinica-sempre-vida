import streamlit as st
import pandas as pd
import datetime as dt_lib
from supabase import create_client

# --- 1. CONFIGURAÇÕES INICIAIS ---
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

st.set_page_config(page_title="Clínica Sempre Vida", layout="wide")
SENHA_ACESSO = "8484" 

# FUNÇÃO DE PAGINAÇÃO
def buscar_todos(tabela, select_str="*", filtros=None):
    page_size = 1000
    offset = 0
    dados = []
    while True:
        query = supabase.table(tabela).select(select_str).range(offset, offset + page_size - 1)
        if filtros:
            for f in filtros: query = query.eq(f[0], f[1])
        res = query.execute()
        if not res.data: break
        dados.extend(res.data)
        if len(res.data) < page_size: break
        offset += page_size
    return dados

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
    "9. Gestão de Especialidades"
    
], index=2)

def verificar_senha():
    if "autenticado" not in st.session_state: st.session_state["autenticado"] = False
    if not st.session_state["autenticado"]:
        st.subheader("🔒 Área Restrita")
        senha_digitada = st.text_input("Senha Administrativa:", type="password", key="pwd_main")
        if st.button("Liberar Acesso"):
            if senha_digitada == SENHA_ACESSO:
                st.session_state["autenticado"] = True
                st.rerun()
            else: st.error("Senha incorreta!")
        return False
    return True

# --- 3. LÓGICA DAS TELAS ---


# TELA 1 - CADASTRO (ATUALIZADA COM TODAS AS ESPECIALIDADES)
if menu == "1. Cadastro de Médicos":
    if verificar_senha():
        st.header("👨‍⚕️ Cadastro de Médicos")
        with st.form("f_med"):
            n = st.text_input("Nome do Médico")
            
            # LISTA COMPLETA E ATUALIZADA (LINHA 64)
            lista_especialidades = sorted([
                "Cardiologia", "Clinica", "Dermatologia", "Endocrinologia", 
                "Endocrinologia - Diabete e Tireoide", "Fonoaudiologia", "Ginecologia", 
                "Nefrologia", "Neurologia", "Neuropsicologia", "Nutricionista", 
                "ODONTOLOGIA", "Oftalmologia", "Ortopedia", "Otorrinolaringologia", 
                "Pediatria", "Pneumologia", "Psicologia", "Psiquiatria", "Urologia"
            ])
            
            e = st.selectbox("Especialidade", lista_especialidades)
            
            u = st.selectbox("Unidade", [
                "Pç 7 Rua Carijos 424 SL 2213", 
                "Pç 7 Rua Rio de Janeiro 462 SL 303", 
                "Eldorado Av Jose Faria da Rocha 4408 2 and",
                "Eldorado Av Jose Faria da Rocha 5959"
            ])
            
            if st.form_submit_button("Salvar"):
                if n:
                    supabase.table("MEDICOS").insert({
                        "nome": n.upper(), 
                        "especialidade": e, 
                        "unidade": u
                    }).execute()
                    st.success(f"Médico {n.upper()} cadastrado com sucesso!")
                else:
                    st.error("Por favor, digite o nome do médico.")




# TELA 2 - ABERTURA (CORRIGIDA)
elif menu == "2. Abertura de Agenda":
    if verificar_senha():
        # A partir daqui, TUDO tem que ter 4 espaços (um 'Tab') de recuo para a direita
        st.header("🏪 Abertura de Agenda")
        medicos = buscar_todos("MEDICOS")
        
        if medicos:
            df_meds = pd.DataFrame(medicos)
            u_filtro = st.selectbox("Selecione a Unidade para filtrar médicos:", sorted(df_meds['unidade'].unique().tolist()))
            df_filtrado = df_meds[df_meds['unidade'] == u_filtro].sort_values(by='nome')
            op = {f"{m['nome']} ({m['especialidade']})": m['id'] for _, m in df_filtrado.iterrows()}
            
            if not df_filtrado.empty:
                sel = st.selectbox("Médico Disponível nesta Unidade (Ordem Alfabética)", list(op.keys()))
                c1, c2, c3 = st.columns(3)
                d = c1.date_input("Data da Agenda", format="DD/MM/YYYY")
                hi = c2.time_input("Hora Início", value=dt_lib.time(8, 0))
                hf = c3.time_input("Hora Final", value=dt_lib.time(18, 0))
                inter = st.number_input("Intervalo (minutos)", 5, 120, 20)
                
                # ESTE BOTÃO SÓ APARECE SE A SENHA FOR LIBERADA ACIMA
               if st.button("Gerar Grade"):
                    # 1. DEFINIÇÃO DO PERÍODO
                    t_inicio_orig = dt_lib.datetime.combine(d, hi)
                    t_fim_orig = dt_lib.datetime.combine(d, hf)
                    
                    # 2. TRAVA ANTI-DUPLICIDADE
                    check = supabase.table("CONSULTAS").select("id") \
                        .eq("medico_id", op[sel]) \
                        .gte("data_hora", t_inicio_orig.isoformat()) \
                        .lte("data_hora", t_fim_orig.isoformat()) \
                        .execute()

                    if check.data:
                        st.warning(f"⚠️ Atenção: Já existe uma grade aberta para este médico neste período!")
                    else:
                        vagas = []
                        t_loop = t_inicio_orig
                        while t_loop < t_fim_orig:
                            vagas.append({
                                "medico_id": op[sel], 
                                "data_hora": t_loop.isoformat(), 
                                "status": "Livre"
                            })
                            t_loop += dt_lib.timedelta(minutes=inter)
                        
                        if vagas:
                            try:
                                supabase.table("CONSULTAS").insert(vagas).execute()
                                
                                # --- NOVO AVISO DETALHADO (SOLICITADO) ---
                                st.success(f"""
                                ### ✅ Agenda Aberta com Sucesso!
                                
                                **📍 Unidade:** {u_filtro}  
                                **👨‍⚕️ Médico:** {sel}  
                                **📅 Data:** {d.strftime('%d/%m/%Y')}  
                                **⏰ Horário:** {hi.strftime('%H:%M')} até {hf.strftime('%H:%M')}
                                """)
                                
                                # Opcional: st.balloons() # Para comemorar a grade gerada!
                                
                            except Exception as e:
                                st.error(f"Erro ao salvar no banco: {e}") 



# TELA 3 - MARCAR CONSULTA (VERSÃO CORRIGIDA COM MENSAGEM DE SUCESSO EXTERNA)
elif menu == "3. Marcar Consulta":
    st.header("📅 Agendamento de Consultas")

    # Inicializa variáveis de estado para o controle do sucesso
    if "agendamento_ok" not in st.session_state:
        st.session_state.agendamento_ok = False
    if "dados_confirmacao" not in st.session_state:
        st.session_state.dados_confirmacao = None
    if "bloqueio" not in st.session_state:
        st.session_state.bloqueio = False

    # 🔹 SE O AGENDAMENTO FOI FEITO COM SUCESSO, MOSTRA A MENSAGEM E O BOTÃO OK
    if st.session_state.agendamento_ok:
        d = st.session_state.dados_confirmacao
        st.success(f"""
        ### ✅ Agendamento Realizado com Sucesso!
        
        **Profissional:** {d['medico']}  
        **Especialidade:** {d['especialidade']}  
        **Data/Hora:** {d['horario']}  
        **Local:** {d['unidade']}
        """)
        
        if st.button("👍 OK, Próximo Agendamento"):
            st.session_state.agendamento_ok = False
            st.session_state.dados_confirmacao = None
            st.rerun()
            
    # 🔹 CASO CONTRÁRIO, MOSTRA O FLUXO NORMAL DE AGENDAMENTO
    else:
        # 1️⃣ Busca Médicos
        medicos_res = supabase.table("MEDICOS").select("*").execute()
        medicos = medicos_res.data

        if medicos:
            df_med = pd.DataFrame(medicos)
            u_sel = st.selectbox("1. Escolha a Unidade", sorted(df_med['unidade'].unique()))
            df_u = df_med[df_med['unidade'] == u_sel]

            esp_sel = st.selectbox("2. Escolha a Especialidade", sorted(df_u['especialidade'].unique()))
            df_esp = df_u[df_u['especialidade'] == esp_sel]

            m_sel = st.selectbox("3. Escolha o Médico", sorted(df_esp['nome'].unique()))
            medico_id = df_esp[df_esp['nome'] == m_sel].iloc[0]['id']

          # 2️⃣ Busca Horários Livres FUTUROS
            agora_iso = dt_lib.datetime.now().isoformat() # Captura data e hora atual
            
            consultas_res = supabase.table("CONSULTAS") \
                .select("*") \
                .eq("medico_id", medico_id) \
                .eq("status", "Livre") \
                .gte("data_hora", agora_iso) \
                .order("data_hora") \
                .limit(10000) \
                .execute()
            consultas = consultas_res.data

            if consultas:
                horarios = []
                for c in consultas:
                    dt = pd.to_datetime(c['data_hora'])
                    horarios.append({"id": c['id'], "display": dt.strftime('%d/%m/%Y %H:%M')})

                df_h = pd.DataFrame(horarios)
                h_sel = st.selectbox("4. Escolha o Horário", df_h['display'].tolist())
                id_vaga = df_h[df_h['display'] == h_sel].iloc[0]['id']

                # FORMULÁRIO DE PACIENTE
                with st.form("form_paciente", clear_on_submit=True):
                    c1, c2 = st.columns(2)
                    pn = c1.text_input("Nome")
                    ps = c1.text_input("Sobrenome")
                    pt = c2.text_input("WhatsApp")
                    pc = c2.text_input("Convênio")

                    submit = st.form_submit_button("Finalizar Agendamento")

                    if submit:
                        if st.session_state.bloqueio:
                            st.warning("⏳ Processando...")
                            st.stop()

                        if pn and pt:
                            st.session_state.bloqueio = True
                            
                            # Update no Banco de Dados
                            resposta = supabase.table("CONSULTAS").update({
                                "paciente_nome": pn.upper(),
                                "paciente_sobrenome": ps.upper(),
                                "paciente_telefone": pt,
                                "paciente_convenio": pc.upper() if pc else "PARTICULAR",
                                "status": "Marcada"
                            }).eq("id", id_vaga).eq("status", "Livre").execute()

                            if resposta.data:
                                # Salva os dados para mostrar a confirmação fora do form
                                st.session_state.dados_confirmacao = {
                                    "medico": m_sel,
                                    "especialidade": esp_sel,
                                    "horario": h_sel,
                                    "unidade": u_sel
                                }
                                st.session_state.agendamento_ok = True
                                st.session_state.bloqueio = False
                                st.rerun()
                            else:
                                st.session_state.bloqueio = False
                                st.error("⚠️ Horário ocupado ou indisponível.")
                        else:
                            st.warning("⚠️ Preencha Nome e WhatsApp!")
            else:
                st.info("Este médico não possui horários livres.")
        else:
            st.error("Nenhum médico cadastrado.")




# TELA 4 - RELATÓRIO DE CONSULTAS FUTURAS (VERSÃO BLINDADA)
elif menu == "4. Relatório de Agendamentos":
    if verificar_senha():
        st.header("📋 Confirmações De Agendas")
        
        agora_br = dt_lib.datetime.now()
        hoje_inicio = agora_br.replace(hour=0, minute=0, second=0, microsecond=0)

        dados_res = supabase.table("CONSULTAS") \
            .select("*, MEDICOS(*)") \
            .eq("status", "Marcada") \
            .gte("data_hora", hoje_inicio.isoformat()) \
            .order("id", desc=True) \
            .limit(10000) \
            .execute()

        dados = dados_res.data

        if dados:
            rel = []
            for r in dados:
                m = r.get('MEDICOS') or r.get('medicos') or {}
                dt_vaga = pd.to_datetime(r['data_hora'])
                pac = f"{r.get('paciente_nome','')} {r.get('paciente_sobrenome','')}".strip()
                tel_limpo = ''.join(filter(str.isdigit, str(r.get('paciente_telefone', ''))))
                
                msg = (f"Olá, Gentileza Confirmar consulta Dr.(a) "
                       f"{m.get('nome')} / {m.get('especialidade')} / "
                       f"{dt_vaga.strftime('%d/%m/%Y %H:%M')} / {m.get('unidade')}")

                link_zap = (f"https://wa.me/55{tel_limpo}?text={msg.replace(' ', '%20')}" if tel_limpo else "")

                rel.append({
                    "ID": r['id'], "Unidade": m.get('unidade'), "Data/Hora": dt_vaga,
                    "Médico": m.get('nome'), "Paciente": pac, "Telefone": r.get('paciente_telefone'),
                    "WhatsApp Link": link_zap, "Confirmado?": r.get('confirmado', False),
                    "Data_Pura": dt_vaga.date()
                })

            df_total = pd.DataFrame(rel)

            unidades_q1 = ["Eldorado Av Jose Faria da Rocha 4408 2 andar", "Eldorado Av Jose Faria da Rocha 4408 2 and", "Eldorado Av Jose Faria da Rocha 5959"]
            unidades_q2 = ["Pç 7 Rua Carijos 424 SL 2213"]
            unidades_q3 = ["Pç 7 Rua Rio de Janeiro 462 SL 303"]

            def renderizar_quadro(titulo, lista_unidades):
                df_q = df_total[df_total['Unidade'].isin(lista_unidades)].copy()
                st.subheader(titulo)
                if not df_q.empty:
                    df_q = df_q.set_index('ID').sort_values(by=['Unidade', 'Data_Pura', 'Médico', 'Data/Hora'])
                    edited_df = st.data_editor(
                        df_q.drop(columns=["Data_Pura"]),
                        column_config={
                            "Data/Hora": st.column_config.DatetimeColumn("Data/Hora", format="DD/MM/YYYY HH:mm"),
                            "WhatsApp Link": st.column_config.LinkColumn("📱 Link Direto", display_text="https://wa.me"),
                            "Confirmado?": st.column_config.CheckboxColumn("✅ Marcar ao Enviar")
                        },
                        use_container_width=True,
                        key=f"editor_{titulo.replace(' ', '_')}"
                    )
                    if st.button(f"💾 Salvar Confirmações - {titulo}"):
                        for original_id, row in edited_df.iterrows():
                            supabase.table("CONSULTAS").update({"confirmado": row['Confirmado?']}).eq("id", original_id).execute()
                        st.success(f"✅ Salvo!")
                        st.rerun()
                else:
                    st.info(f"Sem agendamentos futuros.")
                st.divider()

            renderizar_quadro("🏢 Eldorado", unidades_q1)
            renderizar_quadro("🏢 Pç 7 (Carijós)", unidades_q2)
            renderizar_quadro("🏢 Pç 7 (Rio de Janeiro)", unidades_q3)
        else:
            st.info("Não há consultas marcadas.")


# TELA 4 - RELATÓRIO DE CONSULTAS FUTURAS (VERSÃO BLINDADA E ESTÁVEL)
elif menu == "4. Relatório de Agendamentos":
    if verificar_senha():
        st.header("📋 Confirmações De Agendas")
        
        # 🕒 ESTABILIZAÇÃO: Filtra do início do dia de hoje (00:00) em diante
        # Isso impede que consultas de hoje sumam da tela após o salvamento
        agora_br = dt_lib.datetime.now()
        hoje_inicio = agora_br.replace(hour=0, minute=0, second=0, microsecond=0)

        # 🔒 BUSCA AMPLIADA E INVERTIDA (Garante Eldorado e Especialidades do final da lista)
        dados_res = supabase.table("CONSULTAS") \
            .select("*, MEDICOS(*)") \
            .eq("status", "Marcada") \
            .gte("data_hora", hoje_inicio.isoformat()) \
            .order("id", desc=True) \
            .limit(10000) \
            .execute()

        dados = dados_res.data

        if dados:
            rel = []
            for r in dados:
                m = r.get('MEDICOS') or r.get('medicos') or {}
                dt_vaga = pd.to_datetime(r['data_hora'])
                
                pac = f"{r.get('paciente_nome','')} {r.get('paciente_sobrenome','')}".strip()
                tel_limpo = ''.join(filter(str.isdigit, str(r.get('paciente_telefone', ''))))
                
                msg = (
                    f"Olá, Gentileza Confirmar consulta Dr.(a) "
                    f"{m.get('nome')} / {m.get('especialidade')} / "
                    f"{dt_vaga.strftime('%d/%m/%Y %H:%M')} / {m.get('unidade')}"
                )

                link_zap = (
                    f"https://wa.me/55{tel_limpo}?text={msg.replace(' ', '%20')}"
                    if tel_limpo else ""
                )

                rel.append({
                    "ID": r['id'], 
                    "Unidade": m.get('unidade'),
                    "Data/Hora": dt_vaga,
                    "Médico": m.get('nome'),
                    "Paciente": pac,
                    "Telefone": r.get('paciente_telefone'),
                    "WhatsApp Link": link_zap,
                    "Confirmado?": r.get('confirmado', False),
                    "Data_Pura": dt_vaga.date()
                })

            df_total = pd.DataFrame(rel)

            # 🔹 DEFINIÇÃO DOS GRUPOS (Incluindo variações de Eldorado)
            unidades_q1 = [
                "Eldorado Av Jose Faria da Rocha 4408 2 andar", 
                "Eldorado Av Jose Faria da Rocha 4408 2 and",
                "Eldorado Av Jose Faria da Rocha 5959"
            ]
            unidades_q2 = ["Pç 7 Rua Carijos 424 SL 2213"]
            unidades_q3 = ["Pç 7 Rua Rio de Janeiro 462 SL 303"]

            # 🔹 FUNÇÃO DE RENDERIZAÇÃO E SALVAMENTO SEGURO
            def renderizar_quadro(titulo, lista_unidades):
                df_q = df_total[df_total['Unidade'].isin(lista_unidades)].copy()
                
                st.subheader(titulo)
                if not df_q.empty:
                    # AMARRAÇÃO PELO ID: O ID vira o index para não dar erro de salvamento
                    df_q = df_q.set_index('ID')
                    df_q = df_q.sort_values(by=['Unidade', 'Data_Pura', 'Médico', 'Data/Hora'])
                    
                    # Exibição do Editor
                    edited_df = st.data_editor(
                        df_q.drop(columns=["Data_Pura"]),
                        column_config={
                            "Data/Hora": st.column_config.DatetimeColumn("Data/Hora", format="DD/MM/YYYY HH:mm"),
                            "WhatsApp Link": st.column_config.LinkColumn("📱 Link Direto", display_text="https://wa.me"),
                            "Confirmado?": st.column_config.CheckboxColumn("✅ Marcar ao Enviar")
                        },
                        use_container_width=True,
                        hide_index=False,
                        key=f"editor_{titulo.replace(' ', '_')}"
                    )

                    # Botão de Salvar Específico do Quadro
                    if st.button(f"💾 Salvar Confirmações - {titulo}"):
                        try:
                            contador = 0
                            # iterrows() com o ID como index garante o update correto
                            for original_id, row in edited_df.iterrows():
                                novo_status = row['Confirmado?']
                                supabase.table("CONSULTAS")\
                                    .update({"confirmado": novo_status})\
                                    .eq("id", original_id)\
                                    .execute()
                                contador += 1
                            
                            st.success(f"✅ {contador} registros de {titulo} salvos!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erro ao salvar: {e}")
                else:
                    st.info(f"Sem agendamentos futuros para este grupo.")
                st.divider()

            # 🔹 EXECUÇÃO DOS 3 QUADROS
            renderizar_quadro("🏢 Eldorado", unidades_q1)
            renderizar_quadro("🏢 Pç 7 (Carijós)", unidades_q2)
            renderizar_quadro("🏢 Pç 7 (Rio de Janeiro)", unidades_q3)
            
        else:
            st.info("Não há consultas marcadas para o futuro.")





# TELA 5 - CANCELAR CONSULTA (DATA BRASIL E NOME DO MÉDICO)
elif menu == "5. Cancelar Consulta":
    if verificar_senha():
        st.header("🚫 Cancelar Consulta")
        
        # 🔒 Busca estendida para garantir que todos os agendamentos futuros apareçam
        # Incluímos o JOIN com MEDICOS para pegar o nome do profissional
        dados_res = supabase.table("CONSULTAS")\
            .select("*, MEDICOS(*)")\
            .eq("status", "Marcada")\
            .limit(10000)\
            .execute()
        
        dados = dados_res.data
        
        if dados:
            opcoes = {}
            for r in dados:
                m = r.get('MEDICOS') or r.get('medicos') or {}
                # Ajuste da Data para padrão Brasil
                dt_obj = pd.to_datetime(r['data_hora'])
                data_br = dt_obj.strftime('%d/%m/%Y %H:%M')
                
                nome_paciente = r.get('paciente_nome') or "Paciente s/ nome"
                nome_medico = m.get('nome') or "Médico s/ nome"
                
                # Criando o texto de exibição: Paciente | Data | Médico
                texto_display = f"👤 {nome_paciente.upper()} | 📅 {data_br} | 👨‍⚕️ {nome_medico}"
                opcoes[texto_display] = r['id']
            
            # Seletor com as informações organizadas
            selecionado = st.selectbox("Selecione o agendamento para cancelar:", list(opcoes.keys()))
            id_cancelar = opcoes[selecionado]
            
            if st.button("Confirmar Cancelamento"):
                # 🔒 Executa o cancelamento limpando os dados do paciente e voltando o status para Livre
                # Limpamos também sobrenome e convênio para a vaga ficar totalmente nova
                res = supabase.table("CONSULTAS").update({
                    "status": "Livre", 
                    "paciente_nome": None, 
                    "paciente_sobrenome": None,
                    "paciente_telefone": None,
                    "paciente_convenio": None,
                    "confirmado": False
                }).eq("id", id_cancelar).execute()
                
                if res.data:
                    st.success(f"✅ O agendamento foi cancelado e o horário está livre novamente!")
                    st.rerun()
                else:
                    st.error("Erro ao processar o cancelamento. Tente novamente.")
        else:
            st.info("Não há consultas marcadas no momento para realizar cancelamentos.")





# TELA 6 - EXCLUIR GRADE ABERTA (AJUSTE: NOME + DATA + UNIDADE)
elif menu == "6. Excluir Grade Aberta":
    if verificar_senha():
        st.header("🗑️ Remover Horários Livres (Futuro)")
        
        # Puxa as vagas livres com os dados dos médicos
        dados = buscar_todos("CONSULTAS", "*, MEDICOS(*)", filtros=[("status", "Livre")])
        
        if dados:
            agora = dt_lib.datetime.now().replace(tzinfo=None)
            lista_futura = []
            
            for r in dados:
                dt_vaga = pd.to_datetime(r['data_hora']).replace(tzinfo=None)
                
                # Filtro para mostrar apenas o que for de agora para frente
                if dt_vaga >= agora:
                    m = r.get('MEDICOS') or r.get('medicos') or {}
                    m_nome = m.get('nome', 'Médico N/I')
                    m_unidade = m.get('unidade', 'Unidade N/I')
                    
                    # Formatação solicitada: NOME | DATA HORÁRIO | UNIDADE
                    texto_exibicao = f"{m_nome} | {dt_vaga.strftime('%d/%m/%Y %H:%M')} | {m_unidade}"
                    
                    lista_futura.append({
                        'id': r['id'], 
                        'info': texto_exibicao
                    })
            
            if lista_futura:
                df_ex = pd.DataFrame(lista_futura)
                # O multiselect agora mostrará o nome, data e a unidade à direita
                sel = st.multiselect("Selecione os horários para remover:", df_ex['info'].tolist())
                
                if st.button("Excluir Horários Selecionados"):
                    ids_para_excluir = df_ex[df_ex['info'].isin(sel)]['id'].tolist()
                    if ids_para_excluir:
                        supabase.table("CONSULTAS").delete().in_("id", ids_para_excluir).execute()
                        st.success(f"✅ Removido com sucesso!")
                        st.rerun()
            else:
                st.info("Não há horários livres futuros para exibir.")
        else:
            st.info("Nenhuma grade aberta encontrada.")



# TELA 7 - EXCLUIR CADASTRO DE MÉDICO (CORRIGIDA COM BUSCA TOTAL)
elif menu == "7. Excluir Cadastro de Médico":
    if verificar_senha():
        st.header("👨‍⚕️ Remover Cadastro de Médico")
        
        # AJUSTE FINO: Usando a função de paginação para garantir que busque TODOS os médicos
        meds = buscar_todos("MEDICOS")
        
        if meds:
            # Transformando em DataFrame para ordenar de A a Z por nome
            df_m = pd.DataFrame(meds).sort_values('nome')
            
            # Criando o dicionário de opções para o seletor
            op = {f"{r['nome']} ({r['especialidade']}) - {r['unidade']}": r['id'] for _, r in df_m.iterrows()}
            
            sel = st.selectbox("Escolha o médico para remover permanentemente:", list(op.keys()))
            
            st.warning(f"⚠️ Atenção: Ao excluir o cadastro de {sel}, você não poderá reverter esta ação.")
            
            if st.button("CONFIRMAR EXCLUSÃO PERMANENTE"):
                try:
                    supabase.table("MEDICOS").delete().eq("id", op[sel]).execute()
                    st.success(f"O cadastro de {sel} foi removido com sucesso!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao excluir: {e}")
        else:
            st.info("Não foram encontrados médicos cadastrados no banco de dados.")





# =========================================================
# TELA 8 - RELATÓRIO GERENCIAL (FOCO EM DATAS FUTURAS)
# CORRIGIDO NOS INDICADORES
# =========================================================

elif menu == "8. Relatório Gerencial":

    if verificar_senha():

        st.header("📊 Resumo de Ocupação por Dia")

        dados_consultas = buscar_todos("CONSULTAS")
        dados_medicos = buscar_todos("MEDICOS")

        if dados_consultas:

            df = pd.DataFrame(dados_consultas)

            # 🔒 Segurança de dados
            df = df[df['data_hora'].notna()].copy()
            df['data_dt'] = pd.to_datetime(df['data_hora'], errors='coerce').dt.date
            df = df[df['data_dt'].notna()]

            hoje_dt = dt_lib.datetime.now().date()
            ontem_dt = hoje_dt - dt_lib.timedelta(days=1)
            ante_dt = hoje_dt - dt_lib.timedelta(days=2)

            # =========================================================
            # 🔹 RESUMO COMPLETO CORRIGIDO
            # =========================================================

            resumo_completo = (
                df.groupby('data_dt')
                .agg(
                    Total_Vagas=('id', 'count'),
                    Agendados=('status', lambda x: (x == 'Marcada').sum())
                )
                .reset_index()
            )

            # =========================================================
            # 🔹 PARTE 1 - TABELA FUTURA (INALTERADA VISUALMENTE)
            # =========================================================

            resumo_futuro = resumo_completo[resumo_completo['data_dt'] >= hoje_dt].copy()
            resumo_futuro = resumo_futuro.sort_values('data_dt', ascending=True)
            resumo_futuro['Data'] = resumo_futuro['data_dt'].apply(lambda x: x.strftime('%d/%m/%Y'))

            st.write("### Ocupação Diária (Hoje e Futuro)")

            if not resumo_futuro.empty:
                st.dataframe(
                    resumo_futuro[['Data', 'Total_Vagas', 'Agendados']],
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.info("Não há grades abertas para datas futuras.")

            # =========================================================
            # 🔹 PARTE 2 - MÉDICOS SEM GRADE FUTURA (INALTERADO)
            # =========================================================

            st.divider()
            st.subheader("⚠️ Médicos sem Grade Aberta (Futuro)")

            if dados_medicos:

                df_meds = pd.DataFrame(dados_medicos)
                df_futuro_consultas = df[df['data_dt'] >= hoje_dt]
                ids_com_grade = df_futuro_consultas['medico_id'].unique()
                meds_sem_grade = df_meds[~df_meds['id'].isin(ids_com_grade)]

                if not meds_sem_grade.empty:
                    meds_sem_grade = meds_sem_grade.sort_values('nome')
                    st.dataframe(
                        meds_sem_grade[['nome', 'especialidade', 'unidade']],
                        use_container_width=True,
                        hide_index=True
                    )
                else:
                    st.success("✅ Todos os médicos possuem grades futuras.")

            # =========================================================
            # 🔹 PARTE 3 - INDICADORES CORRIGIDOS
            # =========================================================

            st.divider()
            st.subheader("📈 Comparativo de Desempenho")

            def get_agendados(data):
                filtro = df[df['data_dt'] == data]
                return int((filtro['status'] == 'Marcada').sum())

            def get_vagas(data):
                filtro = df[df['data_dt'] == data]
                return int(len(filtro))

            # 🔹 PACIENTES AGENDADOS
            st.write("**Pacientes Agendados:**")
            a1, a2, a3 = st.columns(3)

            a1.metric(f"Hoje ({hoje_dt.strftime('%d/%m')})", get_agendados(hoje_dt))
            a2.metric(f"Ontem ({ontem_dt.strftime('%d/%m')})", get_agendados(ontem_dt))
            a3.metric(f"Anteontem ({ante_dt.strftime('%d/%m')})", get_agendados(ante_dt))

            # 🔹 GRADES ABERTAS
            st.write("**Grades Abertas (Total):**")
            g1, g2, g3 = st.columns(3)

            g1.metric(f"Hoje ({hoje_dt.strftime('%d/%m')})", get_vagas(hoje_dt))
            g2.metric(f"Ontem ({ontem_dt.strftime('%d/%m')})", get_vagas(ontem_dt))
            g3.metric(f"Anteontem ({ante_dt.strftime('%d/%m')})", get_vagas(ante_dt))

            # =========================================================
            # 🔹 TOTAL GERAL (INALTERADO VISUAL)
            # =========================================================

            st.divider()
            c1, c2 = st.columns(2)

            c1.metric("Total Geral de Vagas (Sistema)", len(df))
            c2.metric("Total Geral Agendado", len(df[df['status'] == 'Marcada']))







# ==========================================================
# TELA 9: GESTÃO DINÂMICA (UNIDADES REAIS DO BANCO)
# ==========================================================

navegador = locals().get('menu') or locals().get('menu_selecionado') or locals().get('escolha')

if navegador == "9. Gestão de Especialidades":
    
    # --- BUSCA AUTOMÁTICA DA VARIÁVEL DE LOGIN ---
    logado_real = False
    for k, v in st.session_state.items():
        if v == True and k not in ['menu', 'sidebar']:
            logado_real = True
            break

    if not logado_real:
        st.error("🔒 Acesso Restrito. Por favor, realize o login na Tela Inicial.")
    else:
        st.title("🛡️ Gestão de Especialidades e Unidades")
        st.markdown("---")

        # --- FUNÇÃO 1: BUSCAR ESPECIALIDADES (Tabela MEDICOS) ---
        def buscar_especialidades_t9():
            try:
                res = supabase.table("MEDICOS").select("especialidade").execute()
                if res.data:
                    bruto = [i['especialidade'] for i in res.data if i['especialidade']]
                    return sorted(list(set(bruto)))
                return []
            except: return []

        # --- FUNÇÃO 2: BUSCAR UNIDADES REAIS (Tabela UNIDADES) ---
        def buscar_unidades_reais():
            try:
                # Busca na sua tabela UNIDADES
                res = supabase.table("UNIDADES").select("nome").execute()
                if res.data:
                    # Puxa os nomes completos (Eldorado Av Jose..., etc)
                    lista = [i['nome'] for i in res.data if i['nome']]
                    return sorted(list(set(lista)))
                return ["Pç 7 Rua Carijos 424 SL 2213", 
                "Pç 7 Rua Rio de Janeiro 462 SL 303", 
                "Eldorado Av Jose Faria da Rocha 4408 2 and",
                "Eldorado Av Jose Faria da Rocha 5959"] # Backup
            except:
                return ["Pç 7 Rua Carijos 424 SL 2213", 
                "Pç 7 Rua Rio de Janeiro 462 SL 303", 
                "Eldorado Av Jose Faria da Rocha 4408 2 and",
                "Eldorado Av Jose Faria da Rocha 5959"]

        c1, c2 = st.columns(2)

        with c1:
            st.subheader("➕ Adicionar Categoria")
            n_esp = st.text_input("Nome da Especialidade", key="t9_f_esp").strip().title()
            n_med = st.text_input("Médico Responsável", key="t9_f_med")
            
            # --- MENU DE UNIDADES DINÂMICO ---
            unidades_banco = buscar_unidades_reais()
            n_uni = st.selectbox("Escolha a Unidade Correta", unidades_banco, key="t9_f_unid")

            if st.button("Ativar Categoria", key="t9_f_btn", use_container_width=True):
                if n_esp and n_med:
                    try:
                        # Salva na tabela MEDICOS relacionando com a unidade escolhida
                        supabase.table("MEDICOS").insert({"nome": n_med, "especialidade": n_esp, "unidade": n_uni}).execute()
                        st.success(f"Especialidade '{n_esp}' cadastrada com sucesso!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao salvar: {e}")
                else:
                    st.warning("Preencha todos os campos.")

        with c2:
            st.subheader("📋 Especialidades Ativas")
            lista_esp = buscar_especialidades_t9()
            if lista_esp:
                for item in lista_esp:
                    st.write(f"✅ {item}")
                st.markdown("---")
                alvo = st.selectbox("Selecione para remover", lista_esp, key="t9_f_del")
                if st.button("Remover do Sistema", type="primary", key="t9_f_btn_del", use_container_width=True):
                    supabase.table("MEDICOS").update({"especialidade": "Sem Especialidade"}).eq("especialidade", alvo).execute()
                    st.warning(f"'{alvo}' removida!")
                    st.rerun()
            else:
                st.info("Nenhuma especialidade encontrada.")

        st.markdown("---")
        st.caption("IA.na.Empresa - Gestão de Unidades e Especialidades")
