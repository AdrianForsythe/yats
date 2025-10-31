import pyodbc
from .sequencing_config import SEQUENCING_DB_CONFIG

def get_hades_connection():
    """Get connection to HADES2017 sequencing database"""
    try:
        # Try FreeTDS first (works on Ubuntu 24.04)
        if SEQUENCING_DB_CONFIG['driver'] == 'FreeTDS':
            connection_string = (
                f"DRIVER={{{SEQUENCING_DB_CONFIG['driver']}}};"
                f"SERVER={SEQUENCING_DB_CONFIG['server']};"
                f"PORT={SEQUENCING_DB_CONFIG['port']};"
                f"DATABASE={SEQUENCING_DB_CONFIG['database']};"
                f"UID={SEQUENCING_DB_CONFIG['username']};"
                f"PWD={SEQUENCING_DB_CONFIG['password']};"
                f"TDS_Version=8.0;"
            )
        else:
            # Microsoft ODBC Driver
            connection_string = (
                f"DRIVER={{{SEQUENCING_DB_CONFIG['driver']}}};"
                f"SERVER={SEQUENCING_DB_CONFIG['server']};"
                f"DATABASE={SEQUENCING_DB_CONFIG['database']};"
                f"UID={SEQUENCING_DB_CONFIG['username']};"
                f"PWD={SEQUENCING_DB_CONFIG['password']};"
            )
        
        return pyodbc.connect(connection_string)
    except Exception as e:
        print(f"Database connection error: {e}")
        return None