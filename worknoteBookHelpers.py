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

def unzip_worknote(src_fn, target_dir = None):
    from zipfile import ZipFile
    from os.path import split, exists, join
    from os import makedirs, listdir
    from shutil import move
    from tempfile import gettempdir
    with ZipFile(src_fn, 'r') as zipfile:
        files = zipfile.namelist()
        wn_dir = split(files[0])[0]
        if target_dir is None:
            target_dir = wn_dir
        if exists(target_dir):
            raise OSError('The target directory already exists')
        else:
            makedirs(target_dir)
            tmpdir = gettempdir()
            zipfile.extractall(tmpdir)
            for fn in listdir(join(tmpdir, wn_dir)):
                move(join(join(tmpdir, wn_dir), fn), target_dir)
                
class Configuration(object):
    
    def __init__(self, cfg_file, default_cfg = None):
        from ConfigParser import SafeConfigParser
        self.cfg_file = cfg_file
        self.config = SafeConfigParser()
        if not default_cfg is None:
            for section in default_cfg:
                for option in default_cfg[section]:
                    self.__put_item([section, option], default_cfg[section][option])
        self.read_cfg_file()
    
    def __getitem__(self, indices):
        indices = indices[0:2]
        section, option = indices
        if not section in self.config.sections():
            return None
        if not option in self.config.options(section):
            return None
        val = self.config.get(section, option)
        try:
            val = int(val)
        except ValueError:
            pass
        else:
            return val
        try:
            val = float(val)
        except ValueError:
            pass
        else:
            return val
        if val == 'False':
            return False
        elif val == 'True':
            return True
        return val
        
    def __put_item(self, indices, value):
        indices = indices[0:2]
        value = str(value)
        section, option = indices
        if not section in self.config.sections():
            self.config.add_section(section)
        if not option in self.config.options(section):
            self.config.set(section, option, value)
    
    def __setitem__(self, indices, value):
        self.__put_item(indices, value)
        self.update_cfg_file()
            
    def update_cfg_file(self):
        with open(self.cfg_file, 'w') as outfile:
            self.config.write(outfile)
    
    def read_cfg_file(self):
        from os.path import exists
        if exists(self.cfg_file):
            self.config.read(self.cfg_file)
