#!/usr/bin/env python3
"""
Antigravity Voice Cloud - 24/7 Always-On Production Voice Engine
Runs anywhere in the cloud (Render, Koyeb, Hugging Face Spaces, Fly.io, VPS) 100% Free.
Supports:
1. High-Fidelity Web-Phone PWA with:
   - Incremental Chunked Audio Streaming via WebSockets (/ws/call)
   - Dual FFT Waveform Analyser (mic + neural AI voice syllables)
   - Web Audio Studio Vocal BiquadFilter EQ & Dynamics Compressor
   - Hands-Free Continuous VAD vs Push-to-Talk (Spacebar & Touch hold)
   - Haptic Feedback & Procedural Web Audio Chimes
   - Direct Telegram Sync (@orbitgrav_bot)
   - PWA Web App Manifest (/manifest.json) for 1-click home screen install
2. Cloud Intelligence:
   - Direct Google Gemini API (Gemini 2.0 Flash / 1.5 Flash) with zero local dependencies
   - Instant Local Voice Commands (<0.2s for time, diagnostics, voice notes)
3. Bidirectional Speech Synthesis with edge-tts neural voices & fallback.
"""

import os
import sys
import json
import urllib.request
import urllib.parse
import urllib.error
import html
import asyncio
import base64
import time
import re
from datetime import datetime
import edge_tts
from aiohttp import web

PORT = int(os.getenv("PORT", 8655))
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8965653104:AAFfye3yaVWJGJTHjUVUs1NFj_OJz7C7Xig")
TELEGRAM_USER_ID = os.getenv("TELEGRAM_USER_ID", "8069526508")
VOICE_PREFERENCES = ["es-US-AlonsoNeural", "es-MX-DaliaNeural", "es-ES-AlvaroNeural"]

CALL_MEMORY = []
AUDIO_CACHE = {}
SAVED_VOICE_NOTES = []

def split_sentences(text: str) -> list:
    """Splits text into logical sentence chunks for incremental streaming synthesis."""
    raw = re.split(r'(?<=[.!?])\s+', text)
    cleaned = [s.strip() for s in raw if s.strip()]
    if not cleaned:
        return [text]
    merged = []
    curr = ""
    for s in cleaned:
        if curr:
            curr += " " + s
        else:
            curr = s
        if len(curr) >= 35 or s == cleaned[-1]:
            merged.append(curr)
            curr = ""
    if curr:
        if merged:
            merged[-1] += " " + curr
        else:
            merged.append(curr)
    return merged

def handle_fast_command(user_text: str) -> tuple:
    """Intercepts instantaneous voice commands for zero-latency (<0.2s) execution."""
    txt = user_text.lower().strip()
    
    # 1. Time query
    if any(q in txt for q in ["qué hora es", "que hora es", "dime la hora", "hora actual"]):
        now_str = datetime.now().strftime("%I:%M %p")
        return True, f"Son las {now_str}, Daniel. Servidor en la nube activo."
    
    # 2. Cloud server diagnostics
    if any(q in txt for q in ["cómo está el servidor", "recursos del sistema", "estado del sistema", "dónde estás corriendo"]):
        return True, "Antigravity Cloud en línea. Servidor web activo 24/7 en la nube con soporte WebSocket dúplex."
    
    # 3. Voice note saving
    m_note = re.search(r'(?:anota|guarda la nota|recuérdame|recuerdame)\s+(.+)', txt, re.IGNORECASE)
    if m_note:
        note = m_note.group(1).strip()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        SAVED_VOICE_NOTES.append(f"[{timestamp}] {note}")
        return True, f"Nota registrada en la nube: {note}."
        
    # 4. Read voice notes
    if any(q in txt for q in ["lee mis notas", "cuáles son mis notas", "qué notas tengo"]):
        if SAVED_VOICE_NOTES:
            recent = SAVED_VOICE_NOTES[-3:]
            summary = " ".join([l.split("] ", 1)[-1] for l in recent])
            return True, f"Tus últimas notas son: {summary}"
        return True, "No tienes notas guardadas en este momento."
        
    # 5. Clear memory
    if any(q in txt for q in ["limpia la memoria", "borra la conversación", "resetea la memoria"]):
        global CALL_MEMORY
        CALL_MEMORY.clear()
        return True, "Memoria de conversación reseteada. Empecemos de cero."

    return False, ""

def query_gemini_api(prompt: str, persona: str = "analitico") -> str:
    """Queries Google Gemini API directly using free tier API key."""
    if not GEMINI_API_KEY:
        # Fallback intelligent response when API key is not yet set in environment
        return (
            "Hola Daniel, estoy operando en la nube 24/7. "
            "Para activar razonamiento avanzado completo sin límites, recuerda configurar tu GEMINI_API_KEY gratuita en el panel de la nube. "
            "Todo el canal de voz y notas está 100% activo."
        )

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"
    
    persona_prompts = {
        "ejecutivo": "Modo Ejecutivo: Sé ultra-directo, conciso y veloz. Responde en 1 sola oración contundente (máximo 25 palabras).",
        "analitico": "Modo Analítico: Sé técnico, analítico y riguroso. Razona con lógica y precisión en 2 a 3 oraciones orales.",
        "estrategico": "Modo Estratégico: Enfócate en el panorama global, impacto de largo plazo y trade-offs en 2 a 3 oraciones.",
        "creativo": "Modo Creativo: Sé inspirador, propositivo y elocuente en 2 a 3 oraciones."
    }
    persona_rule = persona_prompts.get(persona, persona_prompts["analitico"])

    global CALL_MEMORY
    CALL_MEMORY.append(f"Daniel: {prompt}")
    recent_history = "\n".join(CALL_MEMORY[-8:])

    system_instruction = (
        f"Eres Antigravity, la IA avanzada y asistente personal de Daniel Sosa. "
        f"Estás hablando de viva voz con él por una llamada telefónica/Web-Phone directa desde la nube 24/7. "
        f"{persona_rule} "
        "Sé fluido, carismático, inteligente y natural. "
        "PROHIBIDO usar asteriscos, markdown, listas con guiones o números, ya que tu texto será sintetizado por voz hablada oralmente.\n\n"
        f"Historial reciente de la llamada:\n{recent_history}\n\n"
        "Tu respuesta hablada:"
    )

    payload = {
        "contents": [
            {
                "parts": [{"text": system_instruction}]
            }
        ],
        "generationConfig": {
            "maxOutputTokens": 180,
            "temperature": 0.7
        }
    }

    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=12) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            candidates = data.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                if parts:
                    text = parts[0].get("text", "").strip()
                    clean = text.replace("\n", " ").replace("*", "").replace("#", "").strip()
                    CALL_MEMORY.append(f"Antigravity: {clean}")
                    return clean
    except Exception as e:
        print(f"[Gemini API Error] {e}", file=sys.stderr)

    return "Te escucho Daniel, sigo en la línea contigo desde la nube."

def run_antigravity_cloud(prompt: str, persona: str = "analitico") -> str:
    """Executes reasoning via fast commands or Gemini API."""
    global CALL_MEMORY
    is_fast, fast_reply = handle_fast_command(prompt)
    if is_fast:
        CALL_MEMORY.append(f"Daniel: {prompt}")
        CALL_MEMORY.append(f"Antigravity: {fast_reply}")
        return fast_reply

    return query_gemini_api(prompt, persona)

async def synthesize_speech_base64(text: str, preferred_voice: str = None, rate: str = "+0%") -> str:
    """Synthesizes text into MP3 with automatic voice fallback, rate adjustment, and caching."""
    cache_key = f"{text}|{preferred_voice}|{rate}"
    if cache_key in AUDIO_CACHE:
        return AUDIO_CACHE[cache_key]

    voices = [preferred_voice] + [v for v in VOICE_PREFERENCES if v != preferred_voice] if preferred_voice else VOICE_PREFERENCES
    for voice in voices:
        try:
            comm = edge_tts.Communicate(text, voice, rate=rate)
            chunks = []
            async for chunk in comm.stream():
                if chunk["type"] == "audio":
                    chunks.append(chunk["data"])
            audio_bytes = b"".join(chunks)
            if audio_bytes:
                b64 = base64.b64encode(audio_bytes).decode("utf-8")
                if len(AUDIO_CACHE) < 150:
                    AUDIO_CACHE[cache_key] = b64
                return b64
        except Exception as e:
            print(f"[TTS Fallback: {voice}] {e}", file=sys.stderr, flush=True)
            continue
    return ""

# ==================== WEBSOCKET & REST API ====================

async def handle_ws_call(request):
    """Full-Duplex Real-Time WebSocket for cloud voice streaming."""
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    print("[WebSocket Voice] Cliente conectado en la nube.", flush=True)

    try:
        async for msg in ws:
            if msg.type == web.WSMsgType.TEXT:
                data = json.loads(msg.data)
                action = data.get("action")
                if action == "ping":
                    await ws.send_json({"type": "pong"})
                elif action == "chat":
                    user_text = data.get("text", "").strip()
                    voice = data.get("voice", "es-US-AlonsoNeural")
                    persona = data.get("persona", "analitico")
                    rate = data.get("rate", "+0%")

                    if not user_text:
                        await ws.send_json({"type": "response", "reply": "¿Sí, Daniel? Te escucho.", "audio": "", "latency": 0.0})
                        continue

                    # Instant command check (<0.2s)
                    is_fast, fast_reply = handle_fast_command(user_text)
                    if is_fast:
                        t0 = time.time()
                        audio_b64 = await synthesize_speech_base64(fast_reply, voice, rate)
                        latency = round(time.time() - t0, 2)
                        await ws.send_json({
                            "type": "response",
                            "reply": fast_reply,
                            "audio": audio_b64,
                            "latency": latency
                        })
                        continue

                    await ws.send_json({"type": "thinking"})
                    t0 = time.time()
                    reply = await asyncio.to_thread(run_antigravity_cloud, user_text, persona)

                    sentences = split_sentences(reply)
                    total_chunks = len(sentences)

                    # Synthesize chunk 0 first and stream immediately
                    chunk0_audio = await synthesize_speech_base64(sentences[0], voice, rate)
                    first_audio_lat = round(time.time() - t0, 2)

                    await ws.send_json({
                        "type": "audio_chunk",
                        "index": 0,
                        "total": total_chunks,
                        "text": sentences[0],
                        "audio": chunk0_audio,
                        "full_reply": reply,
                        "latency": first_audio_lat
                    })

                    # Stream remaining chunks
                    for idx in range(1, total_chunks):
                        chunk_audio = await synthesize_speech_base64(sentences[idx], voice, rate)
                        await ws.send_json({
                            "type": "audio_chunk",
                            "index": idx,
                            "total": total_chunks,
                            "text": sentences[idx],
                            "audio": chunk_audio,
                            "full_reply": "",
                            "latency": round(time.time() - t0, 2)
                        })

                elif action == "clear":
                    global CALL_MEMORY
                    CALL_MEMORY.clear()
                    await ws.send_json({"type": "cleared"})
            elif msg.type == web.WSMsgType.ERROR:
                print(f"[WebSocket Error] {ws.exception()}", flush=True)
    finally:
        print("[WebSocket Voice] Cliente desconectado.", flush=True)
    return ws

async def handle_api_chat(request):
    """HTTP REST fallback for the Web-Phone call interface."""
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON"}, status=400)

    user_text = data.get("text", "").strip()
    voice = data.get("voice", "es-US-AlonsoNeural")
    persona = data.get("persona", "analitico")
    rate = data.get("rate", "+0%")

    if not user_text:
        return web.json_response({"reply": "¿Sí, Daniel? Te escucho.", "audio": "", "latency": 0.0})

    t0 = time.time()
    reply = await asyncio.to_thread(run_antigravity_cloud, user_text, persona)
    audio_b64 = await synthesize_speech_base64(reply, voice, rate)
    latency = round(time.time() - t0, 2)
    return web.json_response({"reply": reply, "audio": audio_b64, "latency": latency})

async def handle_clear_memory(request):
    global CALL_MEMORY
    CALL_MEMORY.clear()
    return web.json_response({"status": "cleared", "memory_count": 0})

async def handle_sync_telegram(request):
    """Sends current call transcript summary directly to Daniel's Telegram bot."""
    try:
        data = await request.json()
        transcript_text = data.get("transcript", "")
    except Exception:
        transcript_text = "\n".join(CALL_MEMORY)

    if not transcript_text:
        return web.json_response({"error": "No hay diálogo que sincronizar"}, status=400)

    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_USER_ID:
        return web.json_response({"error": "Telegram no configurado"}, status=500)

    summary_msg = (
        f"☁️ *Resumen de Llamada Antigravity Cloud 24/7*\n"
        f"📅 _{datetime.now().strftime('%Y-%m-%d %H:%M')}_\n\n"
        f"{transcript_text[:3500]}"
    )
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = json.dumps({"chat_id": TELEGRAM_USER_ID, "text": summary_msg, "parse_mode": "Markdown"}).encode()
    
    try:
        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            return web.json_response({"status": "sent", "code": resp.status})
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)

async def handle_manifest(request):
    """PWA Web App Manifest for native installation on iOS/Android."""
    manifest = {
        "name": "Antigravity Cloud 24/7",
        "short_name": "Antigravity",
        "description": "Llamada de voz y razonamiento continuo con Antigravity AI en la nube 24/7",
        "start_url": "/call",
        "display": "standalone",
        "background_color": "#060a10",
        "theme_color": "#060a10",
        "icons": [
            {
                "src": "data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><circle cx='50' cy='50' r='45' fill='%2300d2ff'/><text x='50' y='65' font-size='45' text-anchor='middle'>☁️</text></svg>",
                "sizes": "192x192 512x512",
                "type": "image/svg+xml",
                "purpose": "any maskable"
            }
        ]
    }
    return web.json_response(manifest)

async def handle_call_ui(request):
    """Serves Ultra 3.0 Web-Phone PWA with dual FFT waveform, chunked streaming, and cloud status."""
    html_content = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="Antigravity Cloud">
<meta name="theme-color" content="#060a10">
<link rel="manifest" href="/manifest.json">
<title>Antigravity Cloud 24/7 - Voz en Vivo</title>
<style>
  :root {
    --bg-gradient: radial-gradient(circle at 50% 12%, #0e223d 0%, #05090f 100%);
    --accent-glow: rgba(0, 210, 255, 0.4);
    --accent-color: #00d2ff;
    --ring-glow: rgba(0, 242, 254, 0.9);
    --wave-stroke-1: rgba(0, 242, 254, 0.9);
    --wave-stroke-2: rgba(0, 114, 255, 0.65);
    --wave-stroke-3: rgba(138, 43, 226, 0.45);
  }
  [data-theme="cyberpunk"] {
    --bg-gradient: radial-gradient(circle at 50% 12%, #260c38 0%, #07040d 100%);
    --accent-glow: rgba(255, 0, 128, 0.45);
    --accent-color: #ff007f;
    --ring-glow: rgba(255, 0, 128, 0.9);
    --wave-stroke-1: rgba(255, 0, 128, 0.9);
    --wave-stroke-2: rgba(0, 242, 254, 0.7);
    --wave-stroke-3: rgba(180, 0, 255, 0.5);
  }
  [data-theme="matrix"] {
    --bg-gradient: radial-gradient(circle at 50% 12%, #082914 0%, #030d06 100%);
    --accent-glow: rgba(46, 213, 115, 0.45);
    --accent-color: #2ed573;
    --ring-glow: rgba(46, 213, 115, 0.9);
    --wave-stroke-1: rgba(46, 213, 115, 0.9);
    --wave-stroke-2: rgba(0, 255, 136, 0.6);
    --wave-stroke-3: rgba(0, 128, 64, 0.4);
  }
  [data-theme="obsidian"] {
    --bg-gradient: radial-gradient(circle at 50% 12%, #1a1a1a 0%, #000000 100%);
    --accent-glow: rgba(255, 255, 255, 0.3);
    --accent-color: #ffffff;
    --ring-glow: rgba(255, 255, 255, 0.8);
    --wave-stroke-1: rgba(255, 255, 255, 0.85);
    --wave-stroke-2: rgba(180, 180, 180, 0.5);
    --wave-stroke-3: rgba(100, 100, 100, 0.3);
  }

  * { box-sizing: border-box; margin: 0; padding: 0; user-select: none; }
  body {
    background: var(--bg-gradient);
    color: #fff;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
    height: 100vh;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    align-items: center;
    padding: 16px 14px 12px 14px;
    overflow: hidden;
    transition: background 0.4s ease;
  }
  .top-bar {
    width: 100%;
    max-width: 480px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    position: relative;
    z-index: 10;
  }
  .status-pill {
    background: rgba(0, 210, 255, 0.1);
    border: 1px solid var(--accent-glow);
    border-radius: 20px;
    padding: 4px 12px;
    font-size: 11.5px;
    color: var(--accent-color);
    font-weight: 600;
    letter-spacing: 0.3px;
    display: flex;
    align-items: center;
    gap: 6px;
  }
  .status-dot {
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: #2ed573;
    box-shadow: 0 0 8px #2ed573;
  }
  .top-actions {
    display: flex;
    gap: 8px;
    align-items: center;
  }
  .btn-header {
    background: rgba(255, 255, 255, 0.08);
    border: 1px solid rgba(255, 255, 255, 0.15);
    border-radius: 16px;
    color: #cfd8dc;
    font-size: 12px;
    padding: 5px 12px;
    cursor: pointer;
    display: flex;
    align-items: center;
    gap: 4px;
    transition: all 0.2s;
  }
  .btn-header:active { transform: scale(0.95); }
  .btn-rec {
    color: #ff4757;
    border-color: rgba(255, 71, 87, 0.35);
  }
  .btn-rec.recording {
    background: rgba(255, 71, 87, 0.25);
    box-shadow: 0 0 10px rgba(255, 71, 87, 0.5);
    animation: pulseRec 1.4s infinite;
  }
  @keyframes pulseRec {
    0% { transform: scale(1); }
    50% { transform: scale(1.05); }
    100% { transform: scale(1); }
  }

  /* Mode Switch Pill */
  .mode-switch-box {
    display: flex;
    background: rgba(255, 255, 255, 0.06);
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 20px;
    padding: 2px;
    margin: 4px 0 2px 0;
  }
  .mode-switch-btn {
    border: none;
    background: none;
    color: #8da4be;
    font-size: 11px;
    padding: 3px 10px;
    border-radius: 16px;
    cursor: pointer;
    transition: all 0.2s;
  }
  .mode-switch-btn.active {
    background: var(--accent-color);
    color: #050c17;
    font-weight: 700;
  }

  /* Settings Modal */
  .settings-modal {
    position: fixed;
    top: 0; left: 0; right: 0; bottom: 0;
    background: rgba(0, 0, 0, 0.78);
    backdrop-filter: blur(10px);
    z-index: 100;
    display: none;
    align-items: center;
    justify-content: center;
    padding: 20px;
  }
  .settings-modal.open { display: flex; }
  .settings-card {
    background: #09131f;
    border: 1px solid var(--accent-glow);
    border-radius: 24px;
    width: 100%;
    max-width: 400px;
    padding: 22px;
    display: flex;
    flex-direction: column;
    gap: 12px;
    box-shadow: 0 20px 60px rgba(0, 0, 0, 0.7);
  }
  .settings-title {
    font-size: 16.5px;
    font-weight: 700;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
  .settings-row {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }
  .settings-label {
    font-size: 11.5px;
    color: #8da4be;
    font-weight: 500;
  }
  .settings-select {
    background: rgba(255, 255, 255, 0.08);
    border: 1px solid rgba(255, 255, 255, 0.15);
    border-radius: 12px;
    color: #fff;
    font-size: 13px;
    padding: 8px 12px;
    outline: none;
  }
  .settings-select option { background: #09131f; }

  /* Caller Avatar & HUD */
  .caller-info {
    display: flex;
    flex-direction: column;
    align-items: center;
    text-align: center;
    cursor: pointer;
    position: relative;
    margin-top: 1px;
  }
  .hud-orbit {
    position: absolute;
    width: 124px;
    height: 124px;
    top: -6px;
    border-radius: 50%;
    border: 1px dashed var(--accent-glow);
    animation: rotateOrbit 12s linear infinite;
    pointer-events: none;
  }
  @keyframes rotateOrbit {
    from { transform: rotate(0deg); }
    to { transform: rotate(360deg); }
  }
  .avatar-ring {
    width: 112px;
    height: 112px;
    border-radius: 50%;
    background: linear-gradient(135deg, var(--accent-color) 0%, #00f2fe 50%, #4facfe 100%);
    padding: 3.5px;
    margin-bottom: 5px;
    box-shadow: 0 0 26px var(--accent-glow);
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all 0.3s ease;
  }
  .avatar-ring.active {
    box-shadow: 0 0 65px var(--ring-glow);
    transform: scale(1.04);
    animation: pulseRing 1.6s infinite;
  }
  @keyframes pulseRing {
    0% { box-shadow: 0 0 25px var(--accent-glow); }
    50% { box-shadow: 0 0 70px var(--ring-glow); }
    100% { box-shadow: 0 0 25px var(--accent-glow); }
  }
  .avatar {
    width: 100%;
    height: 100%;
    border-radius: 50%;
    background: #09131f;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 44px;
  }
  .caller-name {
    font-size: 22px;
    font-weight: 700;
    letter-spacing: -0.5px;
  }
  .call-status {
    font-size: 13px;
    color: var(--accent-color);
    font-weight: 500;
    min-height: 18px;
  }
  .call-timer {
    font-size: 11.5px;
    color: #7f97b0;
    font-family: monospace;
  }

  /* Liquid Spline Canvas */
  .canvas-box {
    width: 100%;
    max-width: 380px;
    height: 52px;
    display: flex;
    justify-content: center;
    align-items: center;
    margin: 1px 0;
  }
  canvas {
    width: 100%;
    height: 100%;
  }

  /* Live Interim Subtitle */
  .live-subtitle-box {
    width: 100%;
    max-width: 440px;
    min-height: 20px;
    text-align: center;
    font-size: 12.5px;
    color: var(--accent-color);
    padding: 0 10px;
    font-style: italic;
    opacity: 0.95;
    word-break: break-word;
  }
  .barge-hint {
    font-size: 10.5px;
    color: rgba(255, 255, 255, 0.45);
    display: none;
    margin-top: 1px;
  }

  /* Transcript Container */
  .transcript-container {
    width: 100%;
    max-width: 480px;
    flex: 1;
    overflow-y: auto;
    margin: 4px 0;
    padding: 8px 12px;
    background: rgba(8, 16, 26, 0.72);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 16px;
    display: flex;
    flex-direction: column;
    gap: 7px;
    scroll-behavior: smooth;
  }
  .msg-bubble {
    padding: 7px 11px;
    border-radius: 13px;
    font-size: 12.8px;
    line-height: 1.42;
    max-width: 86%;
    word-break: break-word;
    user-select: text;
  }
  .msg-user {
    align-self: flex-end;
    background: linear-gradient(135deg, #0066eb, var(--accent-color));
    color: #fff;
    border-bottom-right-radius: 3px;
  }
  .msg-ai {
    align-self: flex-start;
    background: rgba(255, 255, 255, 0.06);
    color: #e2e8f0;
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-bottom-left-radius: 3px;
  }

  /* Quick Action Pills */
  .quick-pills {
    width: 100%;
    max-width: 480px;
    display: flex;
    gap: 6px;
    overflow-x: auto;
    padding-bottom: 3px;
    margin-bottom: 2px;
  }
  .quick-pill {
    background: rgba(255, 255, 255, 0.06);
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 14px;
    padding: 4px 10px;
    font-size: 11.5px;
    color: #b0c4de;
    white-space: nowrap;
    cursor: pointer;
    transition: all 0.15s;
  }
  .quick-pill:hover { background: rgba(0, 210, 255, 0.15); color: var(--accent-color); }

  /* Text Drawer */
  .text-drawer {
    width: 100%;
    max-width: 480px;
    display: none;
    gap: 8px;
    margin-bottom: 5px;
  }
  .text-drawer.open { display: flex; }
  .text-drawer input {
    flex: 1;
    background: rgba(255, 255, 255, 0.08);
    border: 1px solid var(--accent-glow);
    border-radius: 20px;
    padding: 8px 14px;
    color: #fff;
    font-size: 13.5px;
    outline: none;
    user-select: text;
  }
  .text-drawer button {
    background: var(--accent-color);
    border: none;
    border-radius: 20px;
    padding: 0 14px;
    color: #0b1523;
    font-weight: 700;
    cursor: pointer;
  }

  /* Controls */
  .controls {
    display: flex;
    gap: 16px;
    align-items: center;
    justify-content: center;
  }
  .btn-action {
    width: 46px;
    height: 46px;
    border-radius: 50%;
    border: none;
    background: rgba(255, 255, 255, 0.09);
    color: #fff;
    font-size: 18px;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    transition: all 0.2s;
  }
  .btn-action:active { transform: scale(0.92); }
  .btn-call {
    width: 68px;
    height: 68px;
    border-radius: 50%;
    border: none;
    font-size: 28px;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    box-shadow: 0 10px 25px rgba(0, 0, 0, 0.4);
    transition: all 0.2s;
  }
  .btn-start { background: #2ed573; color: white; }
  .btn-start:active { transform: scale(0.92); }
  .btn-end { background: #ff4757; color: white; }
  .btn-end:active { transform: scale(0.92); }
  
  .ptt-hint {
    font-size: 10.5px;
    color: #7f97b0;
    margin-top: 2px;
    text-align: center;
  }
  .footer-links {
    display: flex;
    gap: 14px;
    margin-top: 4px;
  }
  .footer-btn {
    background: none;
    border: none;
    color: #5d758f;
    font-size: 11px;
    cursor: pointer;
    text-decoration: underline;
  }
  .footer-btn:hover { color: var(--accent-color); }
</style>
</head>
<body>
  <div class="top-bar">
    <div class="status-pill">
      <div class="status-dot" id="netDot"></div>
      <span id="pillText">☁️ Cloud 24/7 HD</span>
    </div>
    <div class="top-actions">
      <button class="btn-header btn-rec" id="recBtn" onclick="toggleRecording()" title="Grabar llamada">🔴 Rec</button>
      <button class="btn-header" onclick="toggleSettingsModal()">⚙️ Ajustes</button>
    </div>
  </div>

  <div class="mode-switch-box">
    <button class="mode-switch-btn active" id="btnModeHandsfree" onclick="setMode('handsfree')">🟢 Manos Libres</button>
    <button class="mode-switch-btn" id="btnModePTT" onclick="setMode('ptt')">🎙️ Push-to-Talk</button>
  </div>

  <div class="caller-info" onclick="interruptAI()" title="Toca para interrumpir">
    <div class="hud-orbit"></div>
    <div class="avatar-ring" id="ring">
      <div class="avatar" id="avatarEmoji">☁️</div>
    </div>
    <div class="caller-name">Antigravity Cloud</div>
    <div class="call-status" id="status">En línea 24/7</div>
    <div class="call-timer" id="timer">00:00</div>
  </div>

  <div class="canvas-box">
    <canvas id="waveCanvas" width="400" height="52"></canvas>
  </div>
  <div class="live-subtitle-box" id="liveSubtitle"></div>
  <div class="barge-hint" id="bargeHint">💡 Habla, pulsa espacio o toca el avatar para interrumpir</div>

  <div class="transcript-container" id="transcript">
    <div class="msg-bubble msg-ai">Servidor en la nube activo 24/7. Toca el botón verde 📞 para hablar conmigo aunque tu laptop esté apagada.</div>
  </div>

  <div class="quick-pills">
    <div class="quick-pill" onclick="sendQuickPrompt('¿Qué hora es?')">⏱️ Hora exacta</div>
    <div class="quick-pill" onclick="sendQuickPrompt('¿Cómo está el servidor en la nube?')">☁️ Estado Cloud</div>
    <div class="quick-pill" onclick="sendQuickPrompt('Anota que estamos en la nube 24/7')">📝 Tomar nota</div>
    <div class="quick-pill" onclick="sendQuickPrompt('Dame un resumen ejecutivo del proyecto')">💡 Resumen ejecutivo</div>
  </div>

  <div class="text-drawer" id="textDrawer">
    <input type="text" id="manualText" placeholder="Escribe un mensaje..." onkeydown="if(event.key==='Enter') sendManualText()">
    <button onclick="sendManualText()">Enviar</button>
  </div>

  <div class="controls">
    <button class="btn-action" id="toggleDrawerBtn" onclick="toggleDrawer()" title="Escribir mensaje">💬</button>
    <button class="btn-call btn-start" id="callBtn" onclick="toggleCall()">📞</button>
    <button class="btn-action" id="muteBtn" onclick="toggleMute()" title="Silenciar micrófono">🎤</button>
  </div>
  <div class="ptt-hint" id="pttHint">Espacio: Hablar • Esc: Interrumpir</div>

  <div class="footer-links">
    <button class="footer-btn" onclick="syncToTelegram()">✈️ Enviar a Telegram</button>
    <button class="footer-btn" onclick="copyTranscript()">📋 Copiar diálogo</button>
    <button class="footer-btn" onclick="clearMemory()">🧹 Limpiar memoria</button>
  </div>

  <!-- Settings Modal -->
  <div class="settings-modal" id="settingsModal" onclick="if(event.target===this) toggleSettingsModal()">
    <div class="settings-card">
      <div class="settings-title">
        <span>⚙️ Configuración Cloud</span>
        <span style="cursor:pointer;" onclick="toggleSettingsModal()">✕</span>
      </div>
      <div class="settings-row">
        <label class="settings-label">Tema Visual</label>
        <select class="settings-select" id="themeSelect" onchange="changeTheme(this.value)">
          <option value="default" selected>🌌 Deep Space (Cian / Azul)</option>
          <option value="cyberpunk">⚡ Cyberpunk Neon (Púrpura / Magenta)</option>
          <option value="matrix">🌿 Matrix Emerald (Verde Neón)</option>
          <option value="obsidian">🪐 Obsidian Minimal (Monocromo)</option>
        </select>
      </div>
      <div class="settings-row">
        <label class="settings-label">Voz Neural</label>
        <select class="settings-select" id="voiceSelect" onchange="persistSettings()">
          <option value="es-US-AlonsoNeural" selected>Alonso (Masculino - Neutro)</option>
          <option value="es-MX-DaliaNeural">Dalia (Femenina - Expresiva)</option>
          <option value="es-ES-AlvaroNeural">Álvaro (Castellano)</option>
        </select>
      </div>
      <div class="settings-row">
        <label class="settings-label">Personalidad de Razonamiento</label>
        <select class="settings-select" id="personaSelect" onchange="persistSettings()">
          <option value="analitico" selected>🧠 Analítico (Técnico & Riguroso)</option>
          <option value="ejecutivo">⚡ Ejecutivo (Ultra-Rápido & Conciso)</option>
          <option value="estrategico">💡 Estratégico (Visión Global & Trade-offs)</option>
          <option value="creativo">🎨 Creativo (Propositivo & Expresivo)</option>
        </select>
      </div>
      <div class="settings-row">
        <label class="settings-label">Velocidad de Habla</label>
        <select class="settings-select" id="rateSelect" onchange="persistSettings()">
          <option value="+0%" selected>Normal (1.0x)</option>
          <option value="+15%">Ágil (1.15x)</option>
          <option value="+28%">Ultra-Rápida (1.3x)</option>
        </select>
      </div>
      <button onclick="toggleSettingsModal()" style="background:var(--accent-color);border:none;border-radius:12px;padding:9px;color:#0b1523;font-weight:700;cursor:pointer;margin-top:4px;">Guardar y Cerrar</button>
    </div>
  </div>

<script>
let inCall = false;
let isMuted = false;
let isSpeaking = false;
let isThinking = false;
let isRecording = false;
let recognition = null;
let currentMode = 'handsfree';
let isPTTHeld = false;

// Chunked Streaming Audio Queue
let audioPlayer = new Audio();
let audioQueue = [];
let isPlayingChunk = false;
let callTimerInterval = null;
let callStartTime = null;

// WebSocket Full-Duplex
let ws = null;
let wsHeartbeat = null;

// Web Audio API & Dual FFT Graph
let audioCtx = null;
let analyser = null;
let playerSource = null;
let micSource = null;
let micStream = null;
let thinkingOsc = null;
let thinkingGain = null;
let liveFFTData = null;
let wavePhase = 0;

// Call Recording (MediaRecorder)
let mediaRecorder = null;
let recordedChunks = [];

const statusEl = document.getElementById('status');
const timerEl = document.getElementById('timer');
const transcriptEl = document.getElementById('transcript');
const callBtn = document.getElementById('callBtn');
const muteBtn = document.getElementById('muteBtn');
const recBtn = document.getElementById('recBtn');
const ringEl = document.getElementById('ring');
const bargeHintEl = document.getElementById('bargeHint');
const pillTextEl = document.getElementById('pillText');
const netDotEl = document.getElementById('netDot');
const liveSubtitleEl = document.getElementById('liveSubtitle');
const textDrawer = document.getElementById('textDrawer');
const manualInput = document.getElementById('manualText');
const voiceSelect = document.getElementById('voiceSelect');
const personaSelect = document.getElementById('personaSelect');
const rateSelect = document.getElementById('rateSelect');
const themeSelect = document.getElementById('themeSelect');
const settingsModal = document.getElementById('settingsModal');
const avatarEmoji = document.getElementById('avatarEmoji');
const btnModeHandsfree = document.getElementById('btnModeHandsfree');
const btnModePTT = document.getElementById('btnModePTT');
const pttHint = document.getElementById('pttHint');
const canvas = document.getElementById('waveCanvas');
const ctx = canvas.getContext('2d');

function setMode(mode) {
  currentMode = mode;
  localStorage.setItem('agy_cloud_ptt_mode', mode);
  if (mode === 'handsfree') {
    btnModeHandsfree.classList.add('active');
    btnModePTT.classList.remove('active');
    pttHint.textContent = "Modo Continuo: Habla naturalmente con detección de silencio";
    if (inCall && !isSpeaking && !isMuted) listenAgain();
  } else {
    btnModePTT.classList.add('active');
    btnModeHandsfree.classList.remove('active');
    pttHint.textContent = "Push-to-Talk: Mantén Espacio o el botón verde para hablar";
    if (recognition) { try { recognition.abort(); } catch(e){} }
  }
}

function loadSettings() {
  const theme = localStorage.getItem('agy_cloud_theme') || 'default';
  themeSelect.value = theme;
  changeTheme(theme, false);

  if (localStorage.getItem('agy_cloud_voice')) voiceSelect.value = localStorage.getItem('agy_cloud_voice');
  if (localStorage.getItem('agy_cloud_persona')) personaSelect.value = localStorage.getItem('agy_cloud_persona');
  if (localStorage.getItem('agy_cloud_rate')) rateSelect.value = localStorage.getItem('agy_cloud_rate');
  const savedMode = localStorage.getItem('agy_cloud_ptt_mode') || 'handsfree';
  setMode(savedMode);
}

function persistSettings() {
  localStorage.setItem('agy_cloud_theme', themeSelect.value);
  localStorage.setItem('agy_cloud_voice', voiceSelect.value);
  localStorage.setItem('agy_cloud_persona', personaSelect.value);
  localStorage.setItem('agy_cloud_rate', rateSelect.value);
}

function changeTheme(theme, save=true) {
  if (theme === 'default') document.body.removeAttribute('data-theme');
  else document.body.setAttribute('data-theme', theme);
  if (save) persistSettings();
}
loadSettings();

function triggerHaptic(duration=30) {
  if (navigator.vibrate) {
    try { navigator.vibrate(duration); } catch(e){}
  }
}

// ==================== WEBSOCKET ENGINE ====================

function connectWebSocket() {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const wsUrl = `${protocol}//${window.location.host}/ws/call`;
  try {
    ws = new WebSocket(wsUrl);
    ws.onopen = () => {
      netDotEl.style.background = '#2ed573';
      netDotEl.style.boxShadow = '0 0 8px #2ed573';
      pillTextEl.textContent = '☁️ Cloud 24/7 HD';
      if (wsHeartbeat) clearInterval(wsHeartbeat);
      wsHeartbeat = setInterval(() => {
        if (ws && ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify({action: "ping"}));
      }, 15000);
    };
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'thinking') {
        setStatus("Razonando...", false);
        avatarEmoji.textContent = '🧠';
        startThinkingAmbience();
      } else if (data.type === 'audio_chunk') {
        stopThinkingAmbience();
        isThinking = false;
        pillTextEl.textContent = `⚡ ${data.latency}s • Chunk ${data.index+1}/${data.total}`;
        if (data.full_reply) {
          appendBubble('ai', data.full_reply);
        }
        enqueueAudioChunk(data.audio, data.text);
      } else if (data.type === 'response') {
        stopThinkingAmbience();
        isThinking = false;
        pillTextEl.textContent = `⚡ ${data.latency}s • Cloud Voice`;
        appendBubble('ai', data.reply);
        if (data.audio) enqueueAudioChunk(data.audio, data.reply);
        else {
          avatarEmoji.textContent = '☁️';
          setTimeout(listenAgain, 600);
        }
      } else if (data.type === 'cleared') {
        transcriptEl.innerHTML = '<div class="msg-bubble msg-ai">Memoria reseteada. Empezamos una nueva conversación fresca.</div>';
      }
    };
    ws.onerror = () => {
      netDotEl.style.background = '#ffa502';
      pillTextEl.textContent = 'HTTP Fallback';
    };
    ws.onclose = () => {
      netDotEl.style.background = '#ff4757';
      setTimeout(connectWebSocket, 4000);
    };
  } catch(e) {
    console.log("WS init error, using HTTP:", e);
  }
}
connectWebSocket();

// ==================== AUDIO QUEUE PLAYBACK ====================

function enqueueAudioChunk(b64, text) {
  if (!b64) return;
  audioQueue.push({ b64, text });
  if (!isPlayingChunk && !isSpeaking) {
    playNextAudioChunk();
  }
}

function playNextAudioChunk() {
  if (audioQueue.length === 0) {
    isPlayingChunk = false;
    isSpeaking = false;
    avatarEmoji.textContent = '☁️';
    bargeHintEl.style.display = 'none';
    liveSubtitleEl.textContent = '';
    setStatus("Te escucho...", true);
    if (currentMode === 'handsfree') listenAgain();
    return;
  }

  isPlayingChunk = true;
  isSpeaking = true;
  avatarEmoji.textContent = '🗣️';
  setStatus("Hablando...", true);
  bargeHintEl.style.display = 'block';

  const item = audioQueue.shift();
  if (item.text) {
    liveSubtitleEl.textContent = `Antigravity: "${item.text}"`;
  }

  audioPlayer.src = "data:audio/mp3;base64," + item.b64;
  audioPlayer.play().catch(e => {
    playNextAudioChunk();
  });

  audioPlayer.onended = () => {
    playNextAudioChunk();
  };
}

// ==================== DUAL FFT AUDIO VISUALIZER ====================

function setupWebAudioGraph() {
  try {
    if (!audioCtx) audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    
    if (!analyser) {
      analyser = audioCtx.createAnalyser();
      analyser.fftSize = 128;
      analyser.smoothingTimeConstant = 0.75;
      liveFFTData = new Uint8Array(analyser.frequencyBinCount);
    }

    if (!playerSource && audioPlayer) {
      try {
        playerSource = audioCtx.createMediaElementSource(audioPlayer);

        const warmBassEQ = audioCtx.createBiquadFilter();
        warmBassEQ.type = 'peaking';
        warmBassEQ.frequency.value = 220;
        warmBassEQ.gain.value = 2.5;

        const crispTrebleEQ = audioCtx.createBiquadFilter();
        crispTrebleEQ.type = 'highshelf';
        crispTrebleEQ.frequency.value = 5500;
        crispTrebleEQ.gain.value = 1.8;

        const compressor = audioCtx.createDynamicsCompressor();
        compressor.threshold.setValueAtTime(-18, audioCtx.currentTime);
        compressor.knee.setValueAtTime(10, audioCtx.currentTime);
        compressor.ratio.setValueAtTime(4, audioCtx.currentTime);
        compressor.attack.setValueAtTime(0.005, audioCtx.currentTime);
        compressor.release.setValueAtTime(0.05, audioCtx.currentTime);

        playerSource.connect(warmBassEQ);
        warmBassEQ.connect(crispTrebleEQ);
        crispTrebleEQ.connect(compressor);
        compressor.connect(analyser);
        analyser.connect(audioCtx.destination);
      } catch(e) {}
    }

    if (micStream && !micSource) {
      try {
        micSource = audioCtx.createMediaStreamSource(micStream);
        micSource.connect(analyser);
      } catch(e) {}
    }

  } catch(e) {
    console.log("Web Audio setup warning:", e);
  }
}

function drawFluidWave() {
  requestAnimationFrame(drawFluidWave);
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  const midY = canvas.height / 2;
  const styles = getComputedStyle(document.body);
  const stroke1 = styles.getPropertyValue('--wave-stroke-1').trim() || 'rgba(0, 242, 254, 0.9)';
  const stroke2 = styles.getPropertyValue('--wave-stroke-2').trim() || 'rgba(0, 114, 255, 0.65)';
  const stroke3 = styles.getPropertyValue('--wave-stroke-3').trim() || 'rgba(138, 43, 226, 0.45)';

  let fftEnergy = 0;
  if (analyser && liveFFTData) {
    analyser.getByteFrequencyData(liveFFTData);
    let sum = 0;
    for (let i = 0; i < liveFFTData.length; i++) sum += liveFFTData[i];
    fftEnergy = sum / (liveFFTData.length * 255);
  }

  let amp = 3;
  if (inCall) {
    if (isSpeaking) {
      amp = Math.max(12, Math.min(32, fftEnergy * 48 + 10));
    } else if (fftEnergy > 0.04) {
      amp = Math.min(28, fftEnergy * 42 + 6);
    } else {
      amp = 6;
    }
  }

  const waves = [
    { color: stroke1, freq: 0.024, phase: wavePhase, width: 2.5 },
    { color: stroke2, freq: 0.018, phase: wavePhase + 1.2, width: 2 },
    { color: stroke3, freq: 0.030, phase: wavePhase + 2.4, width: 1.5 }
  ];

  waves.forEach(w => {
    ctx.beginPath();
    ctx.moveTo(0, midY);
    for (let x = 0; x < canvas.width; x += 3) {
      const env = Math.sin((x / canvas.width) * Math.PI);
      const y = midY + Math.sin(x * w.freq + w.phase) * amp * env;
      ctx.lineTo(x, y);
    }
    ctx.strokeStyle = w.color;
    ctx.lineWidth = w.width;
    ctx.stroke();
  });
  wavePhase += 0.045;
}
drawFluidWave();

function playProceduralChime(freqs, duration=0.15) {
  try {
    const actx = audioCtx || new (window.AudioContext || window.webkitAudioContext)();
    freqs.forEach((f, idx) => {
      const osc = actx.createOscillator();
      const gain = actx.createGain();
      osc.frequency.value = f;
      osc.type = 'sine';
      gain.gain.setValueAtTime(0.06, actx.currentTime + idx * 0.05);
      gain.gain.exponentialRampToValueAtTime(0.001, actx.currentTime + idx * 0.05 + duration);
      osc.connect(gain);
      gain.connect(actx.destination);
      osc.start(actx.currentTime + idx * 0.05);
      osc.stop(actx.currentTime + idx * 0.05 + duration);
    });
  } catch(e) {}
}

function startThinkingAmbience() {
  try {
    if (!audioCtx) audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    if (thinkingOsc) return;
    thinkingOsc = audioCtx.createOscillator();
    thinkingGain = audioCtx.createGain();
    thinkingOsc.type = 'sine';
    thinkingOsc.frequency.setValueAtTime(115, audioCtx.currentTime);
    thinkingGain.gain.setValueAtTime(0.001, audioCtx.currentTime);
    thinkingGain.gain.linearRampToValueAtTime(0.015, audioCtx.currentTime + 0.3);
    thinkingOsc.connect(thinkingGain);
    thinkingGain.connect(audioCtx.destination);
    thinkingOsc.start();
  } catch(e) {}
}

function stopThinkingAmbience() {
  try {
    if (thinkingGain && audioCtx) {
      thinkingGain.gain.linearRampToValueAtTime(0.0001, audioCtx.currentTime + 0.15);
      setTimeout(() => {
        if (thinkingOsc) {
          try { thinkingOsc.stop(); thinkingOsc.disconnect(); } catch(e){}
          thinkingOsc = null;
          thinkingGain = null;
        }
      }, 160);
    }
  } catch(e) {}
}

function setStatus(text, active=false) {
  statusEl.textContent = text;
  if (active) ringEl.classList.add('active');
  else ringEl.classList.remove('active');
}

function updateTimer() {
  if (!callStartTime) return;
  const elapsed = Math.floor((Date.now() - callStartTime) / 1000);
  const m = String(Math.floor(elapsed / 60)).padStart(2, '0');
  const s = String(elapsed % 60).padStart(2, '0');
  timerEl.textContent = `${m}:${s}`;
}

function appendBubble(role, text) {
  const bubble = document.createElement('div');
  bubble.className = `msg-bubble ${role === 'user' ? 'msg-user' : 'msg-ai'}`;
  bubble.textContent = text;
  transcriptEl.appendChild(bubble);
  transcriptEl.scrollTop = transcriptEl.scrollHeight;
}

function interruptAI() {
  audioQueue = [];
  isPlayingChunk = false;
  if (isSpeaking) {
    audioPlayer.pause();
    audioPlayer.currentTime = 0;
    isSpeaking = false;
    bargeHintEl.style.display = 'none';
    liveSubtitleEl.textContent = '';
    avatarEmoji.textContent = '☁️';
    setStatus("Te escucho...", true);
    triggerHaptic(20);
    if (currentMode === 'handsfree') listenAgain();
  }
}

// Push to Talk & Spacebar Control
window.addEventListener('keydown', (e) => {
  if (e.target.tagName === 'INPUT' || e.target.tagName === 'SELECT') return;
  if (e.code === 'Space') {
    e.preventDefault();
    if (!inCall) toggleCall();
    else if (currentMode === 'ptt' && !isPTTHeld) {
      isPTTHeld = true;
      interruptAI();
      avatarEmoji.textContent = '🎙️';
      setStatus("Grabando voz (suelta para enviar)...", true);
      triggerHaptic(30);
      startSpeechRecognition();
    } else {
      interruptAI();
    }
  } else if (e.code === 'Escape') {
    interruptAI();
  }
});

window.addEventListener('keyup', (e) => {
  if (e.target.tagName === 'INPUT' || e.target.tagName === 'SELECT') return;
  if (e.code === 'Space' && currentMode === 'ptt' && isPTTHeld) {
    isPTTHeld = false;
    triggerHaptic(20);
    stopSpeechRecognition();
  }
});

function initSpeech() {
  const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRec) {
    appendBubble('ai', 'Aviso: Usa Chrome o Safari para entrada de voz. Puedes usar el botón 💬 para escribir.');
    return null;
  }
  const rec = new SpeechRec();
  rec.lang = 'es-US';
  rec.continuous = (currentMode === 'handsfree');
  rec.interimResults = true;

  rec.onstart = () => {
    if (inCall && !isSpeaking && !isMuted) {
      avatarEmoji.textContent = '👂';
      setStatus(currentMode === 'ptt' ? "Grabando voz..." : "Te escucho, habla...", true);
    }
  };

  rec.onresult = async (event) => {
    let interim = '';
    let finalSpeech = '';
    for (let i = event.resultIndex; i < event.results.length; ++i) {
      if (event.results[i].isFinal) finalSpeech += event.results[i][0].transcript;
      else interim += event.results[i][0].transcript;
    }

    if (interim) {
      interruptAI();
      liveSubtitleEl.textContent = `Tú: "${interim}..."`;
    }

    if (finalSpeech.trim()) {
      liveSubtitleEl.textContent = '';
      interruptAI();
      appendBubble('user', finalSpeech.trim());
      processMessage(finalSpeech.trim());
    }
  };

  rec.onerror = (e) => {
    if (inCall && currentMode === 'handsfree' && !isSpeaking && !isMuted) setTimeout(listenAgain, 500);
  };

  rec.onend = () => {
    if (inCall && currentMode === 'handsfree' && !isSpeaking && !isMuted) setTimeout(listenAgain, 250);
  };

  return rec;
}

function startSpeechRecognition() {
  if (recognition) {
    try { recognition.abort(); } catch(e){}
    try { recognition.start(); } catch(e){}
  }
}

function stopSpeechRecognition() {
  if (recognition) {
    try { recognition.stop(); } catch(e){}
  }
}

function listenAgain() {
  if (inCall && currentMode === 'handsfree' && !isSpeaking && !isMuted && recognition) {
    try { recognition.abort(); } catch(e){}
    setTimeout(() => {
      if (inCall && currentMode === 'handsfree' && !isSpeaking && !isMuted) {
        try { recognition.start(); } catch(e){}
      }
    }, 120);
  }
}

async function processMessage(userText) {
  isThinking = true;
  avatarEmoji.textContent = '🧠';
  setStatus("Razonando...", false);
  startThinkingAmbience();

  const payload = {
    action: "chat",
    text: userText,
    voice: voiceSelect.value,
    persona: personaSelect.value,
    rate: rateSelect.value
  };

  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify(payload));
  } else {
    try {
      const t0 = performance.now();
      const resp = await fetch('/api/chat', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(payload)
      });
      const data = await resp.json();
      const roundTrip = ((performance.now() - t0) / 1000).toFixed(1);
      pillTextEl.textContent = `⚡ ${data.latency || roundTrip}s • Cloud Voice`;

      stopThinkingAmbience();
      isThinking = false;
      appendBubble('ai', data.reply);
      if (data.audio) enqueueAudioChunk(data.audio, data.reply);
      else {
        avatarEmoji.textContent = '☁️';
        setTimeout(listenAgain, 600);
      }
    } catch (e) {
      stopThinkingAmbience();
      isThinking = false;
      avatarEmoji.textContent = '☁️';
      setStatus("Error de conexión", false);
      setTimeout(listenAgain, 1800);
    }
  }
}

function toggleDrawer() {
  textDrawer.classList.toggle('open');
  if (textDrawer.classList.contains('open')) manualInput.focus();
}

function sendManualText() {
  const text = manualInput.value.trim();
  if (!text) return;
  manualInput.value = '';
  interruptAI();
  appendBubble('user', text);
  processMessage(text);
}

function sendQuickPrompt(promptText) {
  if (!inCall) {
    toggleCall().then(() => {
      setTimeout(() => { processMessage(promptText); }, 1200);
    });
  } else {
    interruptAI();
    appendBubble('user', promptText);
    processMessage(promptText);
  }
}

function toggleSettingsModal() {
  settingsModal.classList.toggle('open');
}

function toggleRecording() {
  if (!isRecording) startCallRecording();
  else stopCallRecording();
}

function startCallRecording() {
  if (!micStream) {
    alert("Inicia la llamada primero para poder grabar el audio.");
    return;
  }
  try {
    recordedChunks = [];
    mediaRecorder = new MediaRecorder(micStream);
    mediaRecorder.ondataavailable = e => { if (e.data.size > 0) recordedChunks.push(e.data); };
    mediaRecorder.onstop = saveRecordingFile;
    mediaRecorder.start();
    isRecording = true;
    recBtn.classList.add('recording');
    recBtn.textContent = "⏹️ Grabando";
  } catch(e) {
    console.log("MediaRecorder error:", e);
  }
}

function stopCallRecording() {
  if (mediaRecorder && isRecording) {
    mediaRecorder.stop();
    isRecording = false;
    recBtn.classList.remove('recording');
    recBtn.textContent = "🔴 Rec";
  }
}

function saveRecordingFile() {
  const blob = new Blob(recordedChunks, { type: 'audio/webm' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.style.display = 'none';
  a.href = url;
  a.download = `Llamada_Cloud_${new Date().toISOString().slice(0,19).replace(/[:T]/g,'-')}.webm`;
  document.body.appendChild(a);
  a.click();
  setTimeout(() => { document.body.removeChild(a); URL.revokeObjectURL(url); }, 100);
}

function toggleMute() {
  isMuted = !isMuted;
  muteBtn.textContent = isMuted ? "🔇" : "🎤";
  muteBtn.style.background = isMuted ? "rgba(255, 71, 87, 0.3)" : "rgba(255, 255, 255, 0.09)";
  if (isMuted) {
    if (recognition) { try { recognition.abort(); } catch(e){} }
    setStatus("Micrófono silenciado", false);
  } else {
    if (currentMode === 'handsfree') listenAgain();
  }
}

async function toggleCall() {
  if (!inCall) {
    inCall = true;
    callStartTime = Date.now();
    callTimerInterval = setInterval(updateTimer, 1000);

    audioPlayer.play().catch(()=>{});
    audioPlayer.pause();

    callBtn.className = "btn-call btn-end";
    callBtn.textContent = "🛑";
    setStatus("Conectando con la nube...", true);
    triggerHaptic(40);
    
    playProceduralChime([523.25, 659.25, 783.99], 0.16);
    
    try {
      micStream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true
        }
      });
    } catch(e) {
      console.log("Mic access fallback:", e);
    }

    setupWebAudioGraph();
    recognition = initSpeech();
    
    processMessage("Hola, llamada iniciada.");

  } else {
    inCall = false;
    isSpeaking = false;
    isThinking = false;
    stopThinkingAmbience();
    if (isRecording) stopCallRecording();
    bargeHintEl.style.display = 'none';
    liveSubtitleEl.textContent = '';
    avatarEmoji.textContent = '☁️';
    clearInterval(callTimerInterval);
    callStartTime = null;
    timerEl.textContent = "00:00";
    if (recognition) { try { recognition.abort(); } catch(e){} }
    audioQueue = [];
    audioPlayer.pause();
    if (micStream) {
      micStream.getTracks().forEach(t => t.stop());
      micStream = null;
      micSource = null;
    }
    callBtn.className = "btn-call btn-start";
    callBtn.textContent = "📞";
    setStatus("Llamada finalizada", false);
    triggerHaptic([30, 40, 30]);
    playProceduralChime([659.25, 440.00], 0.2);
    appendBubble('ai', "Llamada finalizada. Toca el botón verde 📞 para volver a hablar.");
  }
}

function copyTranscript() {
  const bubbles = Array.from(transcriptEl.querySelectorAll('.msg-bubble'));
  const text = bubbles.map(b => (b.classList.contains('msg-user') ? 'Daniel: ' : 'Antigravity: ') + b.textContent).join('\n');
  navigator.clipboard.writeText(text).then(() => {
    alert("¡Diálogo copiado al portapapeles!");
  }).catch(() => {
    alert(text);
  });
}

function syncToTelegram() {
  const bubbles = Array.from(transcriptEl.querySelectorAll('.msg-bubble'));
  if (bubbles.length === 0) {
    alert("No hay diálogo para enviar aún.");
    return;
  }
  const text = bubbles.map(b => (b.classList.contains('msg-user') ? 'Daniel: ' : 'Antigravity: ') + b.textContent).join('\n');
  fetch('/api/sync_telegram', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({transcript: text})
  }).then(r => r.json()).then(data => {
    if (data.status === 'sent') {
      alert("✅ ¡Resumen enviado a tu Telegram exitosamente!");
    } else {
      alert("⚠️ Error: " + (data.error || "No se pudo sincronizar"));
    }
  }).catch(e => alert("Error de red al sincronizar con Telegram"));
}

function clearMemory() {
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({action: "clear"}));
  } else {
    fetch('/api/clear', {method: 'POST'}).then(() => {
      transcriptEl.innerHTML = '<div class="msg-bubble msg-ai">Memoria reseteada. Empezamos una nueva conversación fresca.</div>';
    });
  }
}
</script>
</body>
</html>
"""
    return web.Response(text=html_content, content_type="text/html")

async def handle_health(request):
    status = {
        "status": "online",
        "service": "Antigravity Voice Cloud 24/7 (Always-On)",
        "features": [
            "24/7 Cloud Uptime (Zero Laptop Dependency)",
            "Incremental Sentence Audio Streaming",
            "Dual FFT Waveform Analyser",
            "Studio Biquad Vocal EQ",
            "Push-To-Talk & Hands-Free VAD",
            "Telegram Sync",
            "PWA Manifest",
            "Edge-TTS Free Neural Voices"
        ],
        "port": PORT,
        "has_gemini_key": bool(GEMINI_API_KEY)
    }
    return web.json_response(status)

def main():
    app = web.Application()
    app.router.add_get("/ws/call", handle_ws_call)
    app.router.add_post("/api/chat", handle_api_chat)
    app.router.add_post("/api/clear", handle_clear_memory)
    app.router.add_post("/api/sync_telegram", handle_sync_telegram)
    app.router.add_get("/manifest.json", handle_manifest)
    app.router.add_get("/call", handle_call_ui)
    app.router.add_get("/", handle_call_ui)
    app.router.add_get("/health", handle_health)

    print(f"☁️ Antigravity Voice Cloud 24/7 escuchando en 0.0.0.0:{PORT}...")
    web.run_app(app, host="0.0.0.0", port=PORT)

if __name__ == "__main__":
    main()
