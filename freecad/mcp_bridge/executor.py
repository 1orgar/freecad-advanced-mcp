"""Qt main-thread execution of user code and tool handlers.

Only the Qt main thread may touch FreeCAD. The HTTP server runs off-thread,
so Executor bridges the gap: submit() queues code execution, and submit_call()
runs custom tool handlers on the Qt main thread with a synchronous return value.
"""

import queue
import sys
import traceback

import FreeCAD
from PySide.QtCore import QObject, Qt, Signal

from freecad.mcp_bridge.paging import SENTINEL


class TeeWriter:
    """File-like sink: every write goes to the page queue and the Report View."""

    def __init__(self, output_queue, stream):
        self._queue = output_queue
        self._stream = stream

    def write(self, text):
        if text:
            self._queue.put((self._stream, text))
            FreeCAD.Console.PrintMessage(text)

    def flush(self):
        pass


class Executor(QObject):
    wake_up = Signal()

    def __init__(self):
        super().__init__()
        self._jobs = queue.Queue()
        self._busy = False
        self.wake_up.connect(self._dispatch, Qt.QueuedConnection)

    def submit(self, code, output_queue, filepath=None, use_transaction=True):
        """Queue the code execution job and wake the dispatcher."""
        self._jobs.put(("exec", code, output_queue, filepath, use_transaction))
        self.wake_up.emit()

    def submit_call(self, fn, *args, timeout_s=30.0, **kwargs):
        """Run fn(*args, **kwargs) synchronously on the Qt main thread and return result."""
        res_queue = queue.Queue(maxsize=1)
        self._jobs.put(("call", fn, args, kwargs, res_queue))
        self.wake_up.emit()
        try:
            success, val = res_queue.get(timeout=timeout_s)
            if success:
                return val
            raise val
        except queue.Empty:
            raise TimeoutError(f"Operation timed out after {timeout_s}s waiting for Qt main thread.")

    def _dispatch(self):
        """Drain the job queue on the main thread, strictly one job at a time."""
        if self._busy:
            return
        self._busy = True
        try:
            while True:
                try:
                    item = self._jobs.get_nowait()
                except queue.Empty:
                    break

                if isinstance(item, tuple) and len(item) > 0 and item[0] == "call":
                    _, fn, args, kwargs, res_queue = item
                    fn_name = getattr(fn, "__name__", "mcp_tool")
                    read_only_fns = {
                        "get_view", "get_multi_view", "get_section_view", "export_viewer_html",
                        "inspect_geometry", "analyze_stability", "check_overhangs",
                        "audit_wall_thickness", "inspect_fasteners", "get_document_tree",
                        "diagnose_document", "check_clearance", "get_selection",
                        "export_geometry", "manage_document", "undo_redo",
                    }
                    active_doc = FreeCAD.ActiveDocument
                    tx_opened = False
                    if fn_name not in read_only_fns and active_doc:
                        try:
                            active_doc.openTransaction(f"mcp_{fn_name}")
                            tx_opened = True
                        except Exception:
                            tx_opened = False
                    try:
                        res = fn(*args, **kwargs)
                        if tx_opened and active_doc:
                            if isinstance(res, dict) and res.get("error"):
                                active_doc.abortTransaction()
                            else:
                                active_doc.commitTransaction()
                        res_queue.put((True, res))
                    except BaseException as exc:
                        if tx_opened and active_doc:
                            try:
                                active_doc.abortTransaction()
                            except Exception:
                                pass
                        res_queue.put((False, exc))
                else:
                    if isinstance(item, tuple) and len(item) > 0 and item[0] == "exec":
                        _, code, output_queue, filepath, use_transaction = item
                    elif len(item) >= 3:
                        code, output_queue, filepath = item[:3]
                        use_transaction = True
                    else:
                        continue
                    self._run(code, output_queue, filepath, use_transaction)
        finally:
            self._busy = False

    def _run(self, code, output_queue, filepath=None, use_transaction=True):
        """Run one code execution job with optional transaction protection."""
        import FreeCADGui

        stdout_tee = TeeWriter(output_queue, "stdout")
        stderr_tee = TeeWriter(output_queue, "stderr")
        old_out, old_err = sys.stdout, sys.stderr
        sys.stdout, sys.stderr = stdout_tee, stderr_tee
        import math
        import Part
        import Sketcher
        try:
            import PartDesign
        except Exception:
            PartDesign = None
        try:
            import Mesh
            import MeshPart
        except Exception:
            Mesh = None
            MeshPart = None
        try:
            from freecad.mcp_bridge import cad_helpers
        except Exception:
            cad_helpers = None

        env = {
            "__name__": "__main__",
            "math": math,
            "FreeCAD": FreeCAD,
            "App": FreeCAD,
            "FreeCADGui": FreeCADGui,
            "Gui": FreeCADGui,
            "Part": Part,
            "PartDesign": PartDesign,
            "Sketcher": Sketcher,
            "Mesh": Mesh,
            "MeshPart": MeshPart,
            "cad": cad_helpers,
        }
        if filepath is not None:
            env["__file__"] = filepath

        active_doc = FreeCAD.ActiveDocument
        tx_opened = False
        if use_transaction and active_doc:
            try:
                active_doc.openTransaction("mcp_exec")
                tx_opened = True
            except Exception:
                tx_opened = False

        try:
            exec(code, env)
            if tx_opened and active_doc:
                active_doc.commitTransaction()
        except BaseException:
            if tx_opened and active_doc:
                try:
                    active_doc.abortTransaction()
                except Exception:
                    pass
            stderr_tee.write("\n" + traceback.format_exc())
        finally:
            sys.stdout, sys.stderr = old_out, old_err
            output_queue.put(SENTINEL)
