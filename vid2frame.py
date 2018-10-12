import os
import sys
import lmdb
import h5py
import numpy as np
import argparse
from tqdm import tqdm
from subprocess import call
import cPickle as pickle


def read_img(path):
    with open(path, 'rb') as f:
        return f.read()


parser = argparse.ArgumentParser()
parser.add_argument("split_file", type=str, help="the pickled split file")
parser.add_argument("split", type=str, help="the split to use, e.g. split-0")
parser.add_argument("frame_db", type=str, help="the database to store extracted frames, either LMDB or HDF5")
parser.add_argument("db_type", type=str, help="type of the database, LMDB or HDF5")
# resize options
parser.add_argument("-a", "--asis", action="store_true", help="do not resize frames")
parser.add_argument("-s", "--short", type=int, default=0, help="keep the aspect ration and scale the shorter side to s")
parser.add_argument("-H", "--height", type=int, default=0, help="the resized height")
parser.add_argument("-W", "--width", type=int, default=0, help="the resized width")
# frame sampling options
parser.add_argument("-k", "--skip", type=int, default=1, help="only store frames with (ID-1) mod skip==0, frame ID starts from 1")
parser.add_argument("-n", "--num_frame", type=int, default=-1, help="uniformly sample n frames, this will override --skip")
args = parser.parse_args()

# sanity check of the options
if args.asis:
    assert args.short == 0 and args.height == 0 and args.width == 0
if args.short > 0:
    assert (not args.asis) and args.height == 0 and args.width == 0
if args.height > 0 or args.width > 0:
    assert (not args.asis) and args.height > 0 and args.width > 0 and args.short == 0


split = pickle.load(open(args.split_file,'rb'))
print split.keys(), 'using %s' %(args.split)
all_videos = split[args.split]

if args.db_type == 'LMDB':
    frame_db = lmdb.open(args.frame_db, map_size=1<<40)
elif args.db_type == 'HDF5':
    frame_db = h5py.File(args.frame_db, 'a') # append mode
else:
    print 'Unknown db_type'
    sys.exit(1)

is_lmdb = (args.db_type == 'LMDB')

tmp_dir = '/tmp'


for vid in tqdm(all_videos, ncols=64):
    #vvid = vid.split('/')[-1].split('.')[0]
    vvid, _ = os.path.splitext(vid) # discard extension
    _, vvid = os.path.split(vvid)   # get filename without path

    v_dir = os.path.join(tmp_dir, vvid)
    call(["rm", "-rf", v_dir])
    os.mkdir(v_dir)    # caching directory to store ffmpeg extracted frames


    if args.asis:
        call(["ffmpeg", "-loglevel", "panic", "-i", vid, "-qscale:v", "2", v_dir+"/%8d.jpg"])

    elif args.short > 0:
        call(["ffmpeg",
                "-loglevel", "panic",
                "-i", vid,
                "-vf", "scale='iw*1.0/min(iw,ih)*%d':'ih*1.0/min(iw,ih)*%d'" % (args.short, args.short),
                "-qscale:v", "2",
                v_dir+"/%8d.jpg"])

    else:
        call(["ffmpeg",
                "-loglevel", "panic",
                "-i", vid,
                "-vf", "scale=%d:%d" % (args.width, args.height),
                "-qscale:v", "2",
                v_dir+"/%8d.jpg"])

    sample = (args.num_frame > 0)
    if sample:
        ids = [int(f.split('.')[0]) for f in os.listdir(v_dir)]
        sample_ids = set(list(np.linspace(min(ids), max(ids),
                                args.num_frame, endpoint=True, dtype=np.int32)))

    files = []
    for f_name in os.listdir(v_dir):
        fid = int(f_name.split('.')[0])

        if sample:
            if fid not in sample_ids:
                continue
        elif args.skip > 1:
            if (fid-1) % args.skip != 0:
                continue
        files.append((fid, f_name))


    if is_lmdb:
        with frame_db.begin(write=True, buffers=True) as txn:
            for fid, f_name in files:
                s = read_img(os.path.join(v_dir, f_name))
                key = "%s/%08d" % (vvid, fid)   # by padding zeros, frames in db are stored in order
                txn.put(key, s)
    else:
        for fid, f_name in files:
            s = read_img(os.path.join(v_dir, f_name))
            key = "%s/%08d" % (vvid, fid)   # by padding zeros, frames in db are stored in order
            frame_db[key] = np.void(s)

    call(["rm", "-rf", v_dir])



