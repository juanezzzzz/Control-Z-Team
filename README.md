# AgroIA Casanare — Backend

Implementación de FastAPI de la arquitectura descrita en el documento
técnico: **Agente 1** (recepción/NLP), **Agente 2** (estructuración BD) y
**Agente 3** (ventas), usando **Telegram** como canal (100% gratis, sin
verificación de negocio, ideal para el MVP de hackathon), un **LLM gratuito
vía OpenRouter** (hoy MiniMax M3 — ver nota abajo sobre por qué no DeepSeek)
para el Agente 1 (extracción) y el Agente 3 (ventas), **Groq Whisper** para
transcribir notas de voz y **Supabase** (Postgres + JSONB) como base de
datos.

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

Estas cinco son obligatorias; sin ellas el sistema no funciona:

| Variable | Dónde se saca | Para qué |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | `@BotFather` en Telegram → `/newbot` | Recibir y responder mensajes |
| `OPENROUTER_API_KEY` | openrouter.ai → Keys → Create Key | El cerebro del Agente 1 (extracción) y el Agente 3 (ventas) |
| `GROQ_API_KEY` | console.groq.com (capa gratuita) | Transcribir notas de voz |
| `SUPABASE_URL` | Supabase → Project Settings → API → Project URL | Dónde está la BD |
| `SUPABASE_KEY` | Supabase → Project Settings → API → **`service_role`** | Escribir en la BD |

> **`service_role`, no `anon`.** La `anon key` viaja en el bundle de Angular
> (es pública) y con RLS activo solo puede *leer* ofertas activas. El backend
> necesita escribir, así que usa la `service_role key` — y esa nunca debe
> llegar al frontend ni al repositorio.

Las demás son opcionales y tienen valor por defecto: `TELEGRAM_WEBHOOK_URL`,
`OPENROUTER_BASE_URL`, `LLM_MODEL`, `LLM_TIMEOUT`, `GROQ_STT_MODEL`,
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
gestionado que entregue HTTPS de forma nativa y repite este mismo paso
apuntando `TELEGRAM_WEBHOOK_URL` a esa URL definitiva. Ver la sección
**"Desplegar el backend en Render"** más abajo — es gratis y usa el
`Dockerfile` incluido tal cual.

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

En cualquiera de esos pasos el bot te contesta con **texto y nota de voz**.
Pruébalo también mandándole los mensajes como nota de voz (ver la sección
siguiente).

## Conversación por voz, de ida y vuelta

El bot **entiende** notas de voz (Groq Whisper) y **responde** hablando
(Edge TTS). Es la funcionalidad pensada para quien no lee o escribe con
facilidad: puede publicar una oferta completa sin escribir una sola letra.

**Toda respuesta sale por los dos canales: texto y nota de voz**, escriba o
hable la persona. No se condiciona el audio al canal de entrada porque en el
campo es común que quien lee con dificultad igual escriba como pueda —
hacerlo dejaría por fuera justo a quien más lo necesita.

El texto va primero y nunca falta, por tres razones: llega aunque la síntesis
falle, se puede releer, y de ahí se copia un teléfono o un precio. El audio
va encima, nunca en reemplazo. Si el sintetizador no responde en
`TTS_TIMEOUT` segundos, se suelta el audio y queda el texto — antes que
demorarse y arriesgar que Telegram reintente el webhook y duplique la oferta.

### El tono llanero

No lo da solo el sintetizador; son tres capas (`agroia/core/voz.py`):

1. **La voz**: `es-VE-SebastianNeural`. Venezolana, no colombiana, a
   propósito: el llano es binacional (Casanare/Arauca/Meta y Apure/Barinas)
   y el acento llanero está mucho más cerca del venezolano que del bogotano.
2. **El ritmo**: 1.5x de velocidad (`+50%`) y tono natural (`+0Hz`). Hablar
   suelto elimina los silencios entre palabras que hacían sonar la voz a
   dictado. El tono va sin desplazar a propósito: mover el pitch corre los
   formantes y hace que la sílaba tónica caiga rara — el acento suena
   exagerado. Si a 1.5x atropella, `+40%` o `+30%`.
3. **La redacción** (`dar_tono_llanero` + `dar_fluidez`): toques léxicos
   llaneros escogidos para sonar naturales sin caer en caricatura — "buenas"
   en vez de "hola", "hallar" en vez de "encontrar", "vecino" como trato. Se
   evitan a propósito los regionalismos muy marcados y el exceso de "pues".
   Es un llanero **neutro**.

Lo que más delata a una máquina no es la voz sino la gramática: un
sintetizador neuronal saca su entonación de la puntuación y de cómo esté
construida la frase. Por eso `dar_fluidez` corrige lo que suena a máquina:

| Suena a robot | Suena a persona |
|---|---|
| "a 2000 pesos **por kilos**" | "a 2000 pesos **el kilo**" |
| "Plátano**,** 20 kilos**,** 2000 pesos**,** Yopal" | "Plátano **de** 20 kilos **a** 2000 pesos **en** Yopal" |
| lista de viñetas leída de corrido | "**La primera,** … **La segunda,** …" |

La segunda fila es la que más se nota: **cada coma es una pausa**, así que
cuatro campos separados por comas salen a tirones. Uniéndolos con
preposiciones (`unir_campos`) la oferta se dice de corrido, con una sola
pausa breve — la del ordinal, que además ayuda a seguir la lista.

Además, el mismo módulo traduce el mensaje escrito a uno *hablable*: `$2.000`
→ "2000 pesos" (si no, lo diría en dólares o como decimal), `kg` → "kilos",
un celular se dicta dígito por dígito para poder anotarlo, y los enlaces
`wa.me/...` se eliminan porque dichos en voz alta son ruido.

```
ESCRITO: ¡Listo! Publiqué tu oferta de plátano. Quedó a $2.000 por kg.
         Los compradores ya pueden verla y contactarte.
HABLADO: ¡Listo pues! Publiqué tu oferta de plátano. Quedó a 2000 pesos
         por kilos. Los compradores, vecino, ya pueden verla y contactarte.
```

Todo se ajusta por variables de entorno sin tocar código: `TTS_VOZ`,
`TTS_VELOCIDAD`, `TTS_TONO`, y `VOZ_RESPUESTA_ACTIVA=false` para dejar el bot
solo en texto. Las pruebas de esta capa no llaman a la red:
`pytest tests/test_voz.py tests/test_webhook_voz.py`.

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

El **backend** no va en Vercel: Vercel solo sirve páginas estáticas y
funciones sin estado — el Agente 1 guarda `CONVERSACIONES` en memoria
mientras dura el proceso, y ahí el proceso no vive lo suficiente. Se
despliega en Render (ver abajo).

### Desplegar el backend en Render

Gratis, con HTTPS nativo (requisito de Telegram), y usa el `Dockerfile` del
repo tal cual — no hay que tocar nada de código.

> **Límite del plan gratis:** el servicio se duerme tras ~15 min sin
> tráfico; despertarlo tarda ~50 s. Mándale un mensaje al bot 2 minutos
> antes de una demo en vivo para que ya esté despierto.

**Opción A — con `render.yaml` (más rápido):**

1. render.com → *New* → *Blueprint* → conecta este repositorio.
2. Render lee `render.yaml` de la raíz y te pide solo las variables marcadas
   como secretas (`TELEGRAM_BOT_TOKEN`, `OPENROUTER_API_KEY`, `GROQ_API_KEY`,
   `SUPABASE_URL`, `SUPABASE_KEY`, `TELEGRAM_WEBHOOK_URL`,
   `CORS_ALLOW_ORIGINS`) — pégalas y confirma.
3. *Deploy* → te da una URL fija tipo `https://agroia-backend.onrender.com`.

**Opción B — manual, si prefieres ver cada campo:**

1. render.com → *New* → *Web Service* → conecta el repo.
2. Render detecta el `Dockerfile` solo (*Runtime* = Docker); deja el resto
   por defecto.
3. Plan **Free**.
4. Pestaña *Environment* → agrega las variables de la tabla de la sección 2
   (las 6 obligatorias + las opcionales que quieras fijar).
5. *Create Web Service*.

**Después del deploy, en cualquiera de las dos opciones:**

1. Verifica que las variables quedaron bien:
   `curl https://agroia-backend.onrender.com/` → `{"status":"ok", ...}`.
2. Pon esa URL como `TELEGRAM_WEBHOOK_URL` (agregando `/api/webhook/telegram`)
   en las variables de entorno del servicio en Render, y regístrala:
   ```bash
   python -m scripts.registrar_webhook
   ```
   (esto corre desde tu portátil, leyendo tu `.env` local — no en Render).
3. En Vercel, pon esa misma URL como `API_BASE_URL` (sección anterior).
4. En Render, pon el dominio de Vercel en `CORS_ALLOW_ORIGINS`.

Los dos servicios quedan apuntándose mutuamente: Vercel llama a Render vía
`apiBase`, y Render solo acepta peticiones del origen de Vercel.

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
│   │   ├── config.py                # única fuente de las variables de entorno
│   │   ├── text_utils.py            # normalización de texto compartida
│   │   └── voz.py                   # texto hablable + tono llanero neutro
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
│   │   ├── telegram_client.py       # enviar texto y notas de voz
│   │   ├── llm_client.py            # OpenRouter (Agentes 1 y 3)
│   │   ├── speech_to_text.py        # Groq Whisper — voz del productor a texto
│   │   └── text_to_speech.py        # Edge TTS — respuesta del bot a voz
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
│   ├── test_agente2.py              # estandarización y validación del Agente 2
│   ├── test_voz.py                  # texto hablable y tono llanero
│   └── test_webhook_voz.py          # cuándo el bot responde hablando
├── frontend/                        # SPA Angular 18, desplegado en Vercel (sección 8)
├── Dockerfile                       # imagen del backend, la usa Render
├── render.yaml                      # blueprint de Render (despliegue del backend)
├── .dockerignore
├── requirements.txt
├── supabase_schema.sql              # DDL de la tabla productos
├── .env.example
└── .gitignore
```

**Por qué está organizado así** — cada capa tiene una única responsabilidad
y solo puede depender de las de más abajo, nunca al revés:

1. `api/routers` recibe HTTP y decide qué agente llamar. No sabe nada de
   Supabase ni del LLM directamente.
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

Las pruebas del Agente 2 corren sin Supabase ni el LLM, porque las dos
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
- **Modelo configurable**: el Agente 1 y el Agente 3 comparten el mismo LLM,
  fijado en una sola variable (`LLM_MODEL`, hoy `minimax/minimax-m3:free` vía
  OpenRouter). Cambiar de modelo o de proveedor —incluso a uno de pago si el
  tier gratuito no alcanza en el día de la demo— es tocar esa única
  variable, porque ambos agentes pasan por `agroia/integrations/llm_client.py`.
  Catálogo completo: [openrouter.ai/models](https://openrouter.ai/models).
- **¿Por qué no DeepSeek?** Era el plan original (era gratis en OpenRouter),
  pero el catálogo de modelos `:free` cambia seguido — el slug
  `deepseek/deepseek-chat-v3.1:free` fue retirado del tier gratuito (queda
  solo la versión de pago). El diseño ya contaba con esto: cambiar de modelo
  es una sola variable de entorno, sin tocar código.
```
