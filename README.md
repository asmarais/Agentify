# BH Assurance AI Agent

## Setup
1. Install Ollama: `ollama pull llama2`.
2. Backend: `cd backend; python -m venv venv; venv\Scripts\activate; pip install -r requirements.txt`.


## Run
- Backend: `uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload`

- Swagger UI: Access at http://localhost:8000/docs for API testing.

