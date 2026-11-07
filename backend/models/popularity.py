"""Bayesian weighted rating reduces the influence of very small review counts."""
import numpy as np


def fit(matrix, prior_count=10):
    counts = np.asarray((matrix != 0).sum(axis=0)).ravel()
    sums = np.asarray(matrix.sum(axis=0)).ravel()
    mean = matrix.data.mean() if matrix.nnz else 3.0
    averages = np.divide(sums, counts, out=np.full(len(counts), mean), where=counts > 0)
    weighted = (sums + prior_count*mean)/(counts+prior_count)
    return weighted, averages, counts, float(mean)
