import pytest
from app import app, load_data

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_index_loads(client):
    rv = client.get('/')
    assert rv.status_code == 200
    assert b'Arc Raiders' in rv.data

def test_arc_detail_loads(client):
    rv = client.get('/arc/wasp')
    assert rv.status_code == 200

def test_invalid_arc_404(client):
    rv = client.get('/arc/nonexistent')
    assert rv.status_code == 404

def test_data_json_valid():
    data = load_data()
    assert 'arc_list' in data
    assert 'weapons' in data
    assert 'explosives' in data
    assert len(data['arc_list']) == 17

def test_arcs_have_strategies():
    data = load_data()
    for arc in data['arcs']:
        assert 'strategies' in arc, f"{arc['name']} missing strategies key"
        assert isinstance(arc['strategies'], list), f"{arc['name']} strategies should be a list"
        assert 'damage' not in arc, f"{arc['name']} still has old damage key"

def test_strategy_structure():
    data = load_data()
    for arc in data['arcs']:
        for i, strategy in enumerate(arc['strategies']):
            assert 'best' in strategy, f"{arc['name']} strategy {i} missing best"
            assert 'items' in strategy, f"{arc['name']} strategy {i} missing items"
            assert len(strategy['items']) > 0, f"{arc['name']} strategy {i} has no items"
            for item in strategy['items']:
                assert item['type'] in ('weapon', 'explosive'), f"{arc['name']} strategy {i} invalid item type"
                assert 'name' in item
                assert 'units' in item

def test_one_best_per_arc():
    data = load_data()
    for arc in data['arcs']:
        best_count = sum(1 for s in arc['strategies'] if s.get('best'))
        assert best_count <= 1, f"{arc['name']} has {best_count} best strategies"
