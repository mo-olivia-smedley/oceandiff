import argparse
from oceandiff.diff.diff import diff_variable
from oceandiff.diff.stats import diff_stats
from oceandiff.diff.metadata_diff import diff_global_metadata, diff_variable_metadata
# from oceandiff.plot.plot import plot_map
# from oceandiff.plot.animate import animate_depths
import matplotlib.pyplot as plt


def main():
    parser = argparse.ArgumentParser(description="oceandiff: ocean NetCDF QA tool")
    parser.add_argument("file1", help="First NetCDF file")
    parser.add_argument("file2", help="Second NetCDF file")
    parser.add_argument("--var1", help="Variable name in first file")
    parser.add_argument("--var2", help="Variable name in second file (defaults to var1)")
    parser.add_argument("-t", "--time-index", type=int, default=0, help="Time index to plot (default: 0, ignored if no time dimension)")
    parser.add_argument("--depth", type=int, default=None, help="Depth index to plot / diff")
    parser.add_argument("--plot", action="store_true", help="Plot surface / depth slice")
    parser.add_argument("--animate", action="store_true", help="Animate depth differences")
    parser.add_argument("--metadata", action="store_true", help="Compare metadata")
    parser.add_argument("--output-gif", help="Path to save GIF (if animate)")

    args = parser.parse_args()

    # --- numerical diff ---
    diff = diff_variable(args.file1, args.file2, args.var1, args.var2, args.time_index, args.depth)
    stats = diff_stats(diff)

    print("=== Numerical difference statistics ===")
    for k, v in stats.items():
        print(f"{k}: {v:.6g}")

    # --- optional plotting ---
    if args.plot:
        plot_map(diff, title=f"{args.var1} - {args.var2 or args.var1}")
        plt.show()

    if args.animate:
        output = args.output_gif or f"{args.var1}_diff.gif"
        animate_depths(diff, output=output)
        print(f"Saved animation to {output}")

    # --- metadata comparison ---
    if args.metadata:
        print("\n=== Global metadata differences ===")
        gdiffs = diff_global_metadata(args.file1, args.file2)
        if gdiffs:
            for k, v in gdiffs.items():
                print(f"{k}: {v['file1']} -> {v['file2']}")
        else:
            print("No global attribute differences")

        print("\n=== Variable metadata differences ===")
        vdiffs = diff_variable_metadata(args.file1, args.file2, variables=[args.var1])
        if vdiffs:
            for var, attrs in vdiffs.items():
                print(f"Variable {var}:")
                for k, v in attrs.items():
                    print(f"  {k}: {v['file1']} -> {v['file2']}")
        else:
            print("No variable attribute differences")


if __name__ == "__main__":
    main()
