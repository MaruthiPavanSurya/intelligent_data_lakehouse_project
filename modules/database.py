# Standard library imports
from typing import List, Optional

# Third-party imports
import duckdb
import pandas as pd

# Local imports
from config import DB_PATH


class DatabaseManager:
    """Centralized database operations manager for DuckDB."""
    
    def __init__(self, db_path: str = DB_PATH):
        """
        Initialize database manager.
        
        Args:
            db_path: Path to DuckDB database file
        """
        self.db_path = db_path
    
    def get_connection(self):
        """Get a database connection."""
        return duckdb.connect(self.db_path)
    
    def execute_query(self, query: str, params: Optional[tuple] = None) -> pd.DataFrame:
        """
        Execute a SQL query and return results.
        
        Args:
            query: SQL query string
            params: Optional query parameters
        
        Returns:
            DataFrame with query results or error message
        """
        try:
            conn = self.get_connection()
            if params:
                result = conn.execute(query, params).fetchdf()
            else:
                result = conn.execute(query).fetchdf()
            conn.close()
            return result
        except Exception as e:
            return str(e)
    
    def get_all_tables(self) -> pd.DataFrame:
        """
        Get list of all tables with row counts.
        
        Returns:
            DataFrame with table names and row counts
        """
        try:
            conn = self.get_connection()
            tables = conn.execute("SHOW TABLES").fetchdf()
            
            if tables.empty:
                conn.close()
                return pd.DataFrame(columns=['table_name', 'row_count'])
            
            table_list = []
            for table_name in tables['name']:
                count = conn.execute(f"SELECT COUNT(*) as cnt FROM {table_name}").fetchdf()['cnt'][0]
                table_list.append({'table_name': table_name, 'row_count': count})
            
            conn.close()
            return pd.DataFrame(table_list)
        except Exception as e:
            return pd.DataFrame(columns=['table_name', 'row_count'])
    
    def get_table_schema(self, table_name: str) -> Optional[pd.DataFrame]:
        """
        Get schema information for a specific table.
        
        Args:
            table_name: Name of the table
        
        Returns:
            DataFrame with column information or None
        """
        try:
            conn = self.get_connection()
            schema = conn.execute(f"DESCRIBE {table_name}").fetchdf()
            conn.close()
            return schema
        except Exception:
            return None
    
    def drop_table(self, table_name: str) -> bool:
        """
        Drop a table from the database.
        
        Args:
            table_name: Name of table to drop
        
        Returns:
            bool: True if successful
        """
        try:
            conn = self.get_connection()
            conn.execute(f"DROP TABLE IF EXISTS {table_name}")
            conn.close()
            return True
        except Exception:
            return False
    
    def drop_all_tables(self) -> bool:
        """
        Drop all tables from the database.
        
        Returns:
            bool: True if successful
        """
        try:
            tables_df = self.get_all_tables()
            conn = self.get_connection()
            
            for table_name in tables_df['table_name']:
                conn.execute(f"DROP TABLE IF EXISTS {table_name}")
            
            conn.close()
            return True
        except Exception:
            return False
    def create_dynamic_table(self, table_name: str, columns: list):
        """
        Creates a table in DuckDB dynamically based on the schema.
        
        Args:
            table_name: Name of the table to create
            columns: List of column definitions
        """
        conn = self.get_connection()
        try:
            # Build CREATE TABLE statement
            cols_sql = ", ".join([f"{c['name']} {c['type']}" for c in columns])
            # Add metadata columns AND raw_data for NoSQL support
            cols_sql += ", _ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, raw_data JSON"
            
            query = f"CREATE TABLE IF NOT EXISTS {table_name} ({cols_sql})"
            conn.execute(query)
        finally:
            conn.close()

    def load_dynamic_data(self, table_name: str, data: list):
        """
        Loads data into the dynamic table.
        
        Args:
            table_name: Target table name
            data: List of dictionaries to load
        """
        if not data:
            return
            
        conn = self.get_connection()
        try:
            # Convert list of dicts to DataFrame for easy loading
            df = pd.DataFrame(data)
            
            # Add raw_data column (as JSON string) for Hybrid Storage
            # We need json imported for this
            import json
            from datetime import datetime
            
            df['raw_data'] = df.apply(lambda row: json.dumps(row.to_dict()), axis=1)
            
            # Add metadata column
            df['_ingested_at'] = datetime.now()
            
            # Schema Evolution: Add any missing columns from the data
            existing_cols = conn.execute(
                f"SELECT column_name FROM information_schema.columns WHERE table_name = '{table_name}'"
            ).fetchdf()
            existing_col_names = set(existing_cols['column_name'].tolist()) if not existing_cols.empty else set()
            
            for col in df.columns:
                if col not in existing_col_names:
                    try:
                        # Add missing column as VARCHAR (safest default type)
                        conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {col} VARCHAR")
                    except:
                        pass # Column might have been added concurrently
            
            # DuckDB INSERT BY NAME handles column mapping automatically
            conn.execute(f"INSERT INTO {table_name} BY NAME SELECT * FROM df")
        finally:
            conn.close()
