# Standard library imports
import io

# Third-party imports
import pandas as pd


def export_to_csv(data: list) -> bytes:
    """
    Export data to CSV format.
    
    Args:
        data: List of dictionaries to export
    
    Returns:
        bytes: CSV data encoded as bytes
    """
    df = pd.DataFrame(data)
    return df.to_csv(index=False).encode('utf-8')


def export_to_parquet(data: list) -> bytes:
    """
    Export data to Parquet format using DuckDB (no pyarrow dependency).
    
    Args:
        data: List of dictionaries to export
    
    Returns:
        bytes: Parquet data as bytes
    """
    import duckdb
    
    # Create an in-memory DuckDB connection
    con = duckdb.connect(database=':memory:')
    
    # Create DataFrame from data
    df = pd.DataFrame(data)
    
    # Register DataFrame as a view
    con.register('df_view', df)
    
    # Use DuckDB to copy to parquet in memory
    # We write to a temporary file because DuckDB COPY TO requires a file path
    # But we can use a BytesIO buffer if we use the Python API's fetch_arrow_table (requires pyarrow)
    # OR we can write to a temp file and read it back.
    # Given the constraints, writing to a temp file is safest without pyarrow.
    
    import tempfile
    import os
    
    with tempfile.NamedTemporaryFile(delete=False, suffix='.parquet') as tmp:
        tmp_path = tmp.name
    
    try:
        con.execute(f"COPY (SELECT * FROM df_view) TO '{tmp_path}' (FORMAT PARQUET)")
        
        with open(tmp_path, 'rb') as f:
            parquet_bytes = f.read()
            
        return parquet_bytes
    finally:
        con.close()
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def validate_schema(schema: list) -> tuple[bool, str]:
    """
    Validate schema structure.
    
    Args:
        schema: List of column definitions
    
    Returns:
        tuple: (is_valid, error_message)
    """
    if not isinstance(schema, list):
        return False, "Schema must be a list"
    
    required_fields = ['name', 'type']
    for col in schema:
        if not isinstance(col, dict):
            return False, "Each column must be a dictionary"
        
        for field in required_fields:
            if field not in col:
                return False, f"Column missing required field: {field}"
    
    return True, ""


def prepare_file_for_analysis(uploaded_file):
    """
    Prepare uploaded file for AI analysis.
    
    Args:
        uploaded_file: Streamlit UploadedFile object
    
    Returns:
        tuple: (file_bytes, mime_type, filename)
    """
    file_bytes = uploaded_file.getvalue()
    mime_type = uploaded_file.type
    filename = uploaded_file.name
    
    return file_bytes, mime_type, filename
