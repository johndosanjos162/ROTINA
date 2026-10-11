# supabase_client.py
# ============================================================
# Camada de acesso a dados (Supabase).
#
# - Usa INSERT/UPDATE explícito em vez de upsert() para evitar
#   o erro "on_conflict" exigido pelo PostgREST.
# - Configurações (escala e alarme) são singletons com id = 1.
# - Todas as funções levantam exceção em caso de erro; o app.py
#   trata cada chamada com try/except para exibir mensagens úteis.
# ============================================================

import streamlit as st
from supabase import create_client, Client
from datetime import date, datetime
from typing import Optional, List, Dict, Any
import pandas as pd


# ============================================================
#  Cliente Supabase
# ============================================================
def _get_client() -> Client:
    """Cria o cliente Supabase a partir dos secrets do Streamlit."""
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)


@st.cache_resource
def get_supabase() -> Client:
    """Retorna um cliente Supabase cacheado (reutilizado entre chamadas)."""
    return _get_client()


# ============================================================
#  CRUD - ATIVIDADES
# ============================================================
def criar_atividade(data: date, descricao: str, categoria: str,
                    duracao_min: int, concluida: bool = False) -> dict:
    """
    Insere uma nova atividade na tabela `atividades`.

    Parâmetros:
        data         : data da atividade
        descricao    : descrição livre
        categoria    : "Estudo", "Exercício", etc.
        duracao_min  : duração em minutos
        concluida    : se foi concluída

    Retorna o registro criado (dict).
    """
    client = get_supabase()
    payload = {
        "data": data.isoformat(),
        "descricao": descricao,
        "categoria": categoria,
        "duracao_min": duracao_min,
        "concluida": concluida,
    }
    res = client.table("atividades").insert(payload).execute()
    return res.data[0] if res.data else {}


def listar_atividades(inicio: date, fim: date) -> List[Dict[str, Any]]:
    """
    Lista atividades entre duas datas (inclusive).

    Retorna lista de dicts. Lista vazia se não houver nada.
    """
    client = get_supabase()
    res = (client.table("atividades")
           .select("*")
           .gte("data", inicio.isoformat())
           .lte("data", fim.isoformat())
           .order("data")
           .execute())
    return res.data if res.data else []


def atualizar_atividade(atividade_id: int, **kwargs) -> dict:
    """
    Atualiza campos específicos de uma atividade.

    Exemplo:
        atualizar_atividade(5, concluida=True)
    """
    client = get_supabase()
    res = (client.table("atividades")
           .update(kwargs)
           .eq("id", atividade_id)
           .execute())
    return res.data[0] if res.data else {}


def deletar_atividade(atividade_id: int) -> bool:
    """
    Remove uma atividade pelo ID.
    Retorna True se a operação foi bem-sucedida.
    """
    client = get_supabase()
    client.table("atividades").delete().eq("id", atividade_id).execute()
    return True


# ============================================================
#  CONFIGURAÇÃO DE ESCALA (singleton, id = 1)
# ============================================================
def salvar_config_escala(data_inicio_trabalho: date) -> dict:
    """
    Salva a configuração da escala.

    Como é um singleton (só existe uma linha, com id=1):
      - Se já existir → UPDATE
      - Se não existir → INSERT com id=1

    Isso evita o erro "on_conflict" do PostgREST.
    """
    client = get_supabase()
    payload = {
        "data_inicio_trabalho": data_inicio_trabalho.isoformat(),
        "atualizado_em": datetime.utcnow().isoformat(),
    }

    # Verifica se a linha singleton já existe
    existente = (client.table("config_escala")
                 .select("id")
                 .limit(1)
                 .execute())

    if existente.data:
        # Já existe → UPDATE
        res = (client.table("config_escala")
               .update(payload)
               .eq("id", 1)
               .execute())
    else:
        # Não existe → INSERT com id=1
        payload["id"] = 1
        res = client.table("config_escala").insert(payload).execute()

    return res.data[0] if res.data else {}


def obter_config_escala() -> Optional[dict]:
    """
    Retorna a configuração atual da escala, ou None se ainda não
    foi configurada.
    """
    client = get_supabase()
    res = (client.table("config_escala")
           .select("*")
           .limit(1)
           .execute())
    return res.data[0] if res.data else None


# ============================================================
#  CONFIGURAÇÃO DE ALARME (singleton, id = 1)
# ============================================================
def salvar_config_alarme(horario: str, ativo: bool = True,
                         duracao_segundos: int = 8,
                         volume: int = 80,
                         repeticoes_voz: int = 2,
                         velocidade_voz: int = 95) -> dict:
    """
    Salva a configuração completa do alarme.

    Parâmetros:
        horario           : "HH:MM" (ex: "20:00")
        ativo             : se o alarme automático está ligado
        duracao_segundos  : duração da sirene (3 a 60)
        volume            : volume em % (0 a 100)
        repeticoes_voz    : quantas vezes falar a mensagem (1 a 10)
        velocidade_voz    : velocidade da voz em % (50 a 200, 100 = normal)

    Como é singleton (id=1):
      - Se já existir → UPDATE
      - Se não existir → INSERT com id=1
    """
    client = get_supabase()
    payload = {
        "horario": horario,
        "ativo": ativo,
        "duracao_segundos": duracao_segundos,
        "volume": volume,
        "repeticoes_voz": repeticoes_voz,
        "velocidade_voz": velocidade_voz,
        "atualizado_em": datetime.utcnow().isoformat(),
    }

    # Verifica se a linha singleton já existe
    existente = (client.table("config_alarme")
                 .select("id")
                 .limit(1)
                 .execute())

    if existente.data:
        # Já existe → UPDATE
        res = (client.table("config_alarme")
               .update(payload)
               .eq("id", 1)
               .execute())
    else:
        # Não existe → INSERT com id=1
        payload["id"] = 1
        res = client.table("config_alarme").insert(payload).execute()

    return res.data[0] if res.data else {}


def obter_config_alarme() -> Optional[dict]:
    """
    Retorna a configuração atual do alarme, ou None se ainda não
    foi configurado.

    O dict retornado contém:
        horario, ativo, duracao_segundos, volume,
        repeticoes_voz, velocidade_voz, atualizado_em
    """
    client = get_supabase()
    res = (client.table("config_alarme")
           .select("*")
           .limit(1)
           .execute())
    return res.data[0] if res.data else None


# ============================================================
#  UTILITÁRIOS (opcionais)
# ============================================================
def contar_atividades() -> int:
    """Retorna o número total de atividades registradas."""
    client = get_supabase()
    res = client.table("atividades").select("id", count="exact").execute()
    return res.count if res.count is not None else 0


def limpar_atividades_antigas(dias: int = 365) -> int:
    """
    Remove atividades mais antigas que N dias.
    Retorna o número de registros removidos.
    """
    from datetime import timedelta
    limite = (date.today() - timedelta(days=dias)).isoformat()
    client = get_supabase()
    res = (client.table("atividades")
           .delete()
           .lt("data", limite)
           .execute())
    return len(res.data) if res.data else 0
