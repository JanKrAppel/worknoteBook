# -*- coding: utf-8 -*-
"""
Created on Wed Sep  2 18:06:23 2015

@author: appel
"""

def parse_index(index):
    from worknote.items import parse_index
    return parse_index(index)[0:2]

def zip_worknote(src_dir, target_fn):
    from os.path import split, join
    from os import listdir
    from zipfile import ZipFile
    wn_dir = split(src_dir)[1]
    zf = ZipFile(target_fn, 'w')
    zf.write(src_dir, wn_dir)
    for fn in listdir(src_dir):
        zf.write(join(src_dir, fn), join(wn_dir, fn))
    zf.close()

def unzip_worknote(src_fn, target_dir):
    pass