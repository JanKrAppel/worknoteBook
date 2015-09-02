# -*- coding: utf-8 -*-
"""
Created on Fri Aug 28 23:19:40 2015

@author: appel
"""

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
    
    def download(self, index):
        from zipfile import ZipFile
        from urllib2 import urlopen
        from tempfile import gettempdir
        from os.path import join
        from worknoteBookHelpers import parse_index
        index = parse_index(index)
        tmpfn = join(gettempdir(), 'worknoteBook_download.zip')
        server_url = 'http://{server:s}/download?index={index:d}'.format(server = self.server, index = index)
        server = urlopen(server_url)
        with open(tmpfn, 'wb') as tmpfile:
            tmpfile.write(server.read())
        with ZipFile(tmpfn, 'r') as zipfile:
            zipfile.extractall('.')
