import asyncio
import sqlite3
from pathlib import Path
from types import SimpleNamespace
import pytest
from fastapi.testclient import TestClient
from backend import config, main, store, testing_reset


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(store, 'DATA', tmp_path)
    monkeypatch.setattr(config, 'DATA', tmp_path)
    monkeypatch.setattr(main, 'list_sources', lambda: [])
    with TestClient(main.app) as client:
        client.post('/api/cases', json={'company': 'TEST TO RESET'})
        yield client


def test_restart_clears_all_test_tables_preserves_references_and_backup(client, tmp_path):
    with store.connect() as db:
        for table in testing_reset.TABLES[2:]:
            db.execute(f'CREATE TABLE IF NOT EXISTS {table} (id TEXT, payload TEXT)')
            db.execute(f'INSERT INTO {table} VALUES (?, ?)', ('test', '{}'))
    for folder in testing_reset.FOLDERS:
        (tmp_path / folder).mkdir()
        (tmp_path / folder / 'fixture.txt').write_text('test file')
    (tmp_path / 'sources.sqlite').write_bytes(b'reference database untouched')
    (tmp_path / 'source-snapshots').mkdir()
    (tmp_path / 'source-snapshots' / 'source.txt').write_text('RNE reference')
    assert client.post('/api/testing/restart', json={}).status_code == 422
    assert len(client.get('/api/cases').json()) == 1
    result = client.post('/api/testing/restart', json={'confirmation': 'restart-testing'})
    assert result.status_code == 200, result.text
    assert result.json()['deleted_cases'] == 1
    assert client.get('/api/cases').json() == []
    with store.connect() as db:
        assert all(db.execute(f'SELECT count(*) FROM {t}').fetchone()[0] == 0 for t in testing_reset.TABLES)
    backup = tmp_path / 'testing-backups' / result.json()['backup']
    with sqlite3.connect(backup / 'dossier.sqlite') as archived:
        assert archived.execute('SELECT count(*) FROM cases').fetchone()[0] == 1
    for folder in testing_reset.FOLDERS:
        assert not (tmp_path / folder).exists()
        assert (backup / folder / 'fixture.txt').read_text() == 'test file'
    assert (tmp_path / 'sources.sqlite').read_bytes() == b'reference database untouched'
    assert (tmp_path / 'source-snapshots' / 'source.txt').read_text() == 'RNE reference'
    assert client.post('/api/testing/restart', json={'confirmation': 'restart-testing'}).json()['deleted_cases'] == 0
    assert (backup / 'uploads' / 'fixture.txt').exists()


def test_move_failure_rolls_back_files_and_dossiers(client, tmp_path, monkeypatch):
    for folder in ('uploads', 'form-previews'):
        (tmp_path / folder).mkdir()
        (tmp_path / folder / 'fixture.txt').write_text('test file')
    original = Path.rename
    def fail_second(path, target):
        if path == tmp_path / 'form-previews':
            raise OSError('Simulated locked directory')
        return original(path, target)
    monkeypatch.setattr(Path, 'rename', fail_second)
    result = client.post('/api/testing/restart', json={'confirmation': 'restart-testing'})
    assert result.status_code == 500
    assert len(client.get('/api/cases').json()) == 1
    assert (tmp_path / 'uploads' / 'fixture.txt').exists()
    assert (tmp_path / 'form-previews' / 'fixture.txt').exists()


@pytest.mark.anyio
async def test_reset_rejects_inflight_writes_and_resumes_afterwards():
    entered, finish = asyncio.Event(), asyncio.Event()
    async def slow(request):
        entered.set()
        await finish.wait()
        return 'done'
    async def next_call(request):
        return 'allowed'
    write = SimpleNamespace(url=SimpleNamespace(path='/api/cases/a/journey'), method='POST')
    restart = SimpleNamespace(url=SimpleNamespace(path=testing_reset.RESET_PATH), method='POST')
    running = asyncio.create_task(testing_reset.reset_guard(write, slow))
    await entered.wait()
    blocked = await testing_reset.reset_guard(restart, next_call)
    assert blocked.status_code == 409
    finish.set()
    await running
    assert await testing_reset.reset_guard(restart, next_call) == 'allowed'
    assert testing_reset.active_writes == 0
    assert testing_reset.resetting is False
