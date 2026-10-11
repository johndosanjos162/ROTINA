# alarme.py
# ============================================================
# Sistema de Alarme de Estudo
# - Som de alarme gerado como WAV e tocado via ffplay
# - Voz "Tá na hora do estudo" via espeak CLI (PT-BR)
# - Só dispara em dias de folga no horário configurado
#
# DEPENDÊNCIAS DO SISTEMA (packages.txt):
#   - espeak       → voz em português
#   - libespeak1   → runtime do espeak
#   - ffmpeg       → fornece o binário `ffplay` para tocar áudio
#
# NENHUMA dependência Python além da stdlib é necessária aqui.
# ============================================================

import os
import math
import wave
import struct
import shutil
import tempfile
import threading
import time
import subprocess
import sys
from datetime import date, datetime
from typing import Optional

import streamlit as st

from escala import e_dia_de_folga


# ============================================================
#  Detecção de binários disponíveis no sistema
# ============================================================
_FFPLAY = shutil.which("ffplay")
_ESPEAK = shutil.which("espeak")

if _FFPLAY is None:
    print("[alarme] AVISO: 'ffplay' não encontrado. Instale o pacote 'ffmpeg'.")
if _ESPEAK is None:
    print("[alarme] AVISO: 'espeak' não encontrado. Instale o pacote 'espeak'.")


# ============================================================
#  Geração do arquivo WAV de alarme (som de sirene)
# ============================================================
def _gerar_wav_alarme(caminho: str, duracao_s: int = 10,
                      sample_rate: int = 44100) -> None:
    """
    Gera um arquivo WAV de alarme com padrão de sirene bitonal
    (880 Hz e 1200 Hz alternando a cada 0.5s) — bem "alarmante".

    Usa apenas o módulo padrão `wave` + `math` + `struct`.
    Nenhuma dependência externa.
    """
    n_samples = int(sample_rate * duracao_s)
    amplitude = 0.85  # 85% de volume máximo
    freq_a, freq_b = 880, 1200

    with wave.open(caminho, "wb") as wav:
        wav.setnchannels(1)      # mono
        wav.setsampwidth(2)      # 16 bits
        wav.setframerate(sample_rate)

        frames = bytearray()
        for i in range(n_samples):
            t = i / sample_rate

            # Padrão bitonal: alterna a cada 0.5s
            freq = freq_a if int(t * 2) % 2 == 0 else freq_b

            # Envelope de fade-in/out global (0.1s no início e fim)
            if t < 0.1:
                env = t / 0.1
            elif t > duracao_s - 0.1:
                env = (duracao_s - t) / 0.1
            else:
                env = 1.0

            sample = math.sin(2 * math.pi * freq * t) * amplitude * env
            value = int(sample * 32767)
            frames += struct.pack("<h", value)

        wav.writeframes(bytes(frames))


# ============================================================
#  Reprodução via subprocessos (ffplay + espeak)
# ============================================================
def _tocar_wav(caminho_wav: str, timeout: int = 30) -> bool:
    """Reproduz um arquivo WAV via ffplay (silencioso, sem janela)."""
    if _FFPLAY is None:
        return False
    try:
        subprocess.run(
            [
                _FFPLAY,
                "-nodisp",           # sem vídeo
                "-autoexit",         # sai ao terminar
                "-loglevel", "quiet",
                caminho_wav,
            ],
            check=True,
            timeout=timeout,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return True
    except Exception as e:
        print(f"[alarme] Erro no ffplay: {e}")
        return False


def _falar_espeak(texto: str, rate: int = 160, volume: int = 200,
                  timeout: int = 15) -> bool:
    """
    Fala usando o comando `espeak` diretamente.

    - `-v pt-br`   → voz em português do Brasil
    - `-s <rate>`  → velocidade (palavras por minuto)
    - `-a <vol>`   → amplitude (0-200, sendo 200 o máximo)
    """
    if _ESPEAK is None:
        return False
    try:
        subprocess.run(
            [
                _ESPEAK,
                "-v", "pt-br",
                "-s", str(rate),
                "-a", str(volume),
                texto,
            ],
            check=True,
            timeout=timeout,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return True
    except subprocess.CalledProcessError as e:
        print(f"[alarme] espeak retornou erro: {e}")
        # Tenta com voz padrão (inglês) como fallback
        try:
            subprocess.run(
                [_ESPEAK, "-s", str(rate), "-a", str(volume), texto],
                check=True, timeout=timeout,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return True
        except Exception:
            return False
    except Exception as e:
        print(f"[alarme] Erro ao invocar espeak: {e}")
        return False


# ============================================================
#  Sequência completa do alarme
# ============================================================
def _tocar_alarme_completo(texto_voz: str = "Tá na hora do estudo",
                           duracao_som: int = 8) -> None:
    """
    Executa a sequência do alarme:
      1) Gera WAV de sirene bitonal e toca via ffplay
      2) Fala "Tá na hora do estudo" via espeak em pt-br
      3) Repete a fala uma segunda vez (para garantir que acorde)
    """
    # ---------- 1. SIRENE ----------
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
            caminho_wav = tmp.name
        _gerar_wav_alarme(caminho_wav, duracao_s=duracao_som)
        _tocar_wav(caminho_wav, timeout=duracao_som + 10)
        os.unlink(caminho_wav)
    except Exception as e:
        print(f"[alarme] Erro ao gerar/tocar sirene: {e}")

    # ---------- 2. VOZ (1ª vez) ----------
    time.sleep(0.3)
    _falar_espeak(texto_voz, rate=160, volume=200)

    # ---------- 3. VOZ (2ª vez, mais lenta) ----------
    time.sleep(0.5)
    _falar_espeak(texto_voz, rate=140, volume=200)


# ============================================================
#  Verificação e disparo
# ============================================================
def verificar_e_disparar_alarme(data_inicio_trabalho: date,
                               horario_configurado: str,
                               texto_voz: str = "Tá na hora do estudo",
                               forcar: bool = False) -> bool:
    """
    Verifica se é dia de folga E se o horário atual coincide
    com o configurado. Se sim, dispara o alarme em thread paralela.

    Retorna True se o alarme foi disparado.
    """
    agora = datetime.now()
    hoje = agora.date()

    if not forcar and not e_dia_de_folga(hoje, data_inicio_trabalho):
        return False

    if not forcar and agora.strftime("%H:%M") != horario_configurado:
        return False

    thread = threading.Thread(
        target=_tocar_alarme_completo,
        args=(texto_voz,),
        daemon=True,
    )
    thread.start()
    return True


# ============================================================
#  Monitor em background
# ============================================================
class MonitorAlarme:
    """
    Monitor que verifica o horário a cada 30s enquanto o app
    estiver aberto. Deve ser instanciado UMA vez por sessão.
    """

    def __init__(self):
        self._ultimo_disparo: Optional[str] = None
        self._thread: Optional[threading.Thread] = None
        self._rodando: bool = False
        self._data_inicio: Optional[date] = None
        self._horario: Optional[str] = None

    def iniciar(self, data_inicio_trabalho: date, horario: str):
        if self._rodando:
            self._data_inicio = data_inicio_trabalho
            self._horario = horario
            return
        self._rodando = True
        self._data_inicio = data_inicio_trabalho
        self._horario = horario
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def atualizar(self, data_inicio_trabalho: date = None,
                  horario: str = None):
        if data_inicio_trabalho is not None:
            self._data_inicio = data_inicio_trabalho
        if horario is not None:
            self._horario = horario

    def _loop(self):
        while self._rodando:
            try:
                agora = datetime.now()
                chave = agora.strftime("%Y-%m-%d %H:%M")
                if chave != self._ultimo_disparo:
                    if self._data_inicio and self._horario:
                        if verificar_e_disparar_alarme(
                            self._data_inicio, self._horario
                        ):
                            self._ultimo_disparo = chave
            except Exception as e:
                print(f"[monitor] Erro: {e}")
            time.sleep(30)

    def parar(self):
        self._rodando = False

    def esta_rodando(self) -> bool:
        return self._rodando


# ============================================================
#  Diagnóstico (útil para o usuário confirmar no app)
# ============================================================
def verificar_dependencias_sistema() -> dict:
    """
    Retorna um dicionário indicando se ffplay e espeak estão
    disponíveis no ambiente. Usado pela UI para exibir status.
    """
    return {
        "ffplay": _FFPLAY is not None,
        "ffplay_path": _FFPLAY or "—",
        "espeak": _ESPEAK is not None,
        "espeak_path": _ESPEAK or "—",
    }
