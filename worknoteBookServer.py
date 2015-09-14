# -*- coding: utf-8 -*-
"""
Created on Fri Aug 28 23:18:40 2015

@author: appel
"""
import cherrypy
from worknoteBookServer_AuthModule import AuthController, require, member_of, name_is

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
        
    def __init__(self, config='~/.worknoteBook/server.cfg'):
        print_enter('worknoteBookServer.__init__')
        from whoosh.index import create_in
        from whoosh.fields import *
        from os.path import exists, join, split
        from os import makedirs
        import worknoteBookHelpers
        if type(config) == str:
            from os.path import expanduser
            from worknoteBookHelpers import Configuration
            cfg_file = config
            if not exists(split(expanduser(cfg_file))[0]):
                makedirs(split(expanduser(cfg_file))[0])
            default_cfg = {'server': {'storagedir': '~/.worknoteBook/storage',
                                      'user_db': '~/.worknoteBook/users.dat',
                                      'url': '0.0.0.0',
                                      'port': 8080}}
            config = Configuration(expanduser(cfg_file), default_cfg)
            if not exists(expanduser(cfg_file)):
                config.update_cfg_file()
        self.config = config
        self.storagedir = self.__getabsdir(self.config[['server', 'storagedir']])
        print 'Storagedir is "{:s}"'.format(self.storagedir)
        if not exists(self.storagedir):
            makedirs(self.storagedir)
        self.staticdir = join(split(worknoteBookHelpers.__file__)[0], 'static')
        self.worknote_list = []
        self.worknotes = {}
        print 'HTML static dir is "{:s}"'.format(self.staticdir)
        self.head = '''<!doctype html>
<html>
    <head>
        <meta charset="utf-8">
        <link rel="stylesheet" type="text/css" href="static/index.css">
        {metadata:s}
    </head>
    <body>'''
        self.foot = '''    </body>
</html>'''
        print 'Defining search index...'
        schema = Schema(index=ID(stored=True),
                        title=TEXT(stored=True),
                        date=TEXT(stored=True),
                        link=STORED,
                        content=TEXT)
        if not exists(join(self.storagedir, '.search_index')):
            makedirs(join(self.storagedir, '.search_index'))
        self.search_index = create_in(join(self.storagedir, '.search_index'), schema)
        print 'Loading chapters...'
        self.__load_chapters()
        print 'Reloading worknotes...'
        self.__reload_worknotes()
        print 'Updating CherryPy config...'
        self.__update_config()
        self.auth = AuthController(self.__getabsdir(self.config[['server', 'user_db']]),
                                   self.head,
                                   self.foot,
                                   self.staticdir)
    
    def __update_config(self):
        print_enter('worknoteBookServer.__update_config')
        print 'Server parameters:'
        print '\turl: {:s}'.format(self.config[['server', 'url']])
        print '\tport: {:d}'.format(self.config[['server', 'port']])
        cherrypy.config.update({'server.socket_host': self.config[['server', 'url']],
                                'server.socket_port': self.config[['server', 'port']],
                                'tools.sessions.on': True,
                                'tools.auth.on': True})
        print 'Mounting "{:s}" to /storage ...'.format(self.storagedir)
        cherrypy.tree.mount(StaticDir(), '/storage', config = {'/': {
                    'tools.staticdir.on': True,
                    'tools.staticdir.root': self.storagedir,
                    'tools.staticdir.dir': '.'
                }})
        print 'Mounting "{:s}" to /static ...'.format(self.staticdir)
        cherrypy.tree.mount(StaticDir(), '/static', config = {'/': {
                    'tools.staticdir.on': True,
                    'tools.staticdir.root': self.staticdir,
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
        print_enter('worknoteBookServer.__load_chapters')
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
        self.__reload_worknotes()
        raise cherrypy.HTTPRedirect('/')
        
    def __reload_worknotes(self):
        print_enter('worknoteBookServer.__reload_worknotes')
        print 'Locking storage dir...'
        self.storagedir_locked = True
        print 'Processing default storage directory...'
        self.worknote_list = []
        self.worknotes = {}
        self.__build_worknote_list(self.storagedir,
                                   self.worknote_list,
                                   self.worknotes)
        for chapter in self.chapter_list:
            print 'Processing chapter "{:s}"...'.format(chapter)
            self.chapters[chapter]['worknote_list'] = []
            self.chapters[chapter]['worknotes'] = {}
            self.__build_worknote_list(self.chapters[chapter]['chapter_dir'],
                                       self.chapters[chapter]['worknote_list'],
                                       self.chapters[chapter]['worknotes'])
        self.__build_search_index()
        print 'Unlocking storage dir...'
        self.storagedir_locked = False

    def __build_worknote_list(self, directory, worknote_list, worknotes):
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
                worknote_list.append([wn_workdir, 
                                      worknotes[wn_workdir].metadata.metadata['title'],
                                      worknotes[wn_workdir].metadata.metadata['date']])
                print '\tTitle:', worknotes[wn_workdir].metadata.metadata['title']
                print '\tBuilding HTML...'
                worknotes[wn_workdir].build('HTML')
                print '\tBuilding Beamer PDF...'
                worknotes[wn_workdir].build('Beamer')
                
    def __build_search_index(self):
        print_enter('worknoteBookServer.__build_search_index')
        from os.path import join
        from worknoteBookHelpers import gen_index
        from whoosh.index import create_in
        self.search_index = create_in(join(self.storagedir, '.search_index'),
                                      self.search_index.schema)
        writer = self.search_index.writer()
        print 'Processing default storage directory...'
        for index, wn in enumerate(self.worknote_list):
            wn_workdir, title, date = wn
            link = u'./storage/{:s}'.format(wn_workdir)
            writer.add_document(index = gen_index(index + 1),
                                title = title,
                                link = link,
                                date = date,
                                content = self.worknotes[wn_workdir].get_text('Markdown'))
        print 'Processing chapters...'
        for chapter_index, chapter in enumerate(self.chapter_list):
            for wn_index, wn in enumerate(self.chapters[chapter]['worknote_list']):
                wn_workdir, title, date = wn
                link = u'./{:s}/{:s}'.format(chapter, wn_workdir)
                writer.add_document(index = gen_index([chapter_index + len(self.worknote_list) + 1,
                                                       wn_index + 1]),
                                    title = title,
                                    link = link,
                                    date = date,
                                    content = self.chapters[chapter]['worknotes'][wn_workdir].get_text('Markdown'))
        writer.commit()

    @cherrypy.expose
    def index(self):
        print_enter('worknoteBookServer.index')
        head = self.head.format(metadata='<title>worknoteBook</title>\n')
        foot = self.foot.format()
        if self.storagedir_locked:
            return head + 'The server is currently busy, please reload the site in a bit...' + foot
        frame = '''{head:s}
    <header>
        <p>
            <form method="get" action="search">
                   <input type="text" name="query" />
                   <button type="submit">Search</button>
            </form>
            <p>{logininfo:s}</p>
            <p><a href="./reload_worknotes"><img src="static/reload.png" alt="">Reload worknotes</a></p>
        </p>
    </header>
    <main>
        <article>
        <ol>
        {wn_list:s}
        </ol>
        </article>
    </main>
{foot:s}'''
        wn_wrapper = '<li><a href="{storagedir:s}/{wn_dir:s}/Report.html">{wn_title:s}</a> ({wn_date:s}) <a href="{dl_link:s}" title="Download"><img src="static/download.png" alt="Download"></a> <a href="{storagedir:s}/{wn_dir:s}/Beamer.pdf" target="_blank" title="Download PDF"><img src="static/pdf.png" alt="Download PDF"></a> <a href="{rm_link:s}" title="Delete"><img src="static/delete.png" alt="Delete"></a></li>\n'
        if self.auth.logged_in is None:
            logininfo = '<a href="auth/login"><img src="static/login.png" alt="Log in">Log in</a>'
        else:
            logininfo = 'Logged in as: {username:s}<a href="auth/logout"><img src="static/logout.png" alt="Log out">Log out</a>'.format(username=self.auth.logged_in)
        print 'Building worknote list...'
        wn_list = ''
        print 'Default storage dir...'
        for index, entry in enumerate(self.worknote_list):
            wn_workdir, title, date = entry           
            print 'Worknote:', wn_workdir
            if '\\today' in date:
                from datetime import datetime
                from os.path import getmtime, join
                time = datetime.fromtimestamp(getmtime(join(join(self.storagedir, wn_workdir), 'notedata.worknote')))
                date = '{day:d}.{month:d}. {year:d}'.format(day=time.day,
                                                            month=time.month,
                                                            year=time.year)
            wn_list += wn_wrapper.format(wn_dir=wn_workdir,
                                         wn_title=title,
                                         wn_date=date,
                                         dl_link='./download?index={index:d}'.format(index=index+1),
                                         rm_link='./delete?index={index:d}'.format(index=index+1),
                                         storagedir = './storage') 
        index = len(self.worknote_list)
        for chapter in self.chapter_list:
            print 'Chapter:', chapter
            wn_list += '<li><b>{:s}</b></br></li>\n'.format(chapter)
            wn_list += '<ol>\n'
            print index
            for subindex, entry in enumerate(self.chapters[chapter]['worknote_list']):
                wn_workdir, title, date = entry            
                print 'Worknote:', wn_workdir
                if '\\today' in date:
                    from datetime import datetime
                    from os.path import getmtime, join
                    time = datetime.fromtimestamp(getmtime(join(join(self.chapters[chapter]['chapter_dir'], wn_workdir), 'notedata.worknote')))
                    date = '{day:d}.{month:d}. {year:d}'.format(day=time.day,
                                                                month=time.month,
                                                                year=time.year)
                wn_list += wn_wrapper.format(wn_dir=wn_workdir,
                                             wn_title=title,
                                             wn_date=date,
                                             dl_link='./download?index={index:d}:{subindex:d}'.format(index=index+1, 
                                                                                                      subindex=subindex+1),
                                             rm_link='./delete?index={index:d}:{subindex:d}'.format(index=index+1, 
                                                                                                    subindex=subindex+1),
                                             storagedir='./{:s}'.format(self.chapters[chapter]['link_name']))
            index += 1
            wn_list += '</ol>\n'
        return frame.format(head=head, foot=foot, wn_list=wn_list, logininfo=logininfo)
        
    @cherrypy.expose
    def download(self, index=None):
        print_enter('worknoteBookServer.download')
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
            print 'Default storage dir...'
            for index, wn in enumerate(self.worknote_list):
                res.append(str(index + 1) + ') ' + wn[1])
            index = len(self.worknote_list)
            for chapter_index, chapter in enumerate(self.chapter_list):
                print 'Chapter "{:s}"...'.format(chapter)
                res.append('Chapter ' + chapter + ':')
                for subindex, wn in enumerate(self.chapters[chapter]['worknote_list']):
                    res.append(str(index + chapter_index + 1) + ':' + str(subindex + 1) + ') ' + wn[1])
                index += 1
            print 'Dumping JSON object...'
            return json.dumps(res)
            
    @cherrypy.expose
    @require()
    def delete(self, index):
        print_enter('worknoteBookServer.delete')
        print cherrypy.request.headers
        from worknoteBookHelpers import parse_index
        from shutil import rmtree
        from os.path import join
        print 'Index:', index
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
            wn_workdir, title, date = self.worknote_list[index]
            print 'Removing "{:s}" from storage directory...'.format(wn_workdir)
            rmtree(join(self.storagedir, wn_workdir))
            self.worknote_list.pop(index)
            self.worknotes.pop(wn_workdir)
        elif len(index) == 2:
            chapter_index, index = index
            chapter_index -= len(self.worknote_list)
            if chapter_index < 0 or chapter_index > len(self.chapter_list) - 1:
                return 'Index out of range'
            chapter = self.chapter_list[chapter_index]
            if index < 0 or index > len(self.chapters[chapter]['worknote_list']) - 1:
                return 'Index out of range'
            wn_workdir, title, date = self.chapters[chapter]['worknote_list'][index]
            print 'Removing "{:s}" from "{:s}"...'.format(wn_workdir, self.chapters[chapter]['chapter_dir'])
            rmtree(join(self.chapters[chapter]['chapter_dir'], wn_workdir))
            self.chapters[chapter]['worknote_list'].pop(index)
            self.chapters[chapter]['worknotes'].pop(wn_workdir)
        self.reload_worknotes()
        return 'Success'

    def __serve_wn(self, wn, storagedir):
        print_enter('worknoteBookServer.__serve_wn')
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
    @require()
    def upload(self, chapter=''):
        print_enter('worknoteBookServer.upload')
        print cherrypy.request.headers
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
    def search_notes(self, query=''):
        print_enter('worknoteBookServer.search_notes')
        from whoosh.qparser import QueryParser
        import json
        print 'Buidling parser...'
        parser = QueryParser("content", self.search_index.schema)
        print 'Building query...'
        query = parser.parse(unicode(query))
        print 'Searching...'
        res = []
        with self.search_index.searcher() as searcher:
            results = searcher.search(query)
            print 'Found {:d} results'.format(len(results))
            for result in results:
                res_entry = {}
                for entry in result:
                    res_entry[entry] = result[entry]
                res.append(res_entry)
        return json.dumps(res)
        
    @cherrypy.expose            
    def search(self, query=''):
        print_enter('worknoteBookServer.search')
        import json
        print 'Performing query...'
        res = json.loads(self.search_notes(query))
        print 'Got {:d} results'.format(len(res))
        head = self.head.format(metadata='<title>worknoteBook - Search results</title>\n')
        foot = self.foot.format()
        frame = '''{head:s}
    <main>
        <header>
            <b>Search results for "{searchstring:s}"</b>
        </header>
        <article>
        <ul>
        {link_list:s}
        </ul>
        </article>
    </main>
{foot:s}'''
        link_wrapper = '<li><b>{index:s}</b> <a href="{link:s}/Report.html">{title:s}</a> <a href="./download?index={index:s}" title="Download"><img src="static/download.png" alt="Download"></a> <a href="{link:s}/Beamer.pdf" target="_blank" title="Download PDF"><img src="static/pdf.png" alt="Download PDF"></a> <a href="./delete?index={index:s}" title="Delete"><img src="static/delete.png" alt="Delete"></a></li>\n'
        print 'Building link list...'
        link_list = ''
        for result in res:
            link_list += link_wrapper.format(index=result[u'index'],
                                             title=result[u'title'],
                                             link=result[u'link'],
                                             date=result[u'date'])
        return frame.format(searchstring=query, head=head, foot=foot, link_list=link_list)
            
