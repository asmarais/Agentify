from fastapi import FastAPI
#from fastapi.middleware.cors import CORSMiddleware
from app.routers import notification, workflow, dashboard
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="BH Assurance AI Agent")

# CORS pour React (localhost:3000)
#app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:3000"], allow_methods=["*"], allow_headers=["*"])

app.include_router(notification.router, prefix="/api/notify")
app.include_router(workflow.router, prefix="/api/workflow")
app.include_router(dashboard.router, prefix="/api/dashboard")
