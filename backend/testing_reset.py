"""Recoverable reset of this single-process local testing workspace."""
import sqlite3
from contextlib import closing
from typing import Literal
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from backend import config, store

router = APIRouter()
RESET_PATH = '/api/testing/restart'
TABLES = ('cases', 'conversations', 'f005_drafts', 'advisor_history', 'journey_history', 'ocr_cache')
FOLDERS = ('uploads', 'form-previews', 'form-generated', 'form-uploads', 'generated')
active_writes = 0
resetting = False


async def reset_guard(request, call_next):
    # Bookkeeping has no await: each transition is atomic on the server event loop.
    global active_writes, resetting
    is_reset = request.url.path == RESET_PATH and request.method == 'POST'
    is_write = request.url.path.startswith('/api/') and request.method not in ('GET', 'HEAD', 'OPTIONS')
    if is_reset:
        if resetting or active_writes:
            return JSONResponse({'detail': 'Une opération est encore en cours. Attendez sa fin, puis réessayez Restart.'}, status_code=409)
        resetting = True
    elif is_write:
        if resetting:
            return JSONResponse({'detail': 'Le redémarrage des tests est en cours. Réessayez ensuite.'}, status_code=409)
        active_writes += 1
    try:
        return await call_next(request)
    finally:
        if is_reset:
            resetting = False
        elif is_write:
            active_writes -= 1


class Restart(BaseModel):
    confirmation: Literal['restart-testing']


@router.post(RESET_PATH)
def restart(body: Restart):
    data = config.DATA.resolve()
    if data != store.DATA.resolve() or not (data / 'dossier.sqlite').is_file():
        raise HTTPException(409, 'Le stockage des dossiers est indisponible. Aucun fichier n’a été modifié.')
    with store.LOCK:
        # Resolve the exact allowlisted children before moving any files.
        targets = []
        for name in FOLDERS:
            target = data / name
            if target.exists():
                if target.resolve().parent != data or target.is_symlink() or target.is_junction():
                    raise HTTPException(409, 'Un répertoire de données pointe hors du stockage local. Redémarrage annulé.')
                targets.append(target)
        backup_root = data / 'testing-backups'
        if backup_root.resolve().parent != data or backup_root.is_symlink() or backup_root.is_junction():
            raise HTTPException(409, 'Répertoire de sauvegarde invalide.')
        backup = backup_root / ('restart-' + uuid4().hex)
        backup.mkdir(parents=True)
        moved = []
        try:
            with closing(store.connect()) as db:
                count = db.execute('SELECT count(*) FROM cases').fetchone()[0]
                with closing(sqlite3.connect(backup / 'dossier.sqlite')) as archive:
                    db.backup(archive)
                tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                with db:
                    db.execute('BEGIN IMMEDIATE')
                    for target in targets:
                        target.rename(backup / target.name)
                        moved.append(target)
                    for table in TABLES:
                        if table in tables:
                            db.execute('DELETE FROM ' + table)
        except Exception:
            for target in reversed(moved):
                (backup / target.name).rename(target)
            raise HTTPException(500, 'Le redémarrage a échoué ; les données ont été conservées.') from None
        return {'status': 'reset', 'deleted_cases': count, 'backup': backup.name}
