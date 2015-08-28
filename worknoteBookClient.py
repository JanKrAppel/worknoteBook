# -*- coding: utf-8 -*-
"""
Created on Fri Aug 28 23:19:40 2015

@author: appel
"""

class worknoteBookClient(object):

    def __init__(self, server):
        self.server = server
    
    def list_worknotes(self):
        import json
        from urllib2 import urlopen
        res = urlopen('http://' + self.server + '/download')
        wn_list = json.loads(res.read())
        for index in wn_list:
            print '{index:s}: {wn_title:s}'.format(index=index, wn_title=wn_list[index])
    
    def download_worknote(self, index, filename = None):
        pass
