# Emergent Atlas

Emergent Atlas is an interactive cellular automata project built for an Emergent Complexity assignment. The website includes editable birth and survival rules, adjustable grid sizes and boundaries, random or known starting patterns, and controls for adding noise to the simulation.

The project also includes an offline Python analysis of 500 cellular automaton rules. The analysis measures their behavior, groups similar rules using PCA and K-means, and tests whether those groups can be predicted from the rules themselves. The generated results are loaded by the website as static data, so the deployed site does not need a backend.

Live site: <https://davidlutx.github.io/emergent-atlas/>

Full report: [report/report.md](report/report.md)

Follow-up exploration: [report/exploration_report.md](report/exploration_report.md)

## Run locally

From the repository root:

```bash
npm run serve
```

Then open <http://localhost:8000/>.

## Reproduce the analysis

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m analysis.analyze
python -m analysis.investigate
python -m analysis.followup
python -m analysis.explore_directions
```

Generated data is written to `data/` and `web/data/`. Generated figures are written to `analysis/figures/`.

## Run tests

```bash
.venv/bin/python -m unittest discover -v
npm test
```
