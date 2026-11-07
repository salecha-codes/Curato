"""Flask JSON API and same-origin frontend. Run with python run.py."""
from pathlib import Path
from threading import RLock
from io import StringIO
import csv
import math
import numpy as np
from flask import Flask, request, jsonify, send_from_directory, Response, g
from werkzeug.exceptions import HTTPException
from .store import Store


def create_app(root=None):
    root = Path(root or Path(__file__).resolve().parents[1])
    app = Flask(__name__,static_folder=None)
    app.config['MAX_CONTENT_LENGTH']=3*1024*1024
    store = Store(root)
    app.config['STORE']=store
    lock = RLock()

    API_PREFIXES = ('/api/', '/overview', '/users', '/matrix', '/profile', '/catalog', '/recommendations', '/ratings', '/dataset', '/data/')

    def is_api():
        return any(request.path.startswith(p) for p in API_PREFIXES)

    @app.before_request
    def before():
        if is_api():
            lock.acquire();g.locked=True

    @app.teardown_request
    def after(error):
        if getattr(g,'locked',False):lock.release()

    @app.after_request
    def headers(response):
        response.headers['X-Content-Type-Options']='nosniff'
        if is_api():response.headers['Cache-Control']='no-store'
        return response

    @app.errorhandler(ValueError)
    def invalid(error):return jsonify(error=str(error)),400

    @app.errorhandler(HTTPException)
    def http_error(error):
        if is_api():
            return jsonify(error='Upload is too large. Maximum request size is 3 MB.' if error.code==413 else error.description),error.code
        return error

    def integer(key, default, low, high):
        try:v=int(request.args.get(key,default))
        except (TypeError,ValueError):raise ValueError(f'{key} must be an integer.')
        if not low<=v<=high:raise ValueError(f'{key} must be between {low} and {high}.')
        return v

    def catalog_record(pid):
        p=dict(store.by_id[pid]);i=store.engine.item_index[pid]
        p.update(average_rating=round(float(store.engine.averages[i]),2),rating_count=int(store.engine.counts[i]))
        return p

    @app.get('/api/overview')
    @app.get('/overview')
    def overview():
        r,e=store.ratings,store.engine
        histogram=r.rating.round().clip(1,5).value_counts()
        counts=r.groupby('product_id').size().sort_values(ascending=False).head(6)
        return jsonify(dataset=store.info,version=store.version,report=store.report,
                       users=len(e.users),products=len(e.items),ratings=len(r),average_rating=round(float(r.rating.mean()),2),
                       sparsity=round((1-e.matrix.nnz/(e.matrix.shape[0]*e.matrix.shape[1]))*100,2),
                       training_ms=e.training_ms,factors=e.svd.factors,
                       categories=sorted(set(p['category'] for p in store.catalog)),
                       rating_distribution=[{'rating':i,'count':int(histogram.get(i,0))} for i in range(1,6)],
                       popular_products=[{'name':store.by_id[pid]['name'],'count':int(count)} for pid,count in counts.items()],
                       singular_values=[] if e.svd.s is None else np.round(e.svd.s,3).tolist())

    @app.get('/api/users')
    @app.get('/users')
    def users():
        q=request.args.get('q','').lower()
        counts=store.ratings.groupby('user_id').rating.agg(['size','mean'])
        data=[{'user_id':u,'ratings':int(counts.loc[u,'size']),'average':round(float(counts.loc[u,'mean']),2)} for u in store.engine.users if q in u.lower()]
        return jsonify(users=data[:500],total=len(data),limit=500)

    @app.get('/api/matrix')
    @app.get('/matrix')
    def matrix():
        users=store.engine.users[:12];items=store.engine.items[:16]
        cells=store.engine.matrix[:len(users),:len(items)].toarray().tolist()
        return jsonify(users=users,products=items,values=cells)

    @app.get('/api/profile')
    @app.get('/profile')
    def profile():
        uid=request.args.get('user_id','NEW')
        rows=store.ratings[store.ratings.user_id==uid]
        history=[]
        for row in rows.itertuples(index=False):
            p=catalog_record(row.product_id);p['user_rating']=float(row.rating);history.append(p)
        return jsonify(user_id=uid,cold_start=rows.empty,ratings=history)

    @app.get('/api/catalog')
    @app.get('/catalog')
    def catalog():
        query=request.args.get('q','').lower();cat=request.args.get('category','All')
        records=[catalog_record(p['product_id']) for p in store.catalog if (cat=='All' or cat==p['category']) and query in (p['name']+' '+p['product_id']+' '+p['category']).lower()]
        return jsonify(products=records[:1000],total=len(records),limit=1000)

    def recommendation_data():
        uid=request.args.get('user_id','U001');method=request.args.get('method','svd')
        n=integer('top_n',8,1,30);minimum=integer('min_ratings',1,0,10000)
        rows,neighbors=store.engine.recommend(uid,method,len(store.engine.items),minimum)
        cold=uid not in store.engine.user_index
        fallback='popularity' if cold or (method=='collaborative' and not neighbors) or (method=='svd' and not store.engine.svd.factors) else None
        output=[]
        for row in rows:
            p=dict(store.by_id[row['product_id']]);p.update(row);p['method']=fallback or method
            if fallback or method=='popularity':p['reason']=f'Weighted community rating from {p["rating_count"]} ratings.'
            elif method=='collaborative':p['reason']=f'Similarity-weighted predictions from up to {len(neighbors)} nearby customers; unrated-by-neighbor items use popularity.'
            else:p['reason']=f'Predicted from {store.engine.svd.factors} latent factors in your rating history.'
            output.append(p)
        return {'user_id':uid,'method':method,'effective_method':fallback or method,'cold_start':cold,
                'fallback':fallback,'products':output[:n],'eligible_products':len(output),'version':store.version,
                'neighbors':[dict(x,user_id=store.engine.users[x['index']]) for x in neighbors[:8]],
                'explanation':'Scores are estimated 1–5 ratings, not confidence percentages. Already-rated products are excluded.'}

    @app.get('/api/recommendations')
    @app.get('/recommendations')
    def recommendations():return jsonify(recommendation_data())

    @app.get('/api/recommendations/export')
    @app.get('/recommendations/export')
    def export():
        data=recommendation_data();f=StringIO();writer=csv.writer(f)
        writer.writerow(['product_id','name','method','predicted_rating','rating_count'])
        def safe(s):
            s=str(s);return "'"+s if s.startswith(('=','+','-','@')) else s
        for p in data['products']:writer.writerow([safe(p['product_id']),safe(p['name']),data['effective_method'],p['score'],p['rating_count']])
        return Response(f.getvalue(),mimetype='text/csv',headers={'Content-Disposition':'attachment; filename=recommendations.csv'})

    @app.post('/api/ratings')
    @app.post('/ratings')
    def rate():
        body=request.get_json(silent=True) or {}
        uid=str(body.get('user_id','')).strip();pid=str(body.get('product_id','')).strip()
        if not uid or len(uid)>160:raise ValueError('Customer ID must be 1–160 characters.')
        if pid not in store.by_id:raise ValueError('Product ID is not in the active catalog.')
        try:rating=float(body.get('rating'))
        except (ValueError,TypeError):raise ValueError('Choose a rating from 1 to 5.')
        if not math.isfinite(rating) or not 1<=rating<=5:raise ValueError('Choose a rating from 1 to 5.')
        store.rate(uid,pid,rating)
        return jsonify(message='Rating saved to SQLite. Models retrained.',version=store.version)

    @app.post('/api/dataset')
    @app.post('/dataset')
    def upload():
        file=request.files.get('ratings')
        if not file:raise ValueError('Choose a ratings CSV first.')
        metadata=request.files.get('catalog')
        store.import_dataset(file.read(),metadata.read() if metadata and metadata.filename else None,Path(file.filename).name[:100])
        return jsonify(message='Dataset cleaned, loaded, and models trained.',report=store.report)

    @app.post('/api/dataset/sample')
    @app.post('/dataset/sample')
    def restore():
        store.restore_sample();return jsonify(message='Sample dataset restored. Saved sample ratings are retained.')

    @app.get('/api/data/<kind>')
    @app.get('/data/<kind>')
    def download(kind):
        if kind not in ['ratings','products']:return jsonify(error='Unknown sample file'),404
        return send_from_directory(root/'data',f'{kind}.csv',as_attachment=True)

    @app.get('/')
    def index():return send_from_directory(root/'public','index.html')

    @app.get('/<path:path>')
    def frontend(path):
        target = root/'public'/path
        if target.is_file():
            return send_from_directory(root/'public',path)
        if path.startswith('api/') or is_api():
            return jsonify(error='Endpoint not found'),404
        return send_from_directory(root/'public','index.html')

    return app
