# Tender & Project Intelligence Platform

A production-oriented SaaS for monitoring, discovering, and analyzing government tenders and projects.

## Project Overview
This platform continuously monitors various sources for new business opportunities, applies rules (and later AI), and matches them to user preferences.

### Data Architecture
- **Source**: A website or portal we monitor.
- **Content**: Raw information collected from a source.
- **Opportunity**: A structured, useful business discovery extracted from Content.

## Technology Stack
- **Frontend**: React.js, TypeScript, Vite, React Router
- **Backend**: Python, FastAPI, Pydantic, Uvicorn
- **Database**: MongoDB (Atlas)

## Folder Structure
```text
TenderIntelligence/
├── frontend/ (React UI)
├── backend/ (FastAPI application)
├── README.md
└── .env.example
```

## Prerequisites
- Node.js (v18+)
- Python (3.10+)
- MongoDB Atlas Account

## Setup Instructions

### Environment Variables
1. Copy `.env.example` to `.env` in the root folder (or `backend/.env`).
2. Update the `MONGODB_URI` with your connection string.

### Backend Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```
The API will run at http://localhost:8000

### Frontend Setup
```bash
cd frontend
npm install
npm run dev
```
The frontend will run at http://localhost:5173

## Testing the Application
- Access the frontend dashboard at http://localhost:5173
- Verify that it displays "Connected" for both Backend and Database statuses.
- You can also test APIs directly:
  - `GET http://localhost:8000/api/health`
  - `GET http://localhost:8000/api/health/db`

## Current Project Status
- Basic project architecture set up.
- React frontend connects to FastAPI backend.
- Backend connects to MongoDB Atlas.
- API structure initialized with health check endpoints.

## Future Roadmap
- Authentication and Authorization
- Source scraping and content ingestion
- Content parsing and Opportunity extraction using AI/Rules
- User preference matching and notification system

