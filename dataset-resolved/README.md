# Resolved ScenarioForge-Eval dataset

This directory contains one fixed `.spec.yaml` file for every declared
iteration in `../datasets`: 150 files at generation time. Each specification
uses `iterations: 1`, has no bounded values or `randomize` settings, and stores
its deterministic seed.

The static topology, service, traffic, vulnerability count,
flag-node-generator count, flow length, and segmentation values are resolved.
To persist the exact selected Vulhub image and self-generated service names,
materialize this suite against the intended ScenarioForge catalog. This replaces
the filter lists with schema-validated `specific` rows and writes the complete
selection manifest to `catalog-selections.json`. The materializer balances use
across eligible concrete entries, instead of accepting chance-heavy selection.
It also produces `distribution.svg`, which summarizes the exact image/service
names and their selection frequencies alongside fixed topology, service, flow,
and segmentation totals. Subnet CIDRs are allocated by ScenarioForge during its
topology phase; the resolved YAMLs persist the fixed inputs to that allocation,
not fabricated CIDR values.

`Sample:*` generators are deliberately excluded. When the base suite does not
cover a validated Vulhub image, the materializer adds fixed
`90-catalog-coverage-*.spec.yaml` fixtures (up to three images per fixture) so
every validated image and every enabled non-Sample generator is used at least
once.

Regenerate after changing a source dataset YAML:

```bash
uv run python datasets/generate_resolved_specs.py
uv run python datasets/materialize_catalog_selections.py --sf-path ../scenarioforge
uv run python datasets/generate_resolved_distribution.py
uv run python datasets/generate_ground_truth_figures.py
```

The last command writes two audience-specific figures:

- `ground-truth-distribution.svg`: exact catalog and type aggregates, selection
  frequency histograms, and population statistics.
- `research-distribution.svg`: a concise, paper-ready coverage, balance, type
  diversity, traffic, and network-variation bar-chart summary.

`ground-truth-statistics.json` contains every type aggregate and the metric
definitions used by both figures, including the complete mapping from raw
Vulhub component names and self-generated service types to their semantic
families.

Run the fully resolved suite with:

```bash
uv run scenarioforge-eval dataset-resolved --sf-path ../scenarioforge --execute \
  --out /tmp/scenarioforge-eval-dataset-resolved
```
