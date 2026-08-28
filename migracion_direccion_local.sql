-- Migración puntual: agrega la columna `direccion_local` a una tabla
-- `productos` que ya existe (dirección del local o finca donde el comprador
-- puede ir a comprar en persona; opcional).
--
-- Ejecutar en: Supabase -> SQL Editor -> New query -> Run.
-- Es idempotente: se puede correr las veces que sea.
--
-- Nota: si prefieres, correr `supabase_schema.sql` completo hace lo mismo
-- (también es idempotente y ya incluye esta columna).

alter table public.productos add column if not exists direccion_local text;
