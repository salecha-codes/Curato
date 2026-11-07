"""Shared matrix representation and prediction interface for all three methods."""
import time
import numpy as np
from scipy.sparse import csr_matrix
from . import popularity
from .collaborative import UserCollaborative
from .svd import SVDModel

METHODS = {'popularity', 'collaborative', 'svd'}


class RecommendationEngine:
    def __init__(self, ratings, users=None, items=None):
        start = time.perf_counter()
        self.users = sorted(ratings.user_id.unique()) if users is None else users
        self.items = sorted(ratings.product_id.unique()) if items is None else items
        self.user_index = {u:i for i,u in enumerate(self.users)}
        self.item_index = {p:i for i,p in enumerate(self.items)}
        self.matrix = csr_matrix((ratings.rating.to_numpy(float),
                                 ([self.user_index[u] for u in ratings.user_id], [self.item_index[p] for p in ratings.product_id])),
                                 shape=(len(self.users),len(self.items)))
        self.popularity, self.averages, self.counts, self.global_mean = popularity.fit(self.matrix)
        counts = np.diff(self.matrix.indptr)
        self.means = np.divide(np.asarray(self.matrix.sum(axis=1)).ravel(), counts,
                               out=np.full(len(self.users), self.global_mean), where=counts > 0)
        self.cf = UserCollaborative(self.matrix, self.means, self.popularity)
        self.svd = SVDModel(self.matrix, self.means, self.popularity)
        self.training_ms = round((time.perf_counter()-start)*1000, 1)

    def predict(self, user_id, method):
        if method not in METHODS:
            raise ValueError('Unknown method. Choose popularity, collaborative, or svd.')
        index = self.user_index.get(user_id)
        neighbors = []
        if index is None or method == 'popularity':
            scores = self.popularity.copy()
        elif method == 'collaborative':
            scores, neighbors = self.cf.predict(index)
        else:
            scores = self.svd.predict(index)
        return scores, neighbors

    def recommend(self, user_id, method, n=8, min_ratings=1):
        scores, neighbors = self.predict(user_id, method)
        seen = set()
        if user_id in self.user_index:
            seen = set(self.matrix.getrow(self.user_index[user_id]).indices)
        eligible = [i for i in range(len(self.items)) if i not in seen and self.counts[i] >= min_ratings]
        ordered = sorted(eligible, key=lambda i: (-scores[i], self.items[i]))[:n]
        return [{'product_id':self.items[i], 'score':round(float(scores[i]),4),
                 'average_rating':round(float(self.averages[i]),2), 'rating_count':int(self.counts[i])} for i in ordered], neighbors
