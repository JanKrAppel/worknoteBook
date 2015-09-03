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

    def __init__(self, server_url, server_port):
        self.server = '{url:s}:{port:d}'.format(url=server_url, port=server_port)
    
    def list(self):
        import json
        from urllib2 import urlopen
        res = urlopen('http://' + self.server + '/download')
        wn_list = json.loads(res.read())
        for index in wn_list:
            print '{index:s}: {wn_title:s}'.format(index=index, wn_title=wn_list[index])
    
    def download(self, index, workdir):
        from worknoteBookHelpers import unzip_worknote
        from urllib2 import urlopen, URLError
        from tempfile import gettempdir
        from os.path import join
        from worknoteBookHelpers import parse_index
        index = parse_index(index)[0]
        tmpfn = join(gettempdir(), 'worknoteBook_download.zip')
        server_url = 'http://{server:s}/download?index={index:d}'.format(server = self.server, index = index)
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
            
    def upload(self, workdir, overwrite = False):
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
        request = Request('http://{:s}/upload'.format(self.server), up_file)
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
        