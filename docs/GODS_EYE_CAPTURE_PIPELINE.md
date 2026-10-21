# Deterministic geographic capture

Continues `feature/gods-eye-view-integration`; no merge, deployment, publishing,
paid API, credentials or runtime feed is involved.

## Implemented path

Exact owner narration + supplied endpoint coordinates → native Kokoro word timing
→ geographic action cues → actual upstream God's Eye View viewer factory
→ deterministic Cesium camera, geodesic route and moving marker → local PNG frames
→ H.264 capture → `GeoCinematic` Remotion composition → narrated H.264/AAC MP4.

The adapter imports `createApplicationViewer` from the upstream project instead of
reimplementing its viewer. It runs in an isolated capture page, **not the full
OSINT console**; no live feeds, Esri, Google, ion assets or TeleGeography data load.
All browser requests outside loopback are blocked. Cesium's local NaturalEarthII
texture is the only basemap. Terrain is explicitly WGS84 ellipsoid, **not elevation
or photorealistic buildings**. No satellite/terrain claim should be inferred.

Upstream audited/pinned commit:
`bilawalsidhu/gods-eye-view@713285b554bbc99c8ae0261fe307beb3cbeb2adf`.
MIT code: upstream LICENSE. Reviewed DATA_SOURCES.md, SECURITY.md and CONTRIBUTING.md.
Natural Earth explicitly permits commercial use of its public-domain rasters:
https://www.naturalearthdata.com/about/terms-of-use/ . Cesium credits stay visible.
The demonstration route is illustrative, not an observed flight or migration.

## Reproduction

Use Node 24.14+ (24.x) or 26.x, Python 3.11+, ffmpeg, espeak-ng and CPU-only torch.
Use the existing premium dependency workflow for the voice environment.

```bash
git clone https://github.com/bilawalsidhu/gods-eye-view ../gods-eye-view-upstream
git -C ../gods-eye-view-upstream checkout 713285b554bbc99c8ae0261fe307beb3cbeb2adf
(cd ../gods-eye-view-upstream && npm ci --ignore-scripts --no-audit --no-fund)
(cd ../gods-eye-view-upstream && npx puppeteer browsers install chrome-headless-shell)
(cd tiktok_motion/premium/remotion && npm ci --no-audit --no-fund)
python -m scripts.render_geographic_test --upstream ../gods-eye-view-upstream \
  --spec examples/god_eye_atlantic.json --out outputs/geographic
```

Capture only (pre-timed storyboard):

```bash
node scripts/capture_god_eye.mjs ../gods-eye-view-upstream \
  examples/god_eye_atlantic.json outputs/geographic-capture
```

Each frame is sampled at `frame/30`; wall-clock speed cannot change route position
or camera pose. Warm-up explicitly renders until local terrain/imagery tiles load
at representative poses. A manifest binds storyboard, viewport, upstream commit
and renderer source hashes. The flat-terrain provider uses Cesium’s own synchronous tessellator to avoid
worker startup stalls; this private API is checked explicitly against the pinned
upstream/Cesium dependency. No non-flat terrain provider is altered.
Interrupted capture resumes only matching captures;
frames write atomically. External requests, changed upstream and mismatched output
manifests fail closed. Encoding limits the output frame count explicitly.

## Director integration and limits

`geographic_director.compile_geographic_scene` creates the existing `god_eye` scene
contract. `premium_job.make_plan` accepts `geography` plus exact original `script`
and `geo_clip_id`; the scene must already have its capture installed. Storyboard
narration must match scene narration byte-for-byte. `narrate` probes the capture
and blocks clips shorter than the speech scene (previously these could freeze).

The geographic extension lives beside the existing communication compiler; it
reuses its exact phrase-to-native-word timing binder. It does not claim arbitrary
script understanding. Coordinates and evidence must be supplied explicitly;
factual route data need a source URL, while illustrative paths are labelled.
The current capture supports **two endpoints / one geodesic segment**. Arbitrary
waypoint routes, automatic geocoding, elevated terrain, full-console playback and
universal micro-detail scene generation remain outside this demonstrated scope.
Original Alan7, LogicScript, finance, Blender and communication codepaths remain.

Review the rendered frames and MP4 before approving any downstream publishing.

Completed matching MP4 captures are reusable in the orchestration script only
after checking storyboard equality, capture-driver/browser source hash, frame
count, codec, dimensions and duration. Cold capture is also checked on the
standard GitHub runner behind the existing ZERO_COST_ACTIONS_CONFIRMED gate.
