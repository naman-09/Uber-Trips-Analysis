# 🚗 Uber Trips Data Analysis Platform

A full-stack data analytics web app built with **Python Flask** (backend) + **Chart.js** (frontend).

## Features
- 🔢 **13 REST API endpoints** serving real-time analytics
- 📊 **10+ interactive charts** (line, bar, doughnut, histogram)
- 📋 **Paginated trip records** table with live filters
- 🔍 Filter by category, zone, and trip status
- 📈 Statistical summaries (mean, median, percentiles, std dev)
- 50,000 synthetic but realistic NYC Uber trips (2024)

## Project Structure
```
uber_analytics_project/
├── app.py              ← Flask backend + data generator + all API routes
├── templates/
│   └── index.html      ← Full frontend (sidebar, 7 pages, all charts)
├── requirements.txt
├── Procfile            ← For Heroku / Railway / Render deployment
└── README.md
```

## API Endpoints
| Endpoint | Description |
|---|---|
| `GET /` | Main dashboard UI |
| `GET /api/health` | Health check |
| `GET /api/kpi` | 8 key performance indicators |
| `GET /api/monthly` | Monthly trips + revenue |
| `GET /api/hourly` | 24-hour demand + cancel rate + avg fare |
| `GET /api/dow` | Day-of-week breakdown |
| `GET /api/categories` | Ride category split |
| `GET /api/fare_distribution` | Fare histogram buckets |
| `GET /api/zones` | Top 10 pickup zones |
| `GET /api/routes` | Top routes by volume |
| `GET /api/surge` | Surge pricing by hour |
| `GET /api/ratings` | Rating distribution |
| `GET /api/stats` | Full statistical summary |
| `GET /api/trips` | Paginated raw records (filterable) |
| `GET /api/filters` | Available filter options |

---

## ▶️ Run Locally (3 steps)

```bash
# 1. Install dependencies
pip install flask pandas numpy gunicorn

# 2. Start server
python app.py

# 3. Open browser
open http://localhost:5000
```

---

## 💡 Customising with Real Data

Replace the `generate_uber_data()` function in `app.py` with your own CSV:

```python
import pandas as pd

# Load your real Uber data CSV
DF = pd.read_csv('your_uber_data.csv')

# Make sure these columns exist (or rename them):
# trip_id, timestamp, date, month, day_of_week, hour,
# pickup_zone, dropoff_zone, category, distance_mi,
# duration_min, fare, surge_multiplier, cancelled, rating
```

The Uber open dataset is available at:
https://www.kaggle.com/datasets/yasserh/uber-fares-dataset

---

## Tech Stack
- **Backend**: Python 3.10+, Flask 2.x, Pandas, NumPy
- **Frontend**: Vanilla JS, Chart.js 4.4, Google Fonts
- **Deployment**: Gunicorn WSGI server
