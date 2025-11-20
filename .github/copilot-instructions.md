# Copilot Instructions for File Processor Platform

## Project Overview
- **Type:** Django web application for PDF-to-image conversion and AI-powered image analysis
- **Main App:** `file_processor`
- **Frontend:** Tailwind CSS + Alpine.js (responsive, modern UI)
- **Authentication:** Django built-in user system; users access only their own data, admins see all

## Key Components & Data Flow
- **PDFConversion**: Tracks PDF uploads and conversion status
- **ConvertedImage**: Stores images generated from PDFs
- **ImageAnalysis**: Manages analysis tasks for images (batch, async)
- **AnalysisResult**: Stores results from Dify API (JSON)
- **Service Layer:** `services.py` handles Dify API integration (image upload, workflow execution, result persistence)
- **Async Processing:** Image analysis and PDF conversion are performed asynchronously (see service logic)

## Developer Workflows
- **Setup:** Run `setup.sh` to install dependencies, apply migrations, and get started
- **Run Server:** `python3 manage.py runserver 0.0.0.0:8000`
- **Migrations:**
  - Create: `python3 manage.py makemigrations file_processor`
  - Apply: `python3 manage.py migrate`
- **Superuser:** `python3 manage.py createsuperuser` (optional, for admin access)
- **Testing:** Use `tests.py` in `file_processor/` for unit tests

## Patterns & Conventions
- **Model Relationships:**
  - Foreign keys link users to conversions/analyses
  - Many-to-many for images in analyses
  - Results stored as JSON (Dify API output)
- **Status Tracking:** Models use `status` fields (`pending`, `processing`, `completed`, `failed`)
- **Ordering:** Most models order by creation date or page number
- **Error Handling:** Service layer saves error info in `AnalysisResult.result_data` if Dify API fails
- **Frontend:** Templates in `file_processor/templates/` follow Tailwind/Alpine.js conventions

## External Integrations
- **Dify API:** Used for image analysis; credentials/config in Django settings
- **PyMuPDF, Pillow:** For PDF/image processing
- **requests:** For HTTP calls to Dify

## Examples
- See `services.py` for Dify API usage and error handling
- See `models.py` for data relationships and status conventions
- See `setup.sh` for setup workflow

## Tips for AI Agents
- Always update status fields and persist errors/results
- Use Django ORM for all DB operations
- Follow existing async/batch patterns for analysis/conversion
- Reference templates for UI conventions
- Check `project_status.md` for completed features and current architecture

---
_If any section is unclear or missing, please ask for feedback to iterate further._
