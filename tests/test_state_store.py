import json
import subprocess
from pathlib import Path

import pytest
from state_store import StateStore, StateStoreError, SensitiveStateError, OversizedStateError, compute_task_id, STATE_SCHEMA_VERSION


def run(cwd,*args, check=True):
    return subprocess.run(['git',*args],cwd=cwd,check=check,capture_output=True,text=True)

@pytest.fixture
def repo(tmp_path):
    path=tmp_path/'repo'
    path.mkdir()
    run(path,'init','-b','main')
    run(path,'config','user.email','test@example.invalid')
    run(path,'config','user.name','Test')
    (path/'.gitignore').write_text('.router-state/\n.router-locks/\n.lock\n')
    (path/'README.md').write_text('seed\n')
    run(path,'add','.gitignore','README.md')
    run(path,'commit','-m','init')
    return path

def test_task_id_is_deterministic_and_input_sensitive():
    a=compute_task_id('script',{'topic':'x'},'1.0')
    assert a==compute_task_id('script',{'topic':'x'},'1.0') and len(a)==64
    assert compute_task_id('script',{'a':1,'b':2},'1.0')==compute_task_id('script',{'b':2,'a':1},'1.0')
    for x,y,z in [('script',{'topic':'y'},'1.0'),('seo',{'topic':'x'},'1.0'),('script',{'topic':'x'},'2.0')]:
        assert a!=compute_task_id(x,y,z)

def test_record_and_retrieve_cached_result(repo):
    s=StateStore(repo,push_required=False)
    tid=compute_task_id('script',{'topic':'x'},'1.0')
    assert not s.is_completed(tid) and s.get_cached_result(tid) is None
    assert s.record_completion(tid,'script',{'text':'hello'}) is True
    assert s.get_cached_result(tid)=={'text':'hello'} and s.completed_task_ids()==[tid]
    assert isinstance(s.last_completed_at(),str)

def test_duplicate_completion_is_rejected(repo):
    s=StateStore(repo,push_required=False)
    tid=compute_task_id('script',{'topic':'x'},'1.0')
    assert s.record_completion(tid,'script',{'v':1}) is True
    assert s.record_completion(tid,'script',{'v':999}) is False
    assert s.get_cached_result(tid)=={'v':1}

def test_resume_discards_uncommitted_writes(repo):
    s=StateStore(repo,push_required=False)
    tid=compute_task_id('script',{'topic':'kept'},'1.0')
    s.record_completion(tid,'script',{'text':'kept'})
    state=s._read_state()
    state['tasks']['orphan']={'task_type':'script','completed_at':'1970-01-01T00:00:00+00:00','result':{'stale':True}}
    s._write_state(state)
    s2=StateStore(repo,push_required=False)
    assert 'orphan' not in s2._read_state()['tasks']
    assert s2.completed_task_ids()==[tid]

def test_rejects_sensitive_keys_and_values(repo):
    s=StateStore(repo,push_required=False)
    tid=compute_task_id('script',{'t':1},'1.0')
    with pytest.raises(SensitiveStateError): s.record_completion(tid,'script',{'api_key':'abc'})
    with pytest.raises(SensitiveStateError): s.record_completion(tid,'script',{'blob':'ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ012345'})
    assert s.record_completion(tid,'script',{'token_count':42}) is True

def test_rejects_oversized_result(repo):
    s=StateStore(repo,push_required=False)
    with pytest.raises(OversizedStateError):
        s.record_completion('a'*64,'script',{'blob':'x'*(300*1024)})

def test_lock_file_lives_outside_worktree(repo):
    s=StateStore(repo,push_required=False)
    s._acquire_lock()
    try:
        assert s.lock_path.exists() and s.worktree_path not in s.lock_path.parents
        run(s.worktree_path,'clean','-fd')
        assert s.lock_path.exists()
    finally:
        s._release_lock()

def test_branch_isolation_and_no_credentials_in_state(repo):
    s=StateStore(repo,push_required=False)
    tid=compute_task_id('script',{'topic':'x'},'1.0')
    s.record_completion(tid,'script',{'text':'result'})
    assert not (repo/'state.json').exists()
    assert (repo/'README.md').exists()
    assert run(repo,'rev-parse','--abbrev-ref','HEAD').stdout.strip()=='main'
    raw=s.state_path.read_text().lower()
    assert all(w not in raw for w in ('password','secret','ghp_','sk-','begin rsa'))
    assert s._read_state()['schema_version']==STATE_SCHEMA_VERSION

def test_schema_version_mismatch_raises(repo):
    s=StateStore(repo,push_required=False)
    data=json.loads(s.state_path.read_text())
    data['schema_version']='999'
    s.state_path.write_text(json.dumps(data))
    with pytest.raises(StateStoreError):s._read_state()


def test_rejects_provider_named_credentials(repo):
    s=StateStore(repo,push_required=False)
    with pytest.raises(SensitiveStateError):
        s.record_completion('b'*64,'script',{'gemini_api_key':'my-private-value'})


def test_rejects_bearer_credential_embedded_in_free_text(repo):
    s=StateStore(repo,push_required=False)
    with pytest.raises(SensitiveStateError):
        s.record_completion('c'*64,'script',{'log':'Authorization: Bearer not-a-real-secret-value'})
