"""Evidence-first topic briefs; revenue observations never masquerade as forecasts.

Uses the existing source-first queue. No API calls, paid tools or auto-enabling.
"""
from __future__ import annotations
from datetime import date
from typing import Literal
from pydantic import BaseModel,Field,ConfigDict,model_validator
from .queue import Topic,TopicQueue

class Strict(BaseModel):
    model_config=ConfigDict(extra='forbid',allow_inf_nan=False)

class RPMEstimate(Strict):
    kind:Literal['third_party_estimate']='third_party_estimate'
    low:float=Field(ge=0)
    high:float=Field(ge=0)
    currency:str=Field(pattern=r'^[A-Z]{3}$')
    source_url:str=Field(pattern=r'^https://')
    observed_on:date
    assumptions:str=Field(min_length=30)
    @model_validator(mode='after')
    def ordered(self):
        if self.high<self.low:raise ValueError('Estimate bounds reversed')
        return self

class AnalyticsRPM(Strict):
    kind:Literal['youtube_analytics_observation']='youtube_analytics_observation'
    channel_id:str=Field(pattern=r'^UC[\w-]{22}$')
    period_start:date
    period_end:date
    format:Literal['long_form','shorts']
    denominator:Literal['all_views','engaged_views']
    eligible_views:int=Field(gt=0)
    total_reported_revenue:float=Field(ge=0)
    currency:str=Field(pattern=r'^[A-Z]{3}$')
    provenance:Literal['owner_export','authenticated_analytics_api']
    source_reference:str=Field(min_length=8)
    @model_validator(mode='after')
    def validate_basis(self):
        if self.period_end<self.period_start:raise ValueError('Invalid reporting period')
        expected='all_views' if self.format=='long_form' else 'engaged_views'
        if self.denominator!=expected:raise ValueError('Format/denominator mismatch')
        return self
    @property
    def rpm(self):return round(1000*self.total_reported_revenue/self.eligible_views,4)

class TopicBrief(Strict):
    title:str=Field(min_length=10,max_length=200)
    category:Literal['AI','SaaS','automation','cybersecurity','small_business']
    audience_problem:str=Field(min_length=25)
    original_demo:str=Field(min_length=30)
    primary_sources:list[str]=Field(min_length=2,max_length=8)
    checked_on:date
    demand_evidence:list[str]=Field(default_factory=list)
    utility:int=Field(ge=0,le=5)
    demo_feasibility:int=Field(ge=0,le=5)
    differentiation:int=Field(ge=0,le=5)
    rpm_estimate:RPMEstimate|None=None
    analytics:AnalyticsRPM|None=None
    @model_validator(mode='after')
    def sources(self):
        # Same URL rules as the actual editorial queue.
        from .queue import _validate_queue
        _validate_queue(TopicQueue(topics=[Topic(topic=self.title,urls=self.primary_sources,enabled=False)]))
        if self.checked_on>date.today():raise ValueError('Future research date')
        return self


def rank_topics(briefs:list[TopicBrief]):
    results=[]
    for brief in briefs:
        # Explicit editorial heuristic, NOT audience demand, RPM or growth prediction.
        score=round((.45*brief.utility+.35*brief.demo_feasibility+.20*brief.differentiation)*20,1)
        results.append({**brief.model_dump(mode='json'),'editorial_priority_score':score,
            'score_basis':'Editor-assigned usefulness, demonstration feasibility and differentiation; not measured demand',
            'demand_status':'observations supplied; review required' if brief.demand_evidence else 'not measured',
            'actual_rpm':brief.analytics.rpm if brief.analytics else None,
            'actual_rpm_status':'imported observation; provenance must be reviewed' if brief.analytics else 'No channel revenue analytics imported',
            'ready_for_publication':False})
    return sorted(results,key=lambda r:(-r['editorial_priority_score'],r['title']))


def to_review_queue(briefs:list[TopicBrief]):
    return TopicQueue(topics=[Topic(topic=b.title,urls=b.primary_sources,enabled=False) for b in briefs])
