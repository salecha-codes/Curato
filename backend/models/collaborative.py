"""User-user cosine similarity on raw ratings; weighted rating predictions."""
import numpy as np
from scipy.sparse import diags


class UserCollaborative:
    def __init__(self, matrix, means, fallback, neighbors=20):
        self.matrix, self.means, self.fallback = matrix, means, fallback
        self.neighbors = neighbors
        norm = np.sqrt(np.asarray(matrix.multiply(matrix).sum(axis=1)).ravel())
        self.normalized = diags(np.divide(1., norm, out=np.zeros_like(norm), where=norm > 0)) @ matrix

    def predict(self, index):
        if index is None:
            return self.fallback.copy(), []
        similarities = (self.normalized @ self.normalized.getrow(index).T).toarray().ravel()
        similarities[index] = 0
        # At least two shared ratings avoids one-overlap coincidences.
        binary = self.matrix.copy()
        binary.data[:] = 1
        overlap = (binary @ binary.getrow(index).T).toarray().ravel()
        similarities[overlap < 2] = 0
        order = np.argsort(-similarities)
        order = order[similarities[order] > 0][:self.neighbors]
        if not len(order):
            return self.fallback.copy(), []
        weights = similarities[order]
        neighbors = self.matrix[order]
        mask = neighbors.copy(); mask.data[:] = 1
        denom = np.asarray(mask.T @ weights).ravel()
        numer = np.asarray(neighbors.T @ weights).ravel()
        predictions = np.divide(numer, denom, out=self.fallback.copy(), where=denom > 0)
        details = [{'index': int(u), 'similarity': round(float(similarities[u]), 4), 'overlap': int(overlap[u])} for u in order]
        return np.clip(predictions, 1, 5), details
