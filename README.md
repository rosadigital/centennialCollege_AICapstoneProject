# AI Capstone Project - TTC Delay Prediction SaaS

**Course:** AI Capstone Project - COMP385402.12558.2026W  
**Professor:** Hakim Klif  
**Institution:** Centennial College

## Overview

This repository contains a complete TTC delay prediction workflow:

- **Data & ML:** exploratory analysis and model training in [`aiProject/`](aiProject/)
- **API:** FastAPI backend in [`server/`](server/)
- **UI:** React + Tailwind + MapLibre heatmap client in [`client/`](client/)

Users select **vehicle type**, **month**, **day of week**, and **hour**; the app shows predicted delay intensity on a map and summary KPIs.

## Quick start (run the full stack)

1. **Generate model artifacts** (if not already present): run [`aiProject/01_EDA_TTC_Delay_Prediction.ipynb`](aiProject/01_EDA_TTC_Delay_Prediction.ipynb) so the following files exist:
   - `aiProject/outputs/model_artifacts/model.pkl`
   - `aiProject/outputs/model_artifacts/heatmap_predictions_test_agg.csv`

2. **Start the API** (terminal 1) — see [`server/README.md`](server/README.md) for details.

3. **Start the web client** (terminal 2) — see [`client/README.md`](client/README.md) for details.

Default URLs:

- API: `http://localhost:8000`
- Client: `http://localhost:5173`

## Project structure

```text
centennialCollege_AICapstoneProject/
├── aiProject/
│   ├── 01_EDA_TTC_Delay_Prediction.ipynb
│   ├── outputs/model_artifacts/
│   │   ├── model.pkl
│   │   └── heatmap_predictions_test_agg.csv
│   └── requirements.txt
├── server/                 # FastAPI — see server/README.md
├── client/                 # React + Vite — see client/README.md
├── dataset/
└── README.md               # this file
```

## Dataset

TTC historical delay data (2017–2025) for bus, streetcar, and subway.

**Source:** [Toronto Open Data Portal](https://open.toronto.ca/)

## Documentation

| Topic | File |
|--------|------|
| Run the API | [`server/README.md`](server/README.md) |
| Run the web app | [`client/README.md`](client/README.md) |

## Team

1. Absar Siddiqui-Atta  
2. Bruna De Fatima Miranda Figueiredo Cruz  
3. Felipe Rosa  
4. Krishan Singh  
5. Marco Favaretto  
