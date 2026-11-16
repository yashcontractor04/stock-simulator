# Benchmarks

Every time I make something faster (or try to), I write it down here: the same test before
and after, with numbers. One entry per change. Failed attempts stay in too. They are part
of the story.

## The test setup

Fill in once in M6, update when it changes.

| | |
|---|---|
| Machine | Oracle VM, 2 OCPU / 12 GB, shared with the portfolio worker |
| Postgres limits | 2 GB RAM, 1 CPU |
| Data | ___ instruments, ___ million price rows |
| Load tool | k6 ___ on my Mac through an SSH tunnel |
| Scenario file | `loadtest/___.js` |

## Template

Copy this block for each loop.

```
## Loop N: (what I changed, in a few words)        YYYY-MM-DD

**Symptom.** What was slow or broke, and how I noticed.

**Measurement before.**
| Scenario | Requests/s | p50 | p95 | Errors |
|---|---|---|---|---|
|   |   |   |   |   |

**Finding.** The biggest bottleneck and the evidence (query plan, pg_stat_statements row,
metric, log line). Paste the important lines.

**Change.** One thing. Commit: `abc1234`.

**Measurement after.** Same scenario, same data.
| Scenario | Requests/s | p50 | p95 | Errors |
|---|---|---|---|---|
|   |   |   |   |   |

**Result.** Faster or slower by how much. What it cost (RAM, disk, complexity).

**What I would say in an interview.** Two or three sentences.
```

---

<!-- First entry goes here after M6. -->
