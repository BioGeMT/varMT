import streamlit as st
import pandas as pd
import yaml
from sqlalchemy import create_engine
from typing import Dict, Any

class DatabaseClient:
    """
    Handles PostgreSQL database connections for Streamlit apps.
    Provides caching and connection management.
    """

    def __init__(self, config_path: str='config/db_connection.yml'):
        self.config_path = config_path
        self._config = None

    @st.cache_data
    def load_config(_self) -> Dict[str, Any]:
        """Load database configuration from a YAML file."""

        with open(_self.config_path, 'r') as file:
            return yaml.safe_load(file)
            
    def get_connection(self):
        """Establish a connection to the PostgreSQL database."""

        if self._config is None:
            self._config = self.load_config()

        db_config = self._config['database']
        connection_string = f"postgresql://{db_config['username']}@{db_config['host']}:{db_config['port']}/{db_config['database']}"

        return create_engine(connection_string)

    @st.cache_data
    def execute_query(_self, query: str) -> pd.DataFrame:
        """
        Execute a SQL query and return results as a pandas DataFrame.
        Results are cached for performance.
        """

        conn = _self.get_connection()
        df = pd.read_sql(query, conn)

        return df