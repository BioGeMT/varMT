import streamlit as st
import pandas as pd
import yaml
from sqlalchemy import create_engine
from typing import Dict, Any

class DatabaseClient:
    """
    Handles PostgreSQL database connections for Streamlit application.
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

        if db_config['password']:
            connection_string = f"postgresql://{db_config['username']}:{db_config['password']}@{db_config['host']}:{db_config['port']}/{db_config['database']}" # Using password
        else:
            connection_string = f"postgresql://{db_config['username']}@{db_config['host']}:{db_config['port']}/{db_config['database']}" # Using .pgpass


        return create_engine(connection_string)

    @st.cache_data
    def execute_query(_self, query: str) -> pd.DataFrame:
        """
        Execute a SQL query and return results as a pandas DataFrame.
        Results are cached for performance.
        """

        engine = _self.get_connection()
        df = pd.read_sql(query, engine)

        return df
    
    @st.cache_data
    def execute_query_with_params(_self, query: str, params: tuple) -> pd.DataFrame:
        """
        Execute a SQL query with parameters and return results as a pandas DataFrame.
        Results are cached for performance.
        """

        engine = _self.get_connection()
        df = pd.read_sql(query, engine, params=params)

        return df