# AgroIA Casanare — Backend

Implementación de FastAPI de la arquitectura descrita en el documento
técnico: **Agente 1** (recepción/NLP), **Agente 2** (estructuración BD) y
**Agente 3** (ventas), usando **Telegram** como canal (100% gratis, sin
verificación de negocio, ideal para el MVP de hackathon), **Claude API**
como cerebro de los agentes, **Groq Whisper** para transcribir notas de voz
y **Supabase** (Postgres + JSONB) como base de datos.

## 1. Instalar dependencias

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## 2. Configurar variables de entorno

```bash
cp .env.example .env
```

Completa en `.env`:
- `TELEGRAM_BOT_TOKEN`: créalo hablando con `@BotFather` en Telegram (`/newbot`).
- `ANTHROPIC_API_KEY`: desde console.anthropic.com.
- `GROQ_API_KEY`: desde console.groq.com (capa gratuita).
- `SUPABASE_URL` / `SUPABASE_KEY`: desde el panel de tu proyecto Supabase
  (Settings → API). Usa la `service_role key` solo en el backend, nunca en Angular.
- `CORS_ALLOW_ORIGINS`: orígenes del frontend Angular separados por coma
  (`*` solo para pruebas locales).

## 3. Crear la tabla en Supabase

Copia el contenido de `supabase_schema.sql` y ejecútalo en el **SQL Editor**
de tu proyecto Supabase. Luego activa Realtime para la tabla `productos`
(Database → Replication) si quieres que el catálogo en Angular se actualice
solo, sin recargar la página.

## 4. Levantar el backend en local

Desde la **raíz del proyecto** (donde está esta carpeta `agroia/`):

```bash
uvicorn agroia.main:app --reload --port 8000
```

Prueba rápida:
```bash
curl http://localhost:8000/api/productos/catalogo
```

Documentación interactiva autogenerada: `http://localhost:8000/docs`.

## 5. Exponer el webhook con HTTPS (requisito de Telegram)

Para pruebas locales, usa un túnel (ngrok, cloudflared):

```bash
ngrok http 8000
```

Copia la URL HTTPS que te da ngrok (ej. `https://abcd1234.ngrok.app`) y
ponla en `.env` como:

```
TELEGRAM_WEBHOOK_URL=https://abcd1234.ngrok.app/api/webhook/telegram
```

Luego registra el webhook una sola vez:

```bash
python -m scripts.registrar_webhook
```

Para el despliegue final (no solo pruebas), sube el backend a un servicio
gestionado que entregue HTTPS de forma nativa (Render, Railway o Fly.io son
las opciones más rápidas de configurar para una hackathon — el `Dockerfile`
incluido sirve para cualquiera de los tres) y repite este mismo paso
apuntando `TELEGRAM_WEBHOOK_URL` a esa URL definitiva.

## 6. Correr las pruebas

```bash
pytest
```

Son pruebas de humo (la app arranca, las rutas existen); no reemplazan
probar el flujo real con un bot de Telegram y datos de Supabase.

## 7. Probar el flujo completo

1. Escríbele a tu bot de Telegram algo como: *"Tengo 20 kilos de plátano a
   2000 pesos"* — el Agente 1 detectará que falta la ubicación y te la
   preguntará.
2. Responde con la ubicación (ej. "Yopal") — el Agente 2 guardará la oferta
   en Supabase y el bot confirmará la publicación.
3. Desde el mismo bot (o simulando otro usuario), escribe *"Busco plátano
   por Yopal"* — el Agente 3 responderá con la oferta encontrada y el
   contacto del productor.
4. `GET /api/productos/catalogo` ya debería devolver ese producto — es el
   endpoint que consume el frontend Angular.

## 8. Frontend (Angular)

El frontend vive en `frontend/` (Angular 18, standalone components).

```bash
cd frontend
npm install
npm start          # http://localhost:4200
```

Apunta al backend vía `frontend/src/environments/environment.ts`
(`apiBase`, por defecto `http://localhost:8000`). Levanta primero el backend
con `uvicorn agroia.main:app --reload --port 8000`.

Módulos:
- **Home** (`/`) — landing con el conteo de ofertas en vivo y "cómo funciona".
- **Catálogo** (`/catalogo`) — `GET /api/productos/catalogo` + filtros y orden en cliente.
- **Buscar con IA** (`/buscar`) — `POST /api/sistema/agentes/consulta` (Agente 3).
- **Publicar oferta** (`/publicar`) — `POST /api/productos` (alta directa, sin Telegram).

### Desplegar el frontend en Vercel

El `vercel.json` de la raíz ya deja el repo listo para que Vercel construya
**solo** el frontend (Angular), sin tocar el backend de Python.

1. Importa el repo en Vercel. Si Vercel detecta FastAPI, en *Settings → Build*
   deja **Framework Preset = Other** (o pon *Root Directory* = `frontend`, que
   usa `frontend/vercel.json`).
2. En *Settings → Environment Variables* añade `API_BASE_URL` con la URL pública
   del backend (ej. `https://agroia-backend.onrender.com`, sin barra final).
3. Deploy. Vercel corre `cd frontend && npm run vercel-build` y publica
   `frontend/dist/frontend/browser`.
4. Añade el dominio de Vercel a `CORS_ALLOW_ORIGINS` en el `.env` del backend.

El **backend** no va en Vercel: despliégalo con el `Dockerfile` en Render,
Railway o Fly.io (ver sección 5).

## Endpoints

| Método y ruta                       | Router                     | Descripción                                          |
|-------------------------------------|----------------------------|------------------------------------------------------|
| `POST /api/webhook/telegram`        | `api/routers/webhook.py`   | Webhook único de Telegram; enruta a Agente 1/2 o 3.  |
| `GET  /api/productos/catalogo`      | `api/routers/productos.py` | Catálogo público de ofertas activas (Angular).       |
| `POST /api/productos`               | `api/routers/productos.py` | Alta directa de una oferta desde el formulario web.  |
| `POST /api/sistema/agentes/consulta`| `api/routers/agentes.py`   | Endpoint interno del Agente 3 (probar sin Telegram). |

## Estructura del proyecto

```
agroia-backend/
├── agroia/                          # paquete principal — todo el código vive aquí
│   ├── main.py                      # ensambla la app: routers + CORS + healthcheck
│   ├── core/
│   │   └── config.py                # única fuente de las variables de entorno
│   ├── api/
│   │   └── routers/
│   │       ├── webhook.py           # POST /api/webhook/telegram
│   │       ├── productos.py         # GET /api/productos/catalogo · POST /api/productos
│   │       └── agentes.py           # POST /api/sistema/agentes/consulta
│   ├── agents/                      # la lógica de negocio de cada agente
│   │   ├── agente1_recepcion.py
│   │   ├── agente2_estructuracion.py
│   │   └── agente3_ventas.py
│   ├── integrations/                # clientes hacia servicios externos
│   │   ├── telegram_client.py
│   │   └── speech_to_text.py        # Groq Whisper
│   ├── repositories/                # única capa que habla con la base de datos
│   │   └── productos_repository.py  # Supabase (insertar/listar/buscar)
│   └── schemas/                     # modelos Pydantic (uno por concepto)
│       ├── oferta.py
│       ├── producto.py
│       └── consulta.py
├── scripts/
│   └── registrar_webhook.py         # utilidad de una sola vez para Telegram
├── tests/
│   ├── conftest.py                  # env vars de prueba
│   └── test_health.py               # pruebas de humo
├── frontend/                        # SPA Angular 18 (ver sección 8)
├── Dockerfile
├── requirements.txt
├── supabase_schema.sql              # DDL de la tabla productos
├── .env.example
└── .gitignore
```

**Por qué está organizado así** — cada capa tiene una única responsabilidad
y solo puede depender de las de más abajo, nunca al revés:

1. `api/routers` recibe HTTP y decide qué agente llamar. No sabe nada de
   Supabase ni de Claude directamente.
2. `agents` contiene la lógica de negocio (los 3 agentes del documento).
   No sabe nada de FastAPI ni de HTTP.
3. `integrations` y `repositories` son los únicos módulos que hablan con
   el mundo exterior (Telegram, Groq, Supabase). Si mañana cambian de
   base de datos o de canal de mensajería, el cambio queda contenido acá.
4. `schemas` define la forma de los datos que viajan entre capas.

Esto es justamente lo que le permite decirle al jurado, con código real
detrás, que "cambiar Telegram por WhatsApp Cloud API solo implica tocar
`integrations/telegram_client.py` y el router de webhook — los 3 agentes y
la base de datos no cambian".

## Notas para la presentación ante el jurado

- **Estado conversacional**: el ciclo de "faltan datos" del Agente 1 vive en
  memoria (`CONVERSACIONES` en `agents/agente1_recepcion.py`) para
  simplicidad del MVP. Si el jurado pregunta por escalabilidad, la
  respuesta es moverlo a una tabla en Supabase — el cambio es mínimo porque
  ya está aislado en una sola función.
- **Dos caminos, un solo Agente 2**: la publicación por Telegram y el
  formulario web (`POST /api/productos`) terminan ambos en
  `estructurar_y_guardar`, así que la normalización de datos vive en un
  único lugar.
- **Modelos de Claude**: son configurables por variable de entorno
  (`CLAUDE_MODEL_*` en `.env`). Revisa
  [docs.claude.com](https://docs.claude.com/en/docs/about-claude/models)
  para el alias/modelo vigente al momento de desplegar.
```
