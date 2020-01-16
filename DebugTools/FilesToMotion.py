from __future__ import division

import numpy as np
from PIL import Image
from matplotlib import cm
import itertools
import cv2
import scipy as sp
import scipy.ndimage

width = 1040
height = 1040
cols = (width + 15) // 16
cols += 1
rows = (height + 15) // 16
heatmap = np.full((rows, cols), 0.0, dtype=np.float32)

m = np.fromfile(
    'motion.data', dtype=[
        ('x', 'i1'),
        ('y', 'i1'),
        ('sad', 'u2'),
        ])
frames = m.shape[0] // (cols * rows)
m = m.reshape((frames, rows, cols))

for frame in range(frames):
    data = np.sqrt(
        np.square(m[frame]['x'].astype(np.float32)) +
        np.square(m[frame]['y'].astype(np.float32))
        ).clip(0, 255) / 255
    for x, y in itertools.product(range(len(data)), range(len(data[0]))):
        if data[x, y] > 0.2:
            heatmap[x, y] += np.float32(0.3)
        else:
            heatmap[x, y] *= np.float32(0.9)
    sigma = [5.0, 5.0]
    #heatmap_blurred = sp.ndimage.filters.gaussian_filter(heatmap, sigma, mode='constant')
    #resized = cv2.resize(heatmap_blurred, dsize=(65, 65))
    img = Image.fromarray(np.uint8(cm.jet(heatmap) * 255))
    filename = 'frame%03d.png' % frame
    print('Writing %s' % filename)
    img.save(filename)
