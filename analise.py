# analise.py
# Análise estatística e visual das atividades salvas usando Pandas e Plotly.

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from typing import List, Dict, Any
from datetime import date, timedelta

def atividades_para_dataframe(atividades: List[Dict[str, Any]]) -> pd.DataFrame:
    """Converte lista de atividades (do Supabase) em DataFrame Pandas."""
    if not atividades:
        return pd.DataFrame(columns=[
            "id", "data", "descricao", "categoria",
            "duracao_min", "concluida", "criado_em"
        ])
    df = pd.DataFrame(atividades)
    df["data"] = pd.to_datetime(df["data"])
    df["criado_em"] = pd.to_datetime(df["criado_em"])
    df["duracao_horas"] = df["duracao_min"] / 60.0
    return df

def resumo_estatistico(df: pd.DataFrame) -> dict:
    """Gera métricas resumidas das atividades."""
    if df.empty:
        return {
            "total_atividades": 0,
            "total_horas": 0.0,
            "media_horas_dia": 0.0,
            "taxa_conclusao": 0.0,
            "categoria_mais_frequente": "—",
        }
    total = len(df)
    total_horas = df["duracao_horas"].sum()
    dias_unicos = df["data"].dt.date.nunique()
    media_dia = total_horas / dias_unicos if dias_unicos else 0
    concluidas = df["concluida"].sum()
    taxa = (concluidas / total * 100) if total else 0
    cat_freq = df["categoria"].mode()
    cat_mais = cat_freq.iloc[0] if not cat_freq.empty else "—"
    return {
        "total_atividades": total,
        "total_horas": round(total_horas, 1),
        "media_horas_dia": round(media_dia, 1),
        "taxa_conclusao": round(taxa, 1),
        "categoria_mais_frequente": cat_mais,
    }

def grafico_horas_por_categoria(df: pd.DataFrame) -> go.Figure:
    """Gráfico de barras: horas totais por categoria."""
    if df.empty:
        fig = go.Figure()
        fig.add_annotation(text="Sem dados", showarrow=False)
        return fig
    agrupado = (df.groupby("categoria")["duracao_horas"]
                .sum()
                .reset_index()
                .sort_values("duracao_horas", ascending=False))
    fig = px.bar(
        agrupado, x="categoria", y="duracao_horas",
        labels={"duracao_horas": "Horas", "categoria": "Categoria"},
        title="Horas por Categoria",
        color="categoria",
        text_auto=".1f",
    )
    fig.update_layout(showlegend=False)
    return fig

def grafico_evolucao_diaria(df: pd.DataFrame) -> go.Figure:
    """Gráfico de linha: evolução das horas estudadas por dia."""
    if df.empty:
        fig = go.Figure()
        fig.add_annotation(text="Sem dados", showarrow=False)
        return fig
    diario = (df.groupby(df["data"].dt.date)["duracao_horas"]
              .sum()
              .reset_index())
    diario.columns = ["data", "horas"]
    fig = px.line(
        diario, x="data", y="horas",
        labels={"horas": "Horas", "data": "Data"},
        title="Evolução Diária de Horas",
        markers=True,
    )
    fig.update_traces(line=dict(width=3))
    return fig

def grafico_taxa_conclusao(df: pd.DataFrame) -> go.Figure:
    """Gráfico de rosca: proporção de atividades concluídas vs pendentes."""
    if df.empty:
        fig = go.Figure()
        fig.add_annotation(text="Sem dados", showarrow=False)
        return fig
    contagem = df["concluida"].value_counts()
    labels = ["Concluídas" if k else "Pendentes" for k in contagem.index]
    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=contagem.values,
        hole=0.5,
        marker_colors=["#00CC96", "#EF553B"],
    )])
    fig.update_layout(title="Taxa de Conclusão")
    return fig

def heatmap_atividades_por_dia_semana(df: pd.DataFrame) -> go.Figure:
    """Heatmap: horas por dia da semana x período do dia."""
    if df.empty:
        fig = go.Figure()
        fig.add_annotation(text="Sem dados", showarrow=False)
        return fig
    df = df.copy()
    df["dia_semana"] = df["data"].dt.day_name()
    # Mapeia para português
    mapa_dias = {
        "Monday": "Seg", "Tuesday": "Ter", "Wednesday": "Qua",
        "Thursday": "Qui", "Friday": "Sex", "Saturday": "Sáb",
        "Sunday": "Dom",
    }
    df["dia_semana"] = df["dia_semana"].map(mapa_dias)
    ordem = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]
    pivot = (df.pivot_table(
        index="dia_semana", values="duracao_horas",
        aggfunc="sum", fill_value=0
    ).reindex(ordem, fill_value=0))
    fig = px.imshow(
        pivot.values,
        x=["Horas"],
        y=ordem,
        aspect="auto",
        color_continuous_scale="Blues",
        title="Horas de Estudo por Dia da Semana",
        text_auto=".1f",
    )
    fig.update_layout(coloraxis_showscale=False)
    return fig
