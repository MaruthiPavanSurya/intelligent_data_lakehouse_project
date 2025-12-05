# Standard library imports
from typing import Dict, List, Tuple

# Third-party imports
import pandas as pd
from langchain_google_genai import ChatGoogleGenerativeAI


class ChatHandler:
    """Handles chat operations including SQL generation and natural language responses."""
    
    def __init__(self, model_name: str, api_key: str):
        """
        Initialize the chat handler.
        
        Args:
            model_name: Name of the Gemini model to use
            api_key: Google API key for Gemini
        """
        self.llm = ChatGoogleGenerativeAI(
            model=model_name,
            google_api_key=api_key,
            temperature=0
        )
    
    def generate_sql_query(self, user_question: str, schema_context: str) -> str:
        """
        Generate SQL query from natural language question.
        
        Args:
            user_question: User's question in natural language
            schema_context: Database schema information
        
        Returns:
            str: Generated SQL query
        """
        sql_prompt = f"""You are an expert Data Analyst using DuckDB SQL.

Available Tables and Schemas:
{schema_context}

User Question: {user_question}

Task: Generate a precise SQL query to answer the user's question.

Instructions:
- Return ONLY the SQL query, no explanations or markdown
- Use proper table and column names from the schema above
- For multi-table queries, use appropriate JOINs based on common columns
- Use aggregate functions (SUM, COUNT, AVG) when appropriate
- Add ORDER BY and LIMIT clauses for readability when listing data
- Exclude metadata columns (_ingested_at, raw_data) from SELECT unless specifically requested
- Always try to steer the dialouge towards the Data Analysis of the available data, if the conversation is diverting to something else. 
- whenever the user starts discussing something other than Data Analysis, politely decline delving into the topics not pertaining to Data Analysis and available data, mention you are Data Analysis assistant cannot provide the info regarding other topics.

SQL Query:"""
        
        response = self.llm.invoke(sql_prompt)
        sql_query = response.content.replace("```sql", "").replace("```", "").strip()
        return sql_query
    
    def generate_nl_response(
        self, 
        user_question: str, 
        sql_query: str, 
        result_df: pd.DataFrame
    ) -> tuple[str, str]:
        """
        Generate natural language response from query results.
        
        Args:
            user_question: Original user question
            sql_query: SQL query that was executed
            result_df: Query results as DataFrame
        
        Returns:
            tuple: (natural_language_response, chart_code_or_none)
        """
        # Check if visualization is requested
        viz_keywords = ['plot', 'chart', 'graph', 'visualiz', 'show', 'display', 'draw']
        needs_viz = any(keyword in user_question.lower() for keyword in viz_keywords)
        
        # Prepare data summary
        data_summary = f"Query returned {len(result_df)} rows with {len(result_df.columns)} columns.\n"
        data_summary += f"Columns: {', '.join(result_df.columns.tolist())}\n\n"
        
        if len(result_df) <= 10:
            data_summary += "Complete Results:\n" + result_df.to_string()
        else:
            data_summary += "First 5 rows:\n" + result_df.head(5).to_string()
            data_summary += "\n\nSummary Statistics:\n" + result_df.describe().to_string()
        
        # Generate visualization code if requested
        chart_code = None
        if needs_viz and len(result_df) > 0:
            viz_prompt = f"""Generate Python code using Plotly Express to create a visualization for this data.

Data columns: {', '.join(result_df.columns.tolist())}
Data types: {result_df.dtypes.to_dict()}
First few rows:
{result_df.head(3).to_string()}

User question: {user_question}

Requirements:
- Use plotly.express (import as px)
- Assume data is in a DataFrame called 'data'
- Create appropriate chart type (bar, line, scatter, pie, etc.)
- Add proper labels and title
- Store the figure in a variable called 'fig'
- DO NOT call fig.show() - just create the figure
- Return ONLY the code, no explanations

Example:
import plotly.express as px
fig = px.bar(data, x='category', y='value', title='Sales by Category')

Code:"""
            
            try:
                viz_response = self.llm.invoke(viz_prompt)
                chart_code = viz_response.content.replace("```python", "").replace("```", "").strip()
                # Remove fig.show() if present
                chart_code = chart_code.replace("fig.show()", "").replace("fig.show", "").strip()
            except:
                chart_code = None
        
        nl_prompt = f"""You are a helpful Data Analyst assistant.

User asked: "{user_question}"

SQL Query executed: {sql_query}

Query Results:
{data_summary}

Task: Provide a clear, conversational answer to the user's question based on the query results.

Instructions:
- Write in natural, friendly language
- Highlight key insights and numbers
- If there are interesting patterns, point them out
- Keep it concise but informative
- Use markdown formatting for readability (bold for numbers, bullets for lists)
{"- Mention that a visualization has been generated to help visualize the data" if chart_code else ""}

Response:"""
        
        response = self.llm.invoke(nl_prompt)
        return response.content.strip(), chart_code

    
    @staticmethod
    def create_message(role: str, content: str, **kwargs) -> Dict:
        """
        Create a standardized message object.
        
        Args:
            role: Message role ('user' or 'assistant')
            content: Message content
            **kwargs: Additional fields (query, nl_response, result_html, etc.)
        
        Returns:
            dict: Message object
        """
        message = {
            "role": role,
            "content": content
        }
        message.update(kwargs)
        return message
