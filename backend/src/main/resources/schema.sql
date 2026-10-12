CREATE TABLE IF NOT EXISTS ingredient (
    id TEXT PRIMARY KEY
);
CREATE TABLE IF NOT EXISTS ingredient_translation (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ingredient_id TEXT NOT NULL REFERENCES ingredient(id),
    locale TEXT NOT NULL,
    name TEXT NOT NULL,
    UNIQUE (ingredient_id, locale)
);
CREATE INDEX IF NOT EXISTS ingredient_translation_search ON ingredient_translation(locale, name);
CREATE TABLE IF NOT EXISTS ingredient_price (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ingredient_id TEXT NOT NULL REFERENCES ingredient(id),
    week_start TEXT NOT NULL,
    unit TEXT NOT NULL,
    amount_cents INTEGER NOT NULL CHECK (amount_cents >= 0),
    basis_quantity INTEGER CHECK (basis_quantity IS NULL OR basis_quantity > 0),
    UNIQUE (ingredient_id, week_start, unit)
);
CREATE TABLE IF NOT EXISTS migration_marker (name TEXT PRIMARY KEY);
