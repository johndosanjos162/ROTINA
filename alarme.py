# alarme.py
# Alarme de estudo: som alto + mensagem de voz "Tá na hora do estudo".
# Só dispara em dias de folga e no horário configurado.

import threading
import time
import tempfile
import os
from datetime import date, datetime
from typing import Callable, Optional

import streamlit as st
import pygame
import pyttsx3
from escala import e_dia_de_folga

# Inicialização global do mixer de áudio
pygame.mixer.init()

def _gerar_audio_voz(texto: str = "Tá na hora do estudo") -> str:
    """
    Gera um arquivo de áudio temporário com a voz sintetizada.
    Retorna o caminho do arquivo .mp3 gerado.
    """
    engine = pyttsx3.init()
    engine.setProperty("rate", 160)      # velocidade da fala
    engine.setProperty("volume", 1.0)    # volume máximo
    # Tenta selecionar voz em português, se disponível
    voices = engine.getProperty("voices")
    for v in voices:
        if "portuguese" in v.name.lower() or "brazil" in v.name.lower():
            engine.setProperty("voice", v.id)
            break

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
    engine.save_to_file(texto, tmp.name)
    engine.runAndWait()
    return tmp.name

def _tocar_alarme_completo(texto_voz: str = "Tá na hora do estudo",
                           duracao_som: int = 10):
    """
    Toca sequência: som de alarme (10s) + fala "Tá na hora do estudo".
    Executado em thread separada para não bloquear o Streamlit.
    """
    # 1. Toca som de alarme alto (usando um tom gerado ou arquivo)
    #    Aqui usamos um beep sintético via pygame como fallback universal.
    try:
        # Tenta carregar um som de alarme se existir no diretório
        if os.path.exists("alarme.mp3"):
            pygame.mixer.music.load("alarme.mp3")
            pygame.mixer.music.set_volume(1.0)
            pygame.mixer.music.play()
            time.sleep(duracao_som)
            pygame.mixer.music.stop()
        else:
            # Fallback: gera um tom de alerta com pygame
            import numpy as np
            sample_rate = 44100
            duration = duracao_som
            t = np.linspace(0, duration, int(sample_rate * duration), False)
            # Tom de 880 Hz (A5) com fade
            tone = 0.8 * np.sin(2 * np.pi * 880 * t)
            # Aplica envelope para evitar cliques
            envelope = np.ones_like(tone)
            fade = int(sample_rate * 0.05)
            envelope[:fade] = np.linspace(0, 1, fade)
            envelope[-fade:] = np.linspace(1, 0, fade)
            tone = (tone * envelope * 32767).astype(np.int16)
            stereo = np.column_stack((tone, tone))
            sound = pygame.sndarray.make_sound(stereo)
            sound.play()
            time.sleep(duration)
    except Exception as e:
        # Último recurso: beep do sistema
        print(f"Erro no som: {e}. Usando beep alternativo.")
        for _ in range(5):
            print("\a")  # beep do terminal
            time.sleep(0.5)

    # 2. Fala "Tá na hora do estudo"
    try:
        audio_path = _gerar_audio_voz(texto_voz)
        pygame.mixer.music.load(audio_path)
        pygame.mixer.music.play()
        # Aguarda a duração aproximada da fala
        time.sleep(3)
        pygame.mixer.music.stop()
        os.unlink(audio_path)
    except Exception as e:
        print(f"Erro na voz: {e}")

def verificar_e_disparar_alarme(data_inicio_trabalho: date,
                               horario_configurado: str,
                               texto_voz: str = "Tá na hora do estudo",
                               forcar: bool = False) -> bool:
    """
    Verifica se é dia de folga e se o horário atual coincide com o configurado.
    Se sim, dispara o alarme em thread separada.

    Retorna True se o alarme foi disparado.
    """
    agora = datetime.now()
    hoje = agora.date()

    # Verificação 1: é dia de folga?
    if not forcar and not e_dia_de_folga(hoje, data_inicio_trabalho):
        return False

    # Verificação 2: horário coincide? (tolerância de 1 minuto)
    hora_atual = agora.strftime("%H:%M")
    if not forcar and hora_atual != horario_configurado:
        return False

    # Dispara em thread separada para não travar a UI
    thread = threading.Thread(
        target=_tocar_alarme_completo,
        args=(texto_voz,),
        daemon=True,
    )
    thread.start()
    return True

# ============================================================
#  Monitor em background (executa enquanto o app está aberto)
# ============================================================

class MonitorAlarme:
    """
    Monitor que verifica o horário a cada 30 segundos.
    Deve ser iniciado uma única vez por sessão Streamlit.
    """

    def __init__(self):
        self._ultimo_disparo = None
        self._thread = None
        self._rodando = False

    def iniciar(self, data_inicio_trabalho: date, horario: str):
        if self._rodando:
            return
        self._rodando = True
        self._data_inicio = data_inicio_trabalho
        self._horario = horario
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def _loop(self):
        while self._rodando:
            agora = datetime.now()
            chave = agora.strftime("%Y-%m-%d %H:%M")
            if chave != self._ultimo_disparo:
                disparou = verificar_e_disparar_alarme(
                    self._data_inicio, self._horario
                )
                if disparou:
                    self._ultimo_disparo = chave
            time.sleep(30)

    def parar(self):
        self._rodando = False
