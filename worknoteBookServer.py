# -*- coding: utf-8 -*-
"""
Created on Fri Aug 28 23:18:40 2015

@author: appel
"""

import cherrypy

class StaticDir(object):
    def __init__(self):
        pass
        
def print_enter(name):
    print '-'*len(name)
    print name
    print '-'*len(name)

class worknoteBookServer(object):
    
    def __getabsdir(self, dirname):
        from os.path import abspath, expanduser, expandvars
        return abspath(expandvars(expanduser(dirname)))
        
    def __init__(self, config):
        print_enter('__init__')
        from whoosh.index import create_in
        from whoosh.fields import *
        from os.path import exists, join
        from os import makedirs
        self.config = config
        self.storagedir = self.__getabsdir(self.config[['server', 'storagedir']])
        print 'Storagedir is "{:s}"'.format(self.storagedir)
        self.head = '''<!doctype html>
<html>
    <head>
        <meta charset="utf-8"> 
        {metadata:s}
    </head>
    <body style="font-family: sans-serif">'''
        self.foot = '''    </body>
</html>'''
        schema = Schema(title=TEXT(stored=True), path=ID(stored=True), content=TEXT(stored=True))
        if not exists(join(self.storagedir, 'index')):
            makedirs(join(self.storagedir, 'index'))
        self.index = create_in(join(self.storagedir, 'index'), schema)
        print 'Loading chapters...'
        self.__load_chapters()
        print 'Reloading worknotes...'
        self.reload_worknotes()
        print 'Updating CherryPy config...'
        self.__update_config()
    
    def __update_config(self):
        print_enter('__update_config')
        print 'Server parameters:'
        print '\turl: {:s}'.format(self.config[['server', 'url']])
        print '\tport: {:d}'.format(self.config[['server', 'port']])
        cherrypy.config.update({'server.socket_host': self.config[['server', 'url']],
                                'server.socket_port': self.config[['server', 'port']]})
        print 'Mounting "{:s}" to /storage ...'.format(self.storagedir)
        cherrypy.tree.mount(StaticDir(), '/storage', config = {'/': {
                    'tools.staticdir.on': True,
                    'tools.staticdir.root': self.storagedir,
                    'tools.staticdir.dir': '.'
                }})
        for chapter in self.chapters:
            print 'Mounting "{:s}" to /{:s} ...'.format(self.chapters[chapter]['chapter_dir'],
                                                         self.chapters[chapter]['link_name'])
            cherrypy.tree.mount(StaticDir(), '/{:s}'.format(self.chapters[chapter]['link_name']),
                                config = {'/': {'tools.staticdir.on': True,
                                                'tools.staticdir.root': self.chapters[chapter]['chapter_dir'],
                                                'tools.staticdir.dir': '.'
                                                }})
                
    def __load_chapters(self):
        print_enter('__load_chapters')
        self.chapters = {}
        self.chapter_list = []
        chapters = self.config.get_sections()
        chapters.remove('server')
        print 'Chapters:', chapters
        for chapter in chapters:
            chapter_dir = self.__getabsdir(self.config[[chapter, 'chapter_dir']])
            link_name = chapter.replace(' ', '_')
            self.chapters[chapter] = {}
            self.chapters[chapter]['chapter_dir'] = chapter_dir
            self.chapters[chapter]['link_name'] = link_name
            self.chapters[chapter]['worknote_list'] = []
            self.chapters[chapter]['worknotes'] = {}
            self.chapter_list.append(chapter)

    @cherrypy.expose
    def reload_worknotes(self):
        print_enter('reload_worknotes')
        print 'Locking storage dir...'
        self.storagedir_locked = True
        self.worknotes = {}
        self.worknote_list = []
        print 'Processing default storage directory...'
        self.__build_worknote_list(self.storagedir,
                                   self.worknote_list,
                                   self.worknotes,
                                   self.index.writer())
        for chapter in self.chapters:
            print 'Processing chapter "{:s}"...'.format(chapter)
            self.__build_worknote_list(self.chapters[chapter]['chapter_dir'],
                                       self.chapters[chapter]['worknote_list'],
                                       self.chapters[chapter]['worknotes'],
                                       self.index.writer())
        print 'Unlocking storage dir...'
        self.storagedir_locked = False
        head = self.head.format(metadata='<meta http-equiv="refresh" content="5; url=./">')
        foot = self.foot.format()
        return '{head:s}<p>Rebuilding worknote list, redirecting in 5 seconds...</p>{foot:s}'.format(head=head, foot=foot)
        
    def __build_worknote_list(self, directory, worknote_list, worknotes, index_writer):
        from worknote import Worknote
        from os.path import isdir, join, exists
        from os import listdir
        print 'Processing directory "{:s}"...'.format(directory)
        for wn_workdir in [name for name in listdir(directory)
            if isdir(join(directory, name))
            and exists(join(join(directory, name), 'notedata.worknote'))]:
                print 'Worknote:', wn_workdir
                worknotes[wn_workdir] = Worknote(join(directory, wn_workdir))
                title = worknotes[wn_workdir].metadata.metadata['title']
                path = join(directory, wn_workdir)
                worknote_list.append([wn_workdir, worknotes[wn_workdir].metadata.metadata['title'], worknotes[wn_workdir].metadata.metadata['date']])
                print '\tTitle:', worknotes[wn_workdir].metadata.metadata['title']
                print '\tBuilding HTML...'
                worknotes[wn_workdir].build('HTML')
                print '\tBuilding Beamer PDF...'
                worknotes[wn_workdir].build('Beamer')
                index_writer.add_document(title=title, path=path, content=worknotes[wn_workdir].get_text('Markdown'))
        index_writer.commit()

    @cherrypy.expose
    def index(self):
        print_enter('index')
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
        wn_wrapper = '<li><a href="storage/{wn_dir:s}/Report.html">{wn_title:s}</a> ({wn_date:s}) <a href="{dl_link:s}">Download</a> <a href="storage/{wn_dir:s}/Beamer.pdf" target="_blank">Download PDF</a></li>\n'
        print 'Building worknote list...'
        wn_list = ''
        index = 0
        print 'Default storage dir...'
        for index, entry in enumerate(self.worknote_list):
            wn_workdir, title, date = entry           
            print 'Worknote:', wn_workdir
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
        for chapter in self.chapters:
            print 'Chapter:', chapter
            wn_list += '<li><b>{:s}</b></br></li>\n'.format(chapter)
            wn_list += '<ol>\n'
            index += 1
            for subindex, entry in enumerate(self.chapters[chapter]['worknote_list']):
                wn_workdir, title, date = entry            
                print 'Worknote:', wn_workdir
                if '\\today' in date:
                    from datetime import datetime
                    now = datetime.now()
                    date = '{day:d}.{month:d}. {year:d}'.format(day=now.day,
                                                                month=now.month,
                                                                year=now.year)
                wn_list += wn_wrapper.format(wn_dir=wn_workdir,
                                             wn_title=title,
                                             wn_date=date,
                                             dl_link='./download?index={index:d}:{subindex:d}'.format(index=index+1, subindex=subindex+1)) 
            wn_list += '</ol>\n'
        return frame.format(head=head, foot=foot, wn_list=wn_list)
        
    @cherrypy.expose
    def download(self, index=None):
        print_enter('download')
        if not index is None:
            print 'Index:', index
            from worknoteBookHelpers import parse_index
            try:
                index = parse_index(index)
                if len(index) == 1:
                    index = [index[0] - 1]
                elif len(index) == 2:
                    index = [index[0] - 1, index[1] - 1]
                else:
                    raise ValueError('Too many indices')
            except ValueError, e:
                return str(e)
            print 'Parsed index:', index
            if len(index) == 1:
                index = index[0]
                if index < 0 or index > len(self.worknote_list) - 1:
                    return 'Index out of range'
                return self.__serve_wn(self.worknote_list[index], self.storagedir)
            elif len(index) == 2:
                chapter_index, index = index
                chapter_index -= len(self.worknote_list)
                if chapter_index < 0 or chapter_index > len(self.chapter_list) - 1:
                    return 'Index out of range'
                chapter = self.chapter_list[chapter_index]
                if index < 0 or index > len(self.chapters[chapter]['worknote_list']) - 1:
                    return 'Index out of range'
                return self.__serve_wn(self.chapters[chapter]['worknote_list'][index],
                                       self.chapters[chapter]['chapter_dir'])                
        else:
            print 'No index, returning worknote list...'
            import json
            res = []
            for index, wn in enumerate(self.worknote_list):
                res.append(str(index + 1) + ' ' + wn[1])
            for chapter_index, chapter in enumerate(self.chapter_list):
                res.append(str(index + chapter_index + len(self.worknote_list) + 1) + ' ' + chapter)
                for subindex, wn in enumerate(self.chapters[chapter]['worknote_list']):
                    res.append(str(index + chapter_index + len(self.worknote_list) + 1) + ':' + str(subindex + 1) + ' ' + wn[1])
            return json.dumps(res)
            
    def __serve_wn(self, wn, storagedir):
        print_enter('__serve_wn')
        from tempfile import gettempdir
        from os.path import join, exists
        from cherrypy.lib.static import serve_download
        from worknoteBookHelpers import zip_worknote
        wn_dir, wn_title, wn_date = wn
        print 'Preparing to serve "{:s}" from "{:s}"...'.format(wn_dir, storagedir)
        tmpdir = gettempdir()
        fn_wnzip = '{wn_title:s}.zip'.format(wn_title=wn_title)
        dl_filepath = join(tmpdir, fn_wnzip)
        print 'Zipping worknote...'
        zip_worknote(join(storagedir, wn_dir), dl_filepath)
        if exists(dl_filepath):
            print 'Serving file "{:s}"...'.format(dl_filepath)
            return serve_download(dl_filepath, name=fn_wnzip)    
        else:
            print 'ERROR: Zip file not created'
            return 'Error creating ZIP archive for download'
        

    @cherrypy.config(**{'response.timeout': 3600})
    @cherrypy.expose
    def upload(self, chapter=''):
        print_enter('upload')
        from tempfile import gettempdir
        from shutil import copyfileobj, rmtree
        from os.path import join, split, exists
        from zipfile import ZipFile
        from worknoteBookHelpers import unzip_worknote
        print 'Receiving file...'
        dst_file = join(gettempdir(), 'worknoteBook_upload.zip')   
        with open(dst_file, 'wb') as outfile:
            copyfileobj(cherrypy.request.body, outfile)
        if 'X-Worknote-Workdir' in cherrypy.request.headers:
            wn_dir = cherrypy.request.headers['X-Worknote-Workdir']
            print 'Header set worknote directory: "{:s}"'.format(wn_dir)
        else:
            zipfile = ZipFile(dst_file, 'r')
            wn_dir = split(zipfile.namelist()[0])[0]
            zipfile.close()
            print 'File set worknote directory: "{:s}"'.format(wn_dir)
        if chapter == '':
            print 'Upload to default storage dir...'
            storagedir = self.storagedir
        else:
            print 'Upload to chapter "{:s}"...'.format(chapter)
            if not chapter in self.chapters:
                print 'ERROR: Chapter not found'
                return 'Fail (Chapter {:s} not found)'.format(chapter)
            storagedir = self.chapters[chapter]['chapter_dir']
            print '\tStorage dir: "{:s}"'.format(storagedir)
        if 'X-Worknote-Overwrite' in cherrypy.request.headers:
            overwrite = cherrypy.request.headers['X-Worknote-Overwrite'] == 'True'
            print 'Overwrite set in header, emptying directory "{:s}"...'.format(join(storagedir, wn_dir))
            if  overwrite:
                if exists(join(storagedir, wn_dir)):
                    rmtree(join(storagedir, wn_dir))
        try:
            print 'Unzipping worknote...'
            unzip_worknote(dst_file, join(storagedir, wn_dir))
        except OSError, e:
            print 'ERROR: Unzip failed'
            return 'Fail (' + str(e) + ')'
        else:
            self.reload_worknotes()
            print 'Upload done'
            return 'Success'
    
    @cherrypy.expose            
    def search(self, string=''):
        from whoosh.qparser import QueryParser
        parser = QueryParser("content", self.index.schema)
        query = parser.parse(string)
        with self.index.searcher() as searcher:
            res = searcher.search(query)
        return res
