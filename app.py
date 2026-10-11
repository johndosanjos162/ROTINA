# app.py
# Interface principal do aplicativo Streamlit.

import streamlit as st
from datetime import date, datetime, timedelta
import pandas as pd

import supabase_client as db
import escala as esc
import analise as ana
import alarme as alm

# ============================================================
#  Configuração da página
# ============================================================
st.set_page_config(
    page_title="Escala 12x36 + Alarme de Estudo",
    page_icon="📅",
    layout="wide",
)

# ============================================================
#  Estado da sessão
# ============================================================
if "monitor_iniciado" not in st.session_state:
    st.session_state.monitor_iniciado = False
if "monitor" not in st.session_state:
    st.session_state.monitor = alm.MonitorAlarme()
if "data_inicio_escala" not in st.session_state:
    st.session_state.data_inicio_escala = None
if "horario_alarme" not in st.session_state:
    st.session_state.horario_alarme = "20:00"

# ============================================================
#  Carregamento inicial de configurações
# ============================================================
config_escala = db.obter_config_escala()
if config_escala:
    st.session_state.data_inicio_escala = date.fromisoformat(
        config_escala["data_inicio_trabalho"]
    )

config_alarme = db.obter_config_alarme()
if config_alarme:
    st.session_state.horario_alarme = config_alarme["horario"]

# ============================================================
#  Sidebar - Configurações
# ============================================================
with st.sidebar:
    st.title("⚙️ Configurações")

    # --- Configuração da Escala ---
    st.subheader("📅 Escala 12x36")
    data_inicio = st.date_input(
        "Data do primeiro dia de trabalho",
        value=st.session_state.data_inicio_escala or date.today(),
        help="Escolha a data em que você começa um turno de 12h. "
             "A escala segue: trabalho → folga → rotina em casa.",
    )
    if st.button("💾 Salvar escala"):
        db.salvar_config_escala(data_inicio)
        st.session_state.data_inicio_escala = data_inicio
        st.success("Escala salva!")
        st.rerun()

    st.divider()

    # --- Configuração do Alarme ---
    st.subheader("⏰ Alarme de Estudo")
    horario_input = st.time_input(
        "Horário do alarme (apenas em dias de folga)",
        value=datetime.strptime(
            st.session_state.horario_alarme, "%H:%M"
        ).time(),
    )
    horario_str = horario_input.strftime("%H:%M")

    ativo_alarme = st.toggle(
        "Ativar alarme automático",
        value=True,
        help="Quando ligado, o alarme dispara sozinho nos dias de folga "
             "no horário definido.",
    )

    if st.button("💾 Salvar alarme"):
        db.salvar_config_alarme(horario_str, ativo=ativo_alarme)
        st.session_state.horario_alarme = horario_str
        st.success("Alarme configurado!")
        st.rerun()

    st.divider()
    st.caption("💡 O alarme toca som alto e fala "
               "'Tá na hora do estudo' apenas em dias de folga.")

# ============================================================
#  Iniciar monitor de alarme (uma vez por sessão)
# ============================================================
if (st.session_state.data_inicio_escala
        and not st.session_state.monitor_iniciado):
    st.session_state.monitor.iniciar(
        st.session_state.data_inicio_escala,
        st.session_state.horario_alarme,
    )
    st.session_state.monitor_iniciado = True

# ============================================================
#  Conteúdo principal
# ============================================================
st.title("📅 Gerenciador de Escala 12x36 + Estudos")
st.caption("Trabalho, folga, rotina em casa e alarme inteligente de estudo.")

aba1, aba2, aba3, aba4 = st.tabs([
    "🗓️ Minha Escala",
    "📝 Atividades",
    "📊 Análise",
    "⏰ Alarme",
])

# ----------------------------------------------------------
#  ABA 1: Minha Escala
# ----------------------------------------------------------
with aba1:
    if not st.session_state.data_inicio_escala:
        st.warning("Configure a data de início da escala na barra lateral.")
    else:
        data_ini = st.session_state.data_inicio_escala
        hoje = date.today()

        # --- Status do dia ---
        tipo_hoje = esc.classificar_dia(hoje, data_ini)
        col1, col2, col3 = st.columns(3)

        icones = {
            "trabalho": "🔴 Trabalho (12h)",
            "folga": "🟢 Folga",
            "rotina_casa": "🏠 Rotina em Casa",
        }
        col1.metric("Hoje", icones[tipo_hoje])
        proximas = esc.proximos_dias_folga(data_ini, hoje, 3)
        if proximas:
            col2.metric("Próxima folga", proximas[0].strftime("%d/%m/%Y"))
        else:
            col2.metric("Próxima folga", "—")

        # --- Calendário visual (próximos 30 dias) ---
        st.subheader("Próximos 30 dias")
        dias = esc.gerar_dias_escala(data_ini, 30)

        # Monta grid de 7 colunas
        semanas = [dias[i:i+7] for i in range(0, len(dias), 7)]
        for semana in semanas:
            cols = st.columns(7)
            for i, dia_info in enumerate(semana):
                d = dia_info["data"]
                t = dia_info["tipo"]
                with cols[i]:
                    if t == "trabalho":
                        bg, label = "#FF4B4B", "🔴"
                    elif t == "folga":
                        bg, label = "#00CC96", "🟢"
                    else:
                        bg, label = "#FFA500", "🏠"
                    st.markdown(
                        f"""<div style="background:{bg}; padding:6px; 
                        border-radius:8px; text-align:center; 
                        font-size:12px; color:white; margin:2px;">
                        {label}<br><b>{d.strftime('%d/%m')}</b></div>""",
                        unsafe_allow_html=True,
                    )

        st.divider()
        # --- Legenda ---
        st.markdown(
            "🔴 **Trabalho (12h)** &nbsp;&nbsp; "
            "🟢 **Folga (36h)** &nbsp;&nbsp; "
            "🏠 **Rotina em casa**"
        )

# ----------------------------------------------------------
#  ABA 2: Atividades
# ----------------------------------------------------------
with aba2:
    st.subheader("Registrar Atividade")

    with st.form("form_atividade", clear_on_submit=True):
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            data_atv = st.date_input("Data", value=date.today())
            categoria = st.selectbox(
                "Categoria",
                ["Estudo", "Exercício", "Leitura", "Curso", "Outro"],
            )
        with col_b:
            descricao = st.text_input("Descrição")
            duracao = st.number_input(
                "Duração (min)", min_value=5, max_value=720,
                value=60, step=5,
            )
        with col_c:
            concluida = st.checkbox("Concluída?", value=False)
            st.write("")
            st.write("")
            submitted = st.form_submit_button("➕ Adicionar")

        if submitted and descricao:
            db.criar_atividade(
                data_atv, descricao, categoria, duracao, concluida
            )
            st.success(f"Atividade '{descricao}' adicionada!")
            st.rerun()

    st.divider()
    st.subheader("Atividades Recentes")

    # Filtro de período
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        filtro_inicio = st.date_input(
            "De", value=date.today() - timedelta(days=30)
        )
    with col_f2:
        filtro_fim = st.date_input("Até", value=date.today())

    atividades = db.listar_atividades(filtro_inicio, filtro_fim)
    df = ana.atividades_para_dataframe(atividades)

    if df.empty:
        st.info("Nenhuma atividade no período selecionado.")
    else:
        # Exibe tabela editável resumida
        df_exibir = df[["id", "data", "descricao", "categoria",
                         "duracao_min", "concluida"]].copy()
        df_exibir["data"] = df_exibir["data"].dt.strftime("%d/%m/%Y")
        st.dataframe(df_exibir, use_container_width=True, hide_index=True)

        # Ações
        st.subheader("Gerenciar")
        col_del1, col_del2 = st.columns([1, 3])
        with col_del1:
            id_del = st.number_input(
                "ID para excluir", min_value=1, step=1, value=1
            )
        with col_del2:
            if st.button("🗑️ Excluir atividade"):
                db.deletar_atividade(int(id_del))
                st.success("Atividade excluída!")
                st.rerun()

# ----------------------------------------------------------
#  ABA 3: Análise com Pandas
# ----------------------------------------------------------
with aba3:
    st.subheader("📊 Análise Estatística")

    if df.empty:
        st.info("Sem dados para analisar. Registre atividades primeiro.")
    else:
        # --- Métricas resumidas ---
        resumo = ana.resumo_estatistico(df)
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("Atividades", resumo["total_atividades"])
        m2.metric("Horas totais", f"{resumo['total_horas']}h")
        m3.metric("Média/dia", f"{resumo['media_horas_dia']}h")
        m4.metric("Conclusão", f"{resumo['taxa_conclusao']}%")
        m5.metric("Categoria top", resumo["categoria_mais_frequente"])

        st.divider()

        # --- Gráficos ---
        col_g1, col_g2 = st.columns(2)
        with col_g1:
            st.plotly_chart(
                ana.grafico_horas_por_categoria(df),
                use_container_width=True,
            )
        with col_g2:
            st.plotly_chart(
                ana.grafico_taxa_conclusao(df),
                use_container_width=True,
            )

        st.plotly_chart(
            ana.grafico_evolucao_diaria(df),
            use_container_width=True,
        )

        st.plotly_chart(
            ana.heatmap_atividades_por_dia_semana(df),
            use_container_width=True,
        )

        # --- Tabela detalhada com Pandas ---
        with st.expander("📋 Tabela detalhada (Pandas)"):
            st.dataframe(
                df[["data", "descricao", "categoria",
                    "duracao_horas", "concluida"]]
                .rename(columns={
                    "duracao_horas": "Horas",
                    "descricao": "Descrição",
                    "concluida": "Concluída",
                }),
                use_container_width=True,
                hide_index=True,
            )

# ----------------------------------------------------------
#  ABA 4: Alarme
# ----------------------------------------------------------
with aba4:
    st.subheader("⏰ Alarme de Estudo")

    if not st.session_state.data_inicio_escala:
        st.warning("Configure a escala primeiro na barra lateral.")
    else:
        hoje = date.today()
        dia_folga = esc.e_dia_de_folga(
            hoje, st.session_state.data_inicio_escala
        )

        col_s1, col_s2 = st.columns(2)
        with col_s1:
            st.metric(
                "Hoje é dia de folga?",
                "✅ Sim" if dia_folga else "❌ Não",
            )
        with col_s2:
            st.metric(
                "Horário configurado",
                st.session_state.horario_alarme,
            )

        if not dia_folga:
            st.info(
                "🔕 O alarme **não** dispara hoje porque não é dia de folga. "
                "Ele só toca nos dias marcados como 🟢 na sua escala."
            )
        else:
            st.success(
                "🟢 Hoje é dia de folga! O alarme vai disparar "
                f"às **{st.session_state.horario_alarme}** "
                "e falar: *'Tá na hora do estudo'*."
            )

        st.divider()
        st.subheader("🔧 Teste Manual")
        st.caption("Use este botão para testar o som e a voz do alarme.")

        if st.button("🔔 Testar alarme agora"):
            with st.spinner("Tocando alarme de teste..."):
                alm.verificar_e_disparar_alarme(
                    st.session_state.data_inicio_escala,
                    st.session_state.horario_alarme,
                    forcar=True,
                )
            st.success("Alarme de teste disparado! Verifique o áudio.")

        st.divider()
        st.subheader("📅 Próximos alarmes agendados")
        proximas_folgas = esc.proximos_dias_folga(
            st.session_state.data_inicio_escala, hoje, 5
        )
        for f in proximas_folgas:
            st.markdown(
                f"- **{f.strftime('%d/%m/%Y')}** "
                f"({f.strftime('%A')}) às "
                f"**{st.session_state.horario_alarme}**"
            )

# ============================================================
#  Footer
# ============================================================
st.divider()
st.caption(
    "Desenvolvido com Streamlit + Supabase + Pandas + pygame + pyttsx3. "
    "Pronto para migração para PostgreSQL local."
)
