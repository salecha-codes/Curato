"""Dataset state and SQLite rating overrides. Fitting is atomic before activation."""
from pathlib import Path
import os
import sqlite3
import json
import hashlib
import pandas as pd
from .data import read_ratings, read_catalog
from .models import RecommendationEngine


class Store:
    def __init__(self, root):
        self.root = Path(root)
        self.data_dir = self.root/'data'
        # Vercel's deployed source is read-only; use its writable temporary directory.
        # Local development continues to use the ignored runtime/ directory.
        self.runtime = Path('/tmp/curato-ai') if os.environ.get('VERCEL') else self.root/'runtime'
        self.runtime.mkdir(parents=True, exist_ok=True)
        self.db = self.runtime/'ratings.sqlite3'
        with sqlite3.connect(self.db) as db:
            db.execute('CREATE TABLE IF NOT EXISTS ratings (dataset_id TEXT, user_id TEXT, product_id TEXT, rating REAL, PRIMARY KEY(dataset_id,user_id,product_id))')
        self.active = self.runtime/'active.json'
        self.load()

    def load(self):
        info = json.loads(self.active.read_text()) if self.active.exists() else None
        ratings_path = self.runtime/'imported.csv' if info else self.data_dir/'ratings.csv'
        metadata = self.runtime/'catalog.csv' if info and (self.runtime/'catalog.csv').exists() else None if info else self.data_dir/'products.csv'
        base,report = read_ratings(ratings_path)
        self.dataset_id = report['dataset_id']
        if info and 'cleaning_report' in info: report=info['cleaning_report']
        with sqlite3.connect(self.db) as db:
            updates = pd.read_sql_query('SELECT user_id,product_id,rating FROM ratings WHERE dataset_id=?',db,params=(self.dataset_id,))
        ratings = (pd.concat([base,updates]) if not updates.empty else base).drop_duplicates(['user_id','product_id'],keep='last').reset_index(drop=True)
        catalog = read_catalog(metadata, ratings.product_id)
        self.activate(ratings,catalog,report,info or json.loads((self.data_dir/'dataset_info.json').read_text()))

    def activate(self, ratings, catalog, report, info):
        engine = RecommendationEngine(ratings)
        self.ratings, self.catalog, self.report, self.info, self.engine = ratings,catalog,report,info,engine
        self.by_id = {p['product_id']:p for p in catalog}
        self.version = hashlib.sha256(ratings.to_csv(index=False).encode()).hexdigest()[:12]

    def import_dataset(self, ratings_bytes, metadata_bytes, name):
        from io import BytesIO
        ratings,report = read_ratings(BytesIO(ratings_bytes))
        catalog = read_catalog(BytesIO(metadata_bytes) if metadata_bytes else None,ratings.product_id)
        info = {'name':name,'source':'User-imported CSV. Product metadata is optional.','synthetic':None,'cleaning_report':report}
        # Fit before changing the active dataset, so invalid imports leave it intact.
        engine = RecommendationEngine(ratings)
        (self.runtime/'imported.csv').write_text(ratings.to_csv(index=False))
        pd.DataFrame(catalog).to_csv(self.runtime/'catalog.csv',index=False)
        self.active.write_text(json.dumps(info))
        self.dataset_id = report['dataset_id']
        self.ratings,self.catalog,self.report,self.info,self.engine=ratings,catalog,report,info,engine
        self.by_id = {p['product_id']:p for p in catalog}
        self.version = hashlib.sha256(ratings.to_csv(index=False).encode()).hexdigest()[:12]

    def rate(self, uid, pid, rating):
        rows = self.ratings.copy()
        mask = (rows.user_id==uid)&(rows.product_id==pid)
        if mask.any(): rows.loc[mask,'rating']=rating
        else: rows = pd.concat([rows,pd.DataFrame([{'user_id':uid,'product_id':pid,'rating':rating}])],ignore_index=True)
        # Train first, then persist and swap; a failed training cannot corrupt the active model.
        engine = RecommendationEngine(rows)
        with sqlite3.connect(self.db) as db:
            db.execute('INSERT OR REPLACE INTO ratings VALUES (?,?,?,?)',(self.dataset_id,uid,pid,rating))
        self.ratings,self.engine=rows,engine
        self.version=hashlib.sha256(rows.to_csv(index=False).encode()).hexdigest()[:12]

    def restore_sample(self):
        if self.active.exists(): self.active.unlink()
        self.load()
