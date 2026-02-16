-- Create room_status table
create table room_status (
  room_name text primary key,
  updated_at timestamptz not null default now(),
  played_at timestamptz
);

-- Enable RLS
alter table room_status enable row level security;

-- Allow anon to read all rows
create policy "anon can read room_status"
  on room_status for select
  to anon
  using (true);

-- Allow anon to insert rows
create policy "anon can insert room_status"
  on room_status for insert
  to anon
  with check (true);

-- Allow anon to update rows
create policy "anon can update room_status"
  on room_status for update
  to anon
  using (true)
  with check (true);
