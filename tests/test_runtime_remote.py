"""Local bare-remote persistence and independent-clone concurrency tests."""
from __future__ import annotations
import json
import subprocess
from pathlib import Path
import pytest
from router.runtime import RouterRuntimeStore
from state_store import StateStore

def git(cwd: Path,*args):
    return subprocess.run(['git',*args],cwd=str(cwd),check=True,text=True,capture_output=True).stdout.strip()

def clones(tmp_path: Path):
    remote=tmp_path/'remote.git'
    subprocess.run(['git','init','--bare','--initial-branch=main',str(remote)],check=True,capture_output=True)
    seed=tmp_path/'seed';seed.mkdir()
    git(seed,'init','-b','main');git(seed,'config','user.email','t@e.i');git(seed,'config','user.name','T')
    (seed/'README.md').write_text('seed')
    git(seed,'add','.');git(seed,'commit','-m','seed')
    git(seed,'remote','add','origin',str(remote));git(seed,'push','origin','main')
    found=[]
    for n in (1,2):
        path=tmp_path/f'clone{n}'
        subprocess.run(['git','clone',str(remote),str(path)],check=True,capture_output=True)
        git(path,'config','user.name','T');git(path,'config','user.email','t@e.i')
        found.append(path)
    return remote,found

def read_remote(remote):
    raw=subprocess.run(['git','-C',str(remote),'show','router-state:router_runtime.json'],check=True,text=True,capture_output=True).stdout
    return json.loads(raw)

def test_remote_persistence_fresh_clone(tmp_path):
    remote,(one,two)=clones(tmp_path)
    s1=RouterRuntimeStore(StateStore(one))
    s1.transact(lambda rt:rt.update(alpha=1),operation_id='first')
    s2=RouterRuntimeStore(StateStore(two))
    assert s2.load()['alpha']==1
    s2.transact(lambda rt:rt.update(beta=2),operation_id='second')
    assert read_remote(remote)=={'alpha':1,'beta':2}

def test_stale_clones_do_not_lose_updates(tmp_path):
    remote,(one,two)=clones(tmp_path)
    rt1=RouterRuntimeStore(StateStore(one))
    rt1.transact(lambda rt:rt.update(seed=True))
    rt2=RouterRuntimeStore(StateStore(two))
    rt1.transact(lambda rt:rt.update(a=1))
    rt2.transact(lambda rt:rt.update(b=2))
    assert read_remote(remote)=={'seed':True,'a':1,'b':2}

def test_failed_remote_push_does_not_succeed(tmp_path):
    remote,(one,two)=clones(tmp_path)
    rt=RouterRuntimeStore(StateStore(one))
    rt.transact(lambda state:state.update(seed=True))
    # Reject all writes using a local bare-repository hook (no network).
    hooks=remote/'hooks';hook=hooks/'pre-receive'
    hook.write_text('#!/bin/sh\nexit 1\n');hook.chmod(0o755)
    with pytest.raises(Exception):
        rt.transact(lambda state:state.update(should_not_commit=True),attempts=2)
    assert 'should_not_commit' not in read_remote(remote)
