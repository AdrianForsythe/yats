# -*- coding: utf-8 -*-
"""
Configuration for sequencing database connection
Uses environment variables for security and flexibility
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# HADES2017 Database Configuration
SEQUENCING_DB_CONFIG = {
    'server': os.getenv('SEQUENCING_DB_SERVER'),
    'database': os.getenv('SEQUENCING_DB_DATABASE'),
    'username': os.getenv('SEQUENCING_DB_USERNAME', 'solpipeline'),
    'password': os.getenv('SEQUENCING_DB_PASSWORD'),
    'driver': os.getenv('SEQUENCING_DB_DRIVER'),
    'port': int(os.getenv('SEQUENCING_DB_PORT'))
}

# DMA (Data Management Archive) Configuration
DMA_CONFIG = {
    'base_url': os.getenv('DMA_BASE_URL'),
    'username': os.getenv('DMA_USERNAME'),
    'password': os.getenv('DMA_PASSWORD'),
}

# Collection IDs for DMA archiving status
DMA_COLLECTION_IDS = [
    int(x.strip()) for x in os.getenv('DMA_COLLECTION_IDS', '154756,154755').split(',')
]

# Archive cutoff days (older than this will be flagged as needing archiving)
ARCHIVE_CUTOFF_DAYS = int(os.getenv('ARCHIVE_CUTOFF_DAYS', '14'))