"""Plotting utilities for oceandiff difference fields."""

import numpy as np
import xarray as xr
from pathlib import Path


def _find_spatial_coords(
    da: xr.DataArray, dataset: xr.Dataset = None
) -> tuple[str, str]:
    """Find latitude and longitude coordinate names in a DataArray or dataset.

    Handles variations like lat/latitude, lon/longitude, y/x, nav_lat/nav_lon, etc.
    If not found in DataArray coords, checks the dataset data_vars.
    Falls back to matching data dimensions (x/y) to spatial variables in dataset.
    """
    lat_names = ["lat", "latitude", "y", "nav_lat"]
    lon_names = ["lon", "longitude", "x", "nav_lon"]

    lat_coord = None
    lon_coord = None

    # First check DataArray coordinates
    for name in lat_names:
        if name in da.coords:
            lat_coord = name
            break

    for name in lon_names:
        if name in da.coords:
            lon_coord = name
            break

    # If not found, check dataset data variables
    if (lat_coord is None or lon_coord is None) and dataset is not None:
        if lat_coord is None:
            for name in lat_names:
                if name in dataset.data_vars:
                    lat_coord = name
                    break
        if lon_coord is None:
            for name in lon_names:
                if name in dataset.data_vars:
                    lon_coord = name
                    break

    # If still not found, try to infer from data dimensions
    # e.g., if data has dims (y, x), look for variables with those dimensions
    if (lat_coord is None or lon_coord is None) and dataset is not None:
        # Find which dims in data might be spatial
        potential_y_dims = [d for d in da.dims if d in ["y", "x", "lon", "lat"]]
        if not potential_y_dims and da.dims:
            # Use first non-time/depth dimension as y candidate
            time_depth_names = [
                "time",
                "time_counter",
                "t",
                "depth",
                "deptht",
                "depthu",
                "z",
                "lev",
            ]
            potential_y_dims = [d for d in da.dims if d not in time_depth_names]

        if lat_coord is None and potential_y_dims:
            y_dim = potential_y_dims[0] if potential_y_dims else None
            if y_dim:
                # Find a variable with y_dim that might be latitude
                for var_name in dataset.data_vars:
                    var_dims = dataset[var_name].dims
                    if len(var_dims) == 1 and y_dim in var_dims:
                        for lat_name in lat_names:
                            if lat_name.lower() in var_name.lower():
                                lat_coord = var_name
                                break
                        if lat_coord:
                            break

        if lon_coord is None and len(potential_y_dims) > 1:
            x_dim = potential_y_dims[1]
            # Find a variable with x_dim that might be longitude
            for var_name in dataset.data_vars:
                var_dims = dataset[var_name].dims
                if len(var_dims) == 1 and x_dim in var_dims:
                    for lon_name in lon_names:
                        if lon_name.lower() in var_name.lower():
                            lon_coord = var_name
                            break
                    if lon_coord:
                        break

    if lat_coord is None or lon_coord is None:
        raise ValueError(
            f"Could not find latitude and longitude coordinates. "
            f"Data dims: {da.dims}. Available coords: {list(da.coords.keys())}. "
            f"Available data_vars: {list(dataset.data_vars.keys()) if dataset else 'N/A'}"
        )

    return lat_coord, lon_coord


def _compute_stats(values: np.ndarray) -> dict[str, float]:
    """Compute min/max/mean/rms on finite values only."""
    finite = values[np.isfinite(values)]
    if finite.size == 0:
        return {"min": np.nan, "max": np.nan, "mean": np.nan, "rms": np.nan}
    return {
        "min": float(np.min(finite)),
        "max": float(np.max(finite)),
        "mean": float(np.mean(finite)),
        "rms": float(np.sqrt(np.mean(np.square(finite)))),
    }


def _format_stats_text(stats: dict[str, float]) -> str:
    """Format statistics for display in a side panel."""
    return (
        "Diff Stats\n"
        f"min:  {stats['min']:.6g}\n"
        f"max:  {stats['max']:.6g}\n"
        f"mean: {stats['mean']:.6g}\n"
        f"rms:  {stats['rms']:.6g}"
    )


def plot_map(
    diff: xr.DataArray,
    title: str = None,
    depth_index: int = 0,
    time_index: int = 0,
    output_dir: str = None,
    dataset: xr.Dataset = None,
):
    """Plot a 2D map of the difference field.

    Args:
        diff: xarray DataArray containing difference values
        title: Plot title
        depth_index: Which depth level to plot (if depth dimension exists)
        time_index: Which time level to plot (if time dimension exists)
        output_dir: Optional directory to save plot (as PNG). If None, plot is displayed.
        dataset: Optional xarray Dataset containing spatial coordinates (e.g., nav_lat/nav_lon)
    """
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        raise ImportError(
            "matplotlib is required for plotting. Install with: pip install matplotlib"
        )

    # Make a copy to avoid modifying original
    data = diff.copy()

    # Handle time dimension
    if "time" in data.dims:
        data = data.isel(time=time_index)

    # Handle depth dimension
    if "depth" in data.dims or "deptht" in data.dims:
        depth_dim = "depth" if "depth" in data.dims else "deptht"
        data = data.isel({depth_dim: depth_index})

    # Get spatial coordinates (check dataset if needed for nav_lat/nav_lon)
    lat_coord, lon_coord = _find_spatial_coords(data, dataset=dataset)

    lat = data[lat_coord].values
    lon = data[lon_coord].values

    # Prepare figure and reserve right margin for stats panel
    fig, ax = plt.subplots(figsize=(12, 8))
    fig.subplots_adjust(right=0.80)

    # Determine color scale (symmetric for differences)
    vabs = np.nanmax(np.abs(data.values))
    vmin = -vabs
    vmax = vabs

    # Plot
    im = ax.imshow(
        data.values,
        cmap="RdBu_r",
        origin="lower",
        extent=[lon.min(), lon.max(), lat.min(), lat.max()],
        vmin=vmin,
        vmax=vmax,
    )

    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label("Difference", rotation=270, labelpad=20)

    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")

    # Add numerical stats panel to the right side
    stats = _compute_stats(data.values)
    fig.text(
        0.84,
        0.5,
        _format_stats_text(stats),
        ha="left",
        va="center",
        fontsize=10,
        family="monospace",
        bbox={
            "boxstyle": "round",
            "facecolor": "white",
            "alpha": 0.85,
            "edgecolor": "0.7",
        },
    )

    if title:
        ax.set_title(title)

    if output_dir:
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        # Create filename from title or use generic name
        if title:
            safe_title = title.replace(" ", "_").replace("/", "_")
            filename = f"{safe_title}.png"
        else:
            filename = "difference_map.png"
        filepath = output_path / filename
        fig.savefig(filepath, dpi=150, bbox_inches="tight")
        print(f"Saved plot to {filepath}")
        plt.close(fig)

    return fig, ax
