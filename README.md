# LLM Safety Gateway

**Hackathon Project - Real-time Prompt Injection Defense**

## Team Members

- **Parikshith** - ML + Agentic AI + Architecture Lead
- **Varshith** - Backend Engineer + Integration
- **Manoj** - Frontend (UI)
- **Sujan** - Frontend + Light ML + Normalization/Artifacts

## Project Structure

```
.
├── core/                    # Core shared modules
│   ├── segmentation/       # Segmentation & Origin Tagging (Parikshith - Chapter 1)
│   └── normalization/      # Unicode normalization (Sujan - Chapter 2)
│
├── backend/                # Backend API & orchestration (Varshith)
│   ├── api/                # API endpoints
│   ├── pipeline/           # Processing pipeline
│   └── utils/              # Backend utilities
│
├── frontend/               # Frontend application (Manoj + Sujan)
│   ├── src/                # Source code
│   ├── components/         # UI components
│   └── public/             # Static assets
│
├── ml/                     # ML models & training (Parikshith)
│   ├── models/             # Trained models
│   ├── training/           # Training scripts
│   └── datasets/           # Training datasets
│
├── scripts/                # Utility scripts
│   ├── demos/              # Demo scripts
│   └── utils/              # Utility scripts
│
├── tests/                  # Test suite
│   ├── unit/               # Unit tests
│   └── integration/        # Integration tests
│
├── docs/                   # Documentation
├── config/                 # Configuration files
└── requirements.txt        # Python dependencies
```

## Chapter 1: Segmentation & Origin Tagging

**Implemented by Parikshith**

The segmentation module breaks down user prompts into meaningful segments for risk assessment. Each segment is tagged with its origin type (user/pasted/quoted/codeblock) and enriched with metadata.

### Key Features

- **Priority-based segmentation**: Code blocks → Quoted content → Pasted content → Sentences
- **Origin tagging**: Classifies segments by their origin type
- **Metadata enrichment**: Tracks characteristics like entropy, encoding, URLs, emails
- **Scoring framework**: Defines weights and priorities for different segment types

### Usage

```python
from core.segmentation import Segmenter, SegmentScoringFramework

segmenter = Segmenter()
segments = segmenter.segment(user_prompt)

for segment in segments:
    weight = SegmentScoringFramework.calculate_segment_weight(segment)
    should_review = SegmentScoringFramework.should_review_segment(segment)
```

### Running the Demo

```bash
python scripts/demos/demo_segmentation.py
```

### Running Tests

```bash
python -m unittest tests.unit.test_segmentation
```

## Development Setup

1. Clone the repository
2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Next Steps

- Chapter 2: Unicode Normalization (Sujan)
- Chapter 3: Feature Extraction & ML Classifier (Parikshith + Varshith)
- Chapter 4: Deterministic Rules & Decision Engine (Parikshith + Varshith)

## Documentation

- [Segmentation Module README](core/segmentation/README.md)
- [Backend Integration Spec](core/segmentation/SPECIFICATION_FOR_VARSHITH.md)
