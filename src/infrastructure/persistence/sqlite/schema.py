# ---------------------------------------------------------------------
# Standard library
# ---------------------------------------------------------------------

# ---------------------------------------------------------------------
# Third-party libraries
# ---------------------------------------------------------------------

# ---------------------------------------------------------------------
# Internal application imports
# ---------------------------------------------------------------------


def init_schema(conn) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS categories (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            parent_id TEXT NULL,
            FOREIGN KEY(parent_id) REFERENCES categories(id)
        );

        CREATE TABLE IF NOT EXISTS category_profiles (
            category_id TEXT PRIMARY KEY,
            keywords_json TEXT NOT NULL,
            allowed_genders_json TEXT NULL,
            allowed_business_types_json TEXT NULL,
            FOREIGN KEY(category_id) REFERENCES categories(id)
        );

        CREATE TABLE IF NOT EXISTS products (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            keywords_json TEXT NOT NULL,
            gender TEXT NULL,
            business_type TEXT NULL
        );

        CREATE TABLE IF NOT EXISTS product_category_exclusions (
            product_id TEXT NOT NULL,
            category_id TEXT NOT NULL,
            reason TEXT NOT NULL,
            PRIMARY KEY(product_id, category_id),
            FOREIGN KEY(product_id) REFERENCES products(id),
            FOREIGN KEY(category_id) REFERENCES categories(id)
        );

        CREATE TABLE IF NOT EXISTS faiss_id_map (
            faiss_id INTEGER PRIMARY KEY,
            entity_uuid TEXT UNIQUE NOT NULL
        );

        """
    )
    conn.commit()
