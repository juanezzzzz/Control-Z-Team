-- Esquema inicial para AgroIA Casanare
-- Ejecutar en el SQL Editor de Supabase

create table if not exists productos (
    id uuid primary key default gen_random_uuid(),
    telegram_user_id text not null,
    nombre_productor text,
    telefono_contacto text,
    producto text not null,       -- nombre canónico ("plátano"), no lo que se escribió
    cantidad numeric,
    unidad text,                  -- unidad canónica ("arroba", "kg", "L")
    precio numeric,               -- precio por `unidad`, tal como lo dijo el productor
    ubicacion text,
    estado text not null default 'activo', -- activo | vendido | inactivo

    -- Campos que estandariza el Agente 2 (sección 3 del documento).
    -- Los tres derivados quedan en null cuando la unidad no tiene una
    -- equivalencia fija (bulto, racimo, canasta): ver normalizacion.py.
    unidad_original text,         -- lo que escribió el productor ("arrobitas")
    categoria_unidad text,        -- peso | volumen | conteo
    unidad_base text,             -- kg | L | unidad
    cantidad_base numeric,        -- cantidad convertida a `unidad_base`
    precio_por_unidad_base numeric, -- permite comparar ofertas en unidades distintas
    municipio text,               -- municipio de Casanare reconocido, si aplica

    raw_json jsonb,               -- salida cruda del Agente 1, para auditoría
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

-- Migración para una tabla `productos` que ya existía antes del Agente 2
-- estandarizado. Es idempotente: se puede correr las veces que sea.
alter table productos add column if not exists unidad_original text;
alter table productos add column if not exists categoria_unidad text;
alter table productos add column if not exists unidad_base text;
alter table productos add column if not exists cantidad_base numeric;
alter table productos add column if not exists precio_por_unidad_base numeric;
alter table productos add column if not exists municipio text;

-- Índices para acelerar las búsquedas del Agente 3 (ventas)
create index if not exists idx_productos_producto on productos using gin (to_tsvector('spanish', producto));
create index if not exists idx_productos_ubicacion on productos using gin (to_tsvector('spanish', ubicacion));
create index if not exists idx_productos_estado on productos (estado);
-- El municipio ya viene normalizado por el Agente 2, así que un índice
-- B-tree basta para filtrar el catálogo por zona desde Angular.
create index if not exists idx_productos_municipio on productos (municipio);

-- Un productor no puede tener dos ofertas ACTIVAS del mismo producto. El
-- Agente 2 ya revisa antes de insertar, pero esa revisión es un read-then-write:
-- si llegan dos mensajes casi simultáneos del mismo campesino, ambos pasarían.
-- Este índice parcial cierra esa ventana; el agente atrapa la violación y la
-- resuelve como lo que era: una corrección de la misma oferta.
-- Es parcial (`where estado = 'activo'`) a propósito: el histórico de ofertas
-- ya vendidas o inactivas sí puede repetir producto.
create unique index if not exists idx_productos_oferta_activa_unica
    on productos (telegram_user_id, producto)
    where estado = 'activo';

-- Habilitar Realtime (Database > Replication > productos) para que Angular
-- reciba las tarjetas nuevas sin refrescar la página.

-- ---------------------------------------------------------------------------
-- Row Level Security
-- ---------------------------------------------------------------------------
-- Sin esto, cualquiera con la anon key (que viaja en el bundle de Angular,
-- o sea que es pública) podría borrar el catálogo entero.
--
-- El backend usa la `service_role key`, que ignora RLS por diseño: por eso
-- todas las escrituras siguen funcionando desde FastAPI. El navegador solo
-- puede LEER las ofertas activas.
alter table productos enable row level security;

drop policy if exists "lectura publica de ofertas activas" on productos;
create policy "lectura publica de ofertas activas"
  on productos for select
  to anon, authenticated
  using (estado = 'activo');

-- No se crean políticas de insert/update/delete a propósito: toda escritura
-- pasa por el Agente 2, nunca directo desde el navegador.

-- Trigger simple para mantener updated_at al día
create or replace function set_updated_at()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

drop trigger if exists trg_productos_updated_at on productos;
create trigger trg_productos_updated_at
before update on productos
for each row execute function set_updated_at();
