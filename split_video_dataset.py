import sys
import os
from subprocess import call, check_output
import argparse
import cPickle as pickle

parser = argparse.ArgumentParser()
parser.add_argument("vid_dir", type=str, help="the video directory")
parser.add_argument("num_splits", type=int, help="the number of splits")
parser.add_argument("split_file", type=str, help="the split stored as pickle file")
args = parser.parse_args()

vid_dir = os.path.abspath(args.vid_dir)

#videos = [os.path.join(vid_dir, v) for v in os.listdir(vid_dir)]
video_ext = set(['.mp4', '.avi', '.flv', '.mkv', '.webm', '.mov'])
files = check_output(["find", vid_dir, "-type", "f"])
files = files.split('\n')
videos = []
for f in files:
    name, ext = os.path.splitext(f)
    if ext in video_ext:
        videos.append(f)


print 'Number of videos found: %d' % (len(videos))
print 'Number of unique videos: %s' % (len(set(videos)))

splits = {}
for i in range(args.num_splits):
    si = videos[i::args.num_splits]
    splits['split-%d' %(i,)] = si
    print 'split-%d : %d' % (i, len(si))

verify = []
for x in splits.values():
    verify += x

print 'Joined splits: %d' % (len(verify))
pickle.dump(splits, open(args.split_file, 'wb'), 2)





