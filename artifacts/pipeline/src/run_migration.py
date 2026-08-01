#!/usr/bin/env python3
"""
Run the asset migration.
Usage: python run_migration.py
"""

import asyncio
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

import asyncpg


async def run_migration():
    """Run the asset migration."""
    # Load env
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    key, _, value = line.partition("=")
                    os.environ[key] = value.strip('"')
    
    db_url = os.environ.get("COCKROACHDB_URL")
    if not db_url:
        print("❌ COCKROACHDB_URL not found in environment")
        sys.exit(1)
    
    print(f"Connecting to database...")
    
    # Parse URL
    import urllib.parse
    parsed = urllib.parse.urlparse(db_url)
    
    conn = await asyncpg.connect(
        host=parsed.hostname,
        port=parsed.port or 5432,
        user=parsed.username,
        password=parsed.password,
        database=parsed.path.lstrip("/") or "defaultdb",
        ssl="require",
    )
    
    print("✅ Connected to CockroachDB")
    
    # Read migration file
    migration_path = os.path.join(os.path.dirname(__file__), "..", "migrations", "001_add_assets.sql")
    with open(migration_path) as f:
        migration_sql = f.read()
    
    print(f"\n📦 Running migration: {migration_path}")
    
    # Split by semicolons and execute
    # But don't split inside function definitions
    statements = [s.strip() for s in migration_sql.split(";") if s.strip() and not s.strip().startswith("--")]
    
    executed = 0
    errors = []
    
    # Track created objects for logging
    created_tables = set()
    created_indexes = set()
    
    for stmt in statements:
        if not stmt.strip():
            continue
        try:
            await conn.execute(stmt)
            executed += 1
            
            # Track what was created
            stmt_upper = stmt.upper()
            if "CREATE TABLE" in stmt_upper:
                # Extract table name
                parts = stmt_upper.split("CREATE TABLE")
                if len(parts) > 1:
                    name = parts[1].split("(")[0].replace("IF NOT EXISTS", "").strip()
                    if name and name not in created_tables:
                        created_tables.add(name)
                        print(f"  ✅ Table: {name}")
            elif "CREATE INDEX" in stmt_upper:
                for keyword in ["CREATE INDEX", "CREATE UNIQUE INDEX"]:
                    if keyword in stmt_upper:
                        parts = stmt_upper.split(keyword)
                        if len(parts) > 1:
                            name = parts[1].split("(")[0].replace("IF NOT EXISTS", "").strip()
                            if name and name not in created_indexes:
                                created_indexes.add(name)
                                print(f"  ✅ Index: {name[:40]}")
                        break
            elif "ALTER TABLE" in stmt_upper and "ADD CONSTRAINT" in stmt_upper:
                name = stmt_upper.split("ADD CONSTRAINT")[1].split()[0].strip()
                print(f"  ✅ Constraint: {name[:40]}")
            elif "CREATE VIEW" in stmt_upper:
                name = stmt_upper.split("CREATE VIEW")[1].split("AS")[0].replace("IF NOT EXISTS", "").strip()
                print(f"  ✅ View: {name[:40]}")
                            
        except Exception as e:
            err_str = str(e)
            # Ignore "already exists" errors
            if "already exists" in err_str.lower() or "duplicate" in err_str.lower():
                print(f"  ⏭️  Skipped (already exists)")
            elif "does not exist" in err_str.lower() or "UNDEFINED" in err_str:
                # These are expected for IF NOT EXISTS - just skip
                print(f"  ⏭️  Skipped ({err_str[:50]}...)")
            else:
                errors.append((stmt[:80], err_str))
                print(f"  ❌ Error: {err_str[:80]}")
    
    print(f"\n📊 Migration complete:")
    print(f"   Executed: {executed} statements")
    print(f"   Errors: {len(errors)}")
    
    if errors:
        print("\n⚠️  Errors encountered:")
        for stmt, err in errors[:5]:
            print(f"   - {stmt}...: {err[:60]}")
    
    # Verify tables exist
    print("\n🔍 Verifying tables...")
    tables = await conn.fetch("""
        SELECT table_name FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_name IN ('assets', 'asset_relationships', 'storage_usage')
    """)
    
    for t in tables:
        print(f"  ✅ Table: {t['table_name']}")
    
    await conn.close()
    print("\n✅ Migration complete!")
    return len(errors) == 0


if __name__ == "__main__":
    success = asyncio.run(run_migration())
    sys.exit(0 if success else 1)
