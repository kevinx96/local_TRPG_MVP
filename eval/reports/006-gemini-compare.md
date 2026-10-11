拟定标签下的初步数字；n/a 表示没有可评测数据。

| run | model | variant | responses/total | S0+S1 | S3 | InvalidPlan | conflict | existing.operation 清理/恢复 | exact | kind | injection no_state_change | p50 ms | p95 ms | input tokens | output tokens | cached tokens | cost/turn USD | 归一化次数 |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2026-10-11T112514831356Z-intent-gemini-gemini-3.1-flash-lite-default | gemini-3.1-flash-lite | default | 194/194 | 0.8969 | 0.0309 | 0.0155 | n/a | n/a | 0.8969 | 0.9278 | 1.0000 | 1003.9150 | 1230.7921 | 706.0309 | 83.6443 | n/a | 0.00030197 | 5 |
| 2026-10-11T112526523573Z-intent-gemini-gemini-3.1-flash-lite-lenient | gemini-3.1-flash-lite | lenient | 194/194 | 0.9072 | 0.0361 | 0.0000 | 0.0412 | 3/3 | 0.9072 | 0.9381 | 1.0000 | 1003.9150 | 1230.7921 | 706.0309 | 83.6443 | n/a | 0.00030197 | 0 |
| 2026-10-11T112538606761Z-intent-gemini-gemini-3.1-flash-lite-union_schema | gemini-3.1-flash-lite | union_schema | 194/194 | 0.0000 | 0.0000 | 1.0000 | n/a | n/a | 0.0000 | 0.0000 | 1.0000 | 2145.8700 | 2480.0992 | 706.0309 | 456.9794 | n/a | 0.00086198 | 0 |
| 2026-10-11T113141950061Z-intent-gemini-gemini-3.1-flash-lite-union_schema_noenum | gemini-3.1-flash-lite | union_schema_noenum | 194/194 | 0.0000 | 0.0000 | 1.0000 | n/a | n/a | 0.0000 | 0.0000 | 1.0000 | 2039.6785 | 2504.6798 | 706.0309 | 475.9072 | n/a | 0.00089037 | 0 |
