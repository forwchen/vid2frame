import sys
import time
import lmdb
import h5py
import numpy as np
from PIL import Image
from cStringIO import StringIO


merged = h5py.File('merged.hdf5', 'a')

for db in sys.argv[1:]:
    frame_db = h5py.File(db, 'r')
    for vid in frame_db:
        db_vid = frame_db[vid]
        for fid in db_vid:
            merged['%s/%s'%(vid, fid)] = np.asarray(db_vid[fid])




