# supabase_client.py
# ============================================================
# Camada de acesso a dados (Supabase).
# - Usa INSERT/UPDATE explícito em vez de upsert() para evitar
#   o erro "on_conflict" exigido pelo PostgREST.
# - Configurações (escala e alarme) são singletons com id = 1.
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
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)


@st.cache_resource
def get_supabase() -> Client:
    return _get_client()


# ============================================================
#  CRUD - ATIVIDADES
# ============================================================
def criar_atividade(data: date, descricao: str, categoria: str,
                    duracao_min: int, concluida: bool = False) -> dict:
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
    client = get_supabase()
    res = (client.table("atividades")
           .select("*")
           .gte("data", inicio.isoformat())
           .lte("data", fim.isoformat())
           .order("data")
           .execute())
    return res.data if res.data else []


def atualizar_atividade(atividade_id: int, **kwargs) -> dict:
    client = get_supabase()
    res = (client.table("atividades")
           .update(kwargs)
           .eq("id", atividade_id)
           .execute())
    return res.data[0] if res.data else {}


def deletar_atividade(atividade_id: int) -> bool:
    client = get_supabase()
    client.table("atividades").delete().eq("id", atividade_id).execute()
    return True


# ============================================================
#  CONFIGURAÇÃO DE ESCALA (singleton, id = 1)
# ============================================================
def salvar_config_escala(data_inicio_trabalho: date) -> dict:
    """
    Salva a configuração da escala. Como é um singleton (id=1),
    faz UPDATE se já existir, senão INSERT.
    """
    client = get_supabase()
    payload = {
        "data_inicio_trabalho": data_inicio_trabalho.isoformat(),
        "atualizado_em": datetime.utcnow().isoformat(),
    }

    # Verifica se já existe a linha singleton
    existente = (client.table("config_escala")
                 .select("id")
                 .limit(1)
                 .execute())

    if existente.data:
        res = (client.table("config_escala")
               .update(payload)
               .eq("id", 1)
               .execute())
    else:
        payload["id"] = 1
        res = client.table("config_escala").insert(payload).execute()

    return res.data[0] if res.data else {}


def obter_config_escala() -> Optional[dict]:
    client = get_supabase()
    res = (client.table("config_escala")
           .select("*")
           .limit(1)
           .execute())
    return res.data[0] if res.data else None


# ============================================================
#  CONFIGURAÇÃO DE ALARME (singleton, id = 1)
# ============================================================
def salvar_config_alarme(horario: str, ativo: bool = True) -> dict:
    """
    Salva a configuração do alarme. Singleton com id=1.
    """
    client = get_supabase()
    payload = {
        "horario": horario,
        "ativo": ativo,
        "atualizado_em": datetime.utcnow().isoformat(),
    }

    existente = (client.table("config_alarme")
                 .select("id")
                 .limit(1)
                 .execute())

    if existente.data:
        res = (client.table("config_alarme")
               .update(payload)
               .eq("id", 1)
               .execute())
    else:
        payload["id"] = 1
        res = client.table("config_alarme").insert(payload).execute()

    return res.data[0] if res.data else {}


def obter_config_alarme() -> Optional[dict]:
    client = get_supabase()
    res = (client.table("config_alarme")
           .select("*")
           .limit(1)
           .execute())
    return res.data[0] if res.data else None
