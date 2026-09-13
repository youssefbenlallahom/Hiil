"""Public-source snapshots and exact-passage retrieval; no authored legal answers."""
import asyncio
import hashlib
import io
import json
import re
import sqlite3
import threading
import unicodedata
from contextlib import closing
from pathlib import Path
from urllib.parse import urlparse, urljoin
from urllib.robotparser import RobotFileParser

import httpx
from pypdf import PdfReader
from backend import config, store

MANIFEST = Path(__file__).parent / 'assets' / 'source-manifest.json'
LOCK = threading.RLock()
REFRESH_LOCK = asyncio.Lock()
USER_AGENT = 'DossierTN/1.0'
MAX_BYTES = 12 * 1024 * 1024


def normalize(text: str) -> str:
    return ' '.join(''.join(c for c in unicodedata.normalize('NFKD', text.casefold()) if not unicodedata.combining(c)).split())


def manifest():
    return json.loads(MANIFEST.read_text(encoding='utf-8-sig'))


def connection():
    config.DATA.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(config.DATA / 'sources.sqlite', timeout=15)
    db.row_factory = sqlite3.Row
    db.execute('CREATE TABLE IF NOT EXISTS sources (id TEXT PRIMARY KEY, payload TEXT NOT NULL)')
    db.execute('CREATE VIRTUAL TABLE IF NOT EXISTS passages USING fts5(source_id UNINDEXED, page UNINDEXED, text, tokenize="unicode61 remove_diacritics 2")')
    return db


def pages_from(content, mime):
    if mime == 'application/pdf':
        reader = PdfReader(io.BytesIO(content))
        if reader.is_encrypted or len(reader.pages) > 150:
            raise ValueError('PDF chiffré ou trop volumineux pour ce corpus.')
        pages = [{'page': i + 1, 'text': p.extract_text() or ''} for i, p in enumerate(reader.pages)]
    else:
        import trafilatura
        result = trafilatura.extract(content, include_tables=True, include_comments=False, favor_precision=True)
        pages = [{'page': 1, 'text': result or ''}]
    if sum(len(p['text'].strip()) for p in pages) < 80:
        raise ValueError('Texte insuffisant : cette référence nécessite une vérification ou un OCR.')
    return pages


def record(entry, content, mime, provenance, headers=None):
    pages = pages_from(content, mime)
    digest = hashlib.sha256(content).hexdigest()
    folder = config.DATA / 'source-snapshots'
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / digest
    if not path.exists():
        path.write_bytes(content)
    with LOCK, closing(connection()) as db, db:
        row = db.execute('SELECT payload FROM sources WHERE id=?', (entry['id'],)).fetchone()
        old = json.loads(row['payload']) if row else {}
        item = {**entry, 'hash': digest, 'content_type': mime, 'provenance': provenance,
                'retrieved_at': store.now(), 'status': 'available', 'error': None, 'page_count': len(pages),
                'text': '\n\n'.join(p['text'] for p in pages), 'pages': pages,
                'etag': (headers or {}).get('etag'), 'last_modified': (headers or {}).get('last-modified'),
                'changed': bool(old.get('hash') and old['hash'] != digest),
                'previous_hash': old.get('hash') if old.get('hash') != digest else old.get('previous_hash')}
        db.execute('INSERT OR REPLACE INTO sources VALUES (?,?)', (entry['id'], json.dumps(item, ensure_ascii=False)))
        db.execute('DELETE FROM passages WHERE source_id=?', (entry['id'],))
        for page in pages:
            for offset in range(0, len(page['text']), 1400):
                passage = page['text'][offset:offset + 1800].strip()
                if passage:
                    db.execute('INSERT INTO passages(source_id,page,text) VALUES (?,?,?)', (entry['id'], page['page'], passage))
    return item


def bootstrap():
    with LOCK, closing(connection()) as db:
        existing = {r['id'] for r in db.execute('SELECT id FROM sources')}
        for entry in manifest():
            if entry.get('local_asset') and entry['id'] not in existing:
                path = MANIFEST.parent / entry['local_asset']
                record(entry, path.read_bytes(), 'application/pdf', 'supplied_document')


def list_sources():
    bootstrap()
    with closing(connection()) as db:
        current = {r['id']: json.loads(r['payload']) for r in db.execute('SELECT * FROM sources')}
    return [{**entry, **current.get(entry['id'], {'status': 'not_collected', 'retrieved_at': None, 'hash': None, 'pages': [], 'text': ''})} for entry in manifest()]


def retrieve(question: str, limit=5):
    available = {s['id']: s for s in list_sources()}
    stop = set('le la les de des du un une et ou en pour dans sur au aux est sont ce cette quel quelle quels quelles comment pourquoi mon ma mes je tu il elle vous nous que qui avec'.split())
    tokens = list(dict.fromkeys(t for t in re.findall(r'\w+', normalize(question)) if len(t) > 2 and t not in stop))[:24]
    if not tokens:
        return []
    query = ' OR '.join('"' + t.replace('"', '""') + '"' for t in tokens)
    with closing(connection()) as db:
        rows = db.execute('SELECT source_id,page,text,bm25(passages) AS rank FROM passages WHERE passages MATCH ? ORDER BY rank LIMIT ?', (query, limit)).fetchall()
    return [{**{k: v for k, v in available[r['source_id']].items() if k not in ('pages', 'text', 'local_asset')},
             'id': f"{r['source_id']}:{r['page']}:{hashlib.sha256(r['text'].encode()).hexdigest()[:10]}",
             'source_id': r['source_id'], 'page': int(r['page']), 'text': r['text']} for r in rows]


def validate_url(url):
    parsed = urlparse(url)
    hosts = {urlparse(e['url']).hostname for e in manifest()}
    if parsed.scheme != 'https' or parsed.hostname not in hosts or parsed.username or parsed.password or parsed.port not in (None, 443):
        raise ValueError('Adresse hors des domaines officiels autorisés.')


async def refresh_sources():
    """Explicit bounded collection; errors preserve the last readable snapshot."""
    async with REFRESH_LOCK:
        current = {s['id']: s for s in list_sources()}
        robots = {}
        async with httpx.AsyncClient(timeout=20, follow_redirects=False, headers={'User-Agent': USER_AGENT}) as http:
            for entry in manifest():
                try:
                    url = entry['url']
                    validate_url(url)
                    host = urlparse(url).netloc
                    if host not in robots:
                        response = await http.get('https://' + host + '/robots.txt')
                        if response.status_code in (401, 403, 429) or response.status_code >= 500:
                            raise ValueError('Collecte différée : politique robots indisponible.')
                        parser = RobotFileParser()
                        parser.parse(response.text.splitlines() if response.status_code == 200 else [])
                        robots[host] = parser
                    if not robots[host].can_fetch(USER_AGENT, url):
                        raise ValueError('La politique robots interdit cette collecte.')
                    old = current[entry['id']]
                    headers = {}
                    if old.get('etag'):
                        headers['If-None-Match'] = old['etag']
                    if old.get('last_modified'):
                        headers['If-Modified-Since'] = old['last_modified']
                    for redirect in range(4):
                        validate_url(url)
                        if not robots[host].can_fetch(USER_AGENT, url):
                            raise ValueError('La politique robots interdit cette adresse.')
                        async with http.stream('GET', url, headers=headers) as response:
                            if response.status_code in (301, 302, 303, 307, 308):
                                target = urljoin(url, response.headers.get('location', ''))
                                if urlparse(target).netloc != host:
                                    raise ValueError('Redirection vers un autre domaine : collecte suspendue.')
                                url = target
                                continue
                            if response.status_code == 304:
                                with LOCK, closing(connection()) as db, db:
                                    old.update(status='available', error=None, retrieved_at=store.now())
                                    db.execute('INSERT OR REPLACE INTO sources VALUES (?,?)', (entry['id'], json.dumps(old, ensure_ascii=False)))
                                break
                            response.raise_for_status()
                            content = bytearray()
                            async for chunk in response.aiter_bytes():
                                content.extend(chunk)
                                if len(content) > MAX_BYTES:
                                    raise ValueError('Document supérieur à la limite de collecte.')
                            mime = response.headers.get('content-type', '').split(';')[0]
                            if bytes(content).startswith(b'%PDF-'):
                                mime = 'application/pdf'
                            if mime not in ('application/pdf', 'text/html'):
                                raise ValueError('Format de référence non pris en charge.')
                            await asyncio.to_thread(record, entry, bytes(content), mime, 'official_website', dict(response.headers))
                            break
                    else:
                        raise ValueError('Trop de redirections.')
                except Exception as error:
                    detail = str(error) if isinstance(error, ValueError) else (f'HTTP {error.response.status_code}' if isinstance(error, httpx.HTTPStatusError) else 'Source inaccessible. Réessayez ultérieurement.')
                    item = {**current[entry['id']], 'status': 'cached' if current[entry['id']].get('hash') else 'unavailable', 'error': detail, 'last_attempt_at': store.now()}
                    with LOCK, closing(connection()) as db, db:
                        db.execute('INSERT OR REPLACE INTO sources VALUES (?,?)', (entry['id'], json.dumps(item, ensure_ascii=False)))
                await asyncio.sleep(1)
        return list_sources()

