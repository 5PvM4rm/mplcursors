from collections import namedtuple
import copy
from types import MappingProxyType
import warnings
from weakref import WeakKeyDictionary

from matplotlib.cbook import CallbackRegistry

from . import _pick_info


__all__ = ["Cursor", "default_annotation_kwargs", "default_highlight_kwargs"]


default_annotation_kwargs = MappingProxyType(dict(
    xytext=(-15, 15), textcoords="offset points",
    bbox=dict(boxstyle="round,pad=.5", fc="yellow", alpha=.5, ec="k"),
    arrowprops=dict(arrowstyle="->", connectionstyle="arc3", shrinkB=0, ec="k")))
default_highlight_kwargs = MappingProxyType(dict(
    c="yellow", mec="yellow", lw=3, mew=3))
default_bindings = MappingProxyType(dict(
    select=1, deselect=3,
    previous="shift+left", next="shift+right",
    toggle_visibility="d", toggle_enabled="t"))


def _reassigned_axes_event(event, ax):
    """Reassign `event` to `ax`.
    """
    event = copy.copy(event)
    event.xdata, event.ydata = (
        ax.transData.inverted().transform_point((event.x, event.y)))
    return event


Selection = namedtuple("Selection", "pick_info annotation extras")


class Cursor:
    _keep_alive = WeakKeyDictionary()

    def __init__(self,
                 artists,
                 *,
                 hover=False,
                 multiple=False,
                 transformer=lambda c: c,
                 annotation_kwargs=None,
                 highlight=False,
                 bindings=default_bindings):

        self._artists = artists
        self._multiple = multiple
        self._transformer = transformer
        self._annotation_kwargs = {
            **default_annotation_kwargs, **(annotation_kwargs or {})}
        self._highlight_kwargs = (
            None if highlight is False
            else default_highlight_kwargs if highlight is True
            else {**default_highlight_kwargs, **highlight}
        )
        bindings = {**default_bindings, **bindings}
        if set(bindings) != set(default_bindings):
            raise ValueError("Unknown bindings")
        actually_bound = {k: v for k, v in bindings.items() if v is not None}
        if len(set(actually_bound.values())) != len(actually_bound):
            raise ValueError("Duplicate bindings")
        self._bindings = bindings

        self._figures = {artist.figure for artist in artists}
        self._axes = {artist.axes for artist in artists}

        for figure in self._figures:
            type(self)._keep_alive.setdefault(figure, []).append(self)
            if hover:
                if multiple:
                    raise ValueError("`hover` and `multiple` are incompatible")
                figure.canvas.mpl_connect(
                    "motion_notify_event", self._on_select_button_press)
            else:
                figure.canvas.mpl_connect(
                    "button_press_event", self._on_button_press)
                figure.canvas.mpl_connect(
                    "key_press_event", self._on_key_press)

        self._enabled = True
        self._selections = []
        self._callbacks = CallbackRegistry()

    @property
    def enabled(self):
        return self._enabled

    @enabled.setter
    def enabled(self, value):
        self._enabled = value

    @property
    def selections(self):
        return self._selections[:]

    def add_annotation(self, pick_info):
        ann = pick_info.artist.axes.annotate(
            pick_info.ann_text, xy=pick_info.target, **self._annotation_kwargs)
        ann.draggable(use_blit=True)
        extras = []
        if self._highlight_kwargs is not None:
            extras.append(self.add_highlight(pick_info.artist))
        if not self._multiple:
            while self._selections:
                self._remove_selection(self._selections[-1])
        sel = Selection(pick_info, ann, extras)
        self._selections.append(sel)
        self._callbacks.process("add", sel)
        pick_info.artist.figure.canvas.draw_idle()
        return ann

    def add_highlight(self, artist):
        hl = copy.copy(artist)
        hl.set(**self._highlight_kwargs)
        artist.axes.add_artist(hl)
        return hl

    def connect(self, event, func):
        if event not in ["add", "remove"]:
            raise ValueError("Invalid cursor event: {}".format(event))
        return self._callbacks.connect(event, func)

    def disconnect(self, cid):
        self._callbacks.disconnect(cid)

    def _on_button_press(self, event):
        if event.button == self._bindings["select"]:
            self._on_select_button_press(event)
        if event.button == self._bindings["deselect"]:
            self._on_deselect_button_press(event)

    def _on_select_button_press(self, event):
        if event.canvas.widgetlock.locked() or not self.enabled:
            return
        # Work around lack of support for twinned axes.
        per_axes_event = {ax: _reassigned_axes_event(event, ax)
                          for ax in self._axes}
        pis = []
        for artist in self._artists:
            if event.canvas is not artist.figure.canvas:
                continue
            try:
                pi = _pick_info.compute_pick(
                    artist, per_axes_event[artist.axes])
            except NotImplementedError as e:
                warnings.warn(str(e))
            if pi:
                pis.append(pi)
        if not pis:
            return
        self.add_annotation(self._transformer(min(pis, key=lambda c: c.dist)))

    def _on_deselect_button_press(self, event):
        if event.canvas.widgetlock.locked() or not self.enabled:
            return
        for sel in self._selections:
            ann = sel.annotation
            if event.canvas is not ann.figure.canvas:
                continue
            contained, _ = ann.contains(event)
            if contained:
                self._remove_selection(sel)
                self._callbacks.process("remove", sel)

    def _on_key_press(self, event):
        if event.key == self._bindings["toggle_enabled"]:
            self.enabled = not self.enabled
        elif event.key == self._bindings["toggle_visibility"]:
            for sel in self._selections:
                sel.annotation.set_visible(not sel.annotation.get_visible())
                sel.annotation.figure.canvas.draw_idle()
        if self._selections:
            sel = self._selections[-1]
        else:
            return
        if event.key == self._bindings["previous"]:
            self.add_annotation(_pick_info.move(*sel.pick_info, -1))
        elif event.key == self._bindings["next"]:
            self.add_annotation(_pick_info.move(*sel.pick_info, 1))

    def _remove_selection(self, sel):
        self._selections.remove(sel)
        sel.annotation.figure.canvas.draw_idle()
        # Work around matplotlib/matplotlib#6785.
        draggable = sel.annotation._draggable
        if draggable:
            draggable.disconnect()
            try:
                c = draggable._c1
            except AttributeError:
                pass
            else:
                draggable.canvas.mpl_disconnect(draggable._c1)
        # (end of workaround).
        sel.annotation.remove()
        for artist in sel.extras:
            artist.figure.canvas.draw_idle()
            artist.remove()
