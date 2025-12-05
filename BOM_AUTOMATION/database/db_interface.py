"""
Minimal DB interface stub for symbol templates and detection storage.
This uses pymongo if available; otherwise keeps an in-memory fallback for tests.
"""

from typing import Dict, List, Optional
import time

try:
    from pymongo import MongoClient
except Exception:
    MongoClient = None

class InMemoryDB:
    def __init__(self):
        self.templates = {}
        self.detections = {}
    def add_template(self, name, blob):
        self.templates[name] = {'name': name, 'blob': blob, 'created_at': time.time()}
    def list_templates(self):
        return [{'symbol_name': k} for k in self.templates.keys()]
    def get_template(self, name):
        return self.templates.get(name)
    def store_detection(self, filename, results):
        did = str(len(self.detections) + 1)
        self.detections[did] = {'filename': filename, 'results': results, 'timestamp': time.time()}
        return did

class DBInterface:
    def __init__(self, uri: Optional[str] = None, dbname: str = 'symbol_db'):
        if MongoClient is None or uri is None:
            self._db = InMemoryDB()
            self._mode = 'memory'
        else:
            self._client = MongoClient(uri)
            self._db = self._client[dbname]
            self._mode = 'mongo'

    def add_template(self, name: str, blob: bytes):
        if self._mode == 'memory':
            self._db.add_template(name, blob)
        else:
            self._db['symbol_templates'].update_one({'symbol_name': name}, {'$set': {'blob': blob}}, upsert=True)

    def list_templates(self) -> List[Dict]:
        if self._mode == 'memory':
            return self._db.list_templates()
        else:
            return list(self._db['symbol_templates'].find({}, {'symbol_name': 1, '_id': 0}))

    def get_template(self, name: str):
        if self._mode == 'memory':
            return self._db.get_template(name)
        else:
            return self._db['symbol_templates'].find_one({'symbol_name': name})

    def store_detection(self, filename: str, results: Dict) -> str:
        if self._mode == 'memory':
            return self._db.store_detection(filename, results)
        else:
            res = self._db['symbol_detections'].insert_one({'filename': filename, 'results': results})
            return str(res.inserted_id)
