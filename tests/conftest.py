"""Variables de entorno dummy para que la suite de pruebas pueda importar
la app sin depender de credenciales reales."""
import os

os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiJ9.eyJyb2xlIjoiYW5vbiJ9.test-signature")
os.environ.setdefault("OPENROUTER_API_KEY", "sk-or-test-key")
os.environ.setdefault("GROQ_API_KEY", "gsk-test")
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "123:test-token")

# La voz queda APAGADA en las pruebas. En producción el bot habla siempre,
# pero acá cada respuesta saldría a la red a sintetizar audio de verdad: la
# suite se volvería lenta y dependería de que el servicio esté arriba.
# Las pruebas que sí verifican la voz la encienden ellas mismas, mockeando
# el sintetizador (ver tests/test_webhook_voz.py).
os.environ.setdefault("VOZ_RESPUESTA_ACTIVA", "false")
