# oceandiff

oceandiff is a Python package for testing and diagnosing differences in NetCDF outputs from oceanographic workflows, particularly suited for cylc workflows. It lets you:

- Compare variables between two NetCDF files
- Compare metadata and produce human-readable diffs
- Generate diagnostic visualisations — static plots and GIF animations
- Integrate into CI pipelines or post-processing tasks without modifying existing workflows

---

## Installation

```bash
conda create -n oceandiff python=3.11 -y
conda activate oceandiff
pip install -e .
```

---

## Quick start

### Single file comparison

```bash
oceandiff baseline.nc candidate.nc
```

### Include metadata

```bash
oceandiff baseline.nc candidate.nc --metadata
```

### Batch directory QA

```bash
oceandiff --dir1 baseline_outputs --dir2 candidate_outputs --recursive
```

### Generate review artefacts

```bash
oceandiff baseline.nc candidate.nc --plot --output-dir review_outputs
oceandiff baseline.nc candidate.nc --animate --output-dir review_outputs
```

---

## Team quick start workflows

### 1. Local file-to-file QA

Run a quick numerical check first, then include metadata if needed:

```bash
oceandiff baseline.nc candidate.nc
oceandiff baseline.nc candidate.nc --metadata
```

### 2. Batch QA across directories

```bash
oceandiff --dir1 baseline_outputs --dir2 candidate_outputs --recursive
```

Add `--strict-pairs` in validation gates where missing files should fail the run:

```bash
oceandiff --dir1 baseline_outputs --dir2 candidate_outputs --recursive --strict-pairs
```

### 3. Diagnose coordinate/grid issues

If interpolation hides a mismatch, run with `--no-interp`:

```bash
oceandiff baseline.nc candidate.nc --no-interp
```

### 4. Produce review artefacts

```bash
oceandiff baseline.nc candidate.nc --plot --output-dir review_outputs
oceandiff baseline.nc candidate.nc --animate --output-dir review_outputs
```
