# To run poc app backend

cd /Users/pscs/pprojects/db-final/poc/<app-name>
source .venv/bin/activate
uvicorn backend.main:app --reload --port 8000
Open http://localhost:8000

# To run poc app frontend

npm run dev
