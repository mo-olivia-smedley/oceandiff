import argparse
import importlib
import re
from pathlib import Path
from oceandiff.diff.diff import diff_variable
from oceandiff.diff.stats import diff_stats
from oceandiff.diff.metadata_diff import diff_global_metadata, diff_variable_metadata


def _iter_nc_files(directory: str, pattern: str, recursive: bool) -> dict[str, Path]:
    """Return a mapping of relative path -> file path for matched NetCDF files."""
    root = Path(directory)
    if recursive:
        matches = [p for p in root.rglob(pattern) if p.is_file()]
    else:
        matches = [p for p in root.glob(pattern) if p.is_file()]

    return {str(p.relative_to(root)): p for p in sorted(matches)}


def _infer_var_from_filename(
    path: str, filename_var_regex: str | None = None
) -> str | None:
    """Infer variable token from a NetCDF filename.

    If a regex is provided, it must contain a named capture group called 'var'.
    """
    name = Path(path).name

    if filename_var_regex:
        match = re.match(filename_var_regex, name)
        if match:
            return match.group("var")

    stem_tokens = Path(path).stem.split("_")
    for idx, token in enumerate(stem_tokens):
        if re.match(r"^b\d+$", token):
            if idx > 0:
                return stem_tokens[idx - 1]
            break

    return None


def _normalize_filename_for_pairing(filename: str) -> str:
    """Normalize filename tokens so dm/dd-style prefixes can still pair.

    Examples:
    - dm20260704 and dd20260704 both normalize to d20260704.
    - hd20260704 and hi20260704 both normalize to h20260704.
    """
    path = Path(filename)
    tokens = path.stem.split("_")
    normalized_tokens = [
        re.sub(r"^([a-zA-Z])[a-zA-Z](\d+)$", r"\1\2", token) for token in tokens
    ]
    return "_".join(normalized_tokens) + path.suffix


def _build_pair_map(
    files: dict[str, Path],
    root: str,
    filename_var_regex: str | None,
    parser: argparse.ArgumentParser,
    side_name: str,
) -> dict[str, tuple[Path, str | None, str]]:
    """Build pair-key map with collision detection.

    Returns mapping: normalized relative key -> (path, inferred_var, original_relpath)
    """
    mapping: dict[str, tuple[Path, str | None, str]] = {}

    for relpath, abs_path in files.items():
        rel = Path(relpath)
        normalized_name = _normalize_filename_for_pairing(rel.name)
        key = (
            str(rel.parent / normalized_name)
            if str(rel.parent) != "."
            else normalized_name
        )
        inferred_var = _infer_var_from_filename(str(abs_path), filename_var_regex)

        if key in mapping:
            existing = mapping[key][2]
            parser.error(
                f"Ambiguous pairing key '{key}' in {side_name}: '{existing}' and '{relpath}'. "
                "Adjust naming or use a stricter --pattern / --filename-var-regex."
            )

        mapping[key] = (abs_path, inferred_var, relpath)

    return mapping


def _open_data_vars(path: str) -> set[str]:
    """Return the data variable names in a NetCDF file."""
    xr = importlib.import_module("xarray")
    with xr.open_dataset(path) as dataset:
        return set(dataset.data_vars)


def _resolve_comparison_vars(
    file1: str,
    file2: str,
    category_hint: str | None,
    explicit_var1: str | None,
    explicit_var2: str | None,
) -> tuple[list[tuple[str, str]], str]:
    """Resolve the variables that should be compared for a file pair."""
    if explicit_var1:
        return [
            (explicit_var1, explicit_var2 or explicit_var1)
        ], f"explicit variable {explicit_var1}"

    ds1_vars = _open_data_vars(file1)
    ds2_vars = _open_data_vars(file2)
    common_vars = sorted(ds1_vars & ds2_vars)

    if not common_vars:
        raise ValueError("No common data variables found between the two NetCDF files")

    category_map = {
        "TEM": ["thetao"],
        "SAL": ["so"],
        "BED": ["bottomT"],
        "MLD": ["mlotst"],
        "CUR": ["uo", "vo", "ubar", "vbar", "wo"],
    }

    if category_hint in category_map:
        selected = [var for var in category_map[category_hint] if var in common_vars]
        if selected:
            return [(var, var) for var in selected], f"category {category_hint}"

    if len(common_vars) == 1:
        var = common_vars[0]
        return [(var, var)], f"single shared variable {var}"

    return [(var, var) for var in common_vars], "all shared variables"


def _run_single_compare(
    args,
    file1: str,
    file2: str,
    var1: str,
    var2: str | None = None,
    label: str | None = None,
):
    """Run a single comparison and print stats / optional metadata output."""
    if label:
        print(f"\n=== Comparing {label} ===")

    diff = diff_variable(
        file1, file2, var1, var2, args.time_index, args.depth, no_interp=args.no_interp
    )
    stats = diff_stats(diff)
    var2_name = var2 or var1
    title_prefix = f"{var1} ({Path(file1).name}) - {var2_name} ({Path(file2).name})"

    print("=== Numerical difference statistics ===")
    for k, v in stats.items():
        print(f"{k}: {v:.6g}")

    # Open dataset to access spatial coordinates (e.g., nav_lat/nav_lon)
    xr = importlib.import_module("xarray")
    ds1 = xr.open_dataset(file1)

    # --- optional plotting ---
    if args.plot:
        try:
            plt = importlib.import_module("matplotlib.pyplot")
            plot_map = getattr(
                importlib.import_module("oceandiff.plot.plot"), "plot_map"
            )
        except Exception as exc:
            raise RuntimeError(
                "Plotting is unavailable in the current installation"
            ) from exc
        plot_map(diff, title=title_prefix, output_dir=args.output_dir, dataset=ds1)
        if not args.output_dir:
            plt.show()

    if args.animate:
        try:
            animate_depths = getattr(
                importlib.import_module("oceandiff.plot.animate"), "animate_depths"
            )
        except Exception as exc:
            raise RuntimeError(
                "Animation is unavailable in the current installation"
            ) from exc
        output = args.output_gif or f"{var1}_minus_{var2_name}_diff.gif"
        animate_depths(
            diff,
            output=output,
            output_dir=args.output_dir,
            title_prefix=title_prefix,
            dataset=ds1,
        )

    # --- metadata comparison ---
    if args.metadata:
        print("\n=== Global metadata differences ===")
        gdiffs = diff_global_metadata(file1, file2)
        if gdiffs:
            for k, v in gdiffs.items():
                print(f"{k}: {v['file1']} -> {v['file2']}")
        else:
            print("No global attribute differences")

        print("\n=== Variable metadata differences ===")
        vdiffs = diff_variable_metadata(file1, file2, variables=[var1])
        if vdiffs:
            for var, attrs in vdiffs.items():
                print(f"Variable {var}:")
                for k, v in attrs.items():
                    print(f"  {k}: {v['file1']} -> {v['file2']}")
        else:
            print("No variable attribute differences")


def _run_pair_compare(
    args,
    file1: str,
    file2: str,
    label: str,
    category_hint: str | None = None,
) -> None:
    """Resolve variables for a pair and run one or more comparisons."""
    var_pairs, resolution_label = _resolve_comparison_vars(
        file1=file1,
        file2=file2,
        category_hint=category_hint,
        explicit_var1=args.var1,
        explicit_var2=args.var2,
    )

    print(f"Using {resolution_label}")
    for var1, var2 in var_pairs:
        pair_label = label if len(var_pairs) == 1 else f"{label} [{var1}]"
        _run_single_compare(args, file1, file2, var1, var2, label=pair_label)


def main():
    parser = argparse.ArgumentParser(description="oceandiff: ocean NetCDF QA tool")
    parser.add_argument("file1", nargs="?", help="First NetCDF file")
    parser.add_argument("file2", nargs="?", help="Second NetCDF file")
    parser.add_argument(
        "--var1",
        help="Variable name in first file (optional override; inferred from filename if omitted)",
    )
    parser.add_argument(
        "--var2", help="Variable name in second file (defaults to var1)"
    )
    parser.add_argument(
        "-t",
        "--time-index",
        type=int,
        default=0,
        help="Time index to plot (default: 0, ignored if no time dimension)",
    )
    parser.add_argument(
        "--depth", type=int, default=None, help="Depth index to plot / diff"
    )
    parser.add_argument(
        "--plot", action="store_true", help="Plot surface / depth slice"
    )
    parser.add_argument(
        "--animate", action="store_true", help="Animate depth differences"
    )
    parser.add_argument("--metadata", action="store_true", help="Compare metadata")
    parser.add_argument("--output-dir", help="Directory to save plots and animations")
    parser.add_argument("--output-gif", help="[Deprecated] Use --output-dir instead")
    parser.add_argument(
        "--no-interp",
        action="store_true",
        help="Skip interpolation; require exact grid match",
    )
    parser.add_argument("--dir1", help="First directory of NetCDF files")
    parser.add_argument("--dir2", help="Second directory of NetCDF files")
    parser.add_argument(
        "--pattern",
        default="*.nc",
        help="File match pattern for directory mode (default: *.nc)",
    )
    parser.add_argument(
        "--recursive",
        action="store_true",
        help="Search directories recursively in directory mode",
    )
    parser.add_argument(
        "--strict-pairs",
        action="store_true",
        help="Fail if files exist in one directory but not the other",
    )
    parser.add_argument(
        "--filename-var-regex",
        help="Regex to extract variable from filename with named capture group 'var'",
    )

    args = parser.parse_args()

    if args.filename_var_regex and "(?P<var>" not in args.filename_var_regex:
        parser.error(
            "--filename-var-regex must include a named capture group '(?P<var>...)'"
        )

    dir_mode = args.dir1 is not None or args.dir2 is not None
    file_mode = args.file1 is not None or args.file2 is not None

    if dir_mode:
        if not args.dir1 or not args.dir2:
            parser.error("Both --dir1 and --dir2 are required in directory mode")
        if file_mode:
            parser.error("Use either file arguments or --dir1/--dir2, not both")

        files1 = _iter_nc_files(args.dir1, args.pattern, args.recursive)
        files2 = _iter_nc_files(args.dir2, args.pattern, args.recursive)

        pair_map1 = _build_pair_map(
            files1, args.dir1, args.filename_var_regex, parser, "--dir1"
        )
        pair_map2 = _build_pair_map(
            files2, args.dir2, args.filename_var_regex, parser, "--dir2"
        )

        only1 = sorted(set(pair_map1) - set(pair_map2))
        only2 = sorted(set(pair_map2) - set(pair_map1))
        common = sorted(set(pair_map1) & set(pair_map2))

        if args.strict_pairs and (only1 or only2):
            if only1:
                print("Files only in --dir1:")
                for name in only1:
                    print(f"  {name}")
            if only2:
                print("Files only in --dir2:")
                for name in only2:
                    print(f"  {name}")
            parser.error("Directory contents differ and --strict-pairs is enabled")

        if not common:
            parser.error("No matching files found between --dir1 and --dir2")

        print(f"Found {len(common)} matching file pairs")
        if only1:
            print(f"Skipping {len(only1)} files that only exist in --dir1")
        if only2:
            print(f"Skipping {len(only2)} files that only exist in --dir2")

        failures = 0
        for relpath in common:
            try:
                file1_path, inferred_var1, orig_rel1 = pair_map1[relpath]
                file2_path, inferred_var2, orig_rel2 = pair_map2[relpath]
                label = f"{orig_rel1} <-> {orig_rel2}"
                category_hint = inferred_var1 or inferred_var2
                _run_pair_compare(
                    args,
                    str(file1_path),
                    str(file2_path),
                    label=label,
                    category_hint=category_hint,
                )
            except Exception as exc:
                failures += 1
                print(f"ERROR comparing {relpath}: {exc}")

        if failures:
            raise SystemExit(f"Completed with {failures} failed comparisons")
        return

    if not args.file1 or not args.file2:
        parser.error(
            "Provide FILE1 FILE2 for single-file mode, or --dir1 --dir2 for directory mode"
        )

    category_hint = _infer_var_from_filename(args.file1, args.filename_var_regex)
    _run_pair_compare(
        args,
        args.file1,
        args.file2,
        label=f"{Path(args.file1).name} <-> {Path(args.file2).name}",
        category_hint=category_hint,
    )


if __name__ == "__main__":
    main()
