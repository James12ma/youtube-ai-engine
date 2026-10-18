# Multi-engine motion integration — Phase 1

This branch now includes a **routing foundation**, not working Remotion, Motion Canvas, or Manim render integrations.

- Remotion: planned final editorial composition, animated captions and transitions.
- Motion Canvas: planned maps, networks, vector diagrams and flow graphics.
- Manim: planned mathematical, finance and statistics scenes.
- Existing LogicScript and Alan7: retain existing renderers and owner approval gates.

The deterministic `visual_director.py` routes scene kinds to candidate engines; `engine_registry.py` reports basic dependency availability only. Neither imports or runs the external engines.

## Completion gates
1. Inspect existing engine render contracts and pin dependency versions after license/runtime review.
2. Implement adapters for each renderer and exchange intermediate scene assets through a documented format.
3. Render a real MP4 with each adapter; validate full decode, audio and synchronized captions.
4. Assemble final video and compare frames against user-approved reference; improve artistic direction.
5. Run unit and regression suites, then owner review. No automatic publishing, paid services or merge.

**No claim of production readiness is made.**
