# Standard library imports
import io

# Third-party imports
import pandas as pd
import streamlit as st
from PIL import Image


def render_file_preview(uploaded_file, file_bytes):
    """
    Render a preview of the uploaded file based on its type.
    
    Args:
        uploaded_file: Streamlit UploadedFile object
        file_bytes: File content as bytes
    """
    st.subheader("File Preview")
    
    # Image preview
    if uploaded_file.type.startswith('image/'):
        image = Image.open(io.BytesIO(file_bytes))
        st.image(image, caption=uploaded_file.name, width=400)
    
    # CSV preview
    elif uploaded_file.type == 'text/csv' or uploaded_file.name.endswith('.csv'):
        df_preview = pd.read_csv(io.BytesIO(file_bytes))
        st.markdown(f"**Rows:** {len(df_preview)} | **Columns:** {len(df_preview.columns)}")
        st.markdown(df_preview.head(10).to_html(index=False), unsafe_allow_html=True)
    
    # JSON preview
    elif uploaded_file.type == 'application/json' or uploaded_file.name.endswith('.json'):
        import json
        json_preview = json.loads(file_bytes.decode('utf-8'))
        st.json(json_preview if isinstance(json_preview, list) and len(json_preview) <= 5 else json_preview[:5])
    
    # Text preview
    else:
        text_content = file_bytes.decode('utf-8')
        st.text(text_content[:500] + "..." if len(text_content) > 500 else text_content)


def render_table_card(table_name, row_count, on_delete=None):
    """
    Render a table info card with metrics and actions.
    
    Args:
        table_name: Name of the table
        row_count: Number of rows in the table
        on_delete: Callback function for delete action
    
    Returns:
        bool: True if delete button was clicked
    """
    col1, col2, col3 = st.columns([3, 2, 1])
    
    with col1:
        st.markdown(f"### `{table_name}`")
    with col2:
        st.metric("Rows", f"{row_count:,}")
    with col3:
        delete_clicked = st.button("Delete", key=f"delete_{table_name}", type="secondary")
        if delete_clicked and on_delete:
            on_delete(table_name)
            return True
    
    return False


def render_status_indicator(label, status="info"):
    """
    Render a colored status indicator.
    
    Args:
        label: Text to display
        status: Status type ('success', 'error', 'warning', 'info')
    """
    status_colors = {
        "success": "🟢",
        "error": "🔴",
        "warning": "🟡",
        "info": "🔵"
    }
    
    icon = status_colors.get(status, "⚪")
    st.markdown(f"{icon} {label}")


def render_action_buttons(actions, use_container_width=True):
    """
    Render a row of action buttons.
    
    Args:
        actions: List of dicts with 'label', 'on_click', 'type', etc.
        use_container_width: Whether buttons should fill container width
    
    Returns:
        str: Label of clicked button, or None
    """
    cols = st.columns(len(actions))
    
    for idx, action in enumerate(actions):
        with cols[idx]:
            if st.button(
                action['label'],
                type=action.get('type', 'secondary'),
                use_container_width=use_container_width,
                key=action.get('key')
            ):
                if 'on_click' in action:
                    action['on_click']()
                return action['label']
    
    return None


def apply_custom_css():
    """Apply custom CSS styling to the Streamlit app."""
    st.markdown("""
    <style>
        /* Main content area */
        .main .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
        }
        
        /* Headers */
        h1 {
            color: #1f77b4;
            padding-bottom: 0.5rem;
            border-bottom: 2px solid #1f77b4;
        }
        
        h2 {
            color: #2c3e50;
            margin-top: 1.5rem;
        }
        
        h3 {
            color: #34495e;
        }
        
        /* Tables - Simple styling for readability */
        table {
            border-collapse: collapse;
            width: 100%;
        }
        
        table th {
            background-color: #f0f0f0;
            color: #333;
            padding: 8px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }
        
        table td {
            padding: 8px;
            border-bottom: 1px solid #eee;
        }
        
        /* Chat messages */
        .stChatMessage {
            border-radius: 8px;
            padding: 1rem;
            margin-bottom: 0.5rem;
        }
        
        /* Buttons */
        .stButton button {
            border-radius: 4px;
            transition: all 0.3s ease;
        }
        
        .stButton button:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.15);
        }
        
        /* Metrics */
        [data-testid="stMetricValue"] {
            font-size: 2rem;
            font-weight: 600;
        }
        
        /* Expanders */
        .streamlit-expanderHeader {
            background-color: #f8f9fa;
            border-radius: 4px;
        }
        
        /* Status box */
        .stStatus {
            border-radius: 8px;
        }
    </style>
    """, unsafe_allow_html=True)


def render_sidebar_info(model_name):
    """Render sidebar with system information."""
    with st.sidebar:
        st.header("System Status")
        render_status_indicator("System Online", "success")
        st.info(f"Model: `{model_name}`")
