from matplotlib import rcsetup
from matplotlib.backends.backend_gtk3 import _BackendGTK3, FigureCanvasGTK3

from .base import FigureCanvasCairo


rcsetup.interactive_bk += ["module://mpl_cairo.gtk3"]  # NOTE: Should be fixed in Mpl.


class FigureCanvasGTK3Cairo(FigureCanvasCairo, FigureCanvasGTK3):
    def _renderer_init(self):
        pass

    def on_draw_event(self, widget, ctx):
        renderer = self.get_renderer()
        renderer.set_ctx_from_pycairo_ctx(ctx)
        self.figure.draw(renderer)


@_BackendGTK3.export
class _BackendGTK3Cairo(_BackendGTK3):
    FigureCanvas = FigureCanvasGTK3Cairo