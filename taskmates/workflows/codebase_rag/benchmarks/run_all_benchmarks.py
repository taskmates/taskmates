"""
Run all benchmarks and generate a combined report.
"""
import subprocess
import sys


def run_benchmark(script_name: str) -> int:
    """Run a benchmark script and return exit code."""
    print(f"\n{'=' * 70}")
    print(f"Running {script_name}")
    print('=' * 70)
    
    result = subprocess.run(
        [sys.executable, script_name],
        cwd=".",
        capture_output=False
    )
    
    return result.returncode


def main():
    """Run all benchmarks."""
    print("Starting benchmark suite...")
    
    benchmarks = [
        "benchmark_parallelism.py",
        "benchmark_context_length.py"
    ]
    
    results = {}
    
    for benchmark in benchmarks:
        exit_code = run_benchmark(benchmark)
        results[benchmark] = "SUCCESS" if exit_code == 0 else "FAILED"
    
    # Summary
    print("\n" + "=" * 70)
    print("BENCHMARK SUITE SUMMARY")
    print("=" * 70)
    
    for benchmark, status in results.items():
        status_symbol = "✓" if status == "SUCCESS" else "✗"
        print(f"{status_symbol} {benchmark}: {status}")
    
    all_passed = all(status == "SUCCESS" for status in results.values())
    
    if all_passed:
        print("\nAll benchmarks completed successfully!")
        return 0
    else:
        print("\nSome benchmarks failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())
