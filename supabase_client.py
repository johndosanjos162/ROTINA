# supabase_client.py
# Camada de acesso a dados. Isolada para facilitar migração futura para PostgreSQL local.

import streamlit as st
from supabase import create_client, Client
from datetime import date, datetime
from typing import Optional, List, Dict, Any
import pandas as pd

def _get_client() -> Client:
    """Cria cliente Supabase a partir dos secrets do Streamlit."""
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

# Inicialização protegida (a conexão é reutilizada via cache)
@st.cache_resource
def get_supabase() -> Client:
    return _get_client()

# ============================================================
#  CRUD - ATIVIDADES
# ============================================================

def criar_atividade(data: date, descricao: str, categoria: str,
                    duracao_min: int, concluida: bool = False) -> dict:
    """Insere uma nova atividade na tabela `atividades`."""
    client = get_supabase()
    payload = {
        "data": data.isoformat(),
        "descricao": descricao,
        "categoria": categoria,
        "duracao_min": duracao_min,
        "concluida": concluida,
        "criado_em": datetime.utcnow().isoformat(),
    }
    res = client.table("atividades").insert(payload).execute()
    return res.data[0] if res.data else {}

def listar_atividades(inicio: date, fim: date) -> List[Dict[str, Any]]:
    """Retorna atividades no intervalo de datas."""
    client = get_supabase()
    res = (client.table("atividades")
           .select("*")
           .gte("data", inicio.isoformat())
           .lte("data", fim.isoformat())
           .order("data")
           .execute())
    return res.data if res.data else []

def atualizar_atividade(atividade_id: int, **kwargs) -> dict:
    """Atualiza campos de uma atividade existente."""
    client = get_supabase()
    res = (client.table("atividades")
           .update(kwargs)
           .eq("id", atividade_id)
           .execute())
    return res.data[0] if res.data else {}

def deletar_atividade(atividade_id: int) -> bool:
    """Remove uma atividade pelo ID."""
    client = get_supabase()
    res = client.table("atividades").delete().eq("id", atividade_id).execute()
    return True

# ============================================================
#  CRUD - CONFIGURAÇÃO DE ESCALA
# ============================================================

def salvar_config_escala(data_inicio_trabalho: date) -> dict:
    """Salva/atualiza a configuração da escala 12×36."""
    client = get_supabase()
    payload = {
        "data_inicio_trabalho": data_inicio_trabalho.isoformat(),
        "atualizado_em": datetime.utcnow().isoformat(),
    }
    res = client.table("config_escala").upsert(payload).execute()
    return res.data[0] if res.data else {}

def obter_config_escala() -> Optional[dict]:
    """Retorna a configuração atual da escala, se existir."""
    client = get_supabase()
    res = client.table("config_escala").select("*").limit(1).execute()
    return res.data[0] if res.data else None

# ============================================================
#  CRUD - CONFIGURAÇÃO DE ALARME
# ============================================================

def salvar_config_alarme(horario: str, ativo: bool = True) -> dict:
    """Salva/atualiza a configuração do alarme de estudo."""
    client = get_supabase()
    payload = {
        "horario": horario,          # formato "HH:MM"
        "ativo": ativo,
        "atualizado_em": datetime.utcnow().isoformat(),
    }
    res = client.table("config_alarme").upsert(payload).execute()
    return res.data[0] if res.data else {}

def obter_config_alarme() -> Optional[dict]:
    """Retorna a configuração atual do alarme."""
    client = get_supabase()
    res = client.table("config_alarme").select("*").limit(1).execute()
    return res.data[0] if res.data else None
