# -*- coding: utf-8 -*-
"""
Created on Thu Aug 27 20:41:07 2015

@author: appel
"""

from worknote import Worknote
import cherrypy
import os

class worknoteBook(object):

    def __init__(self, storagedir):
        self.storagedir = os.path.abspath(storagedir)
        self.worknotes = {}
        for wn_workdir in [name for name in os.listdir(storagedir)
            if os.path.isdir(os.path.join(storagedir, name))]:
                self.worknotes[wn_workdir] = Worknote(os.path.join(self.storagedir, wn_workdir))
                self.worknotes[wn_workdir].build('HTML')

    @cherrypy.expose
    def index(self):
        frame = '''<!doctype html>
<html>
    <head>
        <meta charset="utf-8"> 
    </head>
    <body style="font-family: sans-serif">
    <header>
        <h1>Worknotes in Workbook</h1>
    </header>
    <main>
        <article>
        <ul>
        {wn_list:s}
        </ul>
        </article>
    </main>
    </body>
</html>'''
        wn_wrapper = '<li><a href="{wn_dir:s}/Report.html">{wn_title:s}</a></li>\n'
        wn_list = ''
        for wn_workdir in self.worknotes:
            wn_list += wn_wrapper.format(wn_dir = wn_workdir, wn_title = self.worknotes[wn_workdir].metadata.metadata['title'])
        return frame.format(wn_list = wn_list)
        
if __name__ == '__main__':
     conf = {
         '/': {
             'tools.staticdir.on': True,
             'tools.staticdir.root': os.path.abspath('../worknote/testbench'),
             'tools.staticdir.dir': '.'
         }
     }
     cherrypy.quickstart(worknoteBook('../worknote/testbench'), '/', conf)