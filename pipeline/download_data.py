"""Download Cricsheet's all-men's-matches JSON archive and unzip it into all_male_json/.
Usage: python pipeline/download_data.py [--force] [--dest DIR]"""
import argparse, os, shutil, sys, tempfile, urllib.request, zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(HERE)
URL = 'https://cricsheet.org/downloads/all_male_json.zip'

ap = argparse.ArgumentParser()
ap.add_argument('--dest', default=os.path.join(PROJECT, 'all_male_json'))
ap.add_argument('--force', action='store_true', help='replace an existing download')
args = ap.parse_args()

if os.path.isdir(args.dest) and os.listdir(args.dest) and not args.force:
    sys.exit(f'{args.dest} already has data; pass --force to replace it.')

def progress(blocks, block_size, total):
    done = min(blocks * block_size, total)
    print(f'\r  {done / 1e6:6.1f} / {total / 1e6:.1f} MB', end='', flush=True)

with tempfile.TemporaryDirectory() as tmp:
    archive = os.path.join(tmp, 'all_male_json.zip')
    print('Downloading', URL)
    urllib.request.urlretrieve(URL, archive, reporthook=progress)
    print()
    with zipfile.ZipFile(archive) as z:
        if os.path.isdir(args.dest):
            shutil.rmtree(args.dest)
        z.extractall(args.dest)   # zipfile strips absolute paths and '..' from member names

n = sum(f.endswith('.json') for f in os.listdir(args.dest))
print(f'{n} match files in {args.dest}')
# The pipeline's parse cache was built from the old files, so it must be rebuilt
if os.path.isdir(os.path.join(PROJECT, 'cache')):
    print('Delete cache/ before rebuilding, or the notebooks will reuse the old parsed data.')
