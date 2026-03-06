from flask import Flask, render_template_string, request
from main import scrape_tracking, load_csv
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

app = Flask(__name__)

HTML = """
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Suivi de Colis</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Segoe UI', Arial, sans-serif; background: #f0f2f5; min-height: 100vh; }

        .header { background: linear-gradient(135deg, #667eea, #764ba2); padding: 30px 20px; text-align: center; color: white; }
        .header h1 { font-size: 1.8rem; margin-bottom: 8px; }
        .header p { opacity: 0.85; font-size: 0.95rem; }

        .search-box { max-width: 600px; margin: -25px auto 30px; background: white; border-radius: 12px;
                       box-shadow: 0 4px 20px rgba(0,0,0,0.1); padding: 20px; display: flex; gap: 10px; }
        .search-box input { flex: 1; padding: 12px 16px; border: 2px solid #e0e0e0; border-radius: 8px;
                            font-size: 1rem; outline: none; transition: border-color 0.2s; }
        .search-box input:focus { border-color: #667eea; }
        .search-box button { padding: 12px 24px; background: #667eea; color: white; border: none;
                             border-radius: 8px; font-size: 1rem; cursor: pointer; transition: background 0.2s; }
        .search-box button:hover { background: #5a6fd6; }

        .container { max-width: 700px; margin: 0 auto 40px; padding: 0 20px; }

        .parcel-info { background: white; border-radius: 12px; padding: 20px; margin-bottom: 24px;
                       box-shadow: 0 2px 10px rgba(0,0,0,0.06); }
        .parcel-info h2 { color: #333; font-size: 1.1rem; }
        .parcel-info .number { color: #667eea; font-weight: 700; font-size: 1.2rem; }
        .parcel-info .summary { margin-top: 8px; color: #888; font-size: 0.9rem; }

        .timeline { position: relative; padding-left: 30px; }
        .timeline::before { content: ''; position: absolute; left: 10px; top: 0; bottom: 0;
                            width: 3px; background: #e0e0e0; border-radius: 2px; }

        .event { position: relative; margin-bottom: 24px; background: white; border-radius: 10px;
                 padding: 16px 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.05); transition: transform 0.2s; }
        .event:hover { transform: translateX(4px); }
        .event::before { content: ''; position: absolute; left: -26px; top: 20px; width: 13px; height: 13px;
                         background: #667eea; border: 3px solid white; border-radius: 50%;
                         box-shadow: 0 0 0 2px #667eea; }
        .event:first-child::before { background: #27ae60; box-shadow: 0 0 0 2px #27ae60; width: 15px; height: 15px; left: -27px; }

        .event-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; }
        .event-status { font-weight: 600; color: #333; font-size: 0.95rem; }
        .event-datetime { color: #999; font-size: 0.82rem; white-space: nowrap; }
        .event-details { display: flex; gap: 16px; color: #777; font-size: 0.85rem; }
        .event-details span::before { margin-right: 4px; }
        .location::before { content: '📍'; }
        .carrier-name::before { content: '🚚'; }

        .no-data { text-align: center; padding: 60px 20px; color: #999; }
        .no-data .icon { font-size: 3rem; margin-bottom: 12px; }

        .loading { display: none; text-align: center; padding: 40px; color: #667eea; }
        .loading.active { display: block; }
        .spinner { width: 40px; height: 40px; border: 4px solid #e0e0e0; border-top: 4px solid #667eea;
                   border-radius: 50%; animation: spin 0.8s linear infinite; margin: 0 auto 12px; }
        @keyframes spin { to { transform: rotate(360deg); } }

        .error { background: #fff5f5; border: 1px solid #fed7d7; color: #c53030; border-radius: 10px;
                 padding: 16px 20px; margin-bottom: 20px; }
    </style>
</head>
<body>
    <div class="header">
        <h1>📦 Suivi de Colis</h1>
        <p>Entrez votre numéro de suivi pour voir l'état de votre colis</p>
    </div>

    <form class="search-box" method="POST">
        <input type="text" name="track_number" placeholder="Numéro de suivi"
               value="{{ track_number or '' }}" required>
        <button type="submit">Suivre</button>
    </form>

    <div class="container">
        {% if error %}
        <div class="error">{{ error }}</div>
        {% endif %}

        {% if events %}
        <div class="parcel-info">
            <h2>Colis <span class="number">{{ track_number }}</span></h2>
            <div class="summary">{{ events | length }} événement(s) — Dernier statut : {{ events[0].status or 'Inconnu' }}</div>
        </div>

        <div class="timeline">
            {% for e in events %}
            <div class="event">
                <div class="event-header">
                    <span class="event-status">{{ e.status or 'Statut inconnu' }}</span>
                    <span class="event-datetime">{{ e.date or '' }} {{ e.time or '' }}</span>
                </div>
                <div class="event-details">
                    {% if e.location %}<span class="location">{{ e.location }}</span>{% endif %}
                    {% if e.carrier %}<span class="carrier-name">{{ e.carrier }}</span>{% endif %}
                </div>
            </div>
            {% endfor %}
        </div>

        {% elif track_number and not error %}
        <div class="no-data">
            <div class="icon">📭</div>
            <p>Aucun événement trouvé pour ce numéro de suivi.</p>
        </div>
        {% endif %}
    </div>
</body>
</html>
"""


@app.route("/", methods=["GET", "POST"])
def index():
    track_number = None
    events = []
    error = None

    if request.method == "POST":
        track_number = request.form.get("track_number", "").strip()
        if track_number:
            try:
                events = scrape_tracking(track_number)
            except Exception as e:
                logger.error(f"Scraping failed: {e}")
                # Fallback : essayer de charger depuis le CSV existant
                events = load_csv(track_number)
                if not events:
                    error = f"Impossible de récupérer les données. Réessayez plus tard."

    return render_template_string(HTML, track_number=track_number, events=events, error=error)


if __name__ == "__main__":
    app.run(debug=True)