-- Esquema inicial para AgroIA Casanare
-- Ejecutar en el SQL Editor de Supabase

create table if not exists productos (
    id uuid primary key default gen_random_uuid(),
    telegram_user_id text not null,
    nombre_productor text,
    telefono_contacto text,
    producto text not null,
    cantidad numeric,
    unidad text,
    precio numeric,
    ubicacion text,
    estado text not null default 'activo', -- activo | vendido | inactivo
    raw_json jsonb,               -- payload completo generado por el Agente 2
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

-- Índices para acelerar las búsquedas del Agente 3 (ventas)
create index if not exists idx_productos_producto on productos using gin (to_tsvector('spanish', producto));
create index if not exists idx_productos_ubicacion on productos using gin (to_tsvector('spanish', ubicacion));
create index if not exists idx_productos_estado on productos (estado);

-- Habilitar Realtime (Database > Replication > productos) para que Angular
-- reciba las tarjetas nuevas sin refrescar la página.

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
