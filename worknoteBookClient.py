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

    def __init__(self, config='~/.worknoteBook/client.cfg'):
        if type(config) == str:
            from os.path import exists, expanduser, split
            from os import makedirs
            from worknoteBookHelpers import Configuration
            cfg_file = config
            if not exists(split(expanduser(cfg_file))[0]):
                makedirs(split(expanduser(cfg_file))[0])
            default_cfg = {'client_defaults': {'server': 'localhost'},
                           'localhost': {'url': '127.0.0.1',
                                         'port': 8080}}
            config = Configuration(expanduser(cfg_file), default_cfg)
            if not exists(expanduser(cfg_file)):
                config.update_cfg_file()            
        self.config = config
        self.config.update_cfg_file()
        
    def get_server(self, servername=None):
        if servername is None:
            servername = self.config[['client_defaults', 'server']]
        if not servername in self.config.get_sections():
            print 'ERROR: Server name not found.'
            return
        return '{url:s}:{port:d}'.format(url=self.config[[servername, 'url']],
                                         port=self.config[[servername, 'port']])
    
    def list(self, servername=None):
        import json
        from urllib2 import urlopen, URLError, HTTPError
        try:
            res = urlopen('http://' + self.get_server(servername) + '/download')
            wn_list = json.loads(res.read())
        except URLError, e:
            print 'ERROR: Download failed ({:s})'.format(str(e))
            return
        except HTTPError, e:
            print 'ERROR: Download failed ({:s})'.format(str(e))
            return
        for entry in wn_list:
            print entry
    
    def search(self, query, servername=None):
        import json
        from urllib2 import urlopen, URLError, HTTPError
        try:
            query = query.replace(' ', '+')
            res = urlopen('http://' + self.get_server(servername) + '/search_notes?query=' + query)
            wn_list = json.loads(res.read())
        except URLError, e:
            print 'ERROR: Download failed ({:s})'.format(str(e))
            return
        except HTTPError, e:
            print 'ERROR: Download failed ({:s})'.format(str(e))
            return
        for entry in wn_list:
            print entry['index'], entry['title']

    def download(self, index, workdir, servername=None):
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
        server_url = 'http://{server:s}/download?index={index:s}'.format(server = self.get_server(servername), 
                                                                         index = index)
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
            
    def delete(self, index, servername=None):
        from urllib2 import urlopen, URLError
        from worknoteBookHelpers import parse_index
        index = parse_index(index)[0:2]
        if len(index) == 1:
            index = '{:d}'.format(index[0])
        elif len(index) == 2:
            index = '{:d}:{:d}'.format(index[0], index[1])
        server_url = 'http://{server:s}/delete?index={index:s}'.format(server = self.get_server(servername), 
                                                                       index = index)
        try:
            server = urlopen(server_url)
            response = server.read()
        except URLError, e:
            print 'ERROR: Delete failed ({:s})'.format(str(e))

    def upload(self, workdir, overwrite=False, servername=None, chapter=''):
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
        request_url = 'http://{:s}/upload'.format(self.get_server(servername))
        if not chapter == '':
            request_url += '?chapter={:s}'.format(chapter.replace(' ', '+'))
        request = Request(request_url, up_file)
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
            
    def add_server(self, servername, url, port):
        if servername == 'client_defaults':
            print 'ERROR: Server name not allowed.'
            return
        self.config[[servername, 'url']] = url
        self.config[[servername, 'port']] = port
        self.config.update_cfg_file()
    
    def set_default_server(self, servername):
        if servername == 'client_defaults':
            print 'ERROR: Server name not allowed.'
            return
        if not servername in self.config.get_sections():
            print 'ERROR: Server name not configured.'
            return
        self.config[['client_defaults', 'server']] = servername
        self.config.update_cfg_file()
