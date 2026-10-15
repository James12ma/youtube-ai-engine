"""Real online fallback test with an intentionally unavailable primary model."""
import json
from pathlib import Path
from narration_pro import PiperOrEdgeNarrator, NarrationError


def main():
    folder=Path('outputs/edge-check');folder.mkdir(parents=True,exist_ok=True)
    engine=PiperOrEdgeNarrator(folder/'intentionally_missing_primary.onnx',allow_edge_fallback=True)
    report={'primary_unavailable_test':True,'publishing_enabled':False,'paid_calls':0}
    try:
        result=engine.synthesize('This original workflow demonstration requires owner review before any publication.',folder/'edge_fallback.wav')
        report.update(passed=True,backend=sorted(engine.actual_backends),
            duration_s=result.duration_s,sample_rate=result.sample_rate,
            alignment_verified=False,commercial_terms_review_required=True)
        code=0
    except NarrationError:
        report.update(passed=False,error='Online Edge fallback unavailable; Piper remains the validated offline primary')
        code=1
    (folder/'report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
    return code


if __name__=='__main__':raise SystemExit(main())
