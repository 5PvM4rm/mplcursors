"""Display a bar's height and name on top of it upon hovering.

An example of using event handlers to change the annotation text and position.
"""

import string
import matplotlib.pyplot as plt
import mplcursors

fig, ax = plt.subplots()
ax.bar(range(9), range(1, 10), align='center')
labels = string.ascii_uppercase[:9]
ax.set(xticks=range(9), xticklabels=labels, title='Hover over a bar')

cursor = mplcursors.cursor(hover=True)
@cursor.connect("add")
def on_add(sel):
    x, y, width, height = sel.pick_info.artist.get_bbox().bounds
    sel.annotation.set_text("{}: {}".format(x + width / 2, height))
    sel.annotation.xy = (x + width / 2, y + height)
    sel.annotation.xyann = (0, 20)

plt.show()
