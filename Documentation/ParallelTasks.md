# Running parallel tasks with visible failures

`BibleOrgSys.Misc.Parallel.run_parallel` returns results in input order and stops
the remaining workers when a task fails. It monitors result pipes and worker
exit notifications, including unexpected exits that would leave a pool waiting
for a lost result. It does not impose a time limit on successful work.

```python
import multiprocessing
from BibleOrgSys.Misc.Parallel import run_parallel

results = run_parallel(
    process_book, book_parameters,
    processes=4,
    context=multiprocessing.get_context('fork'),
    labels=book_names,
    chunksize=1,
)
```

The function accepts one item and returns a picklable result. `labels`, when
provided, must have one short descriptive name per input item. A failure raises
`ParallelTaskError` with the worker function, task name or chunk range, process
ID, and original traceback when available. Exception notes are included. Workers
send errors as text, so exceptions with custom constructors cannot break the
parent's result receiver. Non-picklable results also produce an explicit error.

Each chunk runs in a fresh daemon process. `chunksize=1` gives each task clean
inherited state; the default uses approximately four chunks per worker, like
`Pool.map`. Workers cannot launch their own child processes. On failure or parent
interruption, remaining workers are terminated, then killed if they ignore
termination. Applications must treat files written before a failure as partial
output; the runner does not roll back side effects.

The default context is the platform's multiprocessing context. Select `fork`
explicitly when a supported application must share large, preloaded, read-only
datasets through inheritance. For `spawn` or `forkserver`, normal multiprocessing
requirements apply: functions and arguments must be picklable, and the entry
point must use an `if __name__ == '__main__'` guard. Application-specific build
flags and resource initialization remain the caller's responsibility.
