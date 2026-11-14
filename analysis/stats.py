"""Statistics with no third-party dependency.

Everything here is validated in ``tests/test_analysis.py`` against cases whose
answer is known independently (the exact Wilcoxon distribution for n <= 8 by
enumeration, the t distribution against published table values, a mixed model
against its closed form when the design is balanced).

Implemented:

* descriptives (n, mean, sd, median, IQR, min, max) and the mean's 95% CI;
* effect sizes: Cohen's dz and Hedges' g for paired data, the rank-biserial
  correlation for Wilcoxon, and the raw mean difference in the metric's units;
* confidence intervals: analytic (t) for the paired mean difference, and a
  deterministic percentile bootstrap for anything whose sampling distribution is
  not worth assuming;
* paired t test (two-sided), exact Wilcoxon signed-rank with a tie-corrected
  normal approximation when the exact distribution does not apply;
* a random-intercept linear mixed model fitted by REML over a single variance
  ratio, so "participant" can be a random effect without an lme4 dependency;
* Holm-Bonferroni and Benjamini-Hochberg corrections.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from statistics import NormalDist
from typing import Iterable, Sequence

_NORMAL = NormalDist()


# --------------------------------------------------------------------------
# distributions
# --------------------------------------------------------------------------
def _betacf(a: float, b: float, x: float, itmax: int = 200, eps: float = 3e-12) -> float:
    """Continued fraction for the incomplete beta function (Numerical Recipes)."""
    tiny = 1e-300
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c = 1.0
    d = 1.0 - qab * x / qap
    if abs(d) < tiny:
        d = tiny
    d = 1.0 / d
    h = d
    for m in range(1, itmax + 1):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < tiny:
            d = tiny
        c = 1.0 + aa / c
        if abs(c) < tiny:
            c = tiny
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < tiny:
            d = tiny
        c = 1.0 + aa / c
        if abs(c) < tiny:
            c = tiny
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < eps:
            break
    return h


def betainc(a: float, b: float, x: float) -> float:
    """Regularised incomplete beta I_x(a, b)."""
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    lbeta = math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
    front = math.exp(lbeta + a * math.log(x) + b * math.log1p(-x))
    if x < (a + 1.0) / (a + b + 2.0):
        return front * _betacf(a, b, x) / a
    return 1.0 - front * _betacf(b, a, 1.0 - x) / b


def t_cdf(t: float, df: float) -> float:
    """P(T <= t) for Student's t with ``df`` degrees of freedom."""
    if df <= 0:
        raise ValueError("df must be positive")
    if math.isinf(t):
        return 0.0 if t < 0 else 1.0
    tail = 0.5 * betainc(df / 2.0, 0.5, df / (df + t * t))
    return 1.0 - tail if t >= 0 else tail


def t_quantile(p: float, df: float) -> float:
    """Inverse of :func:`t_cdf` by bisection (accurate to ~1e-10)."""
    if not 0.0 < p < 1.0:
        raise ValueError("p must be in (0, 1)")
    lo, hi = -1e3, 1e3
    for _ in range(200):
        mid = (lo + hi) / 2.0
        if t_cdf(mid, df) < p:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2.0


# --------------------------------------------------------------------------
# descriptives and effect sizes
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class Summary:
    n: int
    mean: float
    sd: float
    median: float
    q1: float
    q3: float
    minimum: float
    maximum: float
    ci_low: float
    ci_high: float
    ci_method: str

    @property
    def iqr(self) -> float:
        return self.q3 - self.q1


def _quantile(values: Sequence[float], q: float) -> float:
    """Linear-interpolation quantile, the same definition as numpy's default."""
    if not values:
        raise ValueError("empty sample")
    data = sorted(values)
    if len(data) == 1:
        return data[0]
    pos = (len(data) - 1) * q
    low = math.floor(pos)
    high = math.ceil(pos)
    if low == high:
        return data[int(pos)]
    return data[low] + (data[high] - data[low]) * (pos - low)


def sd(values: Sequence[float]) -> float:
    n = len(values)
    if n < 2:
        return float("nan")
    m = sum(values) / n
    return math.sqrt(sum((v - m) ** 2 for v in values) / (n - 1))


def summarise(values: Sequence[float], conf: float = 0.95) -> Summary:
    """Mean with a t-based CI; sd/median/IQR are descriptive only."""
    data = [float(v) for v in values]
    if not data:
        raise ValueError("empty sample")
    n = len(data)
    mean = sum(data) / n
    spread = sd(data)
    if n >= 2 and spread > 0:
        half = t_quantile(1 - (1 - conf) / 2, n - 1) * spread / math.sqrt(n)
        method = "t"
    else:
        half = float("nan")
        method = "undefined (no variance)"
    return Summary(
        n=n,
        mean=mean,
        sd=spread,
        median=_quantile(data, 0.5),
        q1=_quantile(data, 0.25),
        q3=_quantile(data, 0.75),
        minimum=min(data),
        maximum=max(data),
        ci_low=mean - half,
        ci_high=mean + half,
        ci_method=method,
    )


def bootstrap_ci(
    values: Sequence[float],
    statistic=sum,
    conf: float = 0.95,
    resamples: int = 2000,
    seed: int = 42,
) -> tuple[float, float, str]:
    """Percentile bootstrap CI. Deterministic for a given seed.

    ``statistic`` receives a list and must return a scalar; the default is the
    sum, which the caller divides by n for a mean.
    """
    data = list(values)
    if len(data) < 2:
        return (float("nan"), float("nan"), "undefined (n < 2)")
    rng = random.Random(seed)
    n = len(data)
    stats = []
    for _ in range(resamples):
        sample = [data[rng.randrange(n)] for _ in range(n)]
        stats.append(float(statistic(sample)))
    alpha = (1 - conf) / 2
    return (
        _quantile(stats, alpha),
        _quantile(stats, 1 - alpha),
        f"percentile bootstrap, {resamples} resamples, seed {seed}",
    )


# --------------------------------------------------------------------------
# paired comparisons
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class PairedTest:
    name: str
    n: int
    statistic: float | None
    df: float | None
    p_value: float | None
    effect: float | None
    effect_name: str
    ci_low: float | None
    ci_high: float | None
    method: str
    note: str = ""


@dataclass(frozen=True)
class PairedResult:
    """All three views of one pairing, so the report can compare them."""

    n: int
    mean_difference: float
    differences: list[float] = field(default_factory=list)
    t: PairedTest | None = None
    wilcoxon: PairedTest | None = None
    lmm: dict[str, float | str | None] = field(default_factory=dict)
    zero_variance: bool = False


def cohens_dz(differences: Sequence[float]) -> float:
    spread = sd(differences)
    if not spread or math.isnan(spread):
        return float("nan")
    return (sum(differences) / len(differences)) / spread


def hedges_g(differences: Sequence[float]) -> float:
    """Small-sample correction of dz (Hedges 1981); n here is the pair count."""
    n = len(differences)
    dz = cohens_dz(differences)
    if math.isnan(dz) or n < 2:
        return float("nan")
    correction = 1.0 - 3.0 / (4.0 * (n - 1) - 1.0)
    return dz * correction


def paired_t(before: Sequence[float], after: Sequence[float], conf: float = 0.95) -> PairedTest:
    if len(before) != len(after):
        raise ValueError("paired samples must have equal length")
    differences = [b - a for b, a in zip(before, after)]
    n = len(differences)
    if n < 2:
        return PairedTest("paired t", n, None, None, None, None, "dz", None, None,
                          "not computed", "fewer than two pairs")
    spread = sd(differences)
    mean = sum(differences) / n
    if not spread:
        return PairedTest(
            "paired t", n, None, n - 1, None, float("nan"), "dz", None, None,
            "not computed",
            "every paired difference is identical, so the standard error is zero "
            "and the statistic is 0/0 rather than infinite evidence",
        )
    se = spread / math.sqrt(n)
    t = mean / se
    p = 2 * (1 - t_cdf(abs(t), n - 1))
    half = t_quantile(1 - (1 - conf) / 2, n - 1) * se
    return PairedTest(
        "paired t", n, t, n - 1, min(1.0, p), cohens_dz(differences), "dz",
        mean - half, mean + half, "two-sided, df = n - 1",
    )


def _wilcoxon_exact_p(w_plus: int, n: int) -> float:
    """Two-sided exact p for the signed-rank statistic with distinct ranks.

    The null distribution of W+ is the number of subsets of {1..n} with each sum,
    computed by dynamic programming (no 2^n enumeration).
    """
    max_sum = n * (n + 1) // 2
    counts = [0] * (max_sum + 1)
    counts[0] = 1
    for rank in range(1, n + 1):
        for total in range(max_sum, rank - 1, -1):
            counts[total] += counts[total - rank]
    total_assignments = 2 ** n
    lower = sum(counts[: w_plus + 1])
    upper = sum(counts[w_plus:])
    return min(1.0, 2 * min(lower, upper) / total_assignments)


def wilcoxon(before: Sequence[float], after: Sequence[float], conf: float = 0.95) -> PairedTest:
    if len(before) != len(after):
        raise ValueError("paired samples must have equal length")
    differences = [b - a for b, a in zip(before, after)]
    nonzero = [d for d in differences if d != 0]
    n = len(nonzero)
    if n == 0:
        return PairedTest(
            "wilcoxon", 0, None, None, None, float("nan"), "r", None, None,
            "not computed", "every paired difference is zero",
        )
    order = sorted(range(n), key=lambda i: abs(nonzero[i]))
    ranks = [0.0] * n
    i = 0
    ties = False
    while i < n:
        j = i
        while j + 1 < n and abs(nonzero[order[j + 1]]) == abs(nonzero[order[i]]):
            j += 1
        average = (i + j) / 2.0 + 1.0
        if j > i:
            ties = True
        for k in range(i, j + 1):
            ranks[order[k]] = average
        i = j + 1
    w_plus = sum(r for r, d in zip(ranks, nonzero) if d > 0)
    w_minus = sum(ranks) - w_plus
    total_rank = sum(ranks)
    effect = (w_plus - w_minus) / total_rank

    if not ties:
        p = _wilcoxon_exact_p(int(round(w_plus)), n)
        method = "exact two-sided, no ties"
    else:
        mean = total_rank / 2.0
        variance = n * (n + 1) * (2 * n + 1) / 24.0
        # tie correction
        counts: dict[float, int] = {}
        for r in ranks:
            counts[r] = counts.get(r, 0) + 1
        tie_term = sum(c ** 3 - c for c in counts.values())
        variance -= tie_term / 48.0
        z = (abs(w_plus - mean) - 0.5) / math.sqrt(variance) if variance > 0 else 0.0
        p = min(1.0, 2 * (1 - _NORMAL.cdf(abs(z))))
        method = "normal approximation with tie correction and continuity correction"

    low, high, _ = bootstrap_ci(
        differences, statistic=lambda s: sum(s) / len(s), conf=conf
    )
    return PairedTest(
        "wilcoxon", n, w_plus, None, p, effect, "r", low, high, method,
        "" if n >= 6 else "fewer than six non-zero differences: the exact p cannot "
                          "fall below 0.05, so this test cannot reach significance here",
    )


# --------------------------------------------------------------------------
# linear mixed model (random intercept)
# --------------------------------------------------------------------------
def _inverse(matrix: list[list[float]]) -> list[list[float]]:
    n = len(matrix)
    aug = [row[:] + [1.0 if i == j else 0.0 for j in range(n)] for i, row in enumerate(matrix)]
    for col in range(n):
        pivot = max(range(col, n), key=lambda r: abs(aug[r][col]))
        if abs(aug[pivot][col]) < 1e-14:
            raise ValueError("singular matrix")
        aug[col], aug[pivot] = aug[pivot], aug[col]
        divisor = aug[col][col]
        aug[col] = [v / divisor for v in aug[col]]
        for row in range(n):
            if row != col and aug[row][col] != 0.0:
                factor = aug[row][col]
                aug[row] = [a - factor * b for a, b in zip(aug[row], aug[col])]
    return [row[n:] for row in aug]


def _logdet(matrix: list[list[float]]) -> float:
    n = len(matrix)
    total = 0.0
    work = [row[:] for row in matrix]
    for col in range(n):
        pivot = max(range(col, n), key=lambda r: abs(work[r][col]))
        if abs(work[pivot][col]) < 1e-14:
            return float("-inf")
        if pivot != col:
            work[col], work[pivot] = work[pivot], work[col]
        total += math.log(abs(work[col][col]))
        for row in range(col + 1, n):
            factor = work[row][col] / work[col][col]
            for k in range(col, n):
                work[row][k] -= factor * work[col][k]
    return 2 * total


def mixed_model(
    groups: Sequence[str],
    condition: Sequence[float],
    outcome: Sequence[float],
    conf: float = 0.95,
) -> dict[str, float | str | None]:
    """Random-intercept model ``outcome ~ condition + (1 | group)`` fitted by REML.

    The variance ratio lambda = sigma_u^2 / sigma_e^2 is the only free parameter
    after profiling out the residual variance, so a 1-D golden-section search is
    enough. With lambda -> 0 the fit collapses to ordinary least squares, which is
    exactly what should happen when groups do not differ.
    """
    n = len(outcome)
    if not (len(groups) == len(condition) == n):
        raise ValueError("groups, condition and outcome must be the same length")
    if n < 4:
        return {"estimate": None, "se": None, "p_value": None,
                "note": "fewer than four observations"}
    if len(set(groups)) < 2:
        return {
            "estimate": None, "se": None, "ci_low": None, "ci_high": None,
            "p_value": None, "z": None, "sigma2_resid": None, "variance_ratio": None,
            "n_groups": float(len(set(groups))),
            "note": "not estimable here: only one group, so a random intercept is "
                    "collinear with the fixed intercept. The paired tests are the "
                    "appropriate analysis for this design",
        }

    levels = sorted(set(groups))
    index = {g: i for i, g in enumerate(levels)}
    g = len(levels)
    # Design: column 0 = intercept, column 1 = condition; plus Z for the random intercept.
    x = [[1.0, float(c)] for c in condition]
    y = [float(v) for v in outcome]

    def solve(lam: float) -> tuple[float, list[float], float, float]:
        # V = I + lam * Z Z^T, with Z the n x g indicator matrix.
        v = [[0.0] * n for _ in range(n)]
        for i in range(n):
            for j in range(n):
                v[i][j] = (1.0 if i == j else 0.0)
        for i in range(n):
            for j in range(n):
                if index[groups[i]] == index[groups[j]]:
                    v[i][j] += lam
        vinv = _inverse(v)
        xtvix = [[0.0, 0.0], [0.0, 0.0]]
        xtviy = [0.0, 0.0]
        for a in range(2):
            for b in range(2):
                xtvix[a][b] = sum(x[i][a] * vinv[i][j] * x[j][b] for i in range(n) for j in range(n))
            xtviy[a] = sum(x[i][a] * vinv[i][j] * y[j] for i in range(n) for j in range(n))
        beta = _inverse(xtvix)
        coef = [beta[0][0] * xtviy[0] + beta[0][1] * xtviy[1],
                beta[1][0] * xtviy[0] + beta[1][1] * xtviy[1]]
        resid = [y[i] - coef[0] * x[i][0] - coef[1] * x[i][1] for i in range(n)]
        rvir = sum(resid[i] * vinv[i][j] * resid[j] for i in range(n) for j in range(n))
        # A perfect fit drives the residual variance to zero and the log-likelihood to
        # infinity; the floor keeps the search on a finite surface instead of crashing
        # on math.log(0), and the caller reports the degeneracy.
        sigma2 = max(rvir / n, 1e-12)
        loglik = -0.5 * (_logdet(v) + n * math.log(sigma2))
        se = math.sqrt(max(sigma2 * beta[1][1], 1e-30))
        return loglik, coef, se, sigma2

    low, high = 1e-6, 1e3
    phi = (math.sqrt(5) - 1) / 2
    a, b = low, high
    c, d = b - phi * (b - a), a + phi * (b - a)
    fc, fd = solve(c)[0], solve(d)[0]
    for _ in range(80):
        if fc > fd:
            b, d, fd = d, c, fc
            c = b - phi * (b - a)
            fc = solve(c)[0]
        else:
            a, c, fc = c, d, fd
            d = a + phi * (b - a)
            fd = solve(d)[0]
    lam = (a + b) / 2.0
    loglik, coef, se, sigma2 = solve(lam)
    z = coef[1] / se if se else 0.0
    p = 2 * (1 - _NORMAL.cdf(abs(z)))
    half = _NORMAL.inv_cdf(1 - (1 - conf) / 2) * se
    return {
        "estimate": coef[1],
        "se": se,
        "ci_low": coef[1] - half,
        "ci_high": coef[1] + half,
        "p_value": min(1.0, p),
        "z": z,
        "sigma2_resid": sigma2,
        "variance_ratio": lam,
        "n_groups": float(g),
        "note": "REML, random intercept for group; p from the normal approximation "
                "(no Satterthwaite df in a dependency-free implementation)",
        "loglik": loglik,
    }


def compare_paired(
    before: Sequence[float],
    after: Sequence[float],
    groups: Sequence[str] | None = None,
    conf: float = 0.95,
) -> PairedResult:
    """Paired t, exact Wilcoxon and (optionally) the mixed model in one object."""
    differences = [b - a for b, a in zip(before, after)]
    n = len(differences)
    zero = all(d == 0 for d in differences)
    lmm: dict[str, float | str | None] = {}
    if groups is not None and n >= 4:
        stacked_groups = list(groups) + list(groups)
        stacked_condition = [0.0] * n + [1.0] * n
        stacked_outcome = list(before) + list(after)
        lmm = mixed_model(stacked_groups, stacked_condition, stacked_outcome, conf)
    return PairedResult(
        n=n,
        mean_difference=(sum(differences) / n) if n else float("nan"),
        differences=differences,
        t=paired_t(before, after, conf),
        wilcoxon=wilcoxon(before, after, conf),
        lmm=lmm,
        zero_variance=zero,
    )


# --------------------------------------------------------------------------
# multiplicity
# --------------------------------------------------------------------------
def holm(p_values: Sequence[float], alpha: float = 0.05) -> list[dict[str, float | bool]]:
    """Holm-Bonferroni step-down; controls the family-wise error rate."""
    m = len(p_values)
    order = sorted(range(m), key=lambda i: p_values[i])
    out: list[dict[str, float | bool]] = [dict() for _ in range(m)]
    running = 0.0
    for rank, idx in enumerate(order):
        adjusted = min(1.0, max(running, (m - rank) * p_values[idx]))
        running = adjusted
        out[idx] = {"p": p_values[idx], "p_adjusted": adjusted, "reject": adjusted <= alpha}
    return out


def benjamini_hochberg(
    p_values: Sequence[float], alpha: float = 0.05
) -> list[dict[str, float | bool]]:
    """Benjamini-Hochberg step-up; controls the false discovery rate."""
    m = len(p_values)
    order = sorted(range(m), key=lambda i: p_values[i])
    out: list[dict[str, float | bool]] = [dict() for _ in range(m)]
    running = 1.0
    for rank in range(m - 1, -1, -1):
        idx = order[rank]
        adjusted = min(running, p_values[idx] * m / (rank + 1))
        running = adjusted
        out[idx] = {"p": p_values[idx], "p_adjusted": adjusted, "reject": adjusted <= alpha}
    return out
