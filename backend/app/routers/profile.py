"""
Dashboard Router

This module provides endpoints for the dashboard to view interaction history
and analytics from the database.

Author: Agentify Team
Date: 2025-09-02
"""

import json
from fastapi import APIRouter, HTTPException, Query, Response, Depends
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from functools import lru_cache

from pandas import DataFrame
from app.data.data_utils import generate_person_dashboard, get_data_stat
from app.settings import settings
import sys
import os

# Add parent directory to path to import shared modules
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
print(parent_dir,'pareeent')
sys.path.insert(0, parent_dir)



router = APIRouter()

# Initialize global variables
contrats_df = None
sinistres_df = None

# Solution recommandée: Utiliser le caching avec lru_cache
@lru_cache(maxsize=1)
def load_data_cached():
    """Cache the data loading function"""
    return get_data_stat()

async def get_dataframes() -> Tuple[DataFrame, DataFrame]:
    """Dependency that provides DataFrames (cached)"""
    global contrats_df, sinistres_df
    
    # Si les données ne sont pas encore chargées, les charger
    if contrats_df is None or sinistres_df is None:
        contrats_df, sinistres_df = load_data_cached()
    
    return contrats_df, sinistres_df

# Alternative: Solution sans variables globales (plus propre)
async def get_dataframes_alternative() -> Tuple[DataFrame, DataFrame]:
    """Dependency that provides DataFrames using LRU cache"""
    return load_data_cached()

@router.get("/profile")
async def get_profile(
    client_ref: int = Query(...),
    dataframes: tuple = Depends(get_dataframes)
):
    """Get client profile dashboard"""
    try:
        contrats, sinistres = dataframes
        return generate_person_dashboard(client_ref, contrats, sinistres)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching profile: {str(e)}")

# Endpoint pour forcer le rechargement des données (optionnel)
