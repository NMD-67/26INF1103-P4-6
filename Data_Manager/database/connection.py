"""Compatibility entry point for older callers; main uses DatabaseConnection."""
from pathlib import Path
from dotenv import load_dotenv
from Data_Manager.database.database_connection import DatabaseConnection


def create_connection_pool():
    load_dotenv(Path(__file__).resolve().parents[2] / ".env")
    return DatabaseConnection().create_pool()
