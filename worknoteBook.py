#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Created on Thu Aug 27 20:41:07 2015

@author: appel
"""

import cherrypy

class worknoteBookServer(object):

    def __init__(self, storagedir):
        self.storagedir = abspath(storagedir)
        self.head = '''<!doctype html>
<html>
    <head>
        <meta charset="utf-8"> 
        {metadata:s}
    </head>
    <body style="font-family: sans-serif">'''
        self.foot = '''    </body>
</html>'''
        self.reload_worknotes()

    @cherrypy.expose
    def reload_worknotes(self):
        from worknote import Worknote
        from os.path import abspath, isdir, join, exists
        from os import listdir
        self.worknotes = {}
        self.worknote_list = []
        for wn_workdir in [name for name in listdir(self.storagedir)
            if isdir(join(self.storagedir, name))
            and exists(join(join(self.storagedir, name), 'notedata.worknote'))]:
                    self.worknotes[wn_workdir] = Worknote(join(self.storagedir, wn_workdir))
                    self.worknote_list.append([wn_workdir, self.worknotes[wn_workdir].metadata.metadata['title']])
                    self.worknotes[wn_workdir].build('HTML')
        head = self.head.format(metadata='<meta http-equiv="refresh" content="5; url=./">')
        foot = self.foot.format()
        return '{head:s}<p>Rebuilding worknote list...</p>{foot:s}'.format(head=head, foot=foot)

    @cherrypy.expose
    def index(self):
        head = self.head.format(metadata='<title>Workbook</title>\n')
        foot = self.foot.format()
        frame = '''{head:s}
    <header>
        <p><a href="./reload_worknotes">Reload worknotes</a></p>
    </header>
    <main>
        <article>
        <ol>
        {wn_list:s}
        </ol>
        </article>
    </main>
{foot:s}'''
        wn_wrapper = '<li><a href="{wn_dir:s}/Report.html">{wn_title:s}</a></li>\n'
        wn_list = ''
        for wn_workdir, title in self.worknote_list:
            wn_list += wn_wrapper.format(wn_dir=wn_workdir, wn_title=title) 
        return frame.format(head=head, foot=foot, wn_list=wn_list)
        
if __name__ == '__main__':
    from sys import argv
    from os.path import abspath
    if argv[1].lower() == 'server':
        conf = {
            '/': {
                'tools.staticdir.on': True,
                'tools.staticdir.root': abspath('../worknote/testbench'),
                'tools.staticdir.dir': '.'
            }
        }
        cherrypy.quickstart(worknoteBookServer('../worknote/testbench'), '/', conf)
    else:
        print 'not implemented yet'