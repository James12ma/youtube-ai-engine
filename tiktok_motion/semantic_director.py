"""Constrained semantic screenplay compiler; no invented factual assets or silent fallback.

The executable vocabulary covers the communication benchmark. Other requests are
returned as explicit asset/review requirements, never certified as rendered cinema.
"""
from __future__ import annotations
import copy, hashlib, re

GENRES = {'children','finance','news','education','technology','documentary'}
RENDERABLE_ACTIONS = {'establish','compose_send','transmit','receive','review','invite'}
WORLD = {
 'candidate': {'role':'Applicant','skin':'#b97851','hair':'#292639','shirt':'#347e79','appearance_ref':'original-vector/applicant-v1'},
 'recruiter': {'role':'Recruiter','skin':'#e0ac88','hair':'#5b3b31','shirt':'#485f98','appearance_ref':'original-vector/recruiter-v1'},
 'phone': {'case':'#263c4f','accent':'#52d8be','appearance_ref':'original-vector/phone-v1'},
 'company': {'name':'Example Studio','location_id':'company_office','appearance_ref':'original-vector/office-v1'},
 'application': {'id':'APP-042','state':'draft','evidence':'fictional simulation'},
}

def words(text): return re.findall(r"[\w]+(?:['’][\w]+)?", text.lower())

def compile_script(script, genre='education'):
    """Compile exact original sentences to grounded actions or fail closed.

    Rules map concrete verbs/roles, not arbitrary topic prompts. Names and all
    displayed UI details are explicitly fictitious, original vector artwork.
    """
    if genre not in GENRES: raise ValueError('Unsupported film genre')
    if not isinstance(script,str) or not script.strip(): raise ValueError('Complete script required')
    sentences=[m.group(0).strip() for m in re.finditer(r'[^.!?]+[.!?]?(?:\s*|$)',script) if m.group(0).strip()]
    scenes=[];missing=[];stage=0
    for sentence in sentences:
        t=sentence.lower();events=[]
        if re.search(r'\b(candidate|applicant)\b',t) and re.search(r'\b(finds?|prepares?|looks? for|discovers?)\b',t) and re.search(r'\b(position|application|job|opportunity)\b',t):
            events=[('establish','finds' if 'finds' in t else 'prepares')];stage=max(stage,1)
        elif re.search(r'\b(phone|smartphone)\b',t) and re.search(r'\b(sends?|submits?|taps?)\b',t):
            if stage<1:missing.append('Establish applicant and application before sending')
            trigger=next(x for x in ('sends','send','submits','submit','taps','tap') if re.search(r'\b'+x+r'\b',t))
            events=[('compose_send',trigger)];stage=max(stage,2)
        elif re.search(r'\b(message|signal|application)\b',t) and re.search(r'\b(travels?|transmits?|crosses?)\b',t) and 'recruiter' in t:
            if stage<2:missing.append('Cannot receive an application before its send action')
            trigger=next(x for x in ('travels','travel','transmits','transmit','crosses','cross') if re.search(r'\b'+x+r'\b',t))
            events=[('transmit',trigger),('receive','recruiter')];stage=max(stage,3)
        elif 'recruiter' in t and re.search(r'\b(reviews?|reads?|screens?)\b',t):
            if stage<3:missing.append('Recruiter cannot review an application before receiving it')
            trigger=next(x for x in ('reviews','review','reads','read','screens','screen') if re.search(r'\b'+x+r'\b',t))
            events=[('review',trigger)]
            invitation=next((x for x in ('contacts','invites','schedule','schedules') if re.search(r'\b'+x+r'\b',t)),None)
            if invitation:events.append(('invite',invitation))
            stage=max(stage,4)
        else:missing.append('needs_visual_asset: '+sentence)
        if re.search(r'\d|\b(percent|law|guaranteed|profit|returns|dollars|diagnos)\b',t):
            missing.append('needs_evidence_source: factual quantities or high-stakes claim')
        scenes.append({'narration':sentence,'kind':'character','on_screen':'','actors':['Applicant','Recruiter'],
                       'setting':'Fictional communication simulation','camera':'push_in','events':[{'action':a,'trigger':b} for a,b in events]})
    actions=[e['action'] for s in scenes for e in s['events']]
    if stage<4 or not set(RENDERABLE_ACTIONS)<=set(actions): missing.append('Incomplete causal communication story: establish, send, transmit, receive, review, invite required')
    return {'version':1,'planner':'deterministic-semantic-communication-v1','genre':genre,
            'source_sha256':hashlib.sha256(script.encode()).hexdigest(),'world':copy.deepcopy(WORLD),
            'scenes':scenes,'needs_owner_review':True,'missing_requirements':missing,'ready':not missing,
            'asset_provenance':'Original procedural vector illustration; fictional UI and identities',
            'demonstrated_scope':'Applicant-phone-recruiter communication; not unrestricted film generation'}


def _trigger_time(tokens, phrase):
    target=words(phrase)
    stream=[]
    for token in tokens:
        for word in words(token['text']): stream.append((word,token['start'],token['end']))
    for i in range(len(stream)-len(target)+1):
        if [x[0] for x in stream[i:i+len(target)]]==target:return stream[i][1]
    raise ValueError('Native word alignment missing for action trigger: '+phrase)


def bind_timeline(plan):
    """Bind actions to actual Kokoro word durations after waveform generation."""
    director=plan['director']
    if not director['ready']:raise ValueError('Film blocked: '+ '; '.join(director['missing_requirements']))
    shots=[];offset=0
    views={
      'establish':([0,0,1080,1550],[680,800,240,344]),
      'compose_send':([680,800,240,344],[680,800,240,344]),
      'transmit':([80,866,240,344],[0,0,1080,1550]),
      'receive':([0,0,1080,1550],[680,800,240,344]),
      'review':([680,800,240,344],[120,300,840,1205]),
      'invite':([120,300,840,1205],[0,0,1080,1550]),
    }
    for i,scene in enumerate(plan['scenes']):
        frames=scene['durationFrames']; events=director['scenes'][i]['events'];local=[]
        for event in events:
            at=round(_trigger_time(scene['words'],event['trigger'])*30)
            local.append({**event,'at':offset+at})
        boundary=0
        for j,event in enumerate(local):
            start=offset+boundary
            end=offset+frames if j==len(local)-1 else max(start+24,local[j+1]['at']-10)
            if end>offset+frames or event['at']>=end:raise ValueError('Action does not fit speech timeline')
            action=event['action'];a,b=views[action]
            if action=='establish':location='candidate_home';subjects=['candidate'];props=['phone','application']
            elif action=='compose_send':location='candidate_home';subjects=['candidate'];props=['phone','application']
            elif action=='transmit':location='communication_space';subjects=[];props=['phone','application','company']
            else:location='company_office';subjects=['recruiter'];props=['phone','application','company']
            shots.append({'shot_id':f'shot-{len(shots)+1:02d}','scene_index':i,'from':start,'to':end,
                          'action':action,'action_frame':event['at'],'source_sentence':scene['narration'],
                          'narration_range':[offset,offset+frames],'location_id':location,
                          'subjects':[{'entity_id':s,**director['world'][s]} for s in subjects],
                          'props':props,'application_id':director['world']['application']['id'],
                          'camera':{'from':a,'to':b,'movement': 'macro_match' if action=='compose_send' else 'pan_push'},
                          'transition':{'from_shot':shots[-1]['shot_id'] if shots else None,'continuity_object':'phone' if action in ('compose_send','transmit') else 'application','match_point':'same device case / APP-042'},
                          'evidence_source_ids':['original-procedural-artwork'],'simulation_label':'FICTIONAL UI · ANIMATED SIMULATION',
                          'needs_owner_review':True})
            boundary=end-offset
        offset+=frames
    director['shots']=shots
    director['timing_source']='Kokoro native generated word durations'
    director['qa']=validate_film(plan)
    if not director['qa']['passed']:raise ValueError('Film editorial gate: '+ '; '.join(director['qa']['blocking']))
    return plan


def validate_film(plan):
    d=plan['director'];shots=d.get('shots',[]);blocking=[]
    if d['missing_requirements']:blocking+=d['missing_requirements']
    world=d['world'];last=0;seen=[]
    if world!=WORLD: blocking.append('Continuity registry changed from renderer asset contract')
    for s in shots:
        if s['action'] not in RENDERABLE_ACTIONS:blocking.append('Unsupported action')
        if s['from']!=last or s['to']<=s['from']:blocking.append('Non-contiguous shot timeline')
        if not s['from']<=s['action_frame']<s['to']:blocking.append('Action outside its narrated shot')
        if s['application_id']!=world['application']['id']:blocking.append('Wrong sender/recipient application')
        if not s['simulation_label']:blocking.append('Simulation must be labelled')
        for actor in s['subjects']:
            if actor.get('appearance_ref')!=world[actor['entity_id']]['appearance_ref']:blocking.append('Character appearance continuity broken')
        if s['source_sentence']!=plan['scenes'][s['scene_index']]['narration']:blocking.append('Shot is unrelated to source sentence')
        seen.append(s['action']);last=s['to']
    if seen!=['establish','compose_send','transmit','receive','review','invite']:blocking.append('Causal action order or variety missing')
    if last!=plan['durationInFrames']:blocking.append('Uncovered narration frames')
    return {'passed':not blocking,'blocking':blocking,'shot_count':len(shots),'checks':['causal order','same APP-042','stable original assets','source sentence binding','native speech timing','visible simulation label'],
            'pixel_relevance_verified':False,'human_visual_review_required':True}
