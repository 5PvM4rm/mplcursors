"""A very basic example of mplcursor's functionalities.
"""

import matplotlib.pyplot as plt
import numpy as np
from mplcursors import Cursor

data = np.outer(range(10), range(1, 5))

fig, ax = plt.subplots()
lines = ax.plot(data)
ax.set_title('Click somewhere on a line')

Cursor(lines)

plt.show()
