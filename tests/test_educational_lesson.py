import json
from pathlib import Path
import httpx
import pytest
from scripts.diagnose_free_quota import classify

@pytest.mark.parametrize('message,flag',[
    ('free-models-per-day limit exceeded','daily_quota_exhausted'),
    ('Model is temporarily rate-limited upstream','upstream_capacity'),
    ('Requests per minute exceeded','minute_rate_limit'),
])
def test_rate_reason_is_fixed_vocabulary(message,flag):
    response=httpx.Response(429,json={'error':{'message':message,'metadata':{'raw':'secret-value-not-for-output','provider_name':'arbitrary-secret'}}},headers={'Retry-After':'30'})
    result=classify(response)
    assert result[flag] and result['retry_after_seconds']==30
    assert 'secret' not in json.dumps(result)


def test_lesson_has_substantive_script_and_real_demo_expectations():
    lesson=json.loads(Path('content/expense-rule-lesson/lesson.json').read_text())
    assert sum(len(c['narration'].split()) for c in lesson['chapters'])>800
    demos=[c['demo'] for c in lesson['chapters'] if c['demo']]
    assert ['100','travel','AUTO-APPROVED'] in demos
    assert ['100.01','travel','SENT FOR MANAGER REVIEW'] in demos
    assert len(demos)>=7
    assert 'not output' in lesson['provenance']
