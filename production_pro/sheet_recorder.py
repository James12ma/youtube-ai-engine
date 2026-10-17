"""Record a real spreadsheet (LibreOffice Calc) while performing scripted, timed actions.

Free and fully reproducible: LibreOffice on an X display (Xvfb in CI), driven through its
official UNO API, captured with FFmpeg x11grab. Every value and status visible in the video is
computed live by the workbook itself; nothing is drawn or mocked.

Run under an X server, e.g. ``xvfb-run -a -s "-screen 0 1920x1080x24" python -m ...``.
Actions (all refs are 'Sheet!A1' or 'Sheet!A1:B2'):
  {'do':'select','ref':...}                  activate the sheet and select the range
  {'do':'set','ref':cell,'value':v}         number, text, '=formula' or {'date':'YYYY-MM-DD'}
  {'do':'row','row':n,'values':[A..I]}      enter one expense row left to right, then show its status
  {'do':'clear','ref':range}                clear typed contents (formulas untouched)
Writing through UNO bypasses dropdown validation exactly like a paste or an import does.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Callable, Sequence

INPUT_COLUMNS = 'ABCDEFGHI'
CLEAR_FLAGS = 1 | 2 | 4        # VALUE | DATETIME | STRING  (keeps formulas and formatting)
EPOCH = date(1899, 12, 30)


class SheetRecorderError(RuntimeError):
    pass


def split_ref(ref: str) -> tuple[str, str]:
    if '!' not in ref:
        raise SheetRecorderError('Reference must include the sheet: ' + ref)
    sheet, cells = ref.rsplit('!', 1)
    return sheet.strip("'"), cells


def date_serial(text: str) -> int:
    return (date.fromisoformat(text) - EPOCH).days


@dataclass
class RecordingResult:
    video_path: Path
    duration_s: float
    lead_s: float                                    # seconds of video before the action clock's t=0
    log: list[dict] = field(default_factory=list)   # actual action times (seconds on the action clock)


class SheetRecorder:
    def __init__(self, workbook: Path, workdir: Path, *, size=(1920, 1080), fps: int = 24, zoom: int = 135,
                 port: int | None = None, soffice: str = 'soffice'):
        self.source = Path(workbook); self.workdir = Path(workdir); self.size = size; self.fps = fps
        self.zoom = zoom; self.port = port or (2100 + os.getpid() % 500); self.soffice = soffice
        self.proc = None; self.doc = None; self.controller = None

    # ---------------- lifecycle ----------------
    def __enter__(self):
        if not os.environ.get('DISPLAY'):
            raise SheetRecorderError('No X display: run under xvfb-run')
        import uno  # noqa: F401  (python3-uno)
        self.workdir.mkdir(parents=True, exist_ok=True)
        self.workbook = self.workdir / ('recording_' + self.source.name)
        shutil.copy2(self.source, self.workbook)          # never touch the published template
        self.profile = Path(tempfile.mkdtemp(prefix='lo_profile_'))
        # A fresh recording profile must not put a first-run tip in front of
        # the sheet. UNO imports still work behind that modal; keyboard input
        # does not. This affects only the disposable recording profile.
        (self.profile / 'user').mkdir()
        (self.profile / 'user' / 'registrymodifications.xcu').write_text(
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<oor:items xmlns:oor="http://openoffice.org/2001/registry">'
            '<item oor:path="/org.openoffice.Office.Common/Misc">'
            '<prop oor:name="ShowTipOfTheDay" oor:op="fuse"><value>false</value></prop>'
            '</item></oor:items>')
        self._startup_log = (self.workdir / 'libreoffice-startup.log').open('w')
        self.proc = subprocess.Popen([self.soffice, '--calc', '--norestore', '--nologo', '--nodefault',
                                      '--nolockcheck', f'-env:UserInstallation={self.profile.as_uri()}',
                                      f'--accept=socket,host=127.0.0.1,port={self.port};urp;'],
                                     stdout=self._startup_log, stderr=self._startup_log)
        try:
            self._connect()
            self._open()
        except Exception:
            self.__exit__()
            raise
        return self

    def __exit__(self, *exc):
        try:
            if self.doc is not None:
                self.doc.close(True)
        except Exception:
            pass
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(10)
            except subprocess.TimeoutExpired:
                self.proc.kill()
        shutil.rmtree(getattr(self, 'profile', ''), ignore_errors=True)
        if getattr(self, '_startup_log', None):
            self._startup_log.close()

    def _connect(self, timeout_s: float = 60):
        import uno
        local = uno.getComponentContext()
        resolver = local.ServiceManager.createInstanceWithContext('com.sun.star.bridge.UnoUrlResolver', local)
        deadline = time.monotonic() + timeout_s
        while True:
            try:
                self.ctx = resolver.resolve(f'uno:socket,host=127.0.0.1,port={self.port};urp;StarOffice.ComponentContext')
                break
            except Exception:
                if time.monotonic() > deadline or self.proc.poll() is not None:
                    raise SheetRecorderError('Could not connect to LibreOffice; inspect '+
                                             str(self.workdir / 'libreoffice-startup.log')) from None
                time.sleep(0.5)
        self.desktop = self.ctx.ServiceManager.createInstanceWithContext('com.sun.star.frame.Desktop', self.ctx)

    def _open(self):
        import uno
        from com.sun.star.beans import PropertyValue
        hidden = PropertyValue(); hidden.Name = 'Hidden'; hidden.Value = False
        self.doc = self.desktop.loadComponentFromURL(uno.systemPathToFileUrl(str(self.workbook.resolve())),
                                                     '_blank', 0, (hidden,))
        if self.doc is None:
            raise SheetRecorderError('LibreOffice could not open the workbook')
        self.controller = self.doc.getCurrentController()
        window = self.controller.getFrame().getContainerWindow()
        window.setPosSize(0, 0, self.size[0], self.size[1], 15)
        try:
            window.IsMaximized = True
        except Exception:
            pass
        self.controller.ZoomType = 3          # BY_VALUE
        self.controller.ZoomValue = self.zoom
        time.sleep(1.5)

    # ---------------- actions ----------------
    def _range(self, ref: str):
        sheet_name, cells = split_ref(ref)
        sheets = self.doc.getSheets()
        if not sheets.hasByName(sheet_name):
            raise SheetRecorderError('Unknown sheet: ' + sheet_name)
        sheet = sheets.getByName(sheet_name)
        return sheet, sheet.getCellRangeByName(cells)

    def _show(self, sheet, rng):
        self.controller.setActiveSheet(sheet)
        self.controller.select(rng)

    def _write(self, cell, value):
        if isinstance(value, dict) and 'date' in value:
            cell.setValue(date_serial(value['date']))
        elif isinstance(value, bool):
            raise SheetRecorderError('Booleans are not supported; use "Yes"/"No"')
        elif isinstance(value, (int, float)):
            cell.setValue(float(value))
        elif isinstance(value, str) and value.startswith('='):
            cell.setFormula(value)
        elif value is None or value == '':
            cell.clearContents(CLEAR_FLAGS)
        else:
            cell.setString(str(value))      # stored as text, exactly as typed (e.g. "$38.75")

    def apply(self, action: dict, *, pace_s: float = 0.12, sleep: Callable[[float], None] = time.sleep):
        kind = action['do']
        if kind == 'select':
            self._show(*self._range(action['ref']))
        elif kind == 'set':
            sheet, cell = self._range(action['ref'])
            self._show(sheet, cell); sleep(pace_s); self._write(cell, action['value'])
        elif kind == 'clear':
            sheet, rng = self._range(action['ref'])
            self._show(sheet, rng); sleep(pace_s); rng.clearContents(CLEAR_FLAGS)
        elif kind == 'row':
            r = int(action['row']); values = action['values']
            if len(values) > len(INPUT_COLUMNS):
                raise SheetRecorderError('Too many values for the input columns')
            sheet, _ = self._range(f'Expenses!A{r}')
            for col, value in zip(INPUT_COLUMNS, values):
                cell = sheet.getCellRangeByName(f'{col}{r}')
                self._show(sheet, cell)
                if value not in (None, ''):
                    self._write(cell, value); sleep(pace_s)
            self._show(sheet, sheet.getCellRangeByName(f'J{r}:K{r}'))
        elif kind in ('type', 'move', 'click', 'key', 'menu', 'scroll'):
            # These are real X11 input events, unlike UNO's intentional import/set path.
            # Keep set/row for paste/import lessons; never call them "typing" in evidence.
            if not shutil.which('xdotool'):
                raise SheetRecorderError('Visible input requires xdotool')
            if kind == 'type':
                sheet, cell = self._range(action['ref'])
                self._show(sheet, cell)
                self.controller.getFrame().getContainerWindow().setFocus()
                subprocess.run(['xdotool', 'key', '--clearmodifiers', 'F2', 'ctrl+a'], check=True)
                subprocess.run(['xdotool', 'type', '--clearmodifiers', '--delay', '90', '--',
                                str(action['text'])], check=True)
                subprocess.run(['xdotool', 'key', '--clearmodifiers', 'Return'], check=True)
                sleep(0.15)  # let the application's event loop commit the edit before UNO reads it
            elif kind == 'move':
                x, y = int(action['x']), int(action['y'])
                if not 0 <= x < self.size[0] or not 0 <= y < self.size[1]:
                    raise SheetRecorderError('Pointer target outside the recording')
                # Interpolate actual pointer movement rather than teleporting an overlay.
                pos = subprocess.check_output(['xdotool', 'getmouselocation', '--shell'], text=True)
                vals = dict(line.split('=', 1) for line in pos.splitlines() if '=' in line)
                x0, y0 = int(vals['X']), int(vals['Y'])
                for n in range(1, 17):
                    subprocess.run(['xdotool', 'mousemove', '--sync', str(round(x0+(x-x0)*n/16)),
                                    str(round(y0+(y-y0)*n/16))], check=True)
                    sleep(0.015)
            elif kind == 'click':
                subprocess.run(['xdotool', 'click', '1'], check=True)
            elif kind in ('key', 'menu'):
                subprocess.run(['xdotool', 'key', '--clearmodifiers', action['keys']], check=True)
            else:
                count = int(action.get('count', 4))
                if action['direction'] not in ('up', 'down') or not 1 <= count <= 30:
                    raise SheetRecorderError('Invalid scroll action')
                subprocess.run(['xdotool', 'click', '--repeat', str(count), '--delay', '100',
                                '5' if action['direction'] == 'down' else '4'], check=True)
        else:
            raise SheetRecorderError('Unknown action: ' + kind)
        self.doc.calculateAll()

    def value(self, ref: str):
        """Read a computed cell (used by tests and the evidence log)."""
        _, cell = self._range(ref)
        return cell.getString()

    def snapshot(self, out: Path):
        """Capture actual X11 pixels for review, never a fabricated spreadsheet image."""
        subprocess.run(['ffmpeg', '-y', '-v', 'error', '-f', 'x11grab', '-video_size',
                        f'{self.size[0]}x{self.size[1]}', '-i', os.environ['DISPLAY'],
                        '-frames:v', '1', str(out)], check=True, capture_output=True)

    # ---------------- recording ----------------
    def record(self, schedule: Sequence[tuple[float, dict]], total_s: float, out: Path, *,
               evidence_refs: Callable[[dict], list[str]] | None = None) -> RecordingResult:
        """Capture the screen for ``total_s`` seconds, applying each action at its time (s from start)."""
        out = Path(out)
        display = os.environ['DISPLAY']
        ff = subprocess.Popen(['ffmpeg', '-y', '-hide_banner', '-loglevel', 'error', '-f', 'x11grab',
                               '-draw_mouse', '1', '-video_size', f'{self.size[0]}x{self.size[1]}',
                               '-framerate', str(self.fps), '-i', f'{display}+0,0', '-c:v', 'libx264',
                               '-preset', 'ultrafast', '-crf', '18', '-pix_fmt', 'yuv420p', str(out)],
                              stdin=subprocess.PIPE)
        time.sleep(1.0)                     # x11grab warm-up; t0 is when frames are flowing
        t0 = time.monotonic(); log = []
        try:
            for at, action in sorted(schedule, key=lambda x: x[0]):
                wait = at - (time.monotonic() - t0)
                if wait > 0:
                    time.sleep(wait)
                actual = time.monotonic() - t0
                self.apply(action)
                entry = {'planned_s': round(at, 3), 'actual_s': round(actual, 3),
                         'completed_s': round(time.monotonic()-t0, 3), 'action': action}
                if evidence_refs:
                    entry['observed'] = {ref: self.value(ref) for ref in evidence_refs(action)}
                if action['do'] == 'type':
                    _, cell = self._range(action['ref'])
                    entry['typed_cell'] = {'text':cell.getString(), 'formula':cell.getFormula(),
                                           'type':str(cell.getType())}
                if action['do'] in ('type', 'set', 'menu'):
                    snap = self.workdir / f'action_{len(log):02d}.png'
                    self.snapshot(snap)
                    entry['screenshot'] = str(snap)
                log.append(entry)
            remaining = total_s - (time.monotonic() - t0)
            if remaining > 0:
                time.sleep(remaining)
        finally:
            stopped_at = time.monotonic() - t0
            ff.communicate(b'q', timeout=60)
        if ff.returncode not in (0, 255) or not out.is_file():
            raise SheetRecorderError('Screen capture failed')
        # The file starts before t0 (warm-up + ffmpeg start-up); derive the exact lead from its real length.
        probe = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'json', str(out)],
                               capture_output=True, text=True)
        duration = float(json.loads(probe.stdout)['format']['duration'])
        lead = max(0.0, duration - stopped_at)
        return RecordingResult(video_path=out, duration_s=duration, lead_s=lead, log=log)
