"""Sparse truncated SVD of user-centered observed ratings.
Missing entries are zero residuals, not zero-star ratings. Predictions are generated
per user, avoiding a dense users x items prediction matrix.
"""
import numpy as np
from scipy.sparse.linalg import svds


class SVDModel:
    def __init__(self, matrix, means, fallback, factors=12):
        self.means, self.fallback = means, fallback
        self.u = self.s = self.vt = None
        self.factors = 0
        limit = min(matrix.shape)
        if limit < 2 or not matrix.nnz:
            return
        residual = matrix.copy().astype(float)
        residual.data -= np.repeat(means, np.diff(residual.indptr))
        if not np.any(residual.data):
            return
        k = min(factors, limit-1)
        u, s, vt = svds(residual, k=k, random_state=42)
        order = np.argsort(-s)
        self.u, self.s, self.vt = u[:, order], s[order], vt[order]
        self.factors = k
        self.cold_items = np.asarray((matrix != 0).sum(axis=0)).ravel() == 0

    def predict(self, index):
        if index is None or self.u is None:
            return self.fallback.copy()
        predicted = (self.u[index]*self.s) @ self.vt + self.means[index]
        predicted[self.cold_items] = self.fallback[self.cold_items]
        return np.clip(predicted, 1, 5)
