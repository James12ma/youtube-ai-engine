"""Owner-approved scene rendering, real Piper voice and real WhisperX alignment.

Charts and recordings require explicit source assets; no fabricated metrics/UI.
No uploading or publishing occurs here. Heavy CPU dependencies are optional.
"""
from __future__ import annotations
import json,subprocess
from pathlib import Path
from typing import Mapping
from pipeline.models import ScriptArtifact, StoryboardOutput
from verification.models import VerificationGateReport
from production.assets import card
from production_pro.models import EditPlan
from production_pro.editing import compose_scenes,burn_captions
from production_pro.qc import run_qc
from channel.chapters import timeline_from_segments,normalize_timeline
from narration_pro import PiperOrEdgeNarrator,WhisperXAligner,normalize_loudness,build_ass_from_words,assess_caption_quality,save_word_timestamps,save_srt_from_blocks

class VideoBuildError(RuntimeError): pass

_LABELS={'en':{'intro':'THE PROBLEM','end':'NEXT STEP'},
         'es':{'intro':'EL PROBLEMA','end':'SIGUIENTE PASO'}}

def _run(cmd:list[str])->None:
    p=subprocess.run(cmd,capture_output=True,text=True)
    if p.returncode:raise VideoBuildError('FFmpeg error: '+p.stderr[-700:])

def render_approved_video(script:ScriptArtifact, storyboard:StoryboardOutput,
                          gate:VerificationGateReport, model_path:Path,output_path:Path,
                          *,actual_assets:Mapping[int,Path]|None=None,
                          reviewed:bool=False, width:int=1920,height:int=1080,fps:int=24,
                          allow_edge_fallback:bool=False,
                          unreviewed_preview:bool=False)->dict:
    # A preview lets the owner WATCH an automated draft before deciding on
    # editorial approval. It never counts as review: the report says so, and
    # scenes that need real footage become clearly labelled placeholder cards.
    if reviewed and unreviewed_preview:raise VideoBuildError('Choose either reviewed or unreviewed_preview, not both')
    if not reviewed and not unreviewed_preview:raise VideoBuildError('Human-reviewed script and storyboard required')
    if script.language not in _LABELS:raise VideoBuildError('Unsupported narration language: '+script.language)
    if script.topic!=gate.topic or gate.contradictions.pairs or gate.traceability.unverified_cited_claims:
        raise VideoBuildError('Verification gate failed')
    accepted={v.claim_id for v in gate.verdicts if v.accepted}
    if not accepted:raise VideoBuildError('No accepted source-backed claims')
    if {cid for sec in script.sections for cid in sec.claim_ids} - accepted:
        raise VideoBuildError('Script cites rejected claims')
    if not script.hook.strip() or not script.cta.strip() or not script.sections or not storyboard.scenes:
        raise VideoBuildError('Script/storyboard incomplete')
    actual_assets=actual_assets or {}
    if set(s.section_index for s in storyboard.scenes)!=set(range(len(script.sections))):
        raise VideoBuildError('Storyboard must include every script section')
    for idx,scene in enumerate(storyboard.scenes):
        if scene.section_index<0 or scene.section_index>=len(script.sections) or scene.end_s<=scene.start_s:
            raise VideoBuildError('Invalid storyboard scene')
        if idx and scene.start_s < storyboard.scenes[idx-1].end_s-0.01:
            raise VideoBuildError('Overlapping scenes')
    output_path=Path(output_path);output_path.parent.mkdir(parents=True,exist_ok=True)
    work=output_path.parent/(output_path.stem+'_work');work.mkdir(parents=True,exist_ok=True)
    segments=[script.hook]+[sec.narration for sec in script.sections]+[script.cta]
    if not all(t.strip() for t in segments):raise VideoBuildError('Every narration segment must be nonempty')
    narrator=PiperOrEdgeNarrator(model_path,allow_edge_fallback=allow_edge_fallback)
    synthesized=[]
    for i,text in enumerate(segments):synthesized.append(narrator.synthesize(text,work/f'speech_{i}.wav'))
    concat_list=work/'speech_concat.txt'
    paths=[Path(s.wav_path).resolve() for s in synthesized]
    if any("'" in str(p) or '\n' in str(p) for p in paths):raise VideoBuildError('Unsafe temporary path')
    concat_list.write_text(''.join("file '"+str(p)+"'\n" for p in paths),encoding='utf-8')
    raw=work/'voice_raw.wav'
    _run(['ffmpeg','-y','-hide_banner','-loglevel','error','-f','concat','-safe','0',
          '-i',str(concat_list),'-ac','1','-ar','48000','-c:a','pcm_s16le',str(raw)])
    norm=work/'voice_norm.wav'
    loud=normalize_loudness(raw,norm)
    # Real CTC forced alignment; NEVER use proportional timestamps as fallback.
    transcript=' '.join(segments)
    aligned=WhisperXAligner(language=script.language,device='cpu',min_token_coverage=.98).align(norm,transcript)
    save_word_timestamps(aligned,work/'words.json')
    captions=work/'captions.ass'
    portrait=height>width
    caption_count,blocks=build_ass_from_words(aligned.words,captions,width=width,height=height,
        animated=True,size=66 if portrait else 54,max_chars_per_line=24 if portrait else 32,
        bottom_margin=300 if portrait else 80,max_duration_s=2.4)
    caption_qc=assess_caption_quality(aligned.words,blocks,aligned.duration_s,min_coverage=.98)
    if not caption_qc.passed:raise VideoBuildError('Forced captions failed QC: '+repr(caption_qc.failures))
    srt=save_srt_from_blocks(blocks,output_path.with_suffix('.srt'))

    stages=[];placeholders:list[int]=[]
    intro=work/'intro.png';card('text_overlay',_LABELS[script.language]['intro'],script.hook,(width,height),intro)
    stages.append((intro,synthesized[0].duration_s,0.0,False))
    # Divide actual narrated section time across that section's storyboard scenes.
    for sec_idx,sec in enumerate(script.sections):
        scenes=[s for s in storyboard.scenes if s.section_index==sec_idx]
        sum_original=sum(s.end_s-s.start_s for s in scenes)
        for s in scenes:
            motion=False
            seconds=synthesized[sec_idx+1].duration_s * (s.end_s-s.start_s)/sum_original
            if s.visual_type in ('screen_recording','chart','broll') and unreviewed_preview and s.index not in actual_assets:
                src=work/f'section_{sec_idx}_scene_{s.index}_placeholder.png'
                card('text_overlay','PLACEHOLDER: '+s.visual_type.replace('_',' ').upper(),
                     'Real footage needed: '+s.instruction,(width,height),src)
                placeholders.append(s.index)
            elif s.visual_type in ('screen_recording','chart','broll'):
                source=actual_assets.get(s.index)
                if source is None or not Path(source).is_file():
                    raise VideoBuildError('Real reviewed asset required for '+s.visual_type+' scene '+str(s.index))
                if s.visual_type=='screen_recording' and Path(source).suffix.lower() not in ('.mp4','.webm','.mov'):
                    raise VideoBuildError('screen_recording must be a genuine video file')
                if s.visual_type=='chart' and Path(source).suffix.lower() not in ('.png','.jpg','.jpeg'):
                    raise VideoBuildError('Chart must be a reviewed evidence-backed image')
                src=Path(source)
                motion=s.visual_type=='broll' and src.suffix.lower() in ('.jpg','.jpeg','.png')
            else:
                src=work/f'section_{sec_idx}_scene_{s.index}.png'
                card(s.visual_type,sec.heading,sec.on_screen_text or s.instruction,(width,height),src)
            stages.append((src,seconds,0.0,motion))
    end=work/'end.png';card('text_overlay',_LABELS[script.language]['end'],script.cta,(width,height),end)
    stages.append((end,synthesized[-1].duration_s,0.0,False))
    # Crossfade overlaps shorten finished video. Compensate by lengthening the
    # source clips, so audio and video remain aligned in total duration.
    overlap=.30
    plans=[]
    for i,(asset,duration,start,motion) in enumerate(stages):
        next_overlap=overlap if i<len(stages)-1 else 0.0
        plans.append(EditPlan(scene_index=i,source_path=str(asset),start_s=start,
                              duration_s=max(.4,duration)+next_overlap,
                              transition='fade' if i%2==0 else 'smoothleft',
                              overlap_s=overlap if i>0 else 0.0,photo_motion=motion))
    composed=work/'uncaptioned.mp4'
    edit=compose_scenes(plans,norm,composed,width=width,height=height,fps=fps,workdir=work/'edits')
    burn_captions(composed,captions,output_path)
    qc=run_qc(output_path,captions,forced_alignment_verified=aligned.method=='whisperx_ctc' and caption_qc.passed)
    report={'output_path':str(output_path),'narration_backend':'+'.join(sorted(narrator.actual_backends)),
            'alignment_backend':'whisperx_ctc','audio':loud.model_dump(),
            'alignment':{'token_coverage':aligned.token_coverage,'words':len(aligned.words)},
            'captions':caption_count,'caption_qc':caption_qc.model_dump(),'srt_path':str(srt),
            'video_edit':edit,'technical_qc':qc.model_dump(),
            # Narration-timed chapters (hook + sections; CTA folded into the last section).
            # Crossfade overlaps are compensated above, so narration time == video time.
            'chapters':[c.model_dump() for c in normalize_timeline(
                timeline_from_segments('Introduction',[sec.heading for sec in script.sections],
                                       [s.duration_s for s in synthesized]))],
            'ready_for_publication':False,'manual_editorial_approval_still_required':True,
            'editorial_review':'not_performed_unreviewed_preview' if unreviewed_preview else 'owner_confirmed',
            'placeholder_scenes':placeholders}
    (work/'render_report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    if not qc.passed:
        raise VideoBuildError('Rendered video failed technical QC; inspect render_report.json')
    return report
