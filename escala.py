# escala.py
# ============================================================
# Lógica da escala 12x36 REAL:
#   - Trabalha 12h (ex: 6h às 18h)
#   - Folga 36h
#   - Ciclo total: 48h = 2 dias
#
# Padrão: trabalho → folga → trabalho → folga → ...
# ============================================================

from datetime import date, timedelta
from typing import List, Literal

TipoDia = Literal["trabalho", "folga"]


def gerar_dias_escala(data_inicio_trabalho: date,
                      dias_para_gerar: int = 60) -> List[dict]:
    """
    Gera a sequência de dias da escala 12x36.

    Regra:
      - Dia 0 (data_inicio_trabalho) = TRABALHO
      - Dia 1 = FOLGA
      - Dia 2 = TRABALHO
      - Dia 3 = FOLGA
      - Alterna a cada dia.

    Retorna lista de dicts: {data, tipo, indice_ciclo, ciclo_numero}
    """
    resultado = []
    for i in range(dias_para_gerar):
        dia = data_inicio_trabalho + timedelta(days=i)
        tipo = "trabalho" if i % 2 == 0 else "folga"
        resultado.append({
            "data": dia,
            "tipo": tipo,
            "indice_ciclo": i % 2,
            "ciclo_numero": i // 2,
        })
    return resultado


def classificar_dia(data_alvo: date, data_inicio_trabalho: date) -> TipoDia:
    """
    Classifica um dia específico.
    Se a diferença em dias for PAR → trabalho. ÍMPAR → folga.
    """
    delta = (data_alvo - data_inicio_trabalho).days
    return "trabalho" if delta % 2 == 0 else "folga"


def e_dia_de_folga(data_alvo: date, data_inicio_trabalho: date) -> bool:
    """Retorna True se o dia for de folga (alarme pode disparar)."""
    return classificar_dia(data_alvo, data_inicio_trabalho) == "folga"


def proximos_dias_folga(data_inicio_trabalho: date,
                        a_partir_de: date = None,
                        quantidade: int = 5) -> List[date]:
    """Lista as próximas datas de folga a partir de uma data."""
    if a_partir_de is None:
        a_partir_de = date.today()
    folgas = []
    cursor = a_partir_de
    while len(folgas) < quantidade:
        if e_dia_de_folga(cursor, data_inicio_trabalho):
            folgas.append(cursor)
        cursor += timedelta(days=1)
    return folgas
