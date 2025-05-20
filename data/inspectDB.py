import sqlite3
import os

# --- IMPORTANT: Update this path if necessary ---
db_file_path = '/Users/fahadkiani/Desktop/development/Verba-main/goldenverba/data/CartonCapsData.sqlite'

# Check if the file exists
if not os.path.exists(db_file_path):
    print(f"Error: Database file not found at {db_file_path}")
    # Exit or handle error appropriately
else:
    print(f"Found database file at: {db_file_path}\n")
    try:
        # Connect to the SQLite database
        conn = sqlite3.connect(db_file_path)
        cursor = conn.cursor()

        # Get a list of all tables in the database
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        print("Tables in the database:")
        if not tables:
            print("  No tables found.")
        else:
            for table_name_tuple in tables:
                table_name = table_name_tuple[0]
                print(f"\n--- Table: {table_name} ---")

                # Get column information for each table
                cursor.execute(f"PRAGMA table_info('{table_name}');")
                columns = cursor.fetchall()
                print("  Columns (cid, name, type, notnull, default_value, pk):")
                for col in columns:
                    print(f"    {col}")

                # Fetch a few sample rows from each table (e.g., first 5)
                print(f"\n  Sample data from '{table_name}' (first 5 rows):")
                try:
                    cursor.execute(f"SELECT * FROM '{table_name}' LIMIT 5;")
                    sample_rows = cursor.fetchall()
                    if not sample_rows:
                        print("    No data in this table or table is empty.")
                    else:
                        # Print column names as header for sample data
                        col_names = [description[0] for description in cursor.description]
                        print(f"    Columns: {col_names}")
                        for row in sample_rows:
                            print(f"    {row}")
                except sqlite3.Error as e:
                    print(f"    Error fetching sample data from {table_name}: {e}")
                    
        # Close the connection
        conn.close()

    except sqlite3.Error as e:
        print(f"SQLite error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
