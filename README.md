# oceandiff

oceandiff is a Python package for testing and diagnosing differences in NetCDF outputs from oceanographic workflows, particularly suited for cylc workflows. It allows you to:

- Compare variables between two NetCDF files.

- Compare metadata and provide human-readable differences.

- Generate diagnostic visualisations, including static plots and GIF animations, to illustrate spatial, depth, or temporal differences.

- Integrate easily into CI pipelines or post-processing tasks without modifying existing workflows.

OceanDiff is designed to make testing of ocean products easy, reproducible, and visually informative.

## Run oceandiff (current state)

### Prerequisites

- Python 3.11+

### Install locally

From the repository root:

```bash
conda create -n oceandiff python=3.11 -y
conda activate oceandiff
pip install -e .
```

### CLI entry point

After installation, use the console script:

```bash
oceandiff FILE1.nc FILE2.nc
```

Equivalent module form:

```bash
python -m oceandiff.cli.main FILE1.nc FILE2.nc
```

By default, `oceandiff` infers the product category from the filename and then resolves the matching NetCDF data variable(s) from the file contents.
For example, filenames like `metoffice_foam1_amm15_NWS_TEM_b20260706_dm20260704.nc` typically map to `thetao`, `SAL` maps to `so`, `BED` maps to `bottomT`, and `MLD` maps to `mlotst`.
For `CUR` files, `oceandiff` compares the shared current-related variables found in both files.
You can still override with `--var1` / `--var2` if needed.

### Useful examples

Compare the same variable in both files:

```bash
oceandiff metoffice_foam1_amm15_NWS_TEM_b20260706_dm20260704.nc metoffice_foam1_amm15_NWS_TEM_b20260706_dd20260704.nc
```

Compare different variable names across files:

```bash
oceandiff run_a.nc run_b.nc --var1 votemper --var2 thetao
```

Compare a specific time/depth slice:

```bash
oceandiff run_a.nc run_b.nc --time-index 0 --depth 10
```

Include metadata comparison:

```bash
oceandiff run_a.nc run_b.nc --metadata
```

Compare two directories (matches files by normalized relative filename, including variable token such as TEM/SAL/BED):

```bash
oceandiff --dir1 baseline_outputs --dir2 candidate_outputs
```

Compare recursively with strict pair checking:

```bash
oceandiff --dir1 baseline_outputs --dir2 candidate_outputs --recursive --strict-pairs
```

Use a custom file pattern in directory mode:

```bash
oceandiff --dir1 baseline_outputs --dir2 candidate_outputs --pattern "*.nc"
```

If your filename format is different, provide a regex with a named capture group `var`:

```bash
oceandiff run_a.nc run_b.nc --filename-var-regex "^.+_(?P<var>[A-Z]+)_b\\d+_d[a-zA-Z]\\d+\\.nc$"
```

Troubleshooting grid mismatches:

```bash
oceandiff file1.nc file2.nc --no-interp
```

This will skip interpolation and help diagnose grid differences. The CLI will print coordinate ranges before attempting any grid operations.

### Notes on current functionality

- Numerical diff and summary statistics are implemented and working.
- Metadata comparison is implemented and working.
- The filename is used as a category hint by default, then the comparison variable is resolved from the NetCDF contents. Override with `--var1` / `--var2` if needed.
- Directory mode is implemented via `--dir1` and `--dir2`; files are compared pairwise by normalized relative path. This supports `dmYYYYMMDD` vs `ddYYYYMMDD` style filename differences while keeping variables (for example TEM/SAL/BED) distinct.
- `--no-interp` flag disables grid interpolation and requires exact grid match for debugging coordinate issues.
- `--plot` and `--animate` CLI flags are present but plotting/animation functions are not currently wired, so avoid these flags for now.
