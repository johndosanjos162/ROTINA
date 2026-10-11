# alarme_browser.py
# ============================================================
# Alarme que toca NO NAVEGADOR do usuário (cliente).
#
# Parâmetros configuráveis:
#   - duracao_segundos : duração da sirene (3 a 60)
#   - volume           : 0 a 100 (%)
#   - repeticoes_voz   : quantas vezes a voz fala
#   - velocidade_voz   : 50 a 200 (100 = normal)
# ============================================================

import streamlit.components.v1 as components
from datetime import date


def render_alarme_browser(data_inicio: date,
                          horario: str,
                          ativo: bool = True,
                          duracao_segundos: int = 8,
                          volume: int = 80,
                          repeticoes_voz: int = 2,
                          velocidade_voz: int = 95) -> None:
    """
    Injeta o alarme no navegador do usuário com todos os
    parâmetros configuráveis.
    """
    data_iso = data_inicio.isoformat()
    ativo_js = "true" if ativo else "false"
    vol_js = max(0, min(100, volume)) / 100.0  # converte p/ 0.0–1.0
    vel_js = max(0.5, min(2.0, velocidade_voz / 100.0))

    components.html(
        f"""
        <div id="status-alarme" style="
            font-family: sans-serif; font-size: 12px;
            color: #666; padding: 4px;">
            ⏳ Inicializando alarme no navegador...
        </div>

        <script>
        (function() {{
            const DATA_INICIO   = new Date("{data_iso}T00:00:00");
            const HORARIO       = "{horario}";
            const ATIVO         = {ativo_js};
            const DURACAO       = {duracao_segundos};
            const VOLUME        = {vol_js};       // 0.0 a 1.0
            const REPETICOES    = {repeticoes_voz};
            const VELOCIDADE    = {vel_js};        // 0.5 a 2.0

            const statusEl = document.getElementById("status-alarme");
            let ultimoDisparo = null;

            // ---------- Cálculo: é dia de folga? ----------
            function ehDiaDeFolga(data) {{
                const d = new Date(data.getFullYear(),
                                   data.getMonth(),
                                   data.getDate());
                const inicio = new Date(DATA_INICIO.getFullYear(),
                                        DATA_INICIO.getMonth(),
                                        DATA_INICIO.getDate());
                const diffMs = d - inicio;
                const diffDias = Math.round(diffMs / 86400000);
                return (diffDias % 2 !== 0);  // ímpar = folga
            }}

            // ---------- Sirene bitonal via Web Audio ----------
            function tocarSirene() {{
                try {{
                    const ctx = new (window.AudioContext ||
                                     window.webkitAudioContext)();
                    if (ctx.state === "suspended") ctx.resume();

                    const agora = ctx.currentTime;
                    const osc = ctx.createOscillator();
                    const gain = ctx.createGain();
                    osc.connect(gain);
                    gain.connect(ctx.destination);

                    osc.type = "square";

                    // Ganho com fade-in/out para não estourar
                    gain.gain.setValueAtTime(0, agora);
                    gain.gain.linearRampToValueAtTime(
                        VOLUME, agora + 0.05
                    );
                    gain.gain.setValueAtTime(
                        VOLUME, agora + DURACAO - 0.1
                    );
                    gain.gain.linearRampToValueAtTime(
                        0, agora + DURACAO
                    );

                    // Alterna 880 Hz ↔ 1200 Hz a cada 0.5s
                    const total = DURACAO * 2;
                    for (let i = 0; i < total; i++) {{
                        const t = agora + i * 0.5;
                        osc.frequency.setValueAtTime(
                            i % 2 === 0 ? 880 : 1200, t
                        );
                    }}

                    osc.start(agora);
                    osc.stop(agora + DURACAO);
                }} catch (e) {{
                    console.error("Erro no Web Audio:", e);
                }}
            }}

            // ---------- Voz via SpeechSynthesis ----------
            function falarUmaVez(texto) {{
                if (!("speechSynthesis" in window)) return;
                const utt = new SpeechSynthesisUtterance(texto);
                utt.lang = "pt-BR";
                utt.rate = VELOCIDADE;
                utt.volume = VOLUME;
                const vozes = window.speechSynthesis.getVoices();
                const vozPT = vozes.find(v => v.lang.startsWith("pt"));
                if (vozPT) utt.voice = vozPT;
                window.speechSynthesis.speak(utt);
            }}

            function falarRepetido(texto, vezes) {{
                for (let i = 0; i < vezes; i++) {{
                    setTimeout(() => falarUmaVez(texto), i * 2800);
                }}
            }}

            // ---------- Dispara alarme completo ----------
            function dispararAlarme() {{
                tocarSirene();
                // Começa a falar após 1s (para não competir com a sirene)
                setTimeout(() => falarRepetido(
                    "Tá na hora do estudo", REPETICOES
                ), 1000);
            }}

            // ---------- Verificação a cada 20s ----------
            function verificar() {{
                if (!ATIVO) {{
                    statusEl.textContent = "🔕 Alarme desativado.";
                    return;
                }}
                const agora = new Date();
                const horaAtual =
                    String(agora.getHours()).padStart(2, "0") + ":" +
                    String(agora.getMinutes()).padStart(2, "0");
                const chave = agora.toDateString() + " " + horaAtual;

                if (chave === ultimoDisparo) return;

                const folga = ehDiaDeFolga(agora);
                statusEl.textContent =
                    `🔔 Ativo | Hoje: ${{folga ? "FOLGA 🟢" : "TRABALHO 🔴"}} | ` +
                    `Agora: ${{horaAtual}} | Programado: ${{HORARIO}} | ` +
                    `${{DURACAO}}s @ ${{Math.round(VOLUME*100)}}% | ` +
                    `Voz: ${{REPETICOES}}x`;

                if (folga && horaAtual === HORARIO) {{
                    ultimoDisparo = chave;
                    statusEl.textContent = "🚨 ALARME DISPARANDO!";
                    dispararAlarme();
                }}
            }}

            if ("speechSynthesis" in window) {{
                window.speechSynthesis.onvoiceschanged = () => {{}};
            }}

            setInterval(verificar, 20000);
            verificar();
        }})();
        </script>
        """,
        height=40,
    )


def render_botao_teste_browser(duracao_segundos: int = 8,
                               volume: int = 80,
                               repeticoes_voz: int = 2,
                               velocidade_voz: int = 95) -> None:
    """
    Botão HTML que dispara o alarme imediatamente no navegador,
    respeitando os parâmetros configurados.
    """
    vol_js = max(0, min(100, volume)) / 100.0
    vel_js = max(0.5, min(2.0, velocidade_voz / 100.0))

    components.html(
        f"""
        <button id="btn-teste" style="
            background:#1E88E5; color:white; border:none;
            padding:10px 18px; border-radius:8px; font-size:14px;
            cursor:pointer; margin-top:6px;">
            🔔 Testar alarme no navegador
        </button>
        <span id="msg-teste" style="
            margin-left:12px; font-family:sans-serif; font-size:13px;
            color:#00AA55;"></span>

        <script>
        const DURACAO    = {duracao_segundos};
        const VOLUME     = {vol_js};
        const REPETICOES = {repeticoes_voz};
        const VELOCIDADE = {vel_js};

        document.getElementById("btn-teste").onclick = function() {{
            const msg = document.getElementById("msg-teste");
            msg.textContent = "Tocando...";

            try {{
                const ctx = new (window.AudioContext ||
                                 window.webkitAudioContext)();
                if (ctx.state === "suspended") ctx.resume();

                const agora = ctx.currentTime;
                const osc = ctx.createOscillator();
                const gain = ctx.createGain();
                osc.connect(gain);
                gain.connect(ctx.destination);
                osc.type = "square";

                gain.gain.setValueAtTime(0, agora);
                gain.gain.linearRampToValueAtTime(VOLUME, agora + 0.05);
                gain.gain.setValueAtTime(VOLUME, agora + DURACAO - 0.1);
                gain.gain.linearRampToValueAtTime(0, agora + DURACAO);

                for (let i = 0; i < DURACAO * 2; i++) {{
                    osc.frequency.setValueAtTime(
                        i % 2 === 0 ? 880 : 1200,
                        agora + i * 0.5
                    );
                }}
                osc.start(agora);
                osc.stop(agora + DURACAO);

                // Voz
                if ("speechSynthesis" in window) {{
                    for (let i = 0; i < REPETICOES; i++) {{
                        setTimeout(() => {{
                            const utt = new SpeechSynthesisUtterance(
                                "Tá na hora do estudo"
                            );
                            utt.lang = "pt-BR";
                            utt.rate = VELOCIDADE;
                            utt.volume = VOLUME;
                            const vozes =
                                window.speechSynthesis.getVoices();
                            const vozPT =
                                vozes.find(v => v.lang.startsWith("pt"));
                            if (vozPT) utt.voice = vozPT;
                            window.speechSynthesis.speak(utt);
                        }}, 1000 + i * 2800);
                    }}
                }}

                msg.textContent = "✅ Testado! Verifique o áudio.";
                setTimeout(() => msg.textContent = "", 5000);
            }} catch (e) {{
                msg.textContent = "❌ Erro: " + e.message;
            }}
        }};
        </script>
        """,
        height=60,
    )
