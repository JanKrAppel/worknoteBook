# -*- coding: utf-8 -*-
"""
Created on Fri Aug 28 23:18:40 2015

@author: appel
"""

import cherrypy

class worknoteBookServer(object):

    def __init__(self, storagedir):
        from os.path import abspath
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
        self.storagedir_locked = False

    @cherrypy.expose
    def reload_worknotes(self):
        from worknote import Worknote
        from os.path import isdir, join, exists
        from os import listdir
        self.storagedir_locked = True
        self.worknotes = {}
        self.worknote_list = []
        for wn_workdir in [name for name in listdir(self.storagedir)
            if isdir(join(self.storagedir, name))
            and exists(join(join(self.storagedir, name), 'notedata.worknote'))]:
                self.worknotes[wn_workdir] = Worknote(join(self.storagedir, wn_workdir))
                self.worknote_list.append([wn_workdir, self.worknotes[wn_workdir].metadata.metadata['title'], self.worknotes[wn_workdir].metadata.metadata['date']])
                self.worknotes[wn_workdir].build('HTML')
                self.worknotes[wn_workdir].build('Beamer')
        self.storagedir_locked = False
        head = self.head.format(metadata='<meta http-equiv="refresh" content="5; url=./">')
        foot = self.foot.format()
        return '{head:s}<p>Rebuilding worknote list, redirecting in 5 seconds...</p>{foot:s}'.format(head=head, foot=foot)

    @cherrypy.expose
    def index(self):
        head = self.head.format(metadata='<title>Workbook</title>\n')
        foot = self.foot.format()
        if self.storagedir_locked:
            return head + 'The server is currently busy, please reload the site in a bit...' + foot
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
        wn_wrapper = '<li><a href="{wn_dir:s}/Report.html">{wn_title:s}</a> ({wn_date:s}) <a href="{dl_link:s}">Download</a> <a href="{wn_dir:s}/Beamer.pdf" target="_blank">Download PDF</a></li>\n'
        wn_list = ''
        for index, entry in enumerate(self.worknote_list):
            wn_workdir, title, date = entry            
            if '\\today' in date:
                from datetime import datetime
                now = datetime.now()
                date = '{day:d}.{month:d}. {year:d}'.format(day=now.day,
                                                            month=now.month,
                                                            year=now.year)
            wn_list += wn_wrapper.format(wn_dir=wn_workdir,
                                         wn_title=title,
                                         wn_date=date,
                                         dl_link='./download?index={index:d}'.format(index=index+1)) 
        return frame.format(head=head, foot=foot, wn_list=wn_list)
        
    @cherrypy.expose
    def download(self, index=None):
        if not index is None:
            from tempfile import gettempdir
            from os.path import join, exists
            from cherrypy.lib.static import serve_download
            from worknoteBookHelpers import parse_index, zip_worknote
            try:
                index = parse_index(index)[0] - 1
            except ValueError, e:
                return str(e)
            if index < 0 or index > len(self.worknote_list) - 1:
                return 'Index out of range'
            wn_dir, wn_title, wn_date = self.worknote_list[index]
            tmpdir = gettempdir()
            fn_wnzip = '{wn_title:s}.zip'.format(wn_title=wn_title)
            dl_filepath = join(tmpdir, fn_wnzip)
            zip_worknote(join(self.storagedir, wn_dir), dl_filepath)
            if exists(dl_filepath):
                return serve_download(dl_filepath, name=fn_wnzip)    
            else:
                return 'Error creating ZIP archive for download'
        else:
            import json
            res = {}
            for index, wn in enumerate(self.worknote_list):
                res[index + 1] = wn[1]
            return json.dumps(res)

    @cherrypy.config(**{'response.timeout': 3600})
    @cherrypy.expose
    def upload(self):
        from tempfile import gettempdir
        from shutil import copyfileobj, rmtree
        from os.path import join, split, exists
        from zipfile import ZipFile
        from worknoteBookHelpers import unzip_worknote
        dst_file = join(gettempdir(), 'worknoteBook_upload.zip')   
        with open(dst_file, 'wb') as outfile:
            copyfileobj(cherrypy.request.body, outfile)
        if 'X-Worknote-Workdir' in cherrypy.request.headers:
            wn_dir = cherrypy.request.headers['X-Worknote-Workdir']
        else:
            zipfile = ZipFile(dst_file, 'r')
            wn_dir = split(zipfile.namelist()[0])[0]
            zipfile.close()
        if 'X-Worknote-Overwrite' in cherrypy.request.headers:
            overwrite = cherrypy.request.headers['X-Worknote-Overwrite'] == 'True'
            if  overwrite:
                if exists(join(self.storagedir, wn_dir)):
                    rmtree(join(self.storagedir, wn_dir))
        try:
            unzip_worknote(dst_file, join(self.storagedir, wn_dir))
        except OSError, e:
            return 'Fail (' + str(e) + ')'
        else:
            self.reload_worknotes()
            return 'Success'