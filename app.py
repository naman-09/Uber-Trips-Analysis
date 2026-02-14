"""
Uber Trips Data Analysis — Full-Stack Flask Backend
Generates realistic synthetic trip data and exposes REST API endpoints
for the analytics dashboard.
"""

from flask import Flask, jsonify, request, render_template, send_from_directory
import pandas as pd
import numpy as np
import json
import os
from datetime import datetime, timedelta
import random

app = Flask(__name__, template_folder='templates', static_folder='static')

# ─── CORS (manual since no flask-cors) ───────────────────────────────────────
@app.after_request
def add_cors(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return response

# ─── DATA GENERATION ─────────────────────────────────────────────────────────
def generate_uber_data(n=50000):
    """Generate a realistic synthetic Uber NYC trip dataset."""
    np.random.seed(42)
    random.seed(42)

    start_date = datetime(2024, 1, 1)
    end_date   = datetime(2024, 12, 31)
    total_secs = int((end_date - start_date).total_seconds())

    # Zones
    zones = [
        'Midtown Manhattan','JFK Airport','Upper East Side','LGA Airport',
        'Lower Manhattan','Brooklyn Heights','Williamsburg','Astoria',
        'Upper West Side','EWR Airport','East Village','Harlem',
        'Flushing Queens','Staten Island','Bronx','Park Slope',
        'Long Island City','Chelsea','SoHo','Tribeca'
    ]

    categories = ['UberX','Comfort','UberXL','Black','Black SUV','Green']
    cat_weights = [0.61, 0.14, 0.13, 0.07, 0.03, 0.02]

    # Hourly demand weights (higher during rush hours & late night weekends)
    hour_weights = [0.4,0.25,0.18,0.15,0.19,0.48,1.24,1.92,1.78,1.34,
                    1.10,1.26,1.38,1.20,1.18,1.22,1.38,1.62,1.82,2.10,
                    1.94,1.64,1.24,0.82]
    hour_weights = np.array(hour_weights)
    hour_weights /= hour_weights.sum()

    # Base fares per category
    base_fares = {'UberX':12,'Comfort':16,'UberXL':18,'Black':28,'Black SUV':38,'Green':10}
    per_mile   = {'UberX':1.8,'Comfort':2.1,'UberXL':2.3,'Black':3.2,'Black SUV':3.8,'Green':1.5}

    records = []
    for i in range(n):
        # Random timestamp weighted to hour distribution
        hour = np.random.choice(24, p=hour_weights)
        rand_day = random.randint(0, 364)
        rand_min = random.randint(0, 59)
        rand_sec = random.randint(0, 59)
        ts = start_date + timedelta(days=rand_day, hours=hour, minutes=rand_min, seconds=rand_sec)

        weekday = ts.weekday()   # 0=Mon, 6=Sun
        is_weekend = weekday >= 5
        is_rush = hour in [7, 8, 9, 17, 18, 19]
        is_late_night = hour in [22, 23, 0, 1, 2]

        # Category
        cat = np.random.choice(categories, p=cat_weights)

        # Distance (miles) — exponential-ish distribution
        dist = np.random.exponential(4.2)
        dist = round(np.clip(dist, 0.5, 45.0), 1)

        # Airport flag
        pickup = random.choice(zones)
        dropoff = random.choice([z for z in zones if z != pickup])
        is_airport = 'Airport' in pickup or 'Airport' in dropoff

        # Surge multiplier
        surge = 1.0
        if is_rush and not is_weekend:
            surge = round(random.uniform(1.1, 1.8), 1)
        if is_late_night and is_weekend:
            surge = round(random.uniform(1.5, 2.8), 1)
        if is_airport:
            surge = round(max(surge, random.uniform(1.0, 1.6)), 1)

        # Fare
        fare = base_fares[cat] + per_mile[cat] * dist
        fare *= surge
        fare = round(fare + random.gauss(0, 1.5), 2)
        fare = max(fare, 5.0)

        # Duration (minutes) — correlated with distance + traffic
        traffic_factor = 1.0
        if is_rush: traffic_factor = random.uniform(1.3, 1.9)
        duration = round((dist / 18) * 60 * traffic_factor + random.gauss(3, 2), 0)
        duration = max(3, int(duration))

        # Cancellation
        cancel_prob = 0.028
        if is_rush: cancel_prob = 0.075
        if is_late_night: cancel_prob = 0.045
        cancelled = random.random() < cancel_prob

        # Rating (only for completed)
        rating = None
        if not cancelled:
            r = np.random.normal(4.4, 0.5)
            rating = round(np.clip(r, 1.0, 5.0), 1)

        records.append({
            'trip_id':    f'TRP{1000000+i}',
            'timestamp':  ts.strftime('%Y-%m-%d %H:%M:%S'),
            'date':       ts.strftime('%Y-%m-%d'),
            'year':       ts.year,
            'month':      ts.month,
            'month_name': ts.strftime('%b'),
            'day_of_week': ts.strftime('%A'),
            'hour':       hour,
            'pickup_zone': pickup,
            'dropoff_zone': dropoff,
            'category':   cat,
            'distance_mi': dist,
            'duration_min': duration,
            'fare':       round(fare, 2),
            'surge_multiplier': surge,
            'cancelled':  cancelled,
            'rating':     rating,
            'is_airport': is_airport,
            'is_weekend': is_weekend,
        })

    df = pd.DataFrame(records)
    return df

# Generate once on startup
print("Generating dataset...")
DF = generate_uber_data(50000)
print(f"Dataset ready: {len(DF):,} trips")

# ─── HELPER ──────────────────────────────────────────────────────────────────
def completed(df):
    return df[df['cancelled'] == False]

def safe_json(obj):
    """Convert numpy types for JSON serialisation."""
    if isinstance(obj, (np.integer,)): return int(obj)
    if isinstance(obj, (np.floating,)): return float(obj)
    if isinstance(obj, (np.bool_,)): return bool(obj)
    if isinstance(obj, (np.ndarray,)): return obj.tolist()
    raise TypeError(f"Not serializable: {type(obj)}")

# ─── ROUTES ──────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return render_template('index.html')

# ── KPI Summary ──────────────────────────────────────────────────────────────
@app.route('/api/kpi')
def api_kpi():
    df = DF
    comp = completed(df)
    total_trips    = len(df)
    total_revenue  = comp['fare'].sum()
    avg_fare       = comp['fare'].mean()
    avg_distance   = comp['distance_mi'].mean()
    cancel_rate    = df['cancelled'].mean() * 100
    avg_rating     = comp['rating'].mean()
    avg_duration   = comp['duration_min'].mean()
    surge_trips    = (comp['surge_multiplier'] > 1.0).sum()
    surge_pct      = surge_trips / len(comp) * 100

    return jsonify({
        'total_trips':   int(total_trips),
        'total_revenue': round(float(total_revenue), 2),
        'avg_fare':      round(float(avg_fare), 2),
        'avg_distance':  round(float(avg_distance), 2),
        'cancel_rate':   round(float(cancel_rate), 2),
        'avg_rating':    round(float(avg_rating), 2),
        'avg_duration':  round(float(avg_duration), 1),
        'surge_pct':     round(float(surge_pct), 1),
    })

# ── Monthly trends ───────────────────────────────────────────────────────────
@app.route('/api/monthly')
def api_monthly():
    comp = completed(DF)
    grp = comp.groupby('month').agg(
        trips=('trip_id','count'),
        revenue=('fare','sum'),
        avg_fare=('fare','mean')
    ).reset_index()
    grp = grp.sort_values('month')
    months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
    return jsonify({
        'months':  [months[m-1] for m in grp['month']],
        'trips':   [int(v) for v in grp['trips']],
        'revenue': [round(float(v)/1000,1) for v in grp['revenue']],
        'avg_fare':[round(float(v),2) for v in grp['avg_fare']],
    })

# ── Hourly pattern ───────────────────────────────────────────────────────────
@app.route('/api/hourly')
def api_hourly():
    grp = DF.groupby('hour').agg(
        trips=('trip_id','count'),
        cancel_rate=('cancelled','mean'),
        avg_fare=('fare','mean')
    ).reset_index()
    grp = grp.sort_values('hour')
    labels = [f"{h}:00" for h in grp['hour']]
    return jsonify({
        'hours':       labels,
        'trips':       [int(v) for v in grp['trips']],
        'cancel_rate': [round(float(v)*100, 2) for v in grp['cancel_rate']],
        'avg_fare':    [round(float(v), 2) for v in grp['avg_fare']],
    })

# ── Day of week ──────────────────────────────────────────────────────────────
@app.route('/api/dow')
def api_dow():
    day_order = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday']
    grp = DF.groupby('day_of_week').agg(
        trips=('trip_id','count'),
        revenue=('fare','sum'),
        avg_fare=('fare','mean')
    ).reindex(day_order).reset_index()
    short = ['Mon','Tue','Wed','Thu','Fri','Sat','Sun']
    return jsonify({
        'days':    short,
        'trips':   [int(v) for v in grp['trips']],
        'revenue': [round(float(v)/1000,1) for v in grp['revenue']],
        'avg_fare':[round(float(v),2) for v in grp['avg_fare']],
    })

# ── Category split ───────────────────────────────────────────────────────────
@app.route('/api/categories')
def api_categories():
    comp = completed(DF)
    grp = comp.groupby('category').agg(
        trips=('trip_id','count'),
        revenue=('fare','sum'),
        avg_fare=('fare','mean')
    ).reset_index()
    grp['pct'] = (grp['trips'] / grp['trips'].sum() * 100).round(1)
    grp = grp.sort_values('trips', ascending=False)
    return jsonify({
        'categories': grp['category'].tolist(),
        'trips':      [int(v) for v in grp['trips']],
        'revenue':    [round(float(v),2) for v in grp['revenue']],
        'avg_fare':   [round(float(v),2) for v in grp['avg_fare']],
        'pct':        grp['pct'].tolist(),
    })

# ── Fare distribution ────────────────────────────────────────────────────────
@app.route('/api/fare_distribution')
def api_fare_dist():
    comp = completed(DF)
    bins   = [0,10,15,20,25,35,50,75,200]
    labels = ['$0-10','$10-15','$15-20','$20-25','$25-35','$35-50','$50-75','$75+']
    counts, _ = np.histogram(comp['fare'], bins=bins)
    pct = (counts / counts.sum() * 100).round(1)
    return jsonify({'buckets': labels, 'counts': counts.tolist(), 'pct': pct.tolist()})

# ── Top zones ────────────────────────────────────────────────────────────────
@app.route('/api/zones')
def api_zones():
    grp = DF.groupby('pickup_zone').agg(
        trips=('trip_id','count'),
        revenue=('fare','sum'),
        avg_fare=('fare','mean')
    ).reset_index()
    top = grp.nlargest(10,'trips')
    return jsonify({
        'zones':    top['pickup_zone'].tolist(),
        'trips':    [int(v) for v in top['trips']],
        'revenue':  [round(float(v)/1000,1) for v in top['revenue']],
        'avg_fare': [round(float(v),2) for v in top['avg_fare']],
    })

# ── Top routes ───────────────────────────────────────────────────────────────
@app.route('/api/routes')
def api_routes():
    comp = completed(DF)
    comp = comp.copy()
    comp['route'] = comp['pickup_zone'] + ' → ' + comp['dropoff_zone']
    grp = comp.groupby(['pickup_zone','dropoff_zone','route']).agg(
        trips=('trip_id','count'),
        avg_fare=('fare','mean'),
        avg_duration=('duration_min','mean'),
        avg_distance=('distance_mi','mean'),
        surge_freq=('surge_multiplier', lambda x: (x > 1.0).mean())
    ).reset_index()
    top = grp.nlargest(10,'trips')
    rows = []
    for _, r in top.iterrows():
        rows.append({
            'pickup':       r['pickup_zone'],
            'dropoff':      r['dropoff_zone'],
            'trips':        int(r['trips']),
            'avg_fare':     round(float(r['avg_fare']),2),
            'avg_duration': round(float(r['avg_duration']),0),
            'avg_distance': round(float(r['avg_distance']),1),
            'surge_freq':   round(float(r['surge_freq'])*100,1),
        })
    return jsonify({'routes': rows})

# ── Surge analysis ───────────────────────────────────────────────────────────
@app.route('/api/surge')
def api_surge():
    comp = completed(DF)
    grp = comp.groupby('hour').agg(
        avg_surge=('surge_multiplier','mean'),
        max_surge=('surge_multiplier','max'),
        surge_pct=('surge_multiplier', lambda x: (x>1.0).mean()*100)
    ).reset_index()
    return jsonify({
        'hours':     [f"{h}:00" for h in grp['hour']],
        'avg_surge': [round(float(v),2) for v in grp['avg_surge']],
        'max_surge': [round(float(v),2) for v in grp['max_surge']],
        'surge_pct': [round(float(v),1) for v in grp['surge_pct']],
    })

# ── Rating distribution ──────────────────────────────────────────────────────
@app.route('/api/ratings')
def api_ratings():
    comp = completed(DF)
    bins   = [1,1.5,2,2.5,3,3.5,4,4.5,5.01]
    labels = ['1.0','1.5','2.0','2.5','3.0','3.5','4.0','4.5+']
    counts, _ = np.histogram(comp['rating'].dropna(), bins=bins)
    return jsonify({'buckets': labels, 'counts': counts.tolist()})

# ── Raw trips (paginated) ─────────────────────────────────────────────────────
@app.route('/api/trips')
def api_trips():
    page     = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 20))
    category = request.args.get('category','')
    zone     = request.args.get('zone','')
    status   = request.args.get('status','')

    df = DF.copy()
    if category: df = df[df['category'] == category]
    if zone:     df = df[(df['pickup_zone']==zone)|(df['dropoff_zone']==zone)]
    if status == 'completed':  df = df[df['cancelled']==False]
    if status == 'cancelled':  df = df[df['cancelled']==True]

    total  = len(df)
    df     = df.sort_values('timestamp', ascending=False)
    chunk  = df.iloc[(page-1)*per_page : page*per_page]

    cols   = ['trip_id','timestamp','pickup_zone','dropoff_zone','category',
              'distance_mi','duration_min','fare','surge_multiplier','cancelled','rating']
    rows   = chunk[cols].fillna('').to_dict('records')
    for r in rows:
        r['cancelled'] = bool(r['cancelled'])
        if r['rating'] == '': r['rating'] = None

    return jsonify({
        'trips':    rows,
        'total':    int(total),
        'page':     page,
        'per_page': per_page,
        'pages':    int(np.ceil(total/per_page))
    })

# ── Filter options ────────────────────────────────────────────────────────────
@app.route('/api/filters')
def api_filters():
    return jsonify({
        'categories': sorted(DF['category'].unique().tolist()),
        'zones':      sorted(DF['pickup_zone'].unique().tolist()),
    })

# ── Stats summary ────────────────────────────────────────────────────────────
@app.route('/api/stats')
def api_stats():
    comp = completed(DF)
    return jsonify({
        'fare': {
            'min':    round(float(comp['fare'].min()),2),
            'max':    round(float(comp['fare'].max()),2),
            'mean':   round(float(comp['fare'].mean()),2),
            'median': round(float(comp['fare'].median()),2),
            'std':    round(float(comp['fare'].std()),2),
            'p25':    round(float(comp['fare'].quantile(0.25)),2),
            'p75':    round(float(comp['fare'].quantile(0.75)),2),
            'p95':    round(float(comp['fare'].quantile(0.95)),2),
        },
        'distance': {
            'min':    round(float(comp['distance_mi'].min()),2),
            'max':    round(float(comp['distance_mi'].max()),2),
            'mean':   round(float(comp['distance_mi'].mean()),2),
            'median': round(float(comp['distance_mi'].median()),2),
        },
        'duration': {
            'min':    int(comp['duration_min'].min()),
            'max':    int(comp['duration_min'].max()),
            'mean':   round(float(comp['duration_min'].mean()),1),
            'median': round(float(comp['duration_min'].median()),1),
        },
        'total_records': len(DF),
    })

# ── Health check ──────────────────────────────────────────────────────────────
@app.route('/api/health')
def api_health():
    return jsonify({'status':'ok','records': len(DF), 'timestamp': datetime.now().isoformat()})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
