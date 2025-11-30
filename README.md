# Intelligent Document Lakehouse

A GenAI-powered data engineering platform that transforms unstructured documents into structured data using **Gemini** and **DuckDB**.

## Features

- **Universal Data Adapter**: Automatically extracts structured data from PDF invoices
- **Schema Enforcement**: Pydantic-based data validation
- **Lakehouse Storage**: DuckDB for analytics-ready data
- **Real-time Analytics**: Live dashboards showing data quality metrics

## Tech Stack

- **Frontend**: Streamlit
- **GenAI**: Google Gemini (configurable model)
- **Database**: DuckDB
- **Orchestration**: LangChain
- **Deployment**: Docker

## Quick Start

### Option 1: Docker (Recommended)

```bash
# 1. Set your API key in .env
echo "GOOGLE_API_KEY=your_key_here" > .env

# 2. Build and run
docker-compose up --build

# 3. Open http://localhost:8501
```

### Option 2: Virtual Environment

```bash
# 1. Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set your API key
echo "GOOGLE_API_KEY=your_key_here" > .env

# 4. Run the app
streamlit run app.py
```

## Configuration

Edit `.env` to customize:

```
GOOGLE_API_KEY=your_api_key_here
GEMINI_MODEL_NAME=gemini-1.5-flash  # or gemini-1.5-pro
```

## Usage

1. Navigate to the **Ingest** tab
2. Upload an invoice image (JPG/PNG)
3. Click **Process Document**
4. View extracted data in the **Lakehouse** tab
5. See analytics in the **Analytics** tab

## Project Structure

```
document_lakehouse/
├── app.py              # Streamlit UI
├── etl_logic.py        # Extraction and loading logic
├── schema.py           # Pydantic data models
├── config.py           # Configuration management
├── Dockerfile          # Container definition
├── docker-compose.yml  # Orchestration
└── requirements.txt    # Python dependencies
```

## For Portfolio

This project demonstrates:
- **Data Engineering**: ETL pipeline design
- **GenAI Integration**: Multimodal LLM usage
- **Cloud DevOps**: Containerization and IaC
- **Data Quality**: Schema validation and governance
