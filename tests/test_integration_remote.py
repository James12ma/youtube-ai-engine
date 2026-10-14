import json
import subprocess
import sys
import time
from pathlib import Path

import pytest
from state_store import StateStore, compute_task_id

ROOT=Path(__file__).resolve().parent.parent

def run(cwd,*args,check=True):
    return subprocess.run(['git',*args],cwd=cwd,check=check,capture_output=True,text=True)

def seed_remote(tmp_path):
    bare=tmp_path/'remote.git'
    subprocess.run(['git','init','--bare','--initial-branch=main',str(bare)],check=True,capture_output=True)
    seed=tmp_path/'seed';seed.mkdir()
    run(seed,'init','-b','main')
    run(seed,'config','user.email','seed@example.invalid')
    run(seed,'config','user.name','Seed')
    (seed/'README.md').write_text('seed\n')
    run(seed,'add','README.md');run(seed,'commit','-m','init')
    run(seed,'remote','add','origin',str(bare));run(seed,'push','origin','main')
    clones=[]
    for i in (1,2):
        clone=tmp_path/f'clone{i}'
        subprocess.run(['git','clone',str(bare),str(clone)],check=True,capture_output=True)
        run(clone,'config','user.email',f'c{i}@e.i');run(clone,'config','user.name',f'C{i}')
        clones.append(clone)
    return bare,clones

def remote_state(bare):
    return json.loads(run(bare,'show','router-state:state.json').stdout)

def test_state_branch_is_pushed_and_recovered(tmp_path):
    bare,(c1,c2)=seed_remote(tmp_path)
    s1=StateStore(c1)
    tid=compute_task_id('script',{'topic':'hello'},'1.0')
    assert s1.record_completion(tid,'script',{'text':'hi'}) is True
    assert tid in remote_state(bare)['tasks']
    s2=StateStore(c2)
    assert s2.is_completed(tid)
    assert s2.get_cached_result(tid)=={'text':'hi'}

def test_duplicate_across_clones_is_idempotent(tmp_path):
    bare,(c1,c2)=seed_remote(tmp_path)
    tid=compute_task_id('script',{'topic':'same'},'1.0')
    assert StateStore(c1).record_completion(tid,'script',{'v':1}) is True
    assert StateStore(c2).record_completion(tid,'script',{'v':999}) is False
    assert remote_state(bare)['tasks'][tid]['result']=={'v':1}

def spawn_writer(clone,suffix,barrier):
    src=(
       'import sys,time\n'
       f'sys.path.insert(0,{str(ROOT)!r})\n'
       'from pathlib import Path\n'
       'from state_store import StateStore,compute_task_id\n'
       f'barrier=Path({str(barrier)!r})\n'
       'while not barrier.exists():time.sleep(0.02)\n'
       f'store=StateStore(Path({str(clone)!r}))\n'
       f'tid=compute_task_id("script",{{"n":{suffix}}},"1.0")\n'
       f'ok=store.record_completion(tid,"script",{{"value":{suffix}}})\n'
       'print("OK",ok)\n'
    )
    return subprocess.Popen([sys.executable,'-c',src],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)

def test_concurrent_writers_both_succeed(tmp_path):
    bare,(c1,c2)=seed_remote(tmp_path)
    StateStore(c1).push()
    barrier=tmp_path/'GO'
    p1=spawn_writer(c1,1,barrier);p2=spawn_writer(c2,2,barrier)
    time.sleep(0.4);barrier.touch()
    o1,e1=p1.communicate(timeout=60);o2,e2=p2.communicate(timeout=60)
    assert p1.returncode==0,(o1,e1)
    assert p2.returncode==0,(o2,e2)
    assert 'OK True' in o1 and 'OK True' in o2
    assert len(remote_state(bare)['tasks'])==2

def test_resume_after_remote_push_ignores_local_drift(tmp_path):
    bare,(c1,c2)=seed_remote(tmp_path)
    a=compute_task_id('script',{'topic':'A'},'1.0')
    StateStore(c1).record_completion(a,'script',{'v':'A'})
    s2=StateStore(c2)
    assert s2.is_completed(a)
    b=compute_task_id('script',{'topic':'B'},'1.0')
    assert s2.record_completion(b,'script',{'v':'B'}) is True
    assert a in remote_state(bare)['tasks'] and b in remote_state(bare)['tasks']

# Additional adversarial tests not present in DeepSeek's draft

def test_push_rejected_must_not_claim_durable(tmp_path):
    bare,(c1,c2)=seed_remote(tmp_path)
    s=StateStore(c1)
    s.push() # initialize remote state
    # Make remote read-only at the Git layer using a rejecting pre-receive hook.
    hooks=bare/'hooks';hooks.mkdir(exist_ok=True)
    hook=hooks/'pre-receive'
    hook.write_text('#!/bin/sh\necho "push deliberately rejected" 1>&2\nexit 1\n')
    hook.chmod(0o755)
    tid=compute_task_id('script',{'topic':'must-never-confirm'},'1.0')
    try:
        reported=s.record_completion(tid,'script',{'v':'should-not-be-durable'})
    except Exception:
        reported='exception'
    assert reported is not True, 'BUG: success returned despite remote rejection'
    assert tid not in remote_state(bare)['tasks']


def test_remote_unavailable_must_not_claim_durable(tmp_path):
    bare,(c1,c2)=seed_remote(tmp_path)
    s=StateStore(c1)
    s.push()
    new_bad_target=tmp_path/'nonexistent-remote.git'
    run(c1,'remote','set-url','origin',str(new_bad_target))
    tid=compute_task_id('script',{'topic':'offline'},'1.0')
    try:
        reported=s.record_completion(tid,'script',{'v':'off'})
    except Exception:
        reported='exception'
    assert reported is not True, 'BUG: success returned without a reachable remote'
    assert tid not in remote_state(bare)['tasks']


def test_initial_push_failure_must_raise_not_return_false(tmp_path):
    bare,(c1,_) = seed_remote(tmp_path)
    s = StateStore(c1)
    # Branch does not exist on remote yet. Force the first push to fail.
    hook=bare/'hooks'/'pre-receive'
    hook.write_text('#!/bin/sh\nexit 1\n')
    hook.chmod(0o755)
    tid=compute_task_id('script',{'topic':'first-push'},'1.0')
    with pytest.raises(Exception, match='persist|push|concurrent|remote|Failed'):
        s.record_completion(tid,'script',{'v':'should-not-save'})
    assert run(bare,'branch','--list','router-state').stdout.strip()==''


def test_failed_first_push_must_not_leave_cached_completion(tmp_path):
    bare,(c1,_) = seed_remote(tmp_path)
    s=StateStore(c1)
    hook=bare/'hooks'/'pre-receive'
    hook.write_text('#!/bin/sh\nexit 1\n')
    hook.chmod(0o755)
    tid=compute_task_id('script',{'topic':'cache-invalidation'},'1.0')
    with pytest.raises(Exception):
        s.record_completion(tid,'script',{'v':1})
    assert s.get_task(tid) is None, 'BUG: local cache reports completed after rejected first push'
