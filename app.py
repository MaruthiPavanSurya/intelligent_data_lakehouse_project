# Standard library imports
import json
import os

# Third-party imports
import pandas as pd
import streamlit as st

# Local imports
from config import GEMINI_MODEL_NAME, GOOGLE_API_KEY
from etl_logic import (
    analyze_document,
    fix_data_quality_issues,
)
from modules.chat_handler import ChatHandler
from modules.data_processor import export_to_csv, export_to_parquet
from modules.database import DatabaseManager
from modules.ui_components import (
    apply_custom_css,
    render_file_preview,
    render_sidebar_info,
    render_status_indicator,
    render_table_card,
)

# ============================================================================
# PAGE CONFIGURATION
# ============================================================================

st.set_page_config(
    page_title="Intelligent Lakehouse Adapter & Analyst",
    page_icon="🕸️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Apply custom CSS styling
apply_custom_css()

# ============================================================================
# INITIALIZATION
# ============================================================================
GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
GEMINI_MODEL_NAME = st.secrets["GEMINI_MODEL_NAME"]
# Check API Key
if not GOOGLE_API_KEY:
    st.error("`GOOGLE_API_KEY` not found. Please add it to `.env` file.")
    st.stop()

# Initialize session state
if "session_id" not in st.session_state:
    import uuid
    st.session_state.session_id = str(uuid.uuid4())

if "analysis_result" not in st.session_state:
    st.session_state.analysis_result = None
if "messages" not in st.session_state:
    st.session_state.messages = []
if "sample_selection" not in st.session_state:
    st.session_state.sample_selection = None

# Initialize managers with session-specific DB path
# This ensures each user has their own isolated lakehouse
session_db_path = f"lakehouse_{st.session_state.session_id}.db"
db_manager = DatabaseManager(db_path=session_db_path)
chat_handler = ChatHandler(GEMINI_MODEL_NAME, GOOGLE_API_KEY)

# ============================================================================
# HEADER
# ============================================================================

st.title("Intelligent Lakehouse Adapter & Analyst")
st.markdown(
    f"""
    **Powered by {GEMINI_MODEL_NAME} & DuckDB**
    
    Intelligent Lakehouse Adapter & Analyst seamlessly transforms your unstructured files (Images, CSVs, JSON) into a structured, queryable Data Lakehouse.
    Simply upload your data, let the AI discover the schema, and start asking questions in plain English.
    """
)
st.markdown("---")

# ============================================================================
# SIDEBAR
# ============================================================================

render_sidebar_info(GEMINI_MODEL_NAME)

with st.sidebar:
    st.markdown("---")
    st.markdown(
        """
        ### 📖 About
        **Intelligent Lakehouse Adapter & Analyst** bridges the gap between raw data and actionable insights.
        
        **Features:**
        - 🧠 **AI Schema Discovery**: Automatically detects structure from images and files.
        - 🧹 **Smart Data Cleaning**: Fixes quality issues with one click.
        - 💬 **Natural Language Querying**: Chat with your data using AI.
        - 📊 **Instant Visualizations**: Generate charts on the fly.
        """
    )
    st.markdown("---")
    st.subheader("Try Sample Files")
    
    sample_files = {
        "Invoice (Image)": "sample_invoice.jpg",
        "Sales Report (CSV)": "sample_sales_report.csv",
        "Inventory (JSON)": "sample_inventory.json"
    }
    
    selected_sample = st.radio(
        "Select a sample:",
        list(sample_files.keys()),
        index=None,
        key="sample_radio"
    )
    
    if selected_sample and st.button("Load Sample", type="primary"):
        st.session_state.sample_selection = sample_files[selected_sample]
        st.session_state.analysis_result = None
        st.rerun()

# ============================================================================
# TAB NAVIGATION
# ============================================================================

# Check if tables exist
tables_df = db_manager.get_all_tables()
has_tables = not tables_df.empty

# Create tabs
if has_tables:
    tab_ingest, tab_manage, tab_chat = st.tabs([
        "📥 Ingest Data",
        "📊 Manage Lakehouse",
        "💬 AI Analyst"
    ])
else:
    tab_ingest, tab_manage = st.tabs([
        "📥 Ingest Data",
        "📊 Manage Lakehouse"
    ])

# ============================================================================
# TAB 1: INGEST DATA
# ============================================================================

with tab_ingest:
    st.header("Data Ingestion & Schema Discovery")
    st.markdown("Upload any file and let AI discover its structure automatically.")
    
    # File handling
    uploaded_file = None
    file_bytes = None
    
    # Handle sample file selection
    if st.session_state.get("sample_selection"):
        sample_path = st.session_state.sample_selection
        if os.path.exists(sample_path):
            with open(sample_path, "rb") as f:
                file_bytes = f.read()
            
            # Determine MIME type
            if sample_path.endswith(('.jpg', '.jpeg')):
                mime_type = 'image/jpeg'
            elif sample_path.endswith('.csv'):
                mime_type = 'text/csv'
            elif sample_path.endswith('.json'):
                mime_type = 'application/json'
            else:
                mime_type = 'application/octet-stream'
            
            # Create file-like object
            class SampleFile:
                def __init__(self, name, type, bytes_data):
                    self.name = name
                    self.type = type
                    self._bytes = bytes_data
                def getvalue(self):
                    return self._bytes
            
            uploaded_file = SampleFile(sample_path, mime_type, file_bytes)
            st.success(f"Using sample: **{sample_path}**")
            
            if st.button("Clear Sample"):
                st.session_state.sample_selection = None
                st.session_state.analysis_result = None
                st.rerun()
        else:
            st.warning(f"Sample file `{sample_path}` not found.")
    
    # File uploader (always visible)
    st.markdown("---")
    st.subheader("Or Upload Your Own File")
    user_uploaded = st.file_uploader(
        "Browse Files",
        type=["png", "jpg", "jpeg", "csv", "json", "txt"],
        key="user_file_upload"
    )
    
    # User upload takes precedence
    if user_uploaded:
        uploaded_file = user_uploaded
        file_bytes = None
    
    # File preview
    if uploaded_file:
        st.markdown("---")
        if file_bytes is None:
            file_bytes = uploaded_file.getvalue()
        
        render_file_preview(uploaded_file, file_bytes)
        
        st.markdown("---")
        
        # Analyze button
        if st.button("Analyze & Discover Schema", type="primary"):
            with st.spinner("AI is analyzing structure..."):
                try:
                    result = analyze_document(
                        file_bytes,
                        uploaded_file.type,
                        uploaded_file.name
                    )
                    st.session_state.analysis_result = result
                    st.rerun()
                except Exception as e:
                    st.error(f"Analysis Failed: {e}")
                    import traceback
                    st.code(traceback.format_exc())
    
    # Show analysis results
    if st.session_state.analysis_result:
        result = st.session_state.analysis_result
        
        st.markdown("---")
        st.subheader("Analysis Results")
        
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.info(f"**Document Type:** {result.get('document_type', 'Unknown')}")
            st.success(f"**Suggested Table:** `{result.get('table_name', 'data_table')}`")
           
            # Data quality issues
            if result.get("issues"):
                st.warning("**Data Quality Issues:**")
                for issue in result["issues"]:
                    st.write(f"- {issue}")
                
                if st.button("Auto-Fix with AI", type="primary"):
                    with st.spinner("AI is cleaning the data..."):
                        try:
                            cleaned_data = fix_data_quality_issues(
                                result["data"],
                                result["issues"]
                            )
                            st.session_state.analysis_result["data"] = cleaned_data
                            st.session_state.analysis_result["issues"] = []
                            st.success("Data Cleaned!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Fix Failed: {e}")
            else:
                st.success("No data quality issues")
        
        with col2:
            st.markdown("### Data Preview")
            json_data = json.dumps(result["data"], indent=2)
            edited_json = st.text_area(
                "Edit Data (JSON)",
                value=json_data,
                height=300
            )
            
            st.markdown("### Schema Definition")
            json_schema = json.dumps(result["columns"], indent=2)
            edited_schema_json = st.text_area(
                "Edit Schema (JSON)",
                value=json_schema,
                height=200
            )
        
        st.markdown("---")
        
        # Action buttons
        col_action1, col_action2, col_action3 = st.columns(3)
        
        # Check if cleansing is required
        has_issues = len(result.get("issues", [])) > 0
        
        with col_action1:
            if st.button(
                "Approve & Load to Lakehouse",
                type="primary",
                use_container_width=True,
                disabled=has_issues,
                help="Fix data quality issues before loading" if has_issues else None
            ):
                with st.spinner("Loading data..."):
                    try:
                        final_data = json.loads(edited_json)
                        final_schema = json.loads(edited_schema_json)
                        table_name = result.get('table_name', 'data_table')
                        
                        # Use db_manager methods
                        db_manager.create_dynamic_table(table_name, final_schema)
                        db_manager.load_dynamic_data(table_name, final_data)
                        
                        st.toast(f"Data loaded into `{table_name}`!")
                        st.session_state.analysis_result = None
                        st.rerun()
                    except Exception as e:
                        st.error(f"Load Failed: {e}")
        
        with col_action2:
            if edited_json:
                try:
                    final_data = json.loads(edited_json)
                    csv = export_to_csv(final_data)
                    st.download_button(
                        label="Download as CSV",
                        data=csv,
                        file_name=f"{result.get('table_name', 'data')}.csv",
                        mime="text/csv",
                        use_container_width=True,
                        disabled=has_issues,
                        help="Fix data quality issues before downloading" if has_issues else None
                    )
                except:
                    pass
        
        with col_action3:
            if edited_json:
                try:
                    final_data = json.loads(edited_json)
                    parquet = export_to_parquet(final_data)
                    st.download_button(
                        label="Download as Parquet",
                        data=parquet,
                        file_name=f"{result.get('table_name', 'data')}.parquet",
                        mime="application/octet-stream",
                        use_container_width=True,
                        disabled=has_issues,
                        help="Fix data quality issues before downloading" if has_issues else None
                    )
                except:
                    pass

# ============================================================================
# TAB 2: MANAGE LAKEHOUSE
# ============================================================================

with tab_manage:
    st.header("Data Lakehouse Management")
    
    if tables_df.empty:
        st.info("No tables in the lakehouse yet. Upload some data to get started!")
    else:
        col1, col2 = st.columns([3, 1])
        with col1:
            st.success(f"**{len(tables_df)} table(s)** in the lakehouse")
        with col2:
            if st.button("Clear All Tables", type="secondary"):
                db_manager.drop_all_tables()
                st.success("All tables deleted!")
                st.rerun()
        
        st.markdown("---")
        
        # Display tables
        for idx, row in tables_df.iterrows():
            table_name = row['table_name']
            row_count = row['row_count']
            
            render_table_card(table_name, row_count)
            
            # Show schema
            with st.expander(f"View Schema for `{table_name}`"):
                schema_df = db_manager.get_table_schema(table_name)
                if schema_df is not None:
                    st.markdown(schema_df.to_html(index=False), unsafe_allow_html=True)
                
                # Delete button in expander
                if st.button("Delete Table", key=f"delete_expand_{table_name}", type="secondary"):
                    db_manager.drop_table(table_name)
                    st.success(f"Deleted `{table_name}`")
                    st.rerun()
            
            st.markdown("---")

# ============================================================================
# TAB 3: AI ANALYST (CHAT)
# ============================================================================

if has_tables:
    with tab_chat:
        st.header("AI Data Analyst")
        
        # Clear chat button
        if st.button("Clear Chat History"):
            st.session_state.messages = []
            st.rerun()
        
        # Multi-table selector
        table_names = tables_df['table_name'].tolist()
        selected_tables = st.multiselect(
            "Select Table(s) to Query:",
            table_names,
            default=[table_names[0]] if table_names else []
        )
        
        if selected_tables:
            if len(selected_tables) == 1:
                st.success(f"Connected to: `{selected_tables[0]}`")
            else:
                st.success(
                    f"Connected to {len(selected_tables)} tables: "
                    f"{', '.join([f'`{t}`' for t in selected_tables])}"
                )
                
                # Join analysis
                st.markdown("### Join Analysis")
                join_info = []
                metadata_cols = {'_ingested_at', 'raw_data'}
                
                for i, table1 in enumerate(selected_tables):
                    schema1 = db_manager.get_table_schema(table1)
                    cols1 = set(schema1['column_name'].tolist()) if schema1 is not None else set()
                    cols1 = cols1 - metadata_cols
                    
                    for table2 in selected_tables[i+1:]:
                        schema2 = db_manager.get_table_schema(table2)
                        cols2 = set(schema2['column_name'].tolist()) if schema2 is not None else set()
                        cols2 = cols2 - metadata_cols
                        
                        common_cols = cols1.intersection(cols2)
                        if common_cols:
                            join_info.append({
                                'table1': table1,
                                'table2': table2,
                                'common_columns': ', '.join(common_cols)
                            })
                
                if join_info:
                    st.success("Tables are joinable!")
                    for ji in join_info:
                        st.markdown(
                            f"- `{ji['table1']}` ⟷ `{ji['table2']}` "
                            f"on: **{ji['common_columns']}**"
                        )
                else:
                    st.warning("No common columns found. Tables may not be directly joinable.")
            
            # Show schemas
            with st.expander("View Table Schemas"):
                for table in selected_tables:
                    st.markdown(f"#### `{table}`")
                    schema_df = db_manager.get_table_schema(table)
                    if schema_df is not None:
                        st.markdown(schema_df.to_html(index=False), unsafe_allow_html=True)
                    st.markdown("---")
            
            # Chat interface
            st.markdown("---")
            st.subheader("Ask questions about your data")
            
            # Display chat history
            for message in st.session_state.messages:
                with st.chat_message(message["role"]):
                    if message["role"] == "assistant":
                        if "nl_response" in message:
                            st.markdown(message["nl_response"])
                        
                        # Render chart if available
                        if "chart_code" in message and "result_html" in message:
                            try:
                                # Get the data from the stored HTML
                                import io
                                from pandas import read_html
                                
                                # Parse HTML back to DataFrame
                                html_io = io.StringIO(message["result_html"])
                                data = read_html(html_io)[0]
                                
                                # Execute chart code
                                import plotly.express as px
                                exec_globals = {"px": px, "data": data}
                                exec(message["chart_code"], exec_globals)
                                
                                # Display the figure if it was created
                                if "fig" in exec_globals:
                                    st.plotly_chart(exec_globals["fig"], use_container_width=True)
                            except Exception as e:
                                st.warning(f"Could not render visualization: {str(e)}")
                        
                        if "query" in message:
                            with st.expander("View SQL Query & Raw Data"):
                                st.code(message["query"], language="sql")
                                if "result_html" in message:
                                    st.markdown(message["result_html"], unsafe_allow_html=True)
                    else:
                        st.markdown(message["content"])
            
            # Chat input
            user_input = st.chat_input(
                "Ex: What is the total revenue?" if len(selected_tables) == 1
                else "Ex: Join the tables and show summary"
            )
            
            # Process new message
            if user_input:
                st.session_state.messages.append({"role": "user", "content": user_input})
                
                with st.status("Processing your question...", expanded=True) as status:
                    st.write("Generating SQL query...")
                    
                    # Build schema context
                    schema_context = ""
                    for table in selected_tables:
                        schema_info = db_manager.get_table_schema(table).to_string()
                        schema_context += f"\nTable: {table}\n{schema_info}\n"
                    
                    # Generate SQL
                    sql_query = chat_handler.generate_sql_query(user_input, schema_context)
                    
                    st.write(f"Executing query: `{sql_query}`")
                    
                    # Execute query
                    result_df = db_manager.execute_query(sql_query)
                    
                    if isinstance(result_df, pd.DataFrame):
                        st.write("Generating natural language response...")
                        
                        # Generate NL response (and chart code if visualization requested)
                        nl_response, chart_code = chat_handler.generate_nl_response(
                            user_input,
                            sql_query,
                            result_df
                        )
                        
                        # Save to history
                        message_data = chat_handler.create_message(
                            "assistant",
                            nl_response,
                            nl_response=nl_response,
                            query=sql_query,
                            result_html=result_df.to_html(index=False)
                        )
                        
                        if chart_code:
                            message_data["chart_code"] = chart_code
                        
                        st.session_state.messages.append(message_data)
                        
                        status.update(label="Complete!", state="complete", expanded=False)
                    else:
                        error_msg = f"Query Error: {result_df}"
                        st.session_state.messages.append(
                            chat_handler.create_message("assistant", error_msg)
                        )
                        status.update(label="Error occurred", state="error")
                
                st.rerun()
