# ☁️ Antigravity Voice Cloud 24/7 (Always-On Edition)

Sistema autónomo de llamadas de voz y razonamiento en vivo con **Antigravity AI**, desplegable **100% GRATIS** en la nube para hablar las 24 horas del día, los 7 días de la semana, **incluso cuando tu laptop física está completamente apagada**.

---

## 🚀 Despliegue 100% Gratuito en la Nube (Sin Tarjeta de Crédito)

### Opción 1: Render.com (Recomendado - 1 Clic con GitHub)
1. Entra a [render.com](https://render.com) e inicia sesión con tu cuenta de GitHub (`drylexx3`).
2. Haz clic en **"New +"** $\to$ **"Web Service"**.
3. Selecciona tu repositorio `drylexx3/antigravity-voice-cloud`.
4. En la configuración:
   - **Environment:** `Python 3` (o Docker)
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python3 server.py`
   - **Plan:** `Free` ($0.00 / mes)
5. En **Environment Variables**, añade:
   - `GEMINI_API_KEY`: Tu clave gratuita obtenida en [Google AI Studio](https://aistudio.google.com/apikey) (100% gratis, sin tarjeta).
   - `TELEGRAM_BOT_TOKEN`: `8965653104:AAFfye3yaVWJGJTHjUVUs1NFj_OJz7C7Xig`
   - `TELEGRAM_USER_ID`: `8069526508`
6. Haz clic en **"Deploy Web Service"**.
7. En menos de 2 minutos tendrás tu URL pública HTTPS permanente:  
   `https://antigravity-voice-cloud.onrender.com/call`

---

### Opción 2: Hugging Face Spaces (Docker - 16 GB RAM Gratis)
1. Ve a [huggingface.co/new-space](https://huggingface.co/new-space).
2. Elige:
   - **Space SDK:** `Docker` $\to$ `Blank`
   - **Visibility:** `Public`
   - **Hardware:** `Free (2 CPU, 16 GB RAM)`
3. Conecta este repositorio o haz un `git push` a Hugging Face.
4. Tu llamada estará activa 24/7 en: `https://<tu-usuario>-antigravity-voice.hf.space/call`.

---

## ⏱️ Keep-Alive 24/7 (Prevenir Suspensión Gratuita)

Los servicios gratuitos en la nube a veces se suspenden tras 15 minutos sin visitas. Para evitarlo:
1. Este repositorio incluye un workflow automatizado en `.github/workflows/keep_alive.yml`.
2. En GitHub, ve a **Settings** $\to$ **Secrets and variables** $\to$ **Actions**.
3. Crea un secreto llamado `CLOUD_APP_URL` con tu URL de Render (ej: `https://antigravity-voice-cloud.onrender.com`).
4. GitHub Actions enviará un "ping" silencioso a `/health` cada 10 minutos, garantizando que el servidor permanezca **despierto y respondiendo al instante las 24 horas del día sin interrupciones**.

---

## 🎙️ Capacidades Integradas en la Nube
- **Streaming por Oraciones (Zero-Wait):** El audio comienza a sonar en tus audífonos en menos de 350ms tras el razonamiento.
- **Dual FFT Waveform:** Visualizador que reacciona a las frecuencias y sílabas reales de la voz.
- **Selector Manos Libres vs Push-To-Talk:** Espacio o toque para hablar.
- **Sincronización con Telegram:** Envía transcripciones a tu bot privado con 1 toque.
- **PWA Instalable:** Agrégalo a la pantalla de inicio en iOS o Android como una app nativa.
