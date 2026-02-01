import json
import os
import subprocess
from flask import Flask, render_template, abort

app = Flask(__name__)

def get_commit_sha():
    sha = os.environ.get('SOURCE_VERSION', '')
    if not sha:
        try:
            sha = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
        except Exception:
            sha = ''
    return sha[:7] if sha else 'dev'

COMMIT_SHA = get_commit_sha()

@app.context_processor
def inject_globals():
    return {'commit_sha': COMMIT_SHA}

def load_data():
    with open('data.json') as f:
        return json.load(f)

@app.route('/')
def index():
    data = load_data()
    arc_data = {a['slug']: a for a in data['arcs']}
    threat_order = ['extreme', 'critical', 'high', 'moderate', 'low']
    grouped = {level: [] for level in threat_order}
    for arc in data['arc_list']:
        slug = arc['slug']
        arc['has_data'] = slug in arc_data and bool(arc_data[slug].get('strategies'))
        arc['best'] = None
        if slug in arc_data:
            best_strategy = next((s for s in arc_data[slug].get('strategies', []) if s.get('best')), None)
            if best_strategy:
                items = best_strategy['items']
                name = ' + '.join(f"{item['units']}x {item['name']}" for item in items) if len(items) > 1 else items[0]['name']
                units = items[0]['units'] if len(items) == 1 else None
                arc['best'] = {'name': name, 'units': units, 'notes': best_strategy.get('notes', '')}
        grouped[arc['threat_level']].append(arc)
    return render_template('index.html', grouped_arcs=grouped, threat_order=threat_order)

@app.route('/arc/<slug>')
def arc_detail(slug):
    data = load_data()
    arc = next((a for a in data['arcs'] if a['slug'] == slug), None)
    if not arc:
        arc_info = next((a for a in data['arc_list'] if a['slug'] == slug), None)
        if arc_info:
            arc = {**arc_info, 'strategies': []}
        else:
            abort(404)
    return render_template('arc_detail.html', arc=arc)

if __name__ == '__main__':
    app.run(debug=True)
