# Report Outline — ML-Guided Discovery of Emergent Cellular Automata

## 1. Motivation and research questions

- Introduce emergence: simple local decisions can create unexpected macroscopic behavior.
- Ask whether unsupervised ML can discover useful behavioral regimes in a sampled rule space.
- Ask whether the 18 microscopic rule bits predict those regimes.
- Ask how learned regimes respond to independent cell-flip noise.

## 2. Interactive artifact

- Describe the browser simulator and visual `B0…B8` / `S0…S8` editor.
- State that both implementations use an eight-cell Moore neighborhood and toroidal boundaries.
- Describe drawing, run/pause/step/reset, random density, speed, live count, and noise controls.
- Include screenshots of Conway, HighLife, and the ML-selected outlier.

## 3. Correctness checks and initial exploration

- Block remains fixed under `B3/S23`.
- Blinker repeats after two generations.
- Glider translates one diagonal cell after four generations.
- Compare Conway and HighLife random-start behavior. In the sampled experiment both land in the sparse cluster and have similar average density/activity.
- Add screenshots and personal observations from interactive runs, especially any localized, moving, oscillating, or boundary-crossing objects.
- Discuss HighLife's `B6` difference and catalogue any observed HighLife structures. Explicitly distinguish observations made in this project from known patterns mentioned in outside references.

## 4. Dataset and behavioral measurements

- 500 reproducibly sampled rules; five initial densities (`0.10`, `0.20`, `0.30`, `0.40`, `0.50`) per rule.
- 40 × 40 grid for 150 generations, seed `20260925`.
- Define mean density, final density, normalized Hamming activity, growth slope, binary entropy, normalized lifespan, small-lag recurrence, and 8-connected component count.
- Explain averaging trajectory measurements at the rule level.

## 5. Unsupervised behavior map

- Standardize eight feature means, fit PCA, then K-means for `k = 3, 4, 5`.
- Candidate silhouette scores: `0.493`, `0.476`, `0.362`.
- Explain choosing `k = 3`: it had the highest silhouette score and sizes `67/374/59`.
- Two PCs retain `63.3%` of feature variance.
- Interpret measured clusters after fitting:
  - Cluster 1: sparse/declining; mean density `0.197`, activity `0.175`.
  - Cluster 2: persistent/high activity; density `0.498`, activity `0.491`, entropy `0.950`.
  - Cluster 3: dense/lower activity; density `0.800`, activity `0.076`, positive growth.
- Stress that these are groupings under selected measurements, not objective universal classes.

## 6. Predicting regime from microscopic law

- Inputs: `B0…B8, S0…S8`; target: learned cluster.
- Compare majority baseline, logistic regression, a decision tree, and Random Forest with repeated five-fold cross-validation.
- Random Forest accuracy `85.6% ± 2.8`; majority baseline `74.8%`.
- Decision tree has the best balanced accuracy (`81.1%`), while Random Forest has the best overall accuracy.
- Top Random Forest importances: `S6`, `S7`, `S5`, `B3`, `B2`.
- Interpret modestly: above-baseline evidence in this split, not a broad generalization claim.

## 7. ML-guided closer investigation

- Select the point farthest from its own PCA cluster centroid: `B126/S35678`.
- Original averaged measurements: mean density `0.809`, final density `0.962`, activity `0.107`, growth `0.553`, recurrence `1.000`.
- Describe what is visibly happening after replaying several seeds in the simulator.
- Include frames at multiple generations so the claim is connected to observable dynamics.

## 8. Noise and perturbations

- Flip every cell independently after each normal update with `p ∈ {0, .001, .005, .01, .02}`.
- Use one centroid-nearest representative per cluster plus the outlier; ten starts per noise level.
- Transform with the original scaler/PCA instead of refitting the map.
- At `p=.02`, measured displacements are:
  - `B568/S01238`: `0.883`
  - `B123/S02457`: `0.010`
  - `B3/S245678`: `1.254`
  - outlier `B126/S35678`: `6.592`
- The outlier shows the greatest measured sensitivity, with its density falling toward `0.510` and activity rising to `0.331` at `p=.02`.
- Avoid claiming a universal threshold from only five levels and ten starts.

## 9. AI use

- AI helped translate the assignment into a scoped architecture, implement both simulators, write correctness tests, construct the feature/ML pipeline, diagnose issues, develop the visual interface, and organize documentation.
- Verification included independent Python/JavaScript CA tests and inspection of generated outputs.
- The human author should add what they personally reviewed, changed, and learned.

## 10. Limitations and future work

- Small rule sample and short trajectories.
- Sensitivity to initial state and selected densities.
- Hand-designed features, PCA information loss, K-means geometry assumptions.
- Small supervised test set and non-causal importances.
- Future: more seeds/steps, stability analysis across samples, rule mutations, richer—but still interpretable—spatial features.

## 11. Reproducibility appendix

- Link the GitHub repository and deployed site.
- Give commands from `README.md`.
- Link `simulation_features.csv`, `rule_summary.csv`, and generated figures.
- Record the commit hash used for the report.
