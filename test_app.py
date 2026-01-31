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
