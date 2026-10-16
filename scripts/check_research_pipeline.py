"""Bounded live dry run of the EXISTING source-to-script pipeline. Never uploads.

Only public reference documents go to a verified zero-priced OpenRouter model.
Production state/queue and human editorial approval remain untouched.
"""
from __future__ import annotations
import json, os, subprocess, tempfile, re
from dataclasses import replace
from pathlib import Path
from urllib.parse import urlparse
import httpx
from adapters import OpenRouterAdapter
from adapters.config import OPENROUTER_CONFIG
from pipeline import ContentPipeline, HttpSourceFetcher
from pipeline.errors import PipelineQualityError
from router import Router, RouterConfig
from state_store import StateStore
from verification import VerificationGate
from verification.integrated import VerifiedContentPipeline
from channel.metadata import generate_metadata
from scripts.check_free_providers import zero_priced_model

TOPIC = 'Choosing a small-business cybersecurity baseline before workflow automation'
SOURCES = (
    'https://csrc.nist.gov/pubs/ir/7621/r1/final',
    'https://csrc.nist.gov/pubs/sp/1300/final',
)


class RequestBudgetExceeded(RuntimeError):
    pass


def safe_quality_failure(exc):
    """Export gate-owned vocabulary/counts; never generated text or provider bodies."""
    import math
    stages = {'input', 'research', 'verify', 'script', 'storyboard'}
    reasons = {'empty topic', 'insufficient evidence quality', 'verification pass rate below threshold',
        'empty title', 'title too long', 'hook too long', 'no sections',
        'numeric hook or CTA cannot be cited', 'duration outside 8-12 minute target',
        'unknown claim_id cited', 'numeric claim without citation', 'no scenes',
        'section_index out of range', 'non-positive scene duration',
        'nonfinite or negative scene timestamp', 'scene index is not sequential',
        'overlap or gap between scenes', 'script duration is zero', 'duration drift exceeds tolerance'}
    result = {'stage': exc.stage if exc.stage in stages else 'unclassified',
              'reason': exc.report.get('reason') if exc.report.get('reason') in reasons else 'unclassified'}
    for key in ('verified', 'required', 'pass_rate', 'length', 'max', 'words', 'duration_s',
                'word_count', 'min_words', 'max_words', 'scene_index', 'index', 'total_s', 'target_s', 'drift', 'tolerance'):
        value = exc.report.get(key)
        if type(value) in (int, float) and math.isfinite(value): result[key] = value
    earlier = exc.report.get('earlier_failures')
    if isinstance(earlier, list):
        result['earlier_failures'] = [r if r in reasons else 'unclassified' for r in earlier[:5]]
    rejected = exc.report.get('rejected', [])
    if isinstance(rejected, list):
        allowed = {'unknown source_id', 'snippet not found verbatim in source', 'numeric claim not supported by source'}
        result['rejected_counts'] = {r: sum(isinstance(v, dict) and v.get('reason') == r for v in rejected) for r in sorted(allowed)}
    return result

def run(out: Path, *, metadata_client=None, source_fetcher=None, wire_factory=None):
    out.mkdir(parents=True, exist_ok=True)
    report = {'ready_for_publication': False, 'uploads_enabled': False,
              'paid_calls': 0, 'generation_requests': 0, 'generation_requests_max': 20,
              'source_checks': [], 'pipeline_passed': False}
    owned = metadata_client is None
    metadata = metadata_client or httpx.Client(timeout=30, follow_redirects=False)
    fetcher = source_fetcher or HttpSourceFetcher(allowed_hosts={urlparse(u).hostname for u in SOURCES})
    adapter = wire = None
    old = {k: os.environ.get(k) for k in ('ENABLE_LIVE_LLM', 'ROUTER_ALLOW_LIVE_API')}
    try:
        report['stage'] = 'source_retrieval'
        snapshots = {}
        for i, url in enumerate(SOURCES):
            try:
                source = fetcher.fetch(url)
            except Exception as exc:
                # Source failures have a fixed safe diagnostic vocabulary; never echo arbitrary bodies.
                reasons = ('Source is too large', 'Source size limit exceeded',
                           'Redirects are disabled for research sources', 'Empty source text',
                           'Unsupported source content type:')
                reason = next((r for r in reasons if str(exc).startswith(r)), type(exc).__name__)
                failure={'url': url, 'retrieved': False, 'reason': reason}
                status=re.match(r'Fetch failed ([0-9]{3}) for ',str(exc))
                if status:failure['http_status']=int(status.group(1))
                report['source_checks'].append(failure)
                continue
            snapshots[url] = source
            (out/f'source_{i}.json').write_text(source.model_dump_json(indent=2))
            report['source_checks'].append({'url': url, 'retrieved': True, 'text_chars': len(source.text)})
        if len(snapshots) != len(SOURCES):
            report['blocked'] = 'Required source retrieval failed; source bounds and redirect protections preserved'
            return report
        report['stage'] = 'free_account_verification'
        key = os.environ.get('OPENROUTER_API_KEY', '')
        if not key:
            report['blocked'] = 'OpenRouter key missing'; return report
        response = metadata.get('https://openrouter.ai/api/v1/key', headers={'Authorization': 'Bearer '+key})
        response.raise_for_status()
        account = response.json().get('data', {})
        if account.get('is_free_tier') is not True:
            report['blocked'] = 'Free-tier account unverified'; return report
        remaining = account.get('free_model_daily_requests', {}).get('remaining')
        if remaining is not None and remaining < 1:
            report['blocked'] = 'Free request quota exhausted'; return report
        catalog = metadata.get('https://openrouter.ai/api/v1/models')
        catalog.raise_for_status()
        models = [m for m in catalog.json().get('data', []) if zero_priced_model(m)
                  and ('response_format' in m.get('supported_parameters', []) or m['id']=='cohere/north-mini-code:free')]
        models.sort(key=lambda m: (m['id'] != OPENROUTER_CONFIG.default_model, 'preview' in m['id'], m['id']))
        if not models:
            report['blocked'] = 'No verified zero-priced JSON model'; return report
        model = models[0]['id']
        report.update(model=model, all_prices_verified_zero=True, free_request_quota={k:v for k,v in account.get('free_model_daily_requests',{}).items() if k in ('limit','remaining','used') and type(v) is int})
        cap = min(20, remaining) if isinstance(remaining, int) else 20
        report['generation_requests_max'] = cap
        def before_request(request):
            if request.method != 'POST' or str(request.url) != 'https://openrouter.ai/api/v1/chat/completions':
                raise RequestBudgetExceeded('Unexpected generation destination')
            if json.loads(request.content)['model'] != model or report['generation_requests'] >= cap:
                raise RequestBudgetExceeded('Generation request budget/model rejected')
            report['generation_requests'] += 1
        def after_response(response):
            report['last_generation_http_status'] = response.status_code
            if response.status_code==200:
                response.read()
                try:
                    choice=response.json().get('choices',[{}])[0]
                    reason=choice.get('finish_reason')
                    if reason in ('stop','length','content_filter','error'):report['last_finish_reason']=reason
                    content=choice.get('message',{}).get('content','')
                    report['last_output_characters']=len(content) if isinstance(content,str) else 0
                except (ValueError,IndexError,AttributeError,TypeError):pass
        wire = (wire_factory or httpx.Client)(timeout=45, follow_redirects=False,
                    event_hooks={'request': [before_request], 'response': [after_response]})
        os.environ['ENABLE_LIVE_LLM'] = os.environ['ROUTER_ALLOW_LIVE_API'] = '1'
        adapter = OpenRouterAdapter(config=replace(OPENROUTER_CONFIG, default_model=model,
            model_env_var='', max_retries=1, request_timeout=45), client=wire)
        with tempfile.TemporaryDirectory() as temporary:
            repo = Path(temporary)
            for args in (('init', '-b', 'main'), ('config', 'user.name', 'Engine verification'),
                         ('config', 'user.email', 'verification@example.invalid')):
                subprocess.run(['git', *args], cwd=repo, check=True, capture_output=True)
            (repo/'README.md').write_text('Isolated research verification state\n')
            subprocess.run(['git', 'add', '.'], cwd=repo, check=True, capture_output=True)
            subprocess.run(['git', 'commit', '-m', 'Initialize dry-run state'], cwd=repo, check=True, capture_output=True)
            state = StateStore(repo, push_required=False)
            router = Router(state, {'openrouter': adapter}, RouterConfig(provider_order=('openrouter',),
                rpd={'openrouter': cap}, rpm={'openrouter': min(cap,20)}))
            class AuditedRouter:
                def execute(self, task_type, input_data, request, schema):
                    known = {'pipeline.research','pipeline.script','pipeline.script_section','pipeline.storyboard','verify.entailment','verify.contradiction'}
                    if task_type not in known: raise RequestBudgetExceeded('Unexpected pipeline stage')
                    report['active_task'] = task_type
                    counts=report.setdefault('task_attempts',{})
                    counts[task_type]=counts.get(task_type,0)+1
                    value=router.execute(task_type,input_data,request,schema)
                    if task_type in ('pipeline.script','pipeline.script_section'):
                        name=task_type.replace('.','_')+'_'+str(counts[task_type])+'.json'
                        (out/('unaccepted_'+name)).write_text(json.dumps({'accepted':False,'kind':'raw_parsed_model_draft','data':value.model_dump()},indent=2))
                    return value
            class CheckpointPipeline(ContentPipeline):
                def _save_stage(self,name,call,*args):
                    value=call(*args)
                    (out/(name+'.json')).write_text(value.model_dump_json(indent=2))
                    report.setdefault('completed_stages',[]).append(name)
                    return value
                def _stage_research(self,*args): return self._save_stage('research',super()._stage_research,*args)
                def _stage_verify(self,*args): return self._save_stage('verification',super()._stage_verify,*args)
                def _stage_script(self,*args): return self._save_stage('script',super()._stage_script,*args)
                def _stage_storyboard(self,*args): return self._save_stage('storyboard',super()._stage_storyboard,*args)
            audited_router=AuditedRouter()
            class SnapshotFetcher:
                def fetch(self, url): return snapshots[url]
            report['stage'] = 'research_script_storyboard_and_verification'
            result = VerifiedContentPipeline(CheckpointPipeline(state, audited_router, SnapshotFetcher()),
                                             VerificationGate(audited_router)).run(TOPIC, SOURCES)
            for name, value in (('research', result.content.research), ('verification', result.content.verification),
                ('script', result.content.script), ('storyboard', result.content.storyboard),
                ('verification_gate', result.verification_gate.report)):
                (out/f'{name}.json').write_text(value.model_dump_json(indent=2))
            seo = generate_metadata(result.content.script, result.content.research, result.verification_gate.report)
            (out/'metadata_draft.json').write_text(seo.model_dump_json(indent=2))
            report.update(pipeline_passed=True, stage='awaiting_human_editorial_review',
                script_words=result.content.script.word_count, script_duration_estimate_s=result.content.script.duration_s)
    except Exception as exc:
        # Never expose provider messages, generated claims or credential values on failure.
        report['error_type'] = type(exc).__name__
        if report['generation_requests'] >= report['generation_requests_max']:
            report['blocked'] = 'generation_request_budget_exhausted'
        if isinstance(exc, PipelineQualityError):
            report['quality_failure'] = safe_quality_failure(exc)
        known=re.search(r'\b(RateLimitError|AuthError|ClientError|SchemaValidationError|ServerError|BillableModelRejected|ConfigurationError)\b',str(exc))
        if known:report['classified_failure']=known.group(1)
    finally:
        if adapter: adapter.close()
        elif wire: wire.close()
        if owned: metadata.close()
        if source_fetcher is None: fetcher._client.close()
        for name, value in old.items():
            if value is None: os.environ.pop(name, None)
            else: os.environ[name] = value
        (out/'report.json').write_text(json.dumps(report, indent=2))
    return report


if __name__ == '__main__':
    report = run(Path('outputs/research-check'))
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if report['pipeline_passed'] else 1)
