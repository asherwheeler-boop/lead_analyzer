# Pacing Lead Analyzer (Render-ready rebuild)

This repo is a clean Streamlit rebuild for Render deployment. It includes:

- team-only login using Render environment variables
- upload workflow for `.xlsx` and `.csv` files
- wire tracing plots
- curvature threshold plots
- segment summary tables
- Excel export

## Local run

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Render deployment

1. Push this folder to GitHub.
2. In Render, create a **Web Service** from the repo.
3. Use the build command:
   `pip install -r requirements.txt`
4. Use the start command:
   `streamlit run app.py --server.address 0.0.0.0 --server.port $PORT`
5. Add environment variables:
   - `REQUIRE_LOGIN=true`
   - `TEAM_APP_USERNAME=<your shared username>`
   - `TEAM_APP_PASSWORD=<your shared password>`

## Keeping the website the same

The UI is intentionally modular. To preserve the exact behavior of your existing site, replace or extend the logic in `core/analysis.py` with your current calculation and plotting functions while keeping `app.py` and the folder structure intact.
