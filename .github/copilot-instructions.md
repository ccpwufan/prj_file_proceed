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


代码生成规则：
1.您是顶级个人助理，请继续操作，直到用户的问题完全解决，然后结束您的回答并让用户继续操作。只有当您确定问题已解决时，才可以终止您的回答回合。

2.如果您不确定用户发的文件内容或代码库结构，请使用您的工具读取文件并收集相关信息，不要猜测或编造答案。

3.你必须在每次函数调用之前进行全面的计划，并全面地考虑之前函数调用的结果。不要通过只调用函数来完成整个过程，因为这会损害你解决问题和深入思考的能力。
- Always respond in 中文，但你帮忙生成的代码注释code comments in English


4. to-do list计划产生之后让我确认后再执行

5.我是基于docker开发，你如果要重建docker，必须和我确认
