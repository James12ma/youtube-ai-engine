"""Explicit, evidence-labelled geographic screenplay; never guess coordinates."""
import math


def validate_geography(spec):
    if not isinstance(spec, dict):
        raise ValueError('Explicit geographic storyboard required')
    duration = spec.get('duration', 12)
    if isinstance(duration, bool) or not isinstance(duration, (int, float)) or not math.isfinite(duration) or not 1 <= duration <= 30:
        raise ValueError('Geographic duration must be 1–30 seconds')
    points = spec.get('route', [])
    if not isinstance(points, list) or not 2 <= len(points) <= 32:
        raise ValueError('Supply 2–32 route points')
    for point in points:
        if not isinstance(point, dict) or not isinstance(point.get('label'), str) or not 1 <= len(point['label']) <= 60:
            raise ValueError('Route point label required')
        for key, limit in [('lon', 180), ('lat', 90)]:
            v = point.get(key)
            if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or abs(v) > limit:
                raise ValueError('Invalid geographic coordinate')
    if not isinstance(spec.get('narration'), str) or not spec['narration'].strip():
        raise ValueError('Exact geographic narration required')
    if not spec.get('illustrative') and not spec.get('source_url', '').startswith('https://'):
        raise ValueError('Factual routes require an evidence URL')
    cues = spec.get('cues', [])
    if not isinstance(cues, list) or len(cues) < 2:
        raise ValueError('Narration-bound visual cues required')
    last = -1
    for cue in cues:
        at = cue.get('at')
        if isinstance(at, bool) or not isinstance(at, (int, float)) or not math.isfinite(at) or not last < at < duration:
            raise ValueError('Visual cues must be ordered inside the clip')
        if cue.get('phrase', '').lower() not in spec['narration'].lower() or not cue.get('phrase'):
            raise ValueError('Visual cue must quote the exact narration')
        if cue.get('action') not in ('locate', 'trace', 'arrive'):
            raise ValueError('Unsupported geographic action')
        last = at
    if [c['action'] for c in cues] != ['locate', 'trace', 'arrive']:
        raise ValueError('Geographic story requires locate, trace, arrive')
    return spec


def compile_geographic_scene(spec, clip_id):
    import re
    validate_geography(spec)
    if not re.fullmatch(r'[a-zA-Z0-9_-]{1,64}', clip_id):
        raise ValueError('Invalid geographic clip ID')
    return {'narration': spec['narration'], 'kind': 'god_eye',
            'on_screen': spec.get('title', 'A route across the Atlantic'),
            'camera': 'static', 'geo_clip': f'job/god_eye_{clip_id}.mp4',
            'geo_attribution': 'God’s Eye View / CesiumJS; Natural Earth (public domain); route illustrative' if spec.get('illustrative') else 'God’s Eye View / CesiumJS; Natural Earth; route: '+spec['source_url'],
            'geo_storyboard': spec, 'setting': 'GEOGRAPHIC DIRECTOR · ORIGINAL CAPTURE'}
