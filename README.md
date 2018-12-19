# vid2frame
An easy-to-use tool to extract frames from video and store into database.
Basically, this is a python wrapper of ffmpeg which addtionally stores the frames into database.

## Why this tool
* Extracting frames from large video datasets (usually 10k ~ 100k, hundreds of GBs on disk) is tedious, automate it.
* Storing millions of frames on disk makes subsequent processing SLOW.
* Common mistakes I once made:
    * Decode all frames (using scikit-video) and store them into a **LARGE** .npy file, nice way to blow up the disk.
    * Extract all frames using ffmpeg and write to disk. Takes **foreeeeever** to move or delete.
    * Extract JPEG frames using ffmpeg but ignores the JPEG **quality**. For deep learning and computer vision, a good quality of images (JPEG quality around 95) is required. 

* Good practice in my opinion:
    * Add `-qscale:v 2` to [ffmpeg](https://stackoverflow.com/questions/10225403/how-can-i-extract-a-good-quality-jpeg-image-from-an-h264-video-file-with-ffmpeg) command.
    * Store extracted frames into a database, [LMDB](https://lmdb.readthedocs.io/en/release/) or [HDF5](http://docs.h5py.org/en/stable/).
    * (Optional) Use [Tensorpack dataflow](https://tensorpack.readthedocs.io/modules/dataflow.html) to accelerate reading from the database.
    * Suggestions are welcome.

## Usage
### 1. Split video dataset into multiple (if necessary) splits with `split_video_dataset.py`
```
usage: split_video_dataset.py [-h] vid_dir num_splits split_file

positional arguments:
  vid_dir     the video directory
  num_splits  the number of splits
  split_file  the split stored as pickle file

optional arguments:
  -h, --help  show this help message and exit
```
#### Sample usage
Run: `python split_video_dataset.py ./sample_videos 2 split-sample.pkl`

Which outputs split info after completion:
```
Number of videos found: 2
Number of unique videos: 2
split-0 : 1
split-1 : 1
Joined splits: 2
```

#### Notes
* Video files are identified with extensions, currently recognizing `['.mp4', '.avi', '.flv', '.mkv', '.webm', '.mov']`.

* Videos with the same name (without extension) are considered duplicates. Only one of them will be processed.


### 2. Extract frames for videos in a specific split using `vid2frame.py`
```
usage: vid2frame.py [-h] [-a] [-s SHORT] [-H HEIGHT] [-W WIDTH] [-k SKIP]
                    [-n NUM_FRAME]
                    split_file split frame_db db_type

positional arguments:
  split_file            the pickled split file
  split                 the split to use, e.g. split-0
  frame_db              the database to store extracted frames, either LMDB or
                        HDF5
  db_type               type of the database, LMDB or HDF5

optional arguments:
  -h, --help            show this help message and exit
  -a, --asis            do not resize frames
  -s SHORT, --short SHORT
                        keep the aspect ration and scale the shorter side to s
  -H HEIGHT, --height HEIGHT
                        the resized height
  -W WIDTH, --width WIDTH
                        the resized width
  -k SKIP, --skip SKIP  only store frames with (ID-1) mod skip==0, frame ID
                        starts from 1
  -n NUM_FRAME, --num_frame NUM_FRAME
                        uniformly sample n frames, this will override --skip
  -r INTERVAL, --interval INTERVAL
                        extract one frame every r seconds
```
#### Notes
* The frames will be stored as strings of their binary content, i.e. they are NOT decoded. Both LMDB and HDF5 are key-value storage, the keys are in the format of `video_name/frame_id` (assuming there are no two videos with the same name).
* The frames are in JPEG format, with JPEG quality ~95. Note the `-qscale:v 2` option in `vid2frame.py`. This is **important** for subsequent deep learning tasks.
* The database to use is either LMDB or HDF5, choose one according to:
    * Reading from HDF5 is convenient, if you do not plan to use [Tensorpack](https://tensorpack.readthedocs.io/_modules/tensorpack/dataflow/format.html#HDF5Data), which does not support HDF5 well currently, always choose HDF5.
    * LMDB integrates better with [Tensorpack](https://tensorpack.readthedocs.io/modules/dataflow.html#tensorpack.dataflow.LMDBData), but reading from it is less flexible (though much much faster than HDF5).
* Resizing options (exclusive):
    1. Do not resize (--asis)
    2. Resize the shorter edge and keep aspect ratio (the longer edge adapts) (--short)
    3. Resize to specific height & width (--height --width)
* Sampling options (exclusive):
    1. Keep one of frame every `k` frames (default 1, i.e. keep every frame) (--skip)
    2. Uniformly sample `n` frames (--num_frame). For example: If there are 10 frames, --skip=2 will sample frames 1,3,5,7,9 and --num_frame=4 will sample frames 1,4,7,10.
    3. Sample one frame every `r` seconds (--interval) or 1/r FPS. For r==1, its 1 FPS, and r==2, its 0.5 FPS.
    
#### Sample usage
* Extract frame of videos in split-0 generated above:

`python vid2frame.py split-sample.pkl split-0 frames-0.hdf5 HDF5 --short=240`

The output would be:
```
['split-0', 'split-1'] using split-0
100%|█████████████████████████████| 1/1 [00:02<00:00,  2.05s/it]
```
You can also process the other split simultaneously, for large video datasets, 6~8-split is recommended for a server with 40 CPUs:

`python vid2frame.py split-sample.pkl split-1 frames-1.hdf5 HDF5 --short=240`

Note that the output databases for different splits should not be the same in case concurrent write is no supported.

More samples:

`python vid2frame.py split-sample.pkl split-0 frames-0.lmdb LMDB --asis`

`python vid2frame.py split-sample.pkl split-0 frames-0.lmdb LMDB -H 240 -W 360`

### 3. (Optional) Test reading from database using `test_read_db.py`
`test_read_db.py` provides sample code to iterate, read and decode frames in LMDB/HDF5 databases, it also checks for broken images. 
#### Note
* Opening images from string buffer: `img = Image.open(StringIO(v))`
* Reading string from HDF5 db: `s = np.asarray(db_vid[fid]).tostring()`

#### Sample usage
`python test_read_db.py frames-1.lmdb` or `python test_read_db.py frames-0.hdf5`

The script outputs the number of frames in the database, the size of the last image and time to iterate over whole database.

## Dependencies
* Python 2.7
* FFmpeg: Install on [Ubuntu](https://tecadmin.net/install-ffmpeg-on-linux/). Other [platforms](https://www.google.com/).
* Python libraries: `pip install -r requirements.txt`, 


## Common issues
* `RuntimeError: Unable to create link (name already exists)`

   This is caused by writing duplicate frames to a non-empty HDF5 database.
