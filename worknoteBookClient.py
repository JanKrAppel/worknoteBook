# -*- coding: utf-8 -*-
"""
Created on Fri Aug 28 23:19:40 2015

@author: appel
"""

from io import FileIO

class FileLenIO(FileIO):

  def __init__(self, name, mode = 'r', closefd = True):
    super(FileLenIO, self).__init__(name, mode, closefd)
    from os import stat
    self.__size = stat(name).st_size

  def __len__(self):
    return self.__size

class worknoteBookClient(object):

    def __init__(self, config):
        self.config = config
        self.config.update_cfg_file()
        
    def get_server(self, name=None):
        if name is None:
            name = self.config[['client_defaults', 'server']]
        if not name in self.config.get_sections():
            print 'ERROR: Server name not found.'
            return
        return '{url:s}:{port:d}'.format(url=self.config[[name, 'url']],
                                         port=self.config[[name, 'port']])
    
    def list(self, name=None):
        import json
        from urllib2 import urlopen, URLError, HTTPError
        try:
            res = urlopen('http://' + self.get_server(name) + '/download')
            wn_list = json.loads(res.read())
        except URLError, e:
            print 'ERROR: Download failed ({:s})'.format(str(e))
            return
        except HTTPError, e:
            print 'ERROR: Download failed ({:s})'.format(str(e))
            return
        for entry in wn_list:
            print entry
    
    def download(self, index, workdir, name=None):
        from worknoteBookHelpers import unzip_worknote
        from urllib2 import urlopen, URLError
        from tempfile import gettempdir
        from os.path import join
        from worknoteBookHelpers import parse_index
        index = parse_index(index)[0:2]
        if len(index) == 1:
            index = '{:d}'.format(index[0])
        elif len(index) == 2:
            index = '{:d}:{:d}'.format(index[0], index[1])
        tmpfn = join(gettempdir(), 'worknoteBook_download.zip')
        server_url = 'http://{server:s}/download?index={index:s}'.format(server = self.get_server(name), index = index)
        try:        
            server = urlopen(server_url)
            with open(tmpfn, 'wb') as tmpfile:
                tmpfile.write(server.read())
        except URLError, e:
            print 'ERROR: Download failed ({:s})'.format(str(e))
            return
        try:
            unzip_worknote(tmpfn, workdir)
        except OSError, e:
            print 'ERROR: Unable to download file ({:s})'.format(str(e))
        except IOError:
            with open(tmpfn, 'r') as errfile:
                print 'ERROR: Not a zip file ({:s})'.format(errfile.read())
            
    def upload(self, workdir, overwrite=False, name=None):
        from urllib2 import Request, urlopen, HTTPError, URLError
        from worknoteBookHelpers import zip_worknote
        from tempfile import gettempdir
        from os.path import join, exists
        tmpdir = gettempdir()
        zip_fn = join(tmpdir, 'worknoteBook_upload.zip')
        if not exists(workdir):
            print 'ERROR: Directory "{:s}" does not exist.'.format(workdir)
            return
        zip_worknote(workdir, zip_fn)
        up_file = FileLenIO(zip_fn, 'rb')
        request = Request('http://{:s}/upload'.format(self.get_server(name)), up_file)
        request.add_header('Content-Type', 'application/octet-stream')
        request.add_header('X-Worknote-Workdir', workdir)
        request.add_header('X-Worknote-Overwrite', str(overwrite))
        try:        
            response = urlopen(request)
            response = response.read()
        except HTTPError, e:
            print 'ERROR: Upload failed ({:s})'.format(str(e))
            return
        except URLError, e:
            print 'ERROR: Upload failed ({:s})'.format(str(e))
            return
        if response.startswith('Fail'):
            import re
            msg = re.match('Fail (.*)', response)
            print 'ERROR: Upload failed {:s}'.format(msg.group(1))
            
    def add_server(self, name, url, port):
        if name == 'client_defaults':
            print 'ERROR: Server name not allowed.'
            return
        self.config[[name, 'url']] = url
        self.config[[name, 'port']] = port
        self.config.update_cfg_file()
    
    def set_default_server(self, name):
        if name == 'client_defaults':
            print 'ERROR: Server name not allowed.'
            return
        if not name in self.config.get_sections():
            print 'ERROR: Server name not configured.'
            return
        self.config[['client_defaults', 'server']] = name
        self.config.update_cfg_file()