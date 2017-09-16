.. mplcursors documentation master file, created by
   sphinx-quickstart on Tue Jul 19 20:06:56 2016.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

.. toctree::
   :hidden:

   Main page <self>
   Examples <examples/index>

Welcome to mplcursors' documentation!
=====================================

:mod:`mplcursors` provides interactive data selection cursors for
:mod:`matplotlib`.  It is inspired from :mod:`mpldatacursor`
(https://github.com/joferkington/mpldatacursor), with a much simplified API.

:mod:`mplcursors` requires Python 3, and :mod:`matplotlib`\≥2.0.

.. _installation:

Installation
------------

Pick one among:

.. code-block:: sh

    $ pip install mplcursors  # from PyPI
    $ pip install git+https://github.com/anntzer/mplcursors  # from Github

.. _basic-example:

Basic example
-------------

Basic examples work similarly to :mod:`mpldatacursor`::

    import matplotlib.pyplot as plt
    import numpy as np
    import mplcursors

    data = np.outer(range(10), range(1, 5))

    fig, ax = plt.subplots()
    lines = ax.plot(data)
    ax.set_title("Click somewhere on a line.\nRight-click to deselect.\n"
                 "Annotations can be dragged.")

    mplcursors.cursor(lines) # or just mplcursors.cursor()

    plt.show()

.. image:: /images/basic.png

The `cursor` convenience function makes a collection of artists selectable.
Specifically, its first argument can either be a list of artists or axes (in
which case all artists in each of the axes become selectable); or one can just
pass no argument, in which case all artists in all figures become selectable.
Other :class:`arguments <mplcursors.Cursor>` (which are all keyword-only)
allow for basic customization of the `Cursor`’s behavior; please refer to the
constructor's documentation.

.. _activation-by-environment-variable:

Activation by environment variable
----------------------------------

It is possible to use :mod:`mplcursors` without modifying *any* source code:
setting the :envvar:`MPLCURSORS` environment variable to a JSON-encoded dict
will patch `Figure.draw <matplotlib.figure.Figure.draw>` to automatically
call `cursor` (with the passed keyword arguments, if any) after the figure is
drawn for the first time (more precisely, after the first draw that includes a
selectable artist). Typical settings include::

    $ MPLCURSORS={} python foo.py

and::

    $ MPLCURSORS='{"hover": 1}' python foo.py

Note that this will only work if :mod:`mplcursors` has been installed, not if
it is simply added to the :envvar:`PYTHONPATH`.

Note that this will not pick up artists added to the figure after the first
draw, e.g. through interactive callbacks.

.. _default-ui:

Default UI
----------

- A left click on a line (a point, for plots where the data points are not
  connected) creates a draggable annotation there.  Only one annotation is
  displayed (per `Cursor` instance), except if the ``multiple`` keyword
  argument was set.
- A right click on an existing annotation will remove it.
- Clicks do not trigger annotations if the zoom or pan tool are active.  It is
  possible to bypass this by *double*-clicking instead.
- For annotations pointing to lines or images, :kbd:`Shift-Left` and
  :kbd:`Shift-Right` move the cursor "left" or "right" by one data point.  For
  annotations pointing to images, :kbd:`Shift-Up` and :kbd:`Shift-Down` are
  likewise available.
- :kbd:`v` toggles the visibility of the existing annotation(s).
- :kbd:`e` toggles whether the `Cursor` is active at all (if not, no event
  other than re-activation is propagated).

These bindings are all customizable via `Cursor`’s ``bindings`` keyword
argument.  Note that the keyboard bindings are only active if the canvas has
the keyboard input focus.

.. _customization:

Customization
-------------

Instead of providing a host of keyword arguments in `Cursor`’s constructor,
:mod:`mplcursors` represents selections as `Selection` objects (essentially,
namedtuples) and lets you hook into their addition and removal.

Specifically, a `Selection` has the following fields:

    - :attr:`~.artist`: the selected artist,
    - :attr:`~.target`: the point picked within the artist; if a point is
      picked on a :class:`~matplotlib.lines.Line2D`, the index of the point is
      available as the :attr:`target.index` sub-attribute (for more details,
      see :ref:`selection-indices`).
    - :attr:`~.dist`: the distance from the point clicked to the
      :attr:`~.target` (mostly used to decide which artist to select).
    - :attr:`~.annotation`: a :mod:`matplotlib`
      :class:`~matplotlib.text.Annotation` object.
    - :attr:`~.extras`: an additional list of artists, that will be removed
      whenever the main :attr:`~.annotation` is deselected.

For certain classes of artists, additional information about the picked point
is available in the :attr:`target.index` sub-attribute:

    - For :class:`~matplotlib.lines.Line2D`\s, it contains the index of the
      selected point (see :ref:`selection-indices` for more details, especially
      regarding step plots).
    - For :class:`~maplotlib.image.AxesImage`\s, it contains the ``(y, x)``
      indices of the selected point (such that ``data[y, x]`` in that order is
      the value at that point; note that this means that the indices are not in
      the same order as the target coordinates!).
    - For :class:`~matplotlib.container.Container`\s, it contains the index of
      the selected sub-artist.
    - For :class:`~matplotlib.collections.LineCollection`\s and
      :class:`~matplotlib.collections.PathCollection`\s, it contains a pair:
      the index of the selected line, and the index within the line, as defined
      above.

Thus, in order to customize, e.g., the annotation text, one can call::

    lines = ax.plot(range(3), range(3), "o")
    labels = ["a", "b", "c"]
    cursor = mplcursors.cursor(lines)
    cursor.connect(
        "add", lambda sel: sel.annotation.set_text(labels[sel.target.index]))

Whenever a point is selected (resp. deselected), the ``"add"`` (resp.
``"remove"``) event is triggered and the registered callbacks are executed,
with the `Selection` as only argument.  Here, the only callback updates the
text of the annotation to a per-point label. (``cursor.connect("add")`` can
also be used as a decorator to register a callback, see below for an example.)
For an example using :mod:`pandas`’ :class:`DataFrame <pandas.DataFrame>`\s,
see :ref:`examples/dataframe.py <sphx_glr_examples_dataframe.py>`.

For additional customizations of the position and
appearance of the annotation, see :ref:`examples/bar.py
<sphx_glr_examples_bar.py>` and :ref:`examples/change_popup_color.py
<sphx_glr_examples_change_popup_color.py>`.

Callbacks can also be used to make additional changes to the figure when
a selection occurs.  For example, the following snippet (extracted from
:ref:`examples/paired_highlight.py <sphx_glr_examples_paired_highlight.py>`)
ensures that whenever an artist is selected, another artist that has been
"paired" with it (via the ``pairs`` map) also gets selected::

    @cursor.connect("add")
    def on_add(sel):
        sel.extras.append(cursor.add_highlight(pairs[sel.artist]))

Note that the paired artist will also get de-highlighted when the "first"
artist is deselected.

.. note::
   When the callback is fired, the position of the annotating text is
   temporarily set to ``(nan, nan)``.  This allows us to track whether a
   callback explicitly sets this position, and, if none does, automatically
   compute a suitable position.

   Likewise, if the text alignment is not explicitly set but the position is,
   then a suitable alignment will be automatically computed.

.. _selection-indices:

Selection indices
-----------------

When picking a point on a "normal" line, the target index has an integer part
equal to the index of segment it is on, and a fractional part that indicates
where the point is within that segment.

Such an approach does not make sense for step plots (i.e., created by
`plt.step <matplotlib.pyplot.step>` or `plt.plot(..., drawstyle="steps-...")
<matplotlib.pyplot.plot>`.  In this case, we return a special :class:`Index`
object, with attributes :attr:`int` (the segment index), :attr:`x` (how
far the point has advanced in the ``x`` direction) and :attr:`y` (how far
the point has advanced in the ``y`` direction).  See :ref:`examples/step.py
<sphx_glr_examples_step.py>` for an example.

.. _complex-plots:

Complex plots
-------------

Some complex plots, such as contour plots, may be partially supported,
or not at all.  Typically, it is because they do not subclass
:class:`~matplotlib.artist.Artist`, and thus appear to `cursor` as a collection
of independent artists (each contour level, in the case of contour plots).

It is usually possible, again, to hook the ``"add"`` signal to provide
additional information in the annotation text.  See :ref:`examples/coutour.py
<sphx_glr_examples_contour.py>` for an example.

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
