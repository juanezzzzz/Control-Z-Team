-- ============================================================================
-- AgroIA Casanare — Esquema completo para Supabase
-- ----------------------------------------------------------------------------
-- Ejecutar TODO este archivo en:  Supabase → SQL Editor → New query → Run.
-- Es idempotente: se puede volver a correr sin romper datos ni objetos.
-- ============================================================================


-- 1. Extensiones -------------------------------------------------------------
--    unaccent  -> búsquedas que ignoran tildes ("platano" == "plátano")
--    pg_trgm   -> índices GIN para acelerar ILIKE / similitud
--    En Supabase las extensiones viven en el esquema "extensions".
create extension if not exists unaccent;
create extension if not exists pg_trgm;


-- 2. unaccent INMUTABLE ----------------------------------------------------
--    unaccent() por defecto es STABLE, no IMMUTABLE, y Postgres no permite
--    usar funciones no-inmutables dentro de un índice. Este wrapper lo
--    envuelve como IMMUTABLE (con search_path fijo) para poder indexar el
--    texto ya normalizado.
create or replace function public.immutable_unaccent(text)
returns text
language sql
immutable
parallel safe
strict
set search_path = extensions, public, pg_catalog
as $$
  select unaccent($1)
$$;


-- 3. Tabla principal -------------------------------------------------------
create table if not exists public.productos (
    id                uuid primary key default gen_random_uuid(),
    telegram_user_id  text not null,
    nombre_productor  text,
    telefono_contacto text,
    producto          text not null,
    cantidad          numeric,
    unidad            text,
    precio            numeric,
    ubicacion         text,
    estado            text not null default 'activo',   -- activo | vendido | inactivo
    raw_json          jsonb,               -- payload completo que arma el Agente 2
    created_at        timestamptz not null default now(),
    updated_at        timestamptz not null default now()
);


-- 4. Índices -------------------------------------------------------------
--    Trigram sobre el texto normalizado (minúsculas + sin tildes): es lo que
--    usa la búsqueda del Agente 3 con LIKE '%...%'.
create index if not exists idx_productos_producto_trgm
    on public.productos using gin (immutable_unaccent(lower(producto)) gin_trgm_ops);

create index if not exists idx_productos_ubicacion_trgm
    on public.productos using gin (immutable_unaccent(lower(coalesce(ubicacion, ''))) gin_trgm_ops);

create index if not exists idx_productos_estado      on public.productos (estado);
create index if not exists idx_productos_created_at  on public.productos (created_at desc);


-- 5. Trigger updated_at -------------------------------------------------
create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists trg_productos_updated_at on public.productos;
create trigger trg_productos_updated_at
before update on public.productos
for each row execute function public.set_updated_at();


-- 6. Función de búsqueda del Agente 3 (ventas) -------------------------
--    El backend la llama con supabase.rpc("buscar_productos", {...}).
--    - Ignora tildes y mayúsculas en producto y ubicación.
--    - Coincidencia bidireccional: "plátano hartón" encuentra "plátano" y
--      viceversa.
--    - Ordena: primero las que coinciden en ubicación, luego las más recientes.
create or replace function public.buscar_productos(
    p_producto  text default null,
    p_ubicacion text default null,
    p_limit     integer default 5
)
returns setof public.productos
language sql
stable
as $$
  with norm as (
    select
      nullif(trim(coalesce(p_producto,  '')), '') as q_prod,
      nullif(trim(coalesce(p_ubicacion, '')), '') as q_ubic
  )
  select p.*
  from public.productos p, norm n
  where p.estado = 'activo'
    and (
      n.q_prod is null
      or immutable_unaccent(lower(p.producto)) like '%' || immutable_unaccent(lower(n.q_prod)) || '%'
      or immutable_unaccent(lower(n.q_prod))   like '%' || immutable_unaccent(lower(p.producto)) || '%'
    )
    and (
      n.q_ubic is null
      or immutable_unaccent(lower(coalesce(p.ubicacion, ''))) like '%' || immutable_unaccent(lower(n.q_ubic)) || '%'
      or immutable_unaccent(lower(n.q_ubic)) like '%' || immutable_unaccent(lower(coalesce(p.ubicacion, ''))) || '%'
    )
  order by
    (
      n.q_ubic is not null
      and immutable_unaccent(lower(coalesce(p.ubicacion, ''))) like '%' || immutable_unaccent(lower(n.q_ubic)) || '%'
    ) desc,
    p.created_at desc
  limit greatest(coalesce(p_limit, 5), 1);
$$;


-- 7. Row Level Security -----------------------------------------------
--    El backend usa la service_role key y SALTA RLS — estas políticas solo
--    aplican al acceso directo desde el navegador (p. ej. Realtime del
--    catálogo usando la anon key en Angular).
alter table public.productos enable row level security;

drop policy if exists "lectura publica de ofertas activas" on public.productos;
create policy "lectura publica de ofertas activas"
  on public.productos
  for select
  using (estado = 'activo');


-- 8. Realtime -------------------------------------------------------
--    Para que el catálogo en Angular reciba tarjetas nuevas sin refrescar.
do $$
begin
  alter publication supabase_realtime add table public.productos;
exception
  when duplicate_object then null;   -- ya estaba en la publicación
end
$$;


-- 9. Datos de demo (OPCIONAL) --------------------------------------
--    Descomenta este bloque para tener ofertas de prueba y poder probar el
--    Agente 3 y el catálogo sin registrar nada por Telegram.
--
-- insert into public.productos
--   (telegram_user_id, nombre_productor, telefono_contacto, producto, cantidad, unidad, precio, ubicacion)
-- values
--   ('demo-1', 'María López',  '573001112233', 'plátano hartón', 200, 'kg',      2000, 'Yopal'),
--   ('demo-2', 'José Pérez',   '573004445566', 'yuca',           150, 'kg',      1500, 'Tauramena'),
--   ('demo-3', 'Ana Rodríguez','573007778899', 'leche',           80, 'litros',  2500, 'Aguazul'),
--   ('demo-4', 'Pedro Gómez',  '573002223344', 'queso campesino', 30, 'kg',     14000, 'Yopal');
