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
    "8. Relatório Gerencial"
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
                "Eldorado Av Jose Faria da Rocha 4408 2 and"
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



# TELA 2 - ABERTURA (AJUSTE FINO: ORDEM ALFABÉTICA)
elif menu == "2. Abertura de Agenda":
    if verificar_senha():
        st.header("🏪 Abertura de Agenda")
        medicos = buscar_todos("MEDICOS")
        if medicos:
            df_meds = pd.DataFrame(medicos)
            
            # 1. Seleciona a Unidade
            u_filtro = st.selectbox("Selecione a Unidade para filtrar médicos:", sorted(df_meds['unidade'].unique().tolist()))
            
            # 2. Filtra e Ordena os médicos por nome (A-Z)
            df_filtrado = df_meds[df_meds['unidade'] == u_filtro].sort_values(by='nome')
            
            # 3. Monta as opções já ordenadas
            op = {f"{m['nome']} ({m['especialidade']})": m['id'] for _, m in df_filtrado.iterrows()}
            
            sel = st.selectbox("Médico Disponível nesta Unidade (Ordem Alfabética)", list(op.keys()))
            
            c1, c2, c3 = st.columns(3)
            d = c1.date_input("Data da Agenda", format="DD/MM/YYYY")
            hi = c2.time_input("Hora Início", value=dt_lib.time(8, 0))
            hf = c3.time_input("Hora Final", value=dt_lib.time(18, 0))
            inter = st.number_input("Intervalo (minutos)", 5, 120, 20)
            
            if st.button("Gerar Grade"):
                vagas = []
                t, fim = dt_lib.datetime.combine(d, hi), dt_lib.datetime.combine(d, hf)
                while t < fim:
                    vagas.append({"medico_id": op[sel], "data_hora": t.isoformat(), "status": "Livre"})
                    t += dt_lib.timedelta(minutes=inter)
                supabase.table("CONSULTAS").insert(vagas).execute()
                st.success(f"✅ Grade criada com sucesso!")


# TELA 3 - MARCAR CONSULTA (ALTERAÇÃO: ESPECIALIDADE APÓS UNIDADE)
elif menu == "3. Marcar Consulta":
    st.header("📅 Agendamento de Consultas")
    dados = buscar_todos("CONSULTAS", "*, MEDICOS(*)", filtros=[("status", "Livre")])
    if dados:
        v_list = []
        for r in dados:
            m = r.get('MEDICOS') or r.get('medicos')
            if m:
                dt = pd.to_datetime(r['data_hora'])
                v_list.append({'id': r['id'], 'unidade': m['unidade'], 'especialidade': m['especialidade'], 'medico': m['nome'], 'display': dt.strftime('%d/%m/%Y %H:%M'), 'sort': r['data_hora']})
        df = pd.DataFrame(v_list).sort_values('sort')
        
        u_sel = st.selectbox("1. Escolha a Unidade", sorted(df['unidade'].unique()))
        df_u = df[df['unidade'] == u_sel]
        
        esp_sel = st.selectbox("2. Escolha a Especialidade", sorted(df_u['especialidade'].unique())) # NOVO PASSO
        df_esp = df_u[df_u['especialidade'] == esp_sel]
        
        m_sel = st.selectbox("3. Escolha o Médico", sorted(df_esp['medico'].unique()))
        df_m = df_esp[df_esp['medico'] == m_sel]
        
        h_sel = st.selectbox("4. Escolha o Horário", df_m['display'].tolist())
        id_vaga = df_m[df_m['display'] == h_sel].iloc[0]['id']
        
        with st.form("form_paciente"):
            c1, c2 = st.columns(2)
            pn = c1.text_input("Nome")
            ps = c1.text_input("Sobrenome")
            pt = c2.text_input("WhatsApp")
            pc = c2.text_input("Convênio")
            if st.form_submit_button("Finalizar Agendamento"):
                if pn and pt:
                    supabase.table("CONSULTAS").update({"paciente_nome": pn, "paciente_sobrenome": ps, "paciente_telefone": pt, "paciente_convenio": pc, "status": "Marcada"}).eq("id", id_vaga).execute()
                    st.success("✅ Agendada!"); st.rerun()



# TELA 4 - RELATÓRIO DE CONSULTAS FUTURAS (AJUSTE FINO)
elif menu == "4. Relatório de Agendamentos":
    if verificar_senha():
        st.header("📋 Controle de Confirmações")
        dados = buscar_todos("CONSULTAS", "*, MEDICOS(*)")
        if dados:
            agora = dt_lib.datetime.now().replace(tzinfo=None)
            rel = []
            for r in dados:
                m = r.get('MEDICOS') or r.get('medicos') or {}
                dt = pd.to_datetime(r['data_hora']).replace(tzinfo=None)
                
                # Filtra apenas Marcadas e Futuras
                if dt >= agora and r['status'] == "Marcada":
                    pac = f"{r.get('paciente_nome','')} {r.get('paciente_sobrenome','')}".strip()
                    tel = ''.join(filter(str.isdigit, str(r.get('paciente_telefone', ''))))
                    
                    # Mensagem personalizada
                    msg = f"Olá, Gentileza Confirmar consulta Dr.(a) {m.get('nome')} / {m.get('especialidade')} / {dt.strftime('%d/%m/%Y %H:%M')} / {m.get('unidade')}"
                    link = f"https://wa.me/55{tel}?text={msg.replace(' ', '%20')}" if tel else ""
                    
                    rel.append({
                        "Unidade": m.get('unidade'),
                        "Data/Hora": dt,
                        "Médico": m.get('nome'),
                        "Paciente": pac,
                        "WhatsApp (Clique)": link,
                        "Confirmado?": False, # Coluna em branco para você marcar
                        "sort": r['data_hora']
                    })
            
            if rel:
                df_r = pd.DataFrame(rel).sort_values(by=['Unidade', 'sort'])
                
                # Exibe a tabela com editor para permitir marcar o check
                st.data_editor(
                    df_r.drop(columns=['sort']), 
                    column_config={
                        "WhatsApp (Clique)": st.column_config.LinkColumn("📱 Enviar Zap", display_text=None), # Mostra o link/número direto
                        "Data/Hora": st.column_config.DatetimeColumn(format="DD/MM/YYYY HH:mm"),
                        "Confirmado?": st.column_config.CheckboxColumn("✅ Marcar ao Enviar", default=False)
                    }, 
                    use_container_width=True, 
                    hide_index=True
                )
                st.info("💡 Dica: Clique no número para abrir o WhatsApp e depois marque o check ao lado.")
            else:
                st.info("Não há consultas marcadas para o futuro.")


# TELA 5 - CANCELAR CONSULTA
elif menu == "5. Cancelar Consulta":
    if verificar_senha():
        st.header("🚫 Cancelar Consulta")
        dados = buscar_todos("CONSULTAS", filtros=[("status", "Marcada")])
        if dados:
            op = {f"{r['paciente_nome']} | {r['data_hora']}": r['id'] for r in dados}
            sel = st.selectbox("Selecione o agendamento para cancelar:", list(op.keys()))
            if st.button("Confirmar Cancelamento"):
                supabase.table("CONSULTAS").update({"status": "Livre", "paciente_nome": None, "paciente_telefone": None}).eq("id", op[sel]).execute()
                st.success("Cancelado!"); st.rerun()

# TELA 6 - EXCLUIR GRADE ABERTA
elif menu == "6. Excluir Grade Aberta":
    if verificar_senha():
        st.header("🗑️ Remover Horários Livres")
        dados = buscar_todos("CONSULTAS", "*, MEDICOS(*)", filtros=[("status", "Livre")])
        if dados:
            df_ex = pd.DataFrame([{'id': r['id'], 'info': f"{r['MEDICOS']['nome']} | {pd.to_datetime(r['data_hora']).strftime('%d/%m/%Y %H:%M')}"} for r in dados])
            sel = st.multiselect("Selecione os horários para remover do sistema:", df_ex['info'].tolist())
            if st.button("Excluir Definitivamente"):
                ids = df_ex[df_ex['info'].isin(sel)]['id'].tolist()
                supabase.table("CONSULTAS").delete().in_("id", ids).execute()
                st.success("Horários removidos!"); st.rerun()

# TELA 7 - EXCLUIR CADASTRO MÉDICO
elif menu == "7. Excluir Cadastro de Médico":
    if verificar_senha():
        st.header("👨‍⚕️ Remover Médico")
        meds = buscar_todos("MEDICOS")
        if meds:
            df_m = pd.DataFrame(meds).sort_values('nome')
            op = {f"{r['nome']} ({r['especialidade']})": r['id'] for _, r in df_m.iterrows()}
            sel = st.selectbox("Selecione o médico para remover o cadastro:", list(op.keys()))
            if st.button("Excluir Médico"):
                supabase.table("MEDICOS").delete().eq("id", op[sel]).execute()
                st.success("Médico removido!"); st.rerun()

# TELA 8 - GERENCIAL
elif menu == "8. Relatório Gerencial":
    if verificar_senha():
        st.header("📊 Resumo Gerencial")
        dados = buscar_todos("CONSULTAS")
        if dados:
            df = pd.DataFrame(dados)
            df['Dia'] = pd.to_datetime(df['data_hora']).dt.strftime('%d/%m/%Y')
            resumo = df.groupby('Dia').agg(Total_Vagas=('id', 'count'), Agendados=('status', lambda x: (x == 'Marcada').sum())).reset_index()
            st.dataframe(resumo.sort_values('Dia', ascending=False), use_container_width=True, hide_index=True)
