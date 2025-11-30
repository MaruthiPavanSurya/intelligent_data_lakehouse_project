# Standard library imports
import base64
import json
from datetime import datetime

# Third-party imports
import duckdb
import pandas as pd
from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI

# Local imports
from config import DB_PATH, GEMINI_MODEL_NAME, GOOGLE_API_KEY


def get_gemini_model():
    """Initializes the Gemini model based on config."""
    return ChatGoogleGenerativeAI(
        model=GEMINI_MODEL_NAME,
        google_api_key=GOOGLE_API_KEY,
        temperature=0
    )


def analyze_document(file_bytes: bytes, mime_type: str, file_name: str):
    """Analyzes a document to discover its schema and extract data."""
    llm = get_gemini_model()
    
    system_prompt = """You are an expert Data Engineer specializing in schema discovery and data extraction.

Your task: Analyze the provided unstructured data and extract structured, clean data.

Steps:
1. Identify the document type (e.g., "Invoice", "Sales Report", "Inventory List")
2. Suggest a descriptive table name in snake_case (e.g., "sales_transactions", "customer_invoices")
3. Extract ALL data into a list of JSON objects
4. Standardize column names to snake_case (e.g., "customer_name", "total_amount")
5. Assign appropriate SQL data types:
   - VARCHAR for text/strings
   - INTEGER for whole numbers
   - DOUBLE/FLOAT for decimals
   - DATE for dates (format: YYYY-MM-DD)
   - BOOLEAN for true/false values
6. Identify data quality issues:
   - Mixed date formats
   - Missing critical values
   - Inconsistent formatting
   - Duplicate entries

Output Format (JSON only, no markdown):
{
    "document_type": "Type of document",
    "table_name": "suggested_table_name",
    "columns": [
        {"name": "column_name", "type": "SQL_TYPE", "description": "Brief description"}
    ],
    "data": [
        {"column_name": "value", ...}
    ],
    "issues": ["Issue 1", "Issue 2"]
}

Requirements:
- Extract ALL rows/records, not just samples
- Maintain data accuracy and completeness
- Flag ANY quality concerns
- Return valid JSON only
"""
    
    content_parts = [
        {"type": "text", "text": system_prompt},
        {"type": "text", "text": f"Filename: {file_name}"}
    ]
    
    # Add image or text content
    if mime_type.startswith("image/"):
        content_parts.append({
            "type": "image_url",
            "image_url": {"url": f"data:{mime_type};base64,{base64.b64encode(file_bytes).decode('utf-8')}"}
        })
    else:
        content_parts.append({"type": "text", "text": file_bytes.decode("utf-8")})

    response = llm.invoke([HumanMessage(content=content_parts)])
    
    try:
        content = response.content.replace("```json", "").replace("```", "").strip()
        return json.loads(content)
    except Exception as e:
        print(f"Error parsing Gemini response: {e}")
        raise e


# ============================================================================
# NOTE: Database operations have been moved to modules/database.py
# This file now focuses solely on AI/LLM logic for extraction and cleaning.
# ============================================================================


def fix_data_quality_issues(data: list, issues: list):
    """Uses Gemini to automatically fix identified data quality issues."""
    llm = get_gemini_model()
    
    system_prompt = f"""You are an expert Data Quality Engineer.

Data Quality Issues Detected:
{json.dumps(issues, indent=2)}

Your task: Fix these issues in the provided data.

Cleaning Rules:
1. Standardize date formats to YYYY-MM-DD
2. Fix inconsistent formatting (capitalization, spacing)
3. Fill obvious missing values or use null
4. Remove duplicate entries
5. Correct clear typos and misspellings
6. Ensure numeric values are properly formatted
7. Standardize categorical values

IMPORTANT:
- Maintain all original data rows
- Only fix the specific issues mentioned
- Preserve data accuracy
- Return valid JSON only (no markdown)

Output Format:
[
    {{"column1": "cleaned_value1", "column2": "cleaned_value2"}},
    ...
]
"""
    
    content_parts = [
        {"type": "text", "text": system_prompt},
        {"type": "text", "text": f"Data to Clean: {json.dumps(data, indent=2)}"}
    ]
    
    response = llm.invoke([HumanMessage(content=content_parts)])
    
    try:
        content = response.content.replace("```json", "").replace("```", "").strip()
        return json.loads(content)
    except Exception as e:
        print(f"Error parsing Gemini response: {e}")
        raise e
