# AgroIA Casanare — Backend

Implementación de FastAPI de la arquitectura descrita en el documento
técnico: **Agente 1** (recepción/NLP), **Agente 2** (estructuración BD) y
**Agente 3** (ventas), usando **Telegram** como canal (100% gratis, sin
verificación de negocio, ideal para el MVP de hackathon), **Gemini API**
para el Agente 1 (extracción) y **Claude API** para el Agente 3 (ventas),
**Groq Whisper** para transcribir notas de voz y **Supabase** (Postgres +
JSONB) como base de datos.

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

Estas seis son obligatorias; sin ellas el sistema no funciona:

| Variable | Dónde se saca | Para qué |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | `@BotFather` en Telegram → `/newbot` | Recibir y responder mensajes |
| `ANTHROPIC_API_KEY` | console.anthropic.com → API Keys | El cerebro del Agente 3 (ventas) |
| `GEMINI_API_KEY` | aistudio.google.com/apikey | El cerebro del Agente 1 (extracción) |
| `GROQ_API_KEY` | console.groq.com (capa gratuita) | Transcribir notas de voz |
| `SUPABASE_URL` | Supabase → Project Settings → API → Project URL | Dónde está la BD |
| `SUPABASE_KEY` | Supabase → Project Settings → API → **`service_role`** | Escribir en la BD |

> **`service_role`, no `anon`.** La `anon key` viaja en el bundle de Angular
> (es pública) y con RLS activo solo puede *leer* ofertas activas. El backend
> necesita escribir, así que usa la `service_role key` — y esa nunca debe
> llegar al frontend ni al repositorio.

Las demás son opcionales y tienen valor por defecto: `TELEGRAM_WEBHOOK_URL`,
`CLAUDE_MODEL_*`, `GEMINI_MODEL_EXTRACCION`, `GROQ_STT_MODEL`,
`SUPABASE_TABLE_PRODUCTOS`, `APP_ENV` y `CORS_ALLOW_ORIGINS` (en producción,
el dominio real del frontend, no `*`).

**Para verificar que quedaron bien puestas**, llama al healthcheck: te dice
qué falta sin exponer ningún valor.

```bash
curl https://tu-backend/     # -> {"status":"ok","variables_faltantes":[]}
```

### Verificar la conexión con Supabase

```bash
python -m scripts.verificar_supabase
```

Revisa en orden las 6 cosas que pueden fallar, y para cada una dice qué
hacer: variables vacías, URL mal copiada, **clave `anon` en vez de
`service_role`**, tabla inexistente, columnas del Agente 2 faltantes, y
permiso de escritura real (inserta una fila de prueba y la borra).

Ese tercer punto es el que más tiempo ahorra: con la `anon key` los inserts
no lanzan error — Supabase responde 200 con cero filas y la oferta
simplemente desaparece.

## 3. Crear la tabla en Supabase

Copia el contenido de `supabase_schema.sql` y ejecútalo en el **SQL Editor**
de tu proyecto Supabase. Luego activa Realtime para la tabla `productos`
(Database → Replication) si quieres que el catálogo en Angular se actualice
solo, sin recargar la página.

> Si ya habías creado la tabla `productos` antes, vuelve a ejecutar el
> archivo completo: trae los `alter table ... add column if not exists` que
> agregan las columnas estandarizadas por el Agente 2. Es idempotente.

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
│   │   ├── normalizacion.py         # tablas de unidades/productos/municipios
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
│   ├── registrar_webhook.py         # utilidad de una sola vez para Telegram
│   └── verificar_supabase.py        # diagnostica la conexión con la BD
├── tests/
│   ├── conftest.py                  # env vars de prueba
│   ├── test_health.py               # pruebas de humo
│   └── test_agente2.py              # estandarización y validación del Agente 2
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

## Agente 2 — estandarización de unidades

Es la pieza que convierte lo que dice un campesino en un registro comparable.
Sus tres etapas (sección 3 del documento de arquitectura) son sus tres
funciones públicas, y solo la última toca la base de datos:

| Etapa | Función | Qué hace |
|-------|---------|----------|
| Entrada | `validar_oferta` | Revalida los 4 atributos obligatorios y devuelve **todos** los faltantes juntos, para preguntar una sola vez. Rechaza valores absurdos (una transcripción mala que convierte "dos mil" en 2.000.000.000). |
| Procesamiento | `construir_documento` | Mapea al esquema, estandariza unidad/producto/municipio y calcula los derivados. Función pura. |
| Salida | `estructurar_y_guardar` | Inserta **o actualiza** y devuelve `ResultadoEstructuracion(registro, actualizada)`. |

Ejemplo real (`5 arrobas de PLATANOS a 25.000 la arroba, vereda El Charte, Yopal`):

```jsonc
{
  "producto": "plátano",              // 'PLATANOS' -> nombre canónico
  "cantidad": 5.0,
  "unidad": "arroba",                 // 'arrobas' -> unidad canónica
  "unidad_original": "arrobas",       // se conserva para auditar sinónimos
  "categoria_unidad": "peso",
  "precio": 25000.0,
  "ubicacion": "Vereda El Charte, Yopal",
  "municipio": "Yopal",               // reconocido dentro del texto libre
  "unidad_base": "kg",
  "cantidad_base": 62.5,              // 5 × 12,5 kg
  "precio_por_unidad_base": 2000.0    // permite comparar contra otra oferta en kg
}
```

Decisiones de diseño que vale la pena defender:

- **No se inventan conversiones.** Un `bulto` o un `racimo` no pesan siempre
  lo mismo, así que sus campos derivados quedan en `null` y el catálogo
  muestra el precio tal como lo dijo el productor. Lo mismo con un producto
  que no está en la tabla: se guarda limpio, no "corregido".
- **Solo se persiste lo que Angular no puede derivar.** El precio por
  kilo exige la tabla de equivalencias (vive en el backend), por eso se
  guarda; `cantidad × precio` no se guarda, porque el frontend lo calcula.
- **El catálogo no se llena de duplicados.** Si un productor vuelve a mandar
  el mismo producto, está corrigiendo su precio, no publicando algo nuevo:
  el agente **actualiza** su oferta activa. El bot responde "Actualicé tu
  oferta" en vez de "Publiqué", y `POST /api/productos` devuelve 200 en vez
  de 201. Un índice único parcial en la BD cierra la ventana de carrera
  cuando llegan dos mensajes casi simultáneos.

Ampliar el vocabulario (una unidad, un producto o un municipio nuevo) es
tocar únicamente `agroia/agents/normalizacion.py`.

Las pruebas del Agente 2 corren sin Supabase ni Claude, porque las dos
primeras etapas son puras y la tercera se prueba con un repositorio falso:

```bash
pytest tests/test_agente2.py tests/test_repositorio.py
```

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
- **Modelos configurables**: tanto el modelo de Gemini del Agente 1
  (`GEMINI_MODEL_EXTRACCION`) como los de Claude del Agente 3
  (`CLAUDE_MODEL_*`) se configuran por variable de entorno en `.env`. Revisa
  [ai.google.dev/gemini-api/docs/models](https://ai.google.dev/gemini-api/docs/models)
  y [docs.claude.com](https://docs.claude.com/en/docs/about-claude/models)
  para el alias/modelo vigente al momento de desplegar.
```
