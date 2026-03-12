"""
Migration script to convert business column from ARRAY to VARCHAR
"""
import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from infrastructure.persistence.postgresql.session import SessionLocal
from sqlalchemy import text


def migrate_business_column():
    """Convert business column from VARCHAR[] to VARCHAR"""

    with SessionLocal() as session:
        print("Checking current column type...")

        # Check current column type
        result = session.execute(text("""
            SELECT data_type
            FROM information_schema.columns
            WHERE table_name = 'category_profiles'
            AND column_name = 'business'
        """)).scalar()

        print(f"Current business column type: {result}")

        if result == 'ARRAY':
            print("\n" + "="*60)
            print("Converting business column from ARRAY to VARCHAR...")
            print("="*60)

            # First, show current data
            print("\nCurrent data:")
            current_data = session.execute(text("""
                SELECT category_id, business
                FROM category_profiles
                LIMIT 5
            """)).fetchall()
            for row in current_data:
                print(f"  {row}")

            # Convert array values to single strings (join all array elements)
            print("\nStep 1: Converting array values to strings...")
            session.execute(text("""
                ALTER TABLE category_profiles
                ALTER COLUMN business TYPE VARCHAR(50)
                USING CASE
                    WHEN business IS NULL THEN NULL
                    WHEN array_length(business, 1) IS NULL THEN NULL
                    ELSE array_to_string(business, '')
                END
            """))

            session.commit()
            print("✓ Column type converted successfully")

            # Verify the conversion
            print("\nVerifying conversion:")
            new_data = session.execute(text("""
                SELECT category_id, business
                FROM category_profiles
                LIMIT 5
            """)).fetchall()
            for row in new_data:
                print(f"  {row}")

            print("\n" + "="*60)
            print("Migration completed successfully!")
            print("="*60)

        elif result == 'character varying':
            print("✓ Column is already VARCHAR type - no migration needed")
        else:
            print(f"⚠ Unexpected column type: {result}")


if __name__ == "__main__":
    try:
        migrate_business_column()
    except Exception as e:
        print(f"\n✗ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
