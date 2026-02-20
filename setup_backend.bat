@echo off
echo --- Starting Backend Setup ---

:: 1. Navigate to backend directory
cd backend

:: 2. Install dependencies
echo Installing dependencies from requirements.txt...
pip install -r requirements.txt

cd ..

:: 3. Run the application
echo Starting Uvicorn Server...
uvicorn backend.main:app --reload

pose
