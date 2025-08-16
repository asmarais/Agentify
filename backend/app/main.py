from fastapi import FastAPI
#from fastapi.middleware.cors import CORSMiddleware
from app.routers import analysis

app = FastAPI(title="BH Assurance AI Agent")

# CORS pour React (localhost:3000)
#app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:3000"], allow_methods=["*"], allow_headers=["*"])

app.include_router(analysis.router, prefix="/api/analysis")