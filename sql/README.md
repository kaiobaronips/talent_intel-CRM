# Supabase Postgres Bootstrap

Apply the base schema in Supabase SQL editor or with `psql`:

```sql
\i sql/0001_initial_schema.sql
```

Environment variable used by the application:

- `SUPABASE_DB_URL`

Expected format:

```text
postgresql://postgres:<password>@<host>:5432/postgres
```
