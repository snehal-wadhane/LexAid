@echo off
cd /d D:\LexAid\backend
echo Starting LexAid backend...
.venv\Scripts\uvicorn main:app --reload --port 8000
