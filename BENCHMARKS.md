# API Performance Benchmarks

Performance benchmarks for driftwatch API endpoints.

## Methodology

- **Tool**: httpx ASGITransport (in-process, no network overhead)
- **Requests per scenario**: 1,000
- **Warmup requests**: 50
- **Measurement**: wall-clock time via `time.perf_counter()`
- **Environment**: Python 3.12.3, FastAPI, async event loop

All latencies are in milliseconds. Requests/sec is calculated from wall-clock time.

## Results Summary

| Scenario | Concurrency | Req/s | p50 (ms) | p95 (ms) | p99 (ms) |
|---|---|---:|---:|---:|---:|
| GET /health | 1 | 2360.7 | 0.391 | 0.463 | 0.569 |
| GET /ready | 1 | 2558.5 | 0.378 | 0.425 | 0.544 |
| GET /openapi.json | 1 | 2751.6 | 0.353 | 0.384 | 0.53 |
| GET /health (concurrent) | 10 | 2312.0 | 0.395 | 0.547 | 0.643 |

## Detailed Results

### GET /health

Health check — returns status, version, timestamp (Pydantic serialization)

- **Requests**: 1,000
- **Concurrency**: 1
- **Wall time**: 0.424s
- **Throughput**: 2360.7 req/s
- **Mean latency**: 0.421ms (stdev: 0.612ms)
- **Min**: 0.348ms
- **p50**: 0.391ms
- **p95**: 0.463ms
- **p99**: 0.569ms
- **Max**: 19.693ms

### GET /ready

Readiness probe — lightweight dict response

- **Requests**: 1,000
- **Concurrency**: 1
- **Wall time**: 0.391s
- **Throughput**: 2558.5 req/s
- **Mean latency**: 0.388ms (stdev: 0.038ms)
- **Min**: 0.346ms
- **p50**: 0.378ms
- **p95**: 0.425ms
- **p99**: 0.544ms
- **Max**: 1.052ms

### GET /openapi.json

OpenAPI schema generation — exercises FastAPI schema introspection

- **Requests**: 1,000
- **Concurrency**: 1
- **Wall time**: 0.363s
- **Throughput**: 2751.6 req/s
- **Mean latency**: 0.36ms (stdev: 0.031ms)
- **Min**: 0.32ms
- **p50**: 0.353ms
- **p95**: 0.384ms
- **p99**: 0.53ms
- **Max**: 0.579ms

### GET /health (concurrent)

Health check under 10-concurrent-request load

- **Requests**: 1,000
- **Concurrency**: 10
- **Wall time**: 0.433s
- **Throughput**: 2312.0 req/s
- **Mean latency**: 0.415ms (stdev: 0.062ms)
- **Min**: 0.352ms
- **p50**: 0.395ms
- **p95**: 0.547ms
- **p99**: 0.643ms
- **Max**: 0.972ms

## Performance Targets

| Metric | Target | Status |
|---|---|---|
| Health endpoint p99 | < 10ms | PASS (0.569ms) |
| Readiness endpoint p99 | < 5ms | PASS (0.544ms) |
| Health throughput | > 1,000 req/s | PASS (2360.7 req/s) |
| Readiness throughput | > 2,000 req/s | PASS (2558.5 req/s) |

## How to Reproduce

```bash
# From project root
python benchmarks/bench_api.py
```

Results will be printed to stdout and written to `BENCHMARKS.md`.
