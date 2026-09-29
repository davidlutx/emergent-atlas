# Technical Appendix: Behavioral Features

This appendix records the exact measurements used in the analysis.

Let \(X_t(i)\in\{0,1\}\) be cell \(i\) at generation \(t\), \(N\) the number of cells, and \(T=150\).

## Density

\[
p_t=\frac{1}{N}\sum_i X_t(i)
\]

\[
\text{Mean density}=\frac{1}{T+1}\sum_{t=0}^{T}p_t,
\qquad
\text{Final density}=p_T
\]

## Activity

\[
\text{Activity}=\frac{1}{T}\sum_{t=1}^{T}
\left(\frac{1}{N}\sum_i\mathbf{1}[X_t(i)\neq X_{t-1}(i)]\right)
\]

## Growth

With normalized time \(\tau_t=t/T\), growth is the least-squares slope:

\[
\text{Growth}=\frac{\sum_t(\tau_t-\bar{\tau})(p_t-\bar p)}
{\sum_t(\tau_t-\bar{\tau})^2}
\]

## Entropy

\[
\text{Entropy}=\frac{1}{T+1}\sum_{t=0}^{T}
[-p_t\log_2p_t-(1-p_t)\log_2(1-p_t)]
\]

This measures population balance, not spatial entropy.

## Lifespan

If \(t_0\) is the first generation with \(p_t=0\):

\[
\text{Lifespan}=t_0/T
\]

Set to 1 if the grid never becomes empty.

## Recurrence

\[
d(t,k)=\frac{1}{N}\sum_i\mathbf{1}[X_t(i)\neq X_{t-k}(i)]
\]

\[
\text{Recurrence}=1-\min_{1\leq k\leq10}\min_{k\leq t\leq T}d(t,k)
\]

One exact repeat within ten generations gives 1. Translated patterns are not recognized as repeats.

## Component count

Let \(C_t\) be the number of toroidally 8-connected live groups:

\[
\text{Component count}=\frac{1}{5}\sum_{t\in\{0,37,75,112,150\}}C_t
\]

## Rule averages and standardization

For rule \(r\), feature \(j\), and five runs:

\[
\bar{x}_{r,j}=\frac{1}{5}\sum_{m=1}^{5}x_{r,j,m}
\]

Before PCA and K-means:

\[
z_{r,j}=\frac{\bar{x}_{r,j}-\mu_j}{\sigma_j}
\]

The PCA input is therefore a \(500\times8\) matrix: one row per sampled rule and one standardized column per feature. PCA finds weighted combinations of these eight columns. The first two combinations are used as the two axes of the behavior map.

## Noise experiment

Let \(F_r(X_t)(i)\) be the normal next state under rule \(r\). After that update:

\[
X_{t+1}(i)=F_r(X_t)(i)\mathbin{\mathrm{XOR}}Z_t(i),
\qquad Z_t(i)\sim\operatorname{Bernoulli}(p)
\]

Each cell and generation receives an independent draw. The follow-up sweep used \(p=0,0.01,\ldots,0.99\), with ten runs at each value for each of the three cluster representatives.
