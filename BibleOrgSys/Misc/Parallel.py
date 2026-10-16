# SPDX-FileCopyrightText: © 2026 Robert Hunt <Freely.Given.org+BOS@gmail.com>
# SPDX-License-Identifier: MPL-2.0
"""Ordered parallel results with prompt, transport-safe failure reporting.

Workers execute bounded chunks. The parent watches both result pipes and process
exit sentinels, so a failed/killed worker cannot silently lose a pending result.
Exceptions cross process boundaries as traceback text, never arbitrary exception
objects whose constructors/unpickling could break the receiving thread.
"""
import multiprocessing
from multiprocessing.connection import wait
import time
import traceback


class ParallelTaskError(RuntimeError):
    """A task failed, its result could not be transported, or a worker exited."""


def _run_chunk(sender, function, chunk):
    try:
        results = []
        for index, item in chunk:
            try:
                results.append(function(item))
            except BaseException:
                sender.send(('error', index, traceback.format_exc()))
                return
        try:
            sender.send(('ok', results))
        except BaseException:
            sender.send(('error', None, 'Unable to serialize/send chunk results:\n' + traceback.format_exc()))
    finally:
        sender.close()


def _stop_workers(workers):
    """Stop every remaining worker, including one ignoring SIGTERM."""
    for process in workers:
        if process.is_alive():
            process.terminate()
    deadline = time.monotonic() + 0.5
    for process in workers:
        process.join(max(0, deadline - time.monotonic()))
    for process in workers:
        if process.is_alive():
            process.kill()
    deadline = time.monotonic() + 1
    for process in workers:
        process.join(max(0, deadline - time.monotonic()))


def run_parallel(function, items, *, processes, context=None, chunksize=None, labels=None):
    """Return results in input order, stopping all workers on the first failure.

    context accepts a multiprocessing context (e.g. explicit fork for large
    inherited Bible datasets). By default chunks match Pool.map's approximate
    size; each chunk runs in a fresh process. Use chunksize=1 when per-task
    accumulators must start clean. labels supplies short task names for errors.
    There is no time limit on legitimate work. Cleanup after failure is bounded.
    """
    if not isinstance(processes, int) or processes < 1:
        raise ValueError('processes must be a positive integer')
    items = list(items)
    if labels is not None:
        labels = list(labels)
        if len(labels) != len(items):
            raise ValueError('labels must have one entry per task')
    if chunksize is not None and (not isinstance(chunksize, int) or chunksize < 1):
        raise ValueError('chunksize must be a positive integer')
    if not items:
        return []
    chunksize = chunksize or max(1, (len(items) + processes*4-1) // (processes*4))
    context = context or multiprocessing.get_context()
    worker_name = f'{function.__module__}.{getattr(function, "__qualname__", type(function).__qualname__)}'
    results, active, next_index = [None] * len(items), {}, 0

    def task_name(index):
        return f'{index+1} ({labels[index]})' if labels is not None else str(index+1)

    def chunk_name(first, last):
        return task_name(first) if last == first+1 else f'{task_name(first)} through {task_name(last-1)}'

    try:
        while active or next_index < len(items):
            while len(active) < processes and next_index < len(items):
                first, last = next_index, min(next_index+chunksize, len(items))
                reader, sender = context.Pipe(duplex=False)
                process = context.Process(target=_run_chunk,
                    args=(sender, function, list(enumerate(items[first:last], first))), daemon=True)
                try:
                    process.start()
                except BaseException:
                    reader.close()
                    sender.close()
                    process.close()
                    raise
                sender.close()
                active[reader] = (process, first, last, False)
                next_index = last
            ready = wait([*(reader for reader, (_, _, _, received) in active.items() if not received),
                          *(p.sentinel for p, *_ in active.values())])
            for reader, (process, first, last, received) in list(active.items()):
                if reader in ready:
                    try:
                        message = reader.recv()
                    except EOFError:
                        raise ParallelTaskError(f'{worker_name}: worker {process.pid} closed its result '
                            f'pipe before completing tasks {chunk_name(first,last)} (exit code {process.exitcode})') from None
                    except Exception as error:
                        raise ParallelTaskError(f'{worker_name}: unable to receive tasks '
                            f'{chunk_name(first,last)} from worker {process.pid}: {error}') from error
                    if message[0] == 'error':
                        _, index, details = message
                        name = task_name(index) if index is not None else chunk_name(first,last)
                        raise ParallelTaskError(f'{worker_name}: task {name} failed in worker '
                                                f'{process.pid}:\n{details}')
                    _, values = message
                    if len(values) != last-first:
                        raise ParallelTaskError(f'{worker_name}: incomplete results for tasks {chunk_name(first,last)}')
                    results[first:last] = values
                    received = True
                    active[reader] = (process, first, last, received)
                if process.sentinel in ready:
                    # A pipe message queued before exit can become ready after
                    # wait's snapshot. Consume it on the next pass first.
                    if not received and reader not in ready and reader.poll():
                        continue
                    process.join()
                    if process.exitcode != 0 or not received:
                        raise ParallelTaskError(f'{worker_name}: worker {process.pid} exited with code '
                            f'{process.exitcode} before completing tasks {chunk_name(first,last)}')
                    reader.close()
                    process.close()
                    del active[reader]
    finally:
        workers = [process for process, *_ in active.values()]
        _stop_workers(workers)
        for reader, (process, *_) in active.items():
            reader.close()
            if not process.is_alive():
                process.close()
    return results
