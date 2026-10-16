# SPDX-License-Identifier: MPL-2.0
"""Exercise worker failures in isolated process groups with an outer deadline."""
import multiprocessing
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import unittest

from BibleOrgSys.Misc.Parallel import ParallelTaskError, run_parallel


class UnpicklableError(Exception):
    def __init__(self, detail):
        self.detail = detail
        super().__init__(detail['message'])


def task(argument):
    kind, value = argument
    if kind == 'slow':
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        time.sleep(60)
    elif kind == 'fail':
        time.sleep(0.15)
        error = ValueError("Unsupported source verse label SA1 13:'7And' [Bible KJB-1611]")
        error.add_note('Requested English SA1 13:7')
        raise error
    elif kind == 'custom_error':
        raise UnpicklableError({'message':'custom exception survives as traceback text'})
    elif kind == 'unpicklable_result':
        return lambda: value
    elif kind == 'exit':
        os._exit(value)
    elif kind == 'system_exit':
        raise SystemExit(value)
    elif kind == 'interrupt':
        raise KeyboardInterrupt('worker interrupted')
    elif kind == 'pid':
        return os.getpid()
    elif kind == 'delay':
        time.sleep(value / 100)
    return value


def mapping_error(_):
    from BibleOrgSys.Reference.BibleVersificationMappings import MappingResult, MappingStatus, PartialMappingError
    raise PartialMappingError(MappingResult('eng','org',(('ACT','19','41',None),),MappingStatus.PARTIAL))


def scenario(name):
    context = multiprocessing.get_context('fork')
    started = time.monotonic()
    if name == 'order':
        assert run_parallel(task,[('delay',n) for n in (15,1,5,0)],processes=2,context=context,chunksize=1) == [15,1,5,0]
        assert run_parallel(task,[('return',n) for n in range(23)],processes=3,context=context,chunksize=4) == list(range(23))
        assert run_parallel(task,[],processes=2,context=context) == []
    elif name == 'fresh':
        pids = run_parallel(task,[('pid',None)]*8,processes=2,context=context,chunksize=1)
        assert len(set(pids)) == 8, pids
    elif name == 'spawn':
        assert run_parallel(task,[('return',3),('return',1)],processes=2,
                            context=multiprocessing.get_context('spawn'),chunksize=1) == [3,1]
    elif name == 'mapping_pickle':
        with context.Pool(1) as pool:
            result = pool.apply_async(mapping_error,(None,))
            try:
                result.get(timeout=4)
            except Exception as error:
                from BibleOrgSys.Reference.BibleVersificationMappings import PartialMappingError
                assert isinstance(error,PartialMappingError), repr(error)
                assert error.result.source_references == (('ACT','19','41',None),)
            else:
                raise AssertionError('Expected a mapping failure')
    else:
        if name == 'death':
            failing = ('exit',23)
        elif name == 'zero_exit':
            failing = ('exit',0)
        else:
            failing = (name,4)
        try:
            run_parallel(task,[('slow',0),failing],processes=2,context=context,chunksize=1,
                         labels=['slow Bible','KJB-1611 SA1'])
        except ParallelTaskError as error:
            message = str(error)
            assert 'KJB-1611 SA1' in message, message
            if name == 'fail':
                assert '7And' in message and 'Traceback' in message and 'Requested English SA1 13:7' in message
            elif name == 'unpicklable_result':
                assert 'serialize/send' in message, message
            elif name == 'custom_error':
                assert 'UnpicklableError' in message, message
            elif name == 'system_exit':
                assert 'SystemExit: 4' in message, message
        else:
            raise AssertionError('Expected a worker failure')
    assert time.monotonic()-started < 5, 'Failure was not reported promptly'
    assert not multiprocessing.active_children(), 'Worker cleanup leaked child processes'


@unittest.skipUnless('fork' in multiprocessing.get_all_start_methods(), 'fork process tests')
class ParallelTests(unittest.TestCase):
    def run_scenario(self, name):
        process = subprocess.Popen([sys.executable,str(Path(__file__).resolve()),'--scenario',name],
            stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,start_new_session=True)
        try:
            out,err = process.communicate(timeout=10)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid,signal.SIGKILL)
            out,err = process.communicate()
            self.fail(f'{name} hung beyond the outer deadline:\n{out}\n{err}')
        self.assertEqual(process.returncode,0,f'{name}:\n{out}\n{err}')

    def test_success_results_keep_input_order(self): self.run_scenario('order')
    def test_fresh_workers_do_not_share_task_accumulators(self): self.run_scenario('fresh')
    def test_spawn_context_also_works(self): self.run_scenario('spawn')
    def test_fast_error_does_not_wait_for_slow_job(self): self.run_scenario('fail')
    def test_abrupt_worker_death_does_not_lose_a_result(self): self.run_scenario('death')
    def test_exit_zero_without_result_is_still_failure(self): self.run_scenario('zero_exit')
    def test_system_exit_is_reported(self): self.run_scenario('system_exit')
    def test_keyboard_interrupt_in_worker_is_reported(self): self.run_scenario('interrupt')
    def test_unpicklable_exception_preserves_traceback(self): self.run_scenario('custom_error')
    def test_unpicklable_result_is_reported(self): self.run_scenario('unpicklable_result')
    def test_bos_exception_survives_existing_pool_transport(self): self.run_scenario('mapping_pickle')


if __name__ == '__main__':
    if len(sys.argv)>1 and sys.argv[1]=='--scenario':
        scenario(sys.argv[2])
    else:
        unittest.main()
