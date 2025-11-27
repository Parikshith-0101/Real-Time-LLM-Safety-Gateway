# Backend Module

**Owner: Varshith**

This directory contains the backend API and orchestration logic for the LLM Safety Gateway.

## Structure

- `api/` - API endpoints (FastAPI/Flask)
- `pipeline/` - Processing pipeline orchestration
- `utils/` - Backend utilities and helpers

## Integration Points

- Uses `core/segmentation` for prompt segmentation
- Uses `core/normalization` for Unicode normalization
- Integrates with ML models from `ml/models/`

