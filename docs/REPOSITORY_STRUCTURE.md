# Repository Structure Overview

This document describes the complete repository structure for the LLM Safety Gateway project.

## Directory Structure

```
CODEBASE/
├── core/                          # Core shared modules
│   ├── __init__.py
│   ├── segmentation/              # Parikshith - Chapter 1 ✅
│   │   ├── __init__.py
│   │   ├── segmenter.py
│   │   ├── metadata.py
│   │   ├── scoring_framework.py
│   │   ├── README.md
│   │   └── SPECIFICATION_FOR_VARSHITH.md
│   └── normalization/            # Sujan - Chapter 2 (empty, ready for work)
│       ├── README.md
│       └── .gitkeep
│
├── backend/                       # Varshith - Backend API & Integration
│   ├── README.md
│   ├── api/                       # API endpoints (empty, ready for work)
│   ├── pipeline/                  # Processing pipeline (empty, ready for work)
│   └── utils/                     # Backend utilities (empty, ready for work)
│
├── frontend/                      # Manoj + Sujan - Frontend UI
│   ├── README.md
│   ├── src/                       # Source code (empty, ready for work)
│   ├── components/                # UI components (empty, ready for work)
│   └── public/                   # Static assets (empty, ready for work)
│
├── ml/                            # Parikshith - ML Models & Training
│   ├── README.md
│   ├── models/                    # Trained models (empty, ready for work)
│   ├── training/                  # Training scripts (empty, ready for work)
│   └── datasets/                  # Training datasets (empty, ready for work)
│
├── scripts/                       # Utility scripts
│   ├── demos/
│   │   └── demo_segmentation.py  # Parikshith's demo script
│   └── utils/
│       └── README.md
│
├── tests/                         # Test suite
│   ├── unit/
│   │   ├── __init__.py
│   │   └── test_segmentation.py  # Parikshith's unit tests
│   └── integration/
│       └── README.md
│
├── docs/                          # Documentation
│   ├── README.md
│   └── REPOSITORY_STRUCTURE.md
│
├── config/                        # Configuration files
│   └── README.md
│
├── .gitignore                     # Git ignore rules
├── README.md                      # Main project README
└── requirements.txt              # Python dependencies
```

## Team Responsibilities

### Parikshith (ML + Architecture Lead)
- ✅ **core/segmentation/** - Chapter 1: Segmentation & Origin Tagging (COMPLETE)
- 📝 **ml/** - ML models, training scripts, datasets (READY FOR WORK)
- 📝 **scripts/demos/** - Demo scripts (1 demo created)

### Varshith (Backend Engineer)
- 📝 **backend/** - API endpoints, pipeline orchestration, backend utilities (READY FOR WORK)
- 📝 Integration with core modules

### Manoj (Frontend UI)
- 📝 **frontend/** - UI components, reviewer interface, dashboard (READY FOR WORK)

### Sujan (Frontend + Normalization)
- 📝 **core/normalization/** - Unicode normalization, artifact detection (READY FOR WORK)
- 📝 **frontend/** - Frontend components (shared with Manoj)

## File Status

- ✅ = Implemented and complete
- 📝 = Directory structure ready, waiting for implementation
- 🔄 = In progress

## Getting Started

1. **For Parikshith**: Your segmentation module is complete in `core/segmentation/`. Next: ML models in `ml/`.

2. **For Varshith**: Start with `backend/api/` for endpoints. See `core/segmentation/SPECIFICATION_FOR_VARSHITH.md` for integration details.

3. **For Sujan**: Start with `core/normalization/` for Unicode normalization. See implementation story for requirements.

4. **For Manoj**: Start with `frontend/src/` and `frontend/components/` for the reviewer UI.

## Notes

- All directories have README.md files explaining their purpose
- Empty directories use `.gitkeep` files to ensure they're tracked in git
- Core modules are shared and can be imported by backend and ML components
- Tests are organized by type (unit vs integration)

