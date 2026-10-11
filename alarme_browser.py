# alarme_browser.py
# ============================================================
# Alarme que toca NO NAVEGADOR do usuário (cliente), não no
# servidor do Streamlit Cloud.
#
# Usa:
#   - Web Audio API  → sirene bitonal
#   - SpeechSynthesis → voz "Tá na hora do estudo" em pt-BR
#
# Limitação: só funciona enquanto a aba do app estiver aberta.
# ============================================================

import streamlit.components.v1 as components
from datetime import date


def render_alarme_browser(data_inicio: date,
                          horario: str,
                          ativo: bool = True) -> None:
    """
    Injeta o alarme no navegador do usuário.

    - `data_inicio`: data do primeiro dia de trabalho (escala 12x36)
    - `horario`: "HH:MM" do alarme
    - `ativo`: se False, o alarme fica desligado
    """
    data_iso = data_inicio.isoformat()
    ativo_js = "true" if ativo else "false"

    # Componente HTML/JS. Altura 0 para não ocupar espaço visual.
    components.html(
        f"""
        <div id="status-alarme" style="
            font-family: sans-serif; font-size: 12px;
            color: #666; padding: 4px;">
            ⏳ Inicializando alarme no navegador...
        </div>

        <script>
        (function() {{
            const DATA_INICIO = new Date("{data_iso}T00:00:00");
            const HORARIO    = "{horario}";
            const ATIVO      = {ativo_js};

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
                // Par → trabalho, Ímpar → folga
                return (diffDias % 2 !== 0);
            }}

            // ---------- Sirene bitonal via Web Audio ----------
            function tocarSirene(duracaoSeg = 8) {{
                try {{
                    const ctx = new (window.AudioContext ||
                                     window.webkitAudioContext)();
                    const agora = ctx.currentTime;
                    const osc = ctx.createOscillator();
                    const gain = ctx.createGain();
                    osc.connect(gain);
                    gain.connect(ctx.destination);

                    osc.type = "square";
                    gain.gain.setValueAtTime(0.15, agora);

                    // Alterna 880 Hz ↔ 1200 Hz a cada 0.5s
                    const totalAlternancias = duracaoSeg * 2;
                    for (let i = 0; i < totalAlternancias; i++) {{
                        const t = agora + i * 0.5;
                        osc.frequency.setValueAtTime(
                            i % 2 === 0 ? 880 : 1200, t
                        );
                    }}

                    osc.start(agora);
                    osc.stop(agora + duracaoSeg);
                }} catch (e) {{
                    console.error("Erro no Web Audio:", e);
                }}
            }}

            // ---------- Voz via SpeechSynthesis ----------
            function falar(texto) {{
                if (!("speechSynthesis" in window)) {{
                    console.warn("SpeechSynthesis não suportado.");
                    return;
                }}
                const utt = new SpeechSynthesisUtterance(texto);
                utt.lang = "pt-BR";
                utt.rate = 0.95;
                utt.volume = 1.0;

                // Tenta selecionar uma voz pt-BR
                const vozes = window.speechSynthesis.getVoices();
                const vozPT = vozes.find(v => v.lang.startsWith("pt"));
                if (vozPT) utt.voice = vozPT;

                window.speechSynthesis.speak(utt);
            }}

            // ---------- Verificação a cada 20s ----------
            function verificar() {{
                if (!ATIVO) {{
                    statusEl.textContent = "🔕 Alarme desativado.";
                    return;
                }}
                const agora = new Date();
                const hoje = agora;
                const horaAtual =
                    String(agora.getHours()).padStart(2, "0") + ":" +
                    String(agora.getMinutes()).padStart(2, "0");
                const chave = agora.toDateString() + " " + horaAtual;

                if (chave === ultimoDisparo) return;

                const folga = ehDiaDeFolga(hoje);
                statusEl.textContent =
                    `🔔 Alarme ativo | Hoje: ${{folga ? "FOLGA 🟢" : "TRABALHO 🔴"}} | ` +
                    `Agora: ${{horaAtual}} | Programado: ${{HORARIO}}`;

                if (folga && horaAtual === HORARIO) {{
                    ultimoDisparo = chave;
                    statusEl.textContent = "🚨 ALARME DISPARANDO!";
                    tocarSirene(8);
                    setTimeout(() => falar("Tá na hora do estudo"), 1500);
                    setTimeout(() => falar("Tá na hora do estudo"), 4500);
                }}
            }}

            // Aguarda as vozes carregarem (Chrome carrega async)
            if ("speechSynthesis" in window) {{
                window.speechSynthesis.onvoiceschanged = () => {{}};
            }}

            setInterval(verificar, 20000);  // a cada 20s
            verificar();  // primeira verificação imediata
        }})();
        </script>
        """,
        height=40,
    )


def render_botao_teste_browser() -> None:
    """
    Renderiza um botão HTML que dispara o alarme imediatamente
    no navegador — útil para testar o som e a voz.
    """
    components.html(
        """
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
        document.getElementById("btn-teste").onclick = function() {
            const msg = document.getElementById("msg-teste");
            msg.textContent = "Tocando...";

            try {
                const ctx = new (window.AudioContext ||
                                 window.webkitAudioContext)();
                const agora = ctx.currentTime;
                const osc = ctx.createOscillator();
                const gain = ctx.createGain();
                osc.connect(gain);
                gain.connect(ctx.destination);
                osc.type = "square";
                gain.gain.setValueAtTime(0.15, agora);
                for (let i = 0; i < 16; i++) {
                    osc.frequency.setValueAtTime(
                        i % 2 === 0 ? 880 : 1200,
                        agora + i * 0.5
                    );
                }
                osc.start(agora);
                osc.stop(agora + 8);

                if ("speechSynthesis" in window) {
                    setTimeout(() => {
                        const utt = new SpeechSynthesisUtterance(
                            "Tá na hora do estudo"
                        );
                        utt.lang = "pt-BR";
                        utt.rate = 0.95;
                        window.speechSynthesis.speak(utt);
                    }, 1500);
                }

                msg.textContent = "✅ Testado! Verifique o áudio.";
                setTimeout(() => msg.textContent = "", 4000);
            } catch (e) {
                msg.textContent = "❌ Erro: " + e.message;
            }
        };
        </script>
        """,
        height=60,
    )
