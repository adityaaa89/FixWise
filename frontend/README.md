# Repair or Replace Advisor — Frontend

A responsive, mobile-first React application built with **React 18**, **Tailwind CSS**, and **Lucide React**.

## Features

1. **Guided Step-by-Step Form Wizard (`StepWizard.jsx`)**:
   - Appliance type selector with category badges
   - Brand selector with popular Indian brand quick-chips (IFB, Voltas, Godrej, LG, Samsung, Blue Star, Kent, Havells)
   - Age slider with real-time lifecycle indicator (Early Life, Mid Life, Late Life)
   - Plain-language symptom description box with quick sample symptom chips
2. **Optional Photo Upload Dropzone & Quote Field (`PhotoDropzone.jsx`)**:
   - Drag & drop model sticker upload
   - Automated rating plate metadata extraction via `/api/photo`
   - Technician quote input field (₹) and replacement price estimate
3. **Interactive Loading State (`LoadingState.jsx`)**:
   - Animated multi-stage checklist tracking backend diagnostic triage, price band benchmarking, and deterministic cost engine execution
4. **Result Dashboard View**:
   - **Prominent Header Verdict Card (`VerdictCard.jsx`)**: High-impact "REPAIR" or "REPLACE" visual callout with net annual savings in ₹
   - **Uncertainty Badge**: "FIRM RECOMMENDATION" vs. "CLOSE (Verify X)" sensitivity indicator
   - **Flip Assumption Banner (`FlipBanner.jsx`)**: Callout box detailing the exact tipping point condition required to change the decision
   - **Side-by-Side Cost Comparison Table (`CostComparisonTable.jsx`)**: Structured table comparing upfront cost, owner's time, repeat risk, running cost, and final annualized cost-per-year
   - **Ranked Causes Section (`RankedCausesList.jsx`)**: Ranked potential faults categorized by cheap vs. expensive fixes with DIY feasibility flags (`Easy DIY`, `Moderate DIY`, `Technician Required`) and fair OEM price bands
5. **Saved Case Lookup**: Reopen past assessments by unique Case ID.

## Development

```bash
cd frontend
npm install
npm run dev
```

## Production Zero-Build UI

For instant zero-build execution without npm, FastAPI automatically serves the pre-bundled React 18 SPA from `/` (via `static/index.html`):

```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```
Open [http://localhost:8000](http://localhost:8000) in your browser.

