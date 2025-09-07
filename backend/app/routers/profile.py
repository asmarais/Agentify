"""
Dashboard Router

This module provides endpoints for the dashboard to view interaction history
and analytics from the database.

Author: Agentify Team
Date: 2025-09-02
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict, Optional
from datetime import datetime, timedelta

from pandas import DataFrame
from app.data.data_utils import generate_person_dashboard, get_data_stat
from app.settings import settings
import sys
import os

# Add parent directory to path to import shared modules
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
sys.path.insert(0, parent_dir)

try:
    from shared.database import GestionnaireBaseDonnees, StatutInteraction, TypeReponse
except ImportError as e:
    print(f"Import failed: {e}")
    raise

router = APIRouter()

# Initialize database manager
db_config = {
    'host': settings.DB_HOST,
    'database': settings.DB_NAME,
    'user': settings.DB_USER,
    'password': settings.DB_PASSWORD,
    'port': settings.DB_PORT
}

db_manager = GestionnaireBaseDonnees(db_config)

@router.get("/profile")
async def get_profile(
    client_ref: int ,
   contrats:DataFrame,
   sinistres:DataFrame
):
    """Get paginated interaction history with optional filters"""
    try:
       return generate_person_dashboard(client_ref,contrats,sinistres)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching profile: {str(e)}")
@router.get("/dataFrames")
async def get_contrats_sinistres(
  
):
    """Get paginated interaction history with optional filters"""
    try:
       contrats,sinistres=get_data_stat()
       return  {
            "contrats": contrats,
            "sinistres": sinistres
        } 
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching data contrats sinistress: {str(e)}")