# app.py
# ============================================================
# Interface principal do aplicativo Streamlit.
# Escala 12x36 (trabalho/folga alternados) + Alarme de Estudo
#
# - Banco: Supabase (nuvem)
# - Alarme: toca NO NAVEGADOR do usuário (Web Audio + voz pt-BR)
# - Todas as chamadas ao banco têm try/except para mensagens úteis
# ============================================================

import streamlit as st
from datetime import date, datetime, timedelta
import pandas as pd

import supabase_client as db
import escala as esc
import analise as ana
import alarme_browser as ab

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
if "data_inicio_escala" not in st.session_state:
    st.session_state.data_inicio_escala = None
if "horario_alarme" not in st.session_state:
    st.session_state.horario_alarme = "20:00"
if "ativo_alarme" not in st.session_state:
    st.session_state.ativo_alarme = True

# ============================================================
#  Carregamento inicial de configurações (com tratamento)
# ============================================================
try:
    config_escala = db.obter_config_escala()
    if config_escala:
        st.session_state.data_inicio_escala = date.fromisoformat(
            config_escala["data_inicio_trabalho"]
        )
except Exception as e:
    st.warning(
        f"Não foi possível carregar a configuração da escala. "
        f"Detalhe: {e}"
    )

try:
    config_alarme = db.obter_config_alarme()
    if config_alarme:
        st.session_state.horario_alarme = config_alarme["horario"]
        st.session_state.ativo_alarme = config_alarme.get("ativo", True)
except Exception as e:
    st.warning(
        f"Não foi possível carregar a configuração do alarme. "
        f"Detalhe: {e}"
    )

# ============================================================
#  Sidebar - Configurações
# ============================================================
with st.sidebar:
    st.title("⚙️ Configurações")

    # ---------- Configuração da Escala ----------
    st.subheader("📅 Escala 12x36")
    st.caption(
        "Informe a data em que você **começou um turno de trabalho**. "
        "A escala vai alternar: trabalho → folga → trabalho → folga..."
    )
    data_inicio = st.date_input(
        "Data do primeiro dia de trabalho",
        value=st.session_state.data_inicio_escala or date.today(),
    )
    if st.button("💾 Salvar escala"):
        try:
            db.salvar_config_escala(data_inicio)
            st.session_state.data_inicio_escala = data_inicio
            st.success("Escala salva!")
            st.rerun()
        except Exception as e:
            st.error(f"❌ Erro ao salvar escala: {e}")
            st.info(
                "Verifique se as tabelas foram criadas no Supabase "
                "e se o RLS está desabilitado."
            )

    st.divider()

    # ---------- Configuração do Alarme ----------
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
        value=st.session_state.ativo_alarme,
        help="Quando ligado, o alarme dispara sozinho nos dias "
             "de folga no horário definido.",
    )

    if st.button("💾 Salvar alarme"):
        try:
            db.salvar_config_alarme(horario_str, ativo=ativo_alarme)
            st.session_state.horario_alarme = horario_str
            st.session_state.ativo_alarme = ativo_alarme
            st.success("Alarme configurado!")
            st.rerun()
        except Exception as e:
            st.error(f"❌ Erro ao salvar alarme: {e}")

    st.divider()
    st.caption("💡 O alarme toca som alto e fala "
               "'Tá na hora do estudo' apenas em dias de folga.")

# ============================================================
#  Conteúdo principal
# ============================================================
st.title("📅 Gerenciador de Escala 12x36 + Estudos")
st.caption("Trabalho, folga e alarme inteligente de estudo.")

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
            "trabalho": "🔴 Trabalho (6h → 18h)",
            "folga": "🟢 Folga (36h de descanso)",
        }
        col1.metric("Hoje", icones[tipo_hoje])

        proximas = esc.proximos_dias_folga(data_ini, hoje, 3)
        if proximas:
            col2.metric("Próxima folga", proximas[0].strftime("%d/%m/%Y"))
            if len(proximas) > 1:
                col3.metric(
                    "Folga seguinte", proximas[1].strftime("%d/%m/%Y")
                )

        # --- Calendário visual (próximos 30 dias) ---
        st.subheader("Próximos 30 dias")
        st.caption(
            "🔴 Trabalho &nbsp;•&nbsp; 🟢 Folga "
            "— padrão: trabalho um dia, folga no outro."
        )
        dias = esc.gerar_dias_escala(data_ini, 30)

        # Cabeçalho dos dias da semana
        dias_semana = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]
        cols_header = st.columns(7)
        for i, nome in enumerate(dias_semana):
            cols_header[i].markdown(
                f"<div style='text-align:center; font-weight:bold; "
                f"font-size:12px; color:gray;'>{nome}</div>",
                unsafe_allow_html=True,
            )

        # Alinha o primeiro dia ao dia da semana real
        primeiro = dias[0]["data"]
        offset = primeiro.weekday()  # 0 = segunda, 6 = domingo

        # Preenche células vazias antes do primeiro dia
        celulas = [None] * offset + dias[: 30 - offset]

        # Divide em semanas de 7
        semanas = [celulas[i:i + 7] for i in range(0, len(celulas), 7)]

        for semana in semanas:
            cols = st.columns(7)
            for i, dia_info in enumerate(semana):
                with cols[i]:
                    if dia_info is None:
                        st.markdown("&nbsp;", unsafe_allow_html=True)
                        continue
                    d = dia_info["data"]
                    t = dia_info["tipo"]
                    # Destaca o dia de hoje com borda azul
                    borda = (
                        "3px solid #1E88E5"
                        if d == hoje else "1px solid #ddd"
                    )
                    if t == "trabalho":
                        bg, label = "#FF4B4B", "🔴"
                    else:
                        bg, label = "#00CC96", "🟢"
                    st.markdown(
                        f"""<div style="background:{bg};
                        border:{borda}; padding:6px;
                        border-radius:8px; text-align:center;
                        font-size:12px; color:white; margin:2px;">
                        {label}<br><b>{d.strftime('%d/%m')}</b></div>""",
                        unsafe_allow_html=True,
                    )

        st.divider()
        st.markdown(
            "🔴 **Trabalho (12h)** &nbsp;&nbsp;&nbsp; "
            "🟢 **Folga (36h)** &nbsp;&nbsp;&nbsp; "
            "🔵 **Hoje** (borda azul)"
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
            try:
                db.criar_atividade(
                    data_atv, descricao, categoria, duracao, concluida
                )
                st.success(f"Atividade '{descricao}' adicionada!")
                st.rerun()
            except Exception as e:
                st.error(f"❌ Erro ao adicionar atividade: {e}")
        elif submitted and not descricao:
            st.warning("Preencha a descrição antes de adicionar.")

    st.divider()
    st.subheader("Atividades Recentes")

    col_f1, col_f2 = st.columns(2)
    with col_f1:
        filtro_inicio = st.date_input(
            "De", value=date.today() - timedelta(days=30)
        )
    with col_f2:
        filtro_fim = st.date_input("Até", value=date.today())

    try:
        atividades = db.listar_atividades(filtro_inicio, filtro_fim)
        df = ana.atividades_para_dataframe(atividades)
        erro_carregamento = None
    except Exception as e:
        erro_carregamento = str(e)
        atividades = []
        df = ana.atividades_para_dataframe([])

    if erro_carregamento:
        st.error(f"❌ Erro ao carregar atividades: {erro_carregamento}")
    elif df.empty:
        st.info("Nenhuma atividade no período selecionado.")
    else:
        df_exibir = df[["id", "data", "descricao", "categoria",
                        "duracao_min", "concluida"]].copy()
        df_exibir["data"] = df_exibir["data"].dt.strftime("%d/%m/%Y")
        st.dataframe(df_exibir, use_container_width=True, hide_index=True)

        st.subheader("Gerenciar")
        col_del1, col_del2 = st.columns([1, 3])
        with col_del1:
            id_del = st.number_input(
                "ID para excluir", min_value=1, step=1, value=1
            )
        with col_del2:
            if st.button("🗑️ Excluir atividade"):
                try:
                    db.deletar_atividade(int(id_del))
                    st.success("Atividade excluída!")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Erro ao excluir: {e}")

# ----------------------------------------------------------
#  ABA 3: Análise
# ----------------------------------------------------------
with aba3:
    st.subheader("📊 Análise Estatística")

    if df.empty:
        st.info("Sem dados para analisar. Registre atividades primeiro.")
    else:
        resumo = ana.resumo_estatistico(df)
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("Atividades", resumo["total_atividades"])
        m2.metric("Horas totais", f"{resumo['total_horas']}h")
        m3.metric("Média/dia", f"{resumo['media_horas_dia']}h")
        m4.metric("Conclusão", f"{resumo['taxa_conclusao']}%")
        m5.metric("Categoria top", resumo["categoria_mais_frequente"])

        st.divider()

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
#  ABA 4: Alarme (toca NO NAVEGADOR do usuário)
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
                "🔕 O alarme **não** dispara hoje porque não é dia de "
                "folga. Ele só toca nos dias 🟢 da escala."
            )
        else:
            st.success(
                "🟢 Hoje é dia de folga! O alarme vai disparar "
                f"às **{st.session_state.horario_alarme}** "
                "e falar: *'Tá na hora do estudo'*."
            )

        st.divider()
        st.subheader("🔔 Alarme no seu navegador (tempo real)")
        st.caption(
            "Enquanto esta aba estiver aberta, o alarme tocará "
            "diretamente no seu computador (Web Audio + voz do "
            "navegador). **Mantenha a aba aberta no horário do alarme.**"
        )

        # ⚠️ Importante: o navegador exige uma interação do usuário
        # antes de permitir áudio automático. Clicar no botão de teste
        # abaixo "desbloqueia" o áudio para o resto da sessão.
        st.info(
            "👉 **Dica:** ao abrir o app, clique uma vez em "
            "**🔔 Testar alarme no navegador** para desbloquear o áudio. "
            "Depois disso o alarme automático funcionará."
        )

        # Componente que roda no CLIENTE (navegador do usuário)
        ab.render_alarme_browser(
            data_inicio=st.session_state.data_inicio_escala,
            horario=st.session_state.horario_alarme,
            ativo=st.session_state.ativo_alarme,
        )

        st.divider()
        st.subheader("🔧 Teste Manual no navegador")
        st.caption(
            "Clique no botão abaixo para tocar a sirene e a voz "
            "imediatamente no seu computador."
        )
        ab.render_botao_teste_browser()

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
    "Desenvolvido com Streamlit + Supabase + Pandas + Web Audio API."
)
