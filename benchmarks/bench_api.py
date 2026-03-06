"""API performance benchmarks for driftwatch.

Measures requests/sec, p50/p95/p99 latency for key endpoints
using httpx ASGITransport (no network overhead — pure app performance).
"""

import asyncio
import statistics
import sys
import time

import httpx

from driftwatch.app import create_app

SCENARIOS = [
    {
        "name": "GET /health",
        "method": "GET",
        "url": "/health",
        "description": "Health check — returns status, version, timestamp (Pydantic serialization)",
    },
    {
        "name": "GET /ready",
        "method": "GET",
        "url": "/ready",
        "description": "Readiness probe — lightweight dict response",
    },
    {
        "name": "GET /openapi.json",
        "method": "GET",
        "url": "/openapi.json",
        "description": "OpenAPI schema generation — exercises FastAPI schema introspection",
    },
    {
        "name": "GET /health (concurrent)",
        "method": "GET",
        "url": "/health",
        "description": "Health check under 10-concurrent-request load",
        "concurrency": 10,
    },
]

REQUESTS_PER_SCENARIO = 1000
WARMUP_REQUESTS = 50


def percentile(data: list[float], p: float) -> float:
    """Calculate the p-th percentile of a sorted list."""
    k = (len(data) - 1) * (p / 100)
    f = int(k)
    c = f + 1
    if c >= len(data):
        return data[f]
    return data[f] + (k - f) * (data[c] - data[f])


async def run_single_request(client: httpx.AsyncClient, method: str, url: str) -> float:
    """Execute a single request and return latency in ms."""
    start = time.perf_counter()
    response = await client.request(method, url)
    elapsed = (time.perf_counter() - start) * 1000  # ms
    if response.status_code != 200:
        msg = f"Got {response.status_code} for {url}"
        raise RuntimeError(msg)
    return elapsed


async def bench_sequential(
    client: httpx.AsyncClient, method: str, url: str, n: int
) -> list[float]:
    """Run n sequential requests, return latencies."""
    latencies = []
    for _ in range(n):
        lat = await run_single_request(client, method, url)
        latencies.append(lat)
    return latencies


async def bench_concurrent(
    client: httpx.AsyncClient, method: str, url: str, n: int, concurrency: int
) -> list[float]:
    """Run n requests with given concurrency, return latencies."""
    sem = asyncio.Semaphore(concurrency)
    latencies: list[float] = []
    lock = asyncio.Lock()

    async def worker():
        async with sem:
            lat = await run_single_request(client, method, url)
            async with lock:
                latencies.append(lat)

    tasks = [asyncio.create_task(worker()) for _ in range(n)]
    await asyncio.gather(*tasks)
    return latencies


async def run_benchmarks() -> list[dict]:
    """Run all benchmark scenarios and return results."""
    app = create_app()
    transport = httpx.ASGITransport(app=app)

    results = []
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        for scenario in SCENARIOS:
            name = scenario["name"]
            method = scenario["method"]
            url = scenario["url"]
            concurrency = scenario.get("concurrency", 1)

            # Warmup
            for _ in range(WARMUP_REQUESTS):
                await run_single_request(client, method, url)

            # Benchmark
            wall_start = time.perf_counter()
            if concurrency > 1:
                latencies = await bench_concurrent(
                    client, method, url, REQUESTS_PER_SCENARIO, concurrency
                )
            else:
                latencies = await bench_sequential(
                    client, method, url, REQUESTS_PER_SCENARIO
                )
            wall_elapsed = time.perf_counter() - wall_start

            latencies.sort()
            rps = REQUESTS_PER_SCENARIO / wall_elapsed

            result = {
                "name": name,
                "description": scenario["description"],
                "requests": REQUESTS_PER_SCENARIO,
                "concurrency": concurrency,
                "wall_time_s": round(wall_elapsed, 3),
                "rps": round(rps, 1),
                "mean_ms": round(statistics.mean(latencies), 3),
                "stdev_ms": round(statistics.stdev(latencies), 3),
                "min_ms": round(latencies[0], 3),
                "p50_ms": round(percentile(latencies, 50), 3),
                "p95_ms": round(percentile(latencies, 95), 3),
                "p99_ms": round(percentile(latencies, 99), 3),
                "max_ms": round(latencies[-1], 3),
            }
            results.append(result)
            print(
                f"  {name}: {rps:.1f} req/s"
                f" | p50={result['p50_ms']:.3f}ms"
                f" p95={result['p95_ms']:.3f}ms"
                f" p99={result['p99_ms']:.3f}ms"
            )

    return results


def format_markdown(results: list[dict]) -> str:
    """Format benchmark results as Markdown."""
    lines = [
        "# API Performance Benchmarks",
        "",
        "Performance benchmarks for driftwatch API endpoints.",
        "",
        "## Methodology",
        "",
        "- **Tool**: httpx ASGITransport (in-process, no network overhead)",
        f"- **Requests per scenario**: {REQUESTS_PER_SCENARIO:,}",
        f"- **Warmup requests**: {WARMUP_REQUESTS:,}",
        "- **Measurement**: wall-clock time via `time.perf_counter()`",
        f"- **Environment**: Python {sys.version_info.major}.{sys.version_info.minor}"
        f".{sys.version_info.micro}, FastAPI, async event loop",
        "",
        "All latencies are in milliseconds. Requests/sec is calculated from wall-clock time.",
        "",
        "## Results Summary",
        "",
        "| Scenario | Concurrency | Req/s | p50 (ms) | p95 (ms) | p99 (ms) |",
        "|---|---|---:|---:|---:|---:|",
    ]

    for r in results:
        lines.append(
            f"| {r['name']} | {r['concurrency']} | {r['rps']}"
            f" | {r['p50_ms']} | {r['p95_ms']} | {r['p99_ms']} |"
        )

    lines.append("")
    lines.append("## Detailed Results")
    lines.append("")

    for r in results:
        lines.append(f"### {r['name']}")
        lines.append("")
        lines.append(f"{r['description']}")
        lines.append("")
        lines.append(f"- **Requests**: {r['requests']:,}")
        lines.append(f"- **Concurrency**: {r['concurrency']}")
        lines.append(f"- **Wall time**: {r['wall_time_s']}s")
        lines.append(f"- **Throughput**: {r['rps']} req/s")
        lines.append(f"- **Mean latency**: {r['mean_ms']}ms (stdev: {r['stdev_ms']}ms)")
        lines.append(f"- **Min**: {r['min_ms']}ms")
        lines.append(f"- **p50**: {r['p50_ms']}ms")
        lines.append(f"- **p95**: {r['p95_ms']}ms")
        lines.append(f"- **p99**: {r['p99_ms']}ms")
        lines.append(f"- **Max**: {r['max_ms']}ms")
        lines.append("")

    lines.append("## Performance Targets")
    lines.append("")
    lines.append("| Metric | Target | Status |")
    lines.append("|---|---|---|")

    # Evaluate targets based on results
    health = next(r for r in results if r["name"] == "GET /health")
    ready = next(r for r in results if r["name"] == "GET /ready")

    targets = [
        ("Health endpoint p99", "< 10ms", health["p99_ms"] < 10, f"{health['p99_ms']}ms"),
        ("Readiness endpoint p99", "< 5ms", ready["p99_ms"] < 5, f"{ready['p99_ms']}ms"),
        ("Health throughput", "> 1,000 req/s", health["rps"] > 1000, f"{health['rps']} req/s"),
        ("Readiness throughput", "> 2,000 req/s", ready["rps"] > 2000, f"{ready['rps']} req/s"),
    ]

    for name, target, passed, actual in targets:
        status = "PASS" if passed else "FAIL"
        lines.append(f"| {name} | {target} | {status} ({actual}) |")

    lines.append("")
    lines.append("## How to Reproduce")
    lines.append("")
    lines.append("```bash")
    lines.append("# From project root")
    lines.append("python benchmarks/bench_api.py")
    lines.append("```")
    lines.append("")
    lines.append("Results will be printed to stdout and written to `BENCHMARKS.md`.")
    lines.append("")

    return "\n".join(lines)


async def main():
    print("Running driftwatch API benchmarks...")
    print(f"  {REQUESTS_PER_SCENARIO} requests per scenario, {WARMUP_REQUESTS} warmup\n")

    results = await run_benchmarks()

    md = format_markdown(results)

    # Write BENCHMARKS.md in project root (parent of benchmarks/)
    import pathlib
    project_root = pathlib.Path(__file__).resolve().parent.parent
    out_path = project_root / "BENCHMARKS.md"
    out_path.write_text(md)
    print(f"\nResults written to {out_path}")


if __name__ == "__main__":
    asyncio.run(main())
