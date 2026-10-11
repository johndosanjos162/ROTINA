# escala.py
# Lógica pura da escala 12x36: cálculo de dias de trabalho e folga.

from datetime import date, timedelta
from typing import List, Literal

TipoDia = Literal["trabalho", "folga", "rotina_casa"]

def gerar_dias_escala(data_inicio_trabalho: date,
                      dias_para_gerar: int = 60) -> List[dict]:
    """
    Gera a sequência de dias da escala 12x36.

    Regra:
      - Dia 0 (data_inicio_trabalho) = TRABALHO (12h)
      - Dias 1 e 2 = FOLGA / ROTINA_CASA (36h)
      - Padrão se repete a cada 3 dias.

    Retorna lista de dicts: {data, tipo, indice_ciclo}
    """
    resultado = []
    ciclo = 0
    for i in range(dias_para_gerar):
        dia = data_inicio_trabalho + timedelta(days=i)
        posicao_no_ciclo = i % 3

        if posicao_no_ciclo == 0:
            tipo = "trabalho"
        elif posicao_no_ciclo == 1:
            tipo = "folga"
        else:
            tipo = "rotina_casa"

        resultado.append({
            "data": dia,
            "tipo": tipo,
            "indice_ciclo": posicao_no_ciclo,
            "ciclo_numero": i // 3,
        })
    return resultado

def classificar_dia(data_alvo: date, data_inicio_trabalho: date) -> TipoDia:
    """Classifica um dia específico com base na data de início da escala."""
    delta = (data_alvo - data_inicio_trabalho).days
    posicao = delta % 3
    if posicao == 0:
        return "trabalho"
    elif posicao == 1:
        return "folga"
    else:
        return "rotina_casa"

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