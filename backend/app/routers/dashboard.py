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

@router.get("/interactions")
async def get_interactions(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    expediteur_email: Optional[str] = Query(None, description="Filter by sender email"),
    statut: Optional[str] = Query(None, description="Filter by status"),
    date_debut: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    date_fin: Optional[str] = Query(None, description="End date (YYYY-MM-DD)")
):
    """Get paginated interaction history with optional filters"""
    try:
        interactions = get_filtered_interactions(
            page=page,
            page_size=page_size,
            expediteur_email=expediteur_email,
            statut=statut,
            date_debut=date_debut,
            date_fin=date_fin
        )
        
        total_count = get_total_interactions_count(
            expediteur_email=expediteur_email,
            statut=statut,
            date_debut=date_debut,
            date_fin=date_fin
        )
        
        total_pages = (total_count + page_size - 1) // page_size
        
        return {
            "interactions": interactions,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total_items": total_count,
                "total_pages": total_pages
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching interactions: {str(e)}")

@router.get("/stats")
async def get_interaction_stats():
    """Get interaction statistics for the dashboard"""
    try:
        stats = get_dashboard_stats()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching stats: {str(e)}")

@router.get("/interactions/{interaction_id}")
async def get_interaction_detail(interaction_id: int):
    """Get detailed information for a specific interaction"""
    try:
        interaction = get_interaction_by_id(interaction_id)
        if not interaction:
            raise HTTPException(status_code=404, detail="Interaction not found")
        return interaction
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching interaction: {str(e)}")

def get_filtered_interactions(
    page: int,
    page_size: int,
    expediteur_email: Optional[str] = None,
    statut: Optional[str] = None,
    date_debut: Optional[str] = None,
    date_fin: Optional[str] = None
) -> List[Dict]:
    """Get filtered interactions from database"""
    conn = db_manager.obtenir_connexion()
    cursor = conn.cursor()
    
    try:
        # Build query with filters
        where_conditions = []
        params = []
        
        if expediteur_email:
            where_conditions.append("expediteur_email ILIKE %s")
            params.append(f"%{expediteur_email}%")
        
        if statut:
            where_conditions.append("statut = %s")
            params.append(statut)
        
        if date_debut:
            where_conditions.append("timestamp >= %s")
            params.append(date_debut)
        
        if date_fin:
            where_conditions.append("timestamp <= %s")
            params.append(f"{date_fin} 23:59:59")
        
        where_clause = "WHERE " + " AND ".join(where_conditions) if where_conditions else ""
        
        # Add pagination
        offset = (page - 1) * page_size
        params.extend([page_size, offset])
        
        query = f"""
            SELECT 
                id,
                email_id,
                conversation_id,
                expediteur_email,
                sujet,
                corps,
                type_reponse,
                statut,
                branche_assurance,
                reponse_ia,
                timestamp
            FROM interactions_email
            {where_clause}
            ORDER BY timestamp DESC
            LIMIT %s OFFSET %s
        """
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        interactions = []
        for row in rows:
            interactions.append({
                'id': row[0],
                'email_id': row[1],
                'conversation_id': row[2],
                'expediteur_email': row[3],
                'sujet': row[4],
                'corps': row[5][:200] + "..." if len(row[5]) > 200 else row[5],  # Truncate long content
                'type_reponse': row[6],
                'statut': row[7],
                'branche_assurance': row[8],
                'reponse_ia': row[9][:200] + "..." if row[9] and len(row[9]) > 200 else row[9],
                'timestamp': row[10].isoformat() if row[10] else None
            })
        
        return interactions
        
    finally:
        cursor.close()
        conn.close()

def get_total_interactions_count(
    expediteur_email: Optional[str] = None,
    statut: Optional[str] = None,
    date_debut: Optional[str] = None,
    date_fin: Optional[str] = None
) -> int:
    """Get total count of interactions matching filters"""
    conn = db_manager.obtenir_connexion()
    cursor = conn.cursor()
    
    try:
        where_conditions = []
        params = []
        
        if expediteur_email:
            where_conditions.append("expediteur_email ILIKE %s")
            params.append(f"%{expediteur_email}%")
        
        if statut:
            where_conditions.append("statut = %s")
            params.append(statut)
        
        if date_debut:
            where_conditions.append("timestamp >= %s")
            params.append(date_debut)
        
        if date_fin:
            where_conditions.append("timestamp <= %s")
            params.append(f"{date_fin} 23:59:59")
        
        where_clause = "WHERE " + " AND ".join(where_conditions) if where_conditions else ""
        
        query = f"SELECT COUNT(*) FROM interactions_email {where_clause}"
        cursor.execute(query, params)
        
        return cursor.fetchone()[0]
        
    finally:
        cursor.close()
        conn.close()

def get_dashboard_stats() -> Dict:
    """Get dashboard statistics"""
    conn = db_manager.obtenir_connexion()
    cursor = conn.cursor()
    
    try:
        # Total interactions
        cursor.execute("SELECT COUNT(*) FROM interactions_email")
        total_interactions = cursor.fetchone()[0]
        
        # Interactions by status
        cursor.execute("""
            SELECT statut, COUNT(*) 
            FROM interactions_email 
            GROUP BY statut
        """)
        status_stats = dict(cursor.fetchall())
        
        # Interactions by type
        cursor.execute("""
            SELECT type_reponse, COUNT(*) 
            FROM interactions_email 
            GROUP BY type_reponse
        """)
        type_stats = dict(cursor.fetchall())
        
        # Recent interactions (last 7 days)
        cursor.execute("""
            SELECT COUNT(*) 
            FROM interactions_email 
            WHERE timestamp >= NOW() - INTERVAL '7 days'
        """)
        recent_interactions = cursor.fetchone()[0]
        
        # Top 5 most active senders
        cursor.execute("""
            SELECT expediteur_email, COUNT(*) as count
            FROM interactions_email 
            GROUP BY expediteur_email 
            ORDER BY count DESC 
            LIMIT 5
        """)
        top_senders = [{"email": row[0], "count": row[1]} for row in cursor.fetchall()]
        
        return {
            "total_interactions": total_interactions,
            "recent_interactions": recent_interactions,
            "status_distribution": status_stats,
            "type_distribution": type_stats,
            "top_senders": top_senders
        }
        
    finally:
        cursor.close()
        conn.close()

def get_interaction_by_id(interaction_id: int) -> Optional[Dict]:
    """Get detailed interaction by ID"""
    conn = db_manager.obtenir_connexion()
    cursor = conn.cursor()
    
    try:
        query = """
            SELECT 
                id, email_id, conversation_id, expediteur_email, sujet, corps,
                type_reponse, statut, branche_assurance, reponse_ia, timestamp
            FROM interactions_email
            WHERE id = %s
        """
        
        cursor.execute(query, (interaction_id,))
        row = cursor.fetchone()
        
        if not row:
            return None
        
        return {
            'id': row[0],
            'email_id': row[1],
            'conversation_id': row[2],
            'expediteur_email': row[3],
            'sujet': row[4],
            'corps': row[5],
            'type_reponse': row[6],
            'statut': row[7],
            'branche_assurance': row[8],
            'reponse_ia': row[9],
            'timestamp': row[10].isoformat() if row[10] else None
        }
        
    finally:
        cursor.close()
        conn.close()
