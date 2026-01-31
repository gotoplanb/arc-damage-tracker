import json
from flask import Flask, render_template, abort

app = Flask(__name__)

def load_data():
    with open('data.json') as f:
        return json.load(f)

@app.route('/')
def index():
    data = load_data()
    arcs_with_data = {a['slug'] for a in data['arcs']
                      if a['damage']['weapons'] or a['damage']['explosives']}
    threat_order = ['extreme', 'critical', 'high', 'moderate', 'low']
    grouped = {level: [] for level in threat_order}
    for arc in data['arc_list']:
        arc['has_data'] = arc['slug'] in arcs_with_data
        grouped[arc['threat_level']].append(arc)
    return render_template('index.html', grouped_arcs=grouped, threat_order=threat_order)

@app.route('/arc/<slug>')
def arc_detail(slug):
    data = load_data()
    arc = next((a for a in data['arcs'] if a['slug'] == slug), None)
    if not arc:
        arc_info = next((a for a in data['arc_list'] if a['slug'] == slug), None)
        if arc_info:
            arc = {**arc_info, 'damage': {'weapons': {}, 'explosives': {}}}
        else:
            abort(404)
    return render_template('arc_detail.html', arc=arc)

if __name__ == '__main__':
    app.run(debug=True)
