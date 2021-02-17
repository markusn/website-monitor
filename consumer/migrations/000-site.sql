CREATE TABLE IF NOT EXISTS site (
    id serial PRIMARY KEY,
    url text UNIQUE NOT NULL,
    data JSONB
); 