# CLI Reference

The `oceandiff` command-line tool compares NetCDF files and produces numerical statistics, metadata diffs, and optional visualisations.

---

## Synopsis

```
oceandiff FILE1 FILE2 [OPTIONS]
oceandiff --dir1 DIR1 --dir2 DIR2 [OPTIONS]
```

---

## Positional arguments

| Argument | Description |
|---|---|
| `FILE1` | First (baseline) NetCDF file |
| `FILE2` | Second (candidate) NetCDF file |

---

## Options

### Variable selection

| Flag | Description |
|---|---|
| `--var1 VAR` | Variable name in FILE1. Inferred from filename if omitted. |
| `--var2 VAR` | Variable name in FILE2. Defaults to `--var1`. |
| `--filename-var-regex REGEX` | Regex with a named capture group `(?P<var>...)` to extract variable from filename. |

### Slicing

| Flag | Default | Description |
|---|---|---|
| `-t`, `--time-index N` | `0` | Time index to select. |
| `--depth N` | `None` | Depth index to select. |

### Comparison behaviour

| Flag | Description |
|---|---|
| `--no-interp` | Skip interpolation; require exact grid match. Useful for diagnosing coordinate issues. |
| `--metadata` | Include global and variable-level metadata comparison. |

### Output

| Flag | Description |
|---|---|
| `--plot` | Generate a static map of the difference field. |
| `--animate` | Generate a depth-slice animation GIF. |
| `--output-dir DIR` | Directory to save plots and animations. |

### Directory mode

| Flag | Description |
|---|---|
| `--dir1 DIR` | First directory of NetCDF files. |
| `--dir2 DIR` | Second directory of NetCDF files. Paired with `--dir1` by normalized filename. |
| `--pattern GLOB` | File glob pattern within directories (default: `*.nc`). |
| `--recursive` | Search directories recursively. |
| `--strict-pairs` | Fail if files exist in one directory but not the other. |
| `--filename-match` | Match files by exact filename instead of normalized pairing. Disables `dm`/`dd`-style prefix normalization. |

---

## Examples

### Compare the same variable in both files

```bash
oceandiff metoffice_foam1_amm15_NWS_TEM_b20260706_dm20260704.nc \
          metoffice_foam1_amm15_NWS_TEM_b20260706_dd20260704.nc
```

### Compare different variable names

```bash
oceandiff run_a.nc run_b.nc --var1 votemper --var2 thetao
```

### Specific time/depth slice

```bash
oceandiff run_a.nc run_b.nc --time-index 0 --depth 10
```

### Metadata diff

```bash
oceandiff run_a.nc run_b.nc --metadata
```

### Static plot saved to disk

```bash
oceandiff run_a.nc run_b.nc --plot --output-dir diff_outputs
```

### Depth animation

```bash
oceandiff run_a.nc run_b.nc --animate --output-dir diff_outputs
```

### Directory mode

```bash
oceandiff --dir1 baseline_outputs --dir2 candidate_outputs
```

### Directory mode — recursive, strict pair checking

```bash
oceandiff --dir1 baseline_outputs --dir2 candidate_outputs \
          --recursive --strict-pairs
```

### Directory mode — exact filename matching

When your files have identical filenames in both directories (no `dm`/`dd` prefix differences), use `--filename-match` for a straightforward exact match:

```bash
oceandiff --dir1 baseline_outputs --dir2 candidate_outputs --filename-match
```

Only files with the same relative path in both directories will be paired.

### Custom filename regex

```bash
oceandiff run_a.nc run_b.nc \
  --filename-var-regex "^.+_(?P<var>[A-Z]+)_b\d+_d[a-zA-Z]\d+\.nc$"
```

### Diagnose grid mismatch

```bash
oceandiff file1.nc file2.nc --no-interp
```

---

## Category inference

By default, oceandiff infers the product category from the filename and resolves the corresponding NetCDF variable:

| Category token | Variable(s) |
|---|---|
| `TEM` | `thetao` |
| `SAL` | `so` |
| `BED` | `bottomT` |
| `MLD` | `mlotst` |
| `CUR` | `uo`, `vo`, `ubar`, `vbar`, `wo` |

Override with `--var1` / `--var2` when needed.
