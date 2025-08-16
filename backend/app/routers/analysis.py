# backend/app/routers/analysis.py
from fastapi import APIRouter
from app.services.analyzer_service import AnalyzerService

router = APIRouter()
analyzer = AnalyzerService()

@router.get("/{ref}")
def get_analysis(ref: int):
    """Analyse le portefeuille d'assurance d'un client."""
    return analyzer.analyze_profile(ref)