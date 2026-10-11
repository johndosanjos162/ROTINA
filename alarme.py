# alarme.py
# ============================================================
# Sistema de Alarme de Estudo
# - Toca som alto (pygame) + fala "Tá na hora do estudo" (pyttsx3)
# - Só dispara em dias de folga no horário configurado
# - Voz gerada em SUBPROCESSO para evitar conflitos com o loop
#   de eventos do Streamlit (correção do erro no Cloud)
# ============================================================

import threading
import time
import tempfile
import os
import subprocess
import sys
from datetime import date, datetime
from typing import Optional

import streamlit as st
import pygame

from escala import e_dia_de_folga

# ------------------------------------------------------------
# Inicialização segura do mixer de áudio (com fallback)
# ------------------------------------------------------------
_AUDIO_DISPONIVEL = False
try:
    pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
    _AUDIO_DISPONIVEL = True
except Exception as e:
    print(f"[alarme] Aviso: mixer de áudio indisponível ({e}). "
          f"Alarme usará beep do sistema como fallback.")


# ============================================================
#  Geração de voz em SUBPROCESSO
# ============================================================
def _falar_via_subprocesso(texto: str,
                           rate: int = 160,
                           volume: float = 1.0,
                           timeout: int = 15) -> bool:
    """
    Gera e reproduz a fala em um subprocesso Python isolado.

    Isso evita o conflito clássico entre o loop de eventos do pyttsx3
    (que é bloqueante) e o runtime do Streamlit — principal causa de
    travamentos e do erro de dependência no Streamlit Cloud.

    Retorna True se a fala foi executada com sucesso.
    """
    # Script executado no subprocesso. Usa repr() para escapar o texto
    # com segurança, evitando injeção de código.
    script_voz = (
        "import pyttsx3\n"
        "engine = pyttsx3.init()\n"
        f"engine.setProperty('rate', {rate})\n"
        f"engine.setProperty('volume', {volume})\n"
        # Tenta selecionar voz em português, se disponível
        "voices = engine.getProperty('voices')\n"
        "for v in voices:\n"
        "    nome = v.name.lower()\n"
        "    if 'portuguese' in nome or 'brazil' in nome or 'pt-br' in nome:\n"
        "        engine.setProperty('voice', v.id)\n"
        "        break\n"
        f"engine.say({texto!r})\n"
        "engine.runAndWait()\n"
    )

    try:
        resultado = subprocess.run(
            [sys.executable, "-c", script_voz],
            check=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return True
    except subprocess.CalledProcessError as e:
        print(f"[alarme] Erro no subprocesso de voz: {e.stderr}")
        return False
    except subprocess.TimeoutExpired:
        print("[alarme] Timeout ao gerar voz.")
        return False
    except Exception as e:
        print(f"[alarme] Falha inesperada na voz: {e}")
        return False


# ============================================================
#  Geração de tom sintético (fallback universal)
# ============================================================
def _tocar_tom_sintetico(frequencia: int = 880, duracao: int = 10):
    """
    Gera um tom de alarme sintético via pygame + numpy.
    Usado quando não há arquivo 'alarme.mp3' disponível.
    """
    try:
        import numpy as np
        sample_rate = 44100
        t = np.linspace(0, duracao, int(sample_rate * duracao), False)

        # Tom principal + harmônico para soar mais "alarmante"
        tom = (0.7 * np.sin(2 * np.pi * frequencia * t)
               + 0.3 * np.sin(2 * np.pi * (frequencia * 1.5) * t))

        # Envelope de fade-in / fade-out para evitar cliques
        envelope = np.ones_like(tom)
        fade = int(sample_rate * 0.05)
        envelope[:fade] = np.linspace(0, 1, fade)
        envelope[-fade:] = np.linspace(1, 0, fade)
        tom = tom * envelope

        # Converte para int16 estéreo
        tom_int = (tom * 32767 * 0.8).astype(np.int16)
        stereo = np.column_stack((tom_int, tom_int))

        sound = pygame.sndarray.make_sound(stereo)
        sound.set_volume(1.0)
        sound.play()
        time.sleep(duracao)
    except Exception as e:
        print(f"[alarme] Falha no tom sintético: {e}. Usando beep do sistema.")
        for _ in range(10):
            print("\a", end="", flush=True)
            time.sleep(0.4)


# ============================================================
#  Toca alarme completo: som + voz
# ============================================================
def _tocar_alarme_completo(texto_voz: str = "Tá na hora do estudo",
                           duracao_som: int = 10):
    """
    Executa a sequência do alarme:
      1) Som alto de alerta (arquivo local ou tom sintético)
      2) Fala "Tá na hora do estudo" em subprocesso

    Esta função DEVE rodar em uma thread separada, pois é bloqueante.
    """
    # ---------- 1. SOM DE ALERTA ----------
    if _AUDIO_DISPONIVEL:
        try:
            if os.path.exists("alarme.mp3"):
                pygame.mixer.music.load("alarme.mp3")
                pygame.mixer.music.set_volume(1.0)
                pygame.mixer.music.play()
                time.sleep(duracao_som)
                pygame.mixer.music.stop()
            else:
                # Fallback: tom sintético de 880 Hz por N segundos
                _tocar_tom_sintetico(frequencia=880, duracao=duracao_som)
        except Exception as e:
            print(f"[alarme] Erro no som: {e}")
            for _ in range(10):
                print("\a", end="", flush=True)
                time.sleep(0.4)
    else:
        # Áudio totalmente indisponível: beeps do terminal
        for _ in range(10):
            print("\a", end="", flush=True)
            time.sleep(0.4)

    # ---------- 2. VOZ (SUBPROCESSO) ----------
    # Gera a fala em um processo Python isolado para não travar o Streamlit.
    _falar_via_subprocesso(texto_voz, rate=160, volume=1.0, timeout=15)


# ============================================================
#  Verificação e disparo do alarme
# ============================================================
def verificar_e_disparar_alarme(data_inicio_trabalho: date,
                               horario_configurado: str,
                               texto_voz: str = "Tá na hora do estudo",
                               forcar: bool = False) -> bool:
    """
    Verifica se:
      1) Hoje é dia de folga (a menos que `forcar=True`)
      2) O horário atual bate com o configurado (tolerância de 1 minuto)

    Se sim, dispara o alarme em uma thread separada.

    Retorna True se o alarme foi disparado.
    """
    agora = datetime.now()
    hoje = agora.date()

    # --- Verificação 1: é dia de folga? ---
    if not forcar and not e_dia_de_folga(hoje, data_inicio_trabalho):
        return False

    # --- Verificação 2: horário coincide? ---
    hora_atual = agora.strftime("%H:%M")
    if not forcar and hora_atual != horario_configurado:
        return False

    # --- Dispara em thread separada (não bloqueia a UI) ---
    thread = threading.Thread(
        target=_tocar_alarme_completo,
        args=(texto_voz,),
        daemon=True,
    )
    thread.start()
    return True


# ============================================================
#  Monitor de alarme em background
# ============================================================
class MonitorAlarme:
    """
    Monitor que verifica o horário a cada 30 segundos enquanto o app
    estiver aberto. Deve ser instanciado UMA vez por sessão Streamlit.

    Uso típico:
        if "monitor" not in st.session_state:
            st.session_state.monitor = MonitorAlarme()
        st.session_state.monitor.iniciar(data_inicio, "20:00")
    """

    def __init__(self):
        self._ultimo_disparo: Optional[str] = None
        self._thread: Optional[threading.Thread] = None
        self._rodando: bool = False
        self._data_inicio: Optional[date] = None
        self._horario: Optional[str] = None

    def iniciar(self, data_inicio_trabalho: date, horario: str):
        """Inicia o loop de verificação em thread daemon."""
        if self._rodando:
            # Atualiza apenas os parâmetros se já estiver rodando
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
        """Atualiza os parâmetros sem reiniciar a thread."""
        if data_inicio_trabalho is not None:
            self._data_inicio = data_inicio_trabalho
        if horario is not None:
            self._horario = horario

    def _loop(self):
        """Loop principal do monitor (roda em thread separada)."""
        while self._rodando:
            try:
                agora = datetime.now()
                chave = agora.strftime("%Y-%m-%d %H:%M")

                # Evita disparos duplicados no mesmo minuto
                if chave != self._ultimo_disparo:
                    if self._data_inicio and self._horario:
                        disparou = verificar_e_disparar_alarme(
                            self._data_inicio,
                            self._horario,
                        )
                        if disparou:
                            self._ultimo_disparo = chave
            except Exception as e:
                print(f"[monitor] Erro no loop: {e}")

            time.sleep(30)

    def parar(self):
        """Para o monitor graciosamente."""
        self._rodando = False

    def esta_rodando(self) -> bool:
        return self._rodando
