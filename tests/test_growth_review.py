import json
from datetime import datetime,timezone
from pathlib import Path
import pytest
from pydantic import ValidationError
from channel.intelligence import AnalyticsRPM,RPMEstimate,TopicBrief,rank_topics,to_review_queue
from channel.community import Discussion,discover,draft_comments,post_comment,export_drafts


def discussion():return Discussion.model_validate(json.loads(Path('content/growth/discussion_snapshots.json').read_text())[0])
def analytics(**change):
    data=dict(channel_id='UC7vcWhYzuJtarRqSz7KgJgw',period_start='2026-10-01',period_end='2026-10-10',format='long_form',denominator='all_views',eligible_views=2000,total_reported_revenue=10,currency='USD',provenance='owner_export',source_reference='test fixture, not real revenue')
    return AnalyticsRPM(**{**data,**change})


def test_actual_and_estimated_rpm_remain_different_types():
    actual=analytics();assert actual.rpm==5
    estimate=RPMEstimate(low=2,high=6,currency='USD',source_url='https://example.com/estimate',observed_on='2026-10-01',assumptions='TEST FIXTURE: third party speculation, not channel analytics')
    assert actual.kind!=estimate.kind
    with pytest.raises(ValidationError):AnalyticsRPM.model_validate(estimate.model_dump())

@pytest.mark.parametrize('change',[dict(denominator='engaged_views'),dict(total_reported_revenue=float('nan')),dict(period_end='2026-09-30'),dict(eligible_views=0)])
def test_revenue_rejects_invalid_or_mixed_basis(change):
    with pytest.raises(ValidationError):analytics(**change)


def test_short_rpm_uses_engaged_views():assert analytics(format='shorts',denominator='engaged_views').rpm==5


def test_rank_is_editorial_and_does_not_invent_rpm_or_demand():
    briefs=[TopicBrief.model_validate(x) for x in json.loads(Path('content/growth/topic_briefs.json').read_text())]
    ranked=rank_topics(briefs)
    assert len(ranked)==5 and all(x['actual_rpm'] is None and x['rpm_estimate'] is None and x['demand_status']=='not measured' for x in ranked)
    assert not any(t.enabled for t in to_review_queue(briefs).topics)


def test_relevant_context_required():
    item=discussion();assert discover([item],['Apps Script'])==[item]
    assert discover([item],['gardening'])==[]
    with pytest.raises(ValueError):draft_comments([item.model_copy(update={'context_reviewed':False})])


def test_original_draft_binds_target_and_content_and_never_posts():
    item=discussion();a=draft_comments([item])[0]
    b=draft_comments([item.model_copy(update={'contribution':item.contribution+' Which test failed first?'})])[0]
    assert a['approval_digest']!=b['approval_digest'] and not a['owner_approved'] and not a['posting_enabled']
    with pytest.raises(PermissionError):post_comment(a,approved=True)

@pytest.mark.parametrize('text',['Subscribe to my channel for Apps Script tips.','Apps Script guide at https://example.com is here.'])
def test_reject_promotional_drafts(text):
    with pytest.raises(ValueError):draft_comments([discussion().model_copy(update={'contribution':text})])


def test_duplicate_and_bulk_drafts_are_blocked():
    item=discussion()
    with pytest.raises(ValueError):draft_comments([item,item])
    with pytest.raises(ValueError):draft_comments([item],previous_texts=[item.contribution])
    with pytest.raises(ValueError):draft_comments([item]*4)


def test_review_export_cannot_overwrite_owner_work(tmp_path):
    target=tmp_path/'review.json';export_drafts(target,[])
    with pytest.raises(FileExistsError):export_drafts(target,[])
