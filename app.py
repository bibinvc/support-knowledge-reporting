from pathlib import Path
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit,parse_qs
import argparse,json,sqlite3,threading

ROOT=Path(__file__).resolve().parent
STATUSES=('Open','In progress','Resolved','Closed')

@contextmanager
def connect(path):
    connection=sqlite3.connect(path)
    connection.row_factory=sqlite3.Row
    try:
        with connection:
            yield connection
    finally:
        connection.close()

def initialise(path):
    with connect(path) as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS tickets(id TEXT PRIMARY KEY,status TEXT NOT NULL CHECK(status IN ('Open','In progress','Resolved','Closed')),priority TEXT NOT NULL CHECK(priority IN ('High','Normal','Low')));
        CREATE TABLE IF NOT EXISTS articles(id TEXT PRIMARY KEY,title TEXT NOT NULL,category TEXT NOT NULL,body TEXT NOT NULL);
        """)
        db.executemany('INSERT OR IGNORE INTO tickets VALUES(?,?,?)',[(f'LAB-{n}',state,priority) for n,state,priority in [(1,'Open','High'),(2,'Open','Normal'),(3,'In progress','High'),(4,'Resolved','Normal'),(5,'Resolved','Low'),(6,'Closed','Normal')]])
        db.executemany('INSERT OR IGNORE INTO articles VALUES(?,?,?,?)',[
            ('KB-001','Record a network issue','Network','Record the time, error and affected users. Check the known local connection. Share findings with the authorised network engineer.'),
            ('KB-002','Document an application issue','Applications','Record the application, version and reproducible steps. Keep screenshots free of personal data. Document the resolution or escalation.'),
            ('KB-003','Protect account access','Identity','Never collect passwords. Follow the approved identity-verification procedure. Escalate unexpected access requests to the responsible team.')])

def report(path):
    with connect(path) as db:
        counts=dict(db.execute('SELECT status,COUNT(*) FROM tickets GROUP BY status'))
    rows=[{'status':status,'count':counts.get(status,0)} for status in STATUSES]
    return {'schema_version':1,'synthetic':True,'total':sum(row['count'] for row in rows),'rows':rows}

def articles(path,query=''):
    if not isinstance(query,str) or len(query)>100: raise ValueError('Search must be at most 100 characters')
    literal=query.replace('\\','\\\\').replace('%','\\%').replace('_','\\_')
    with connect(path) as db:
        rows=db.execute("SELECT * FROM articles WHERE title LIKE ? ESCAPE '\\' OR body LIKE ? ESCAPE '\\' ORDER BY id",('%'+literal+'%','%'+literal+'%')).fetchall()
    return [dict(row) for row in rows]

@contextmanager
def server(path,port=0,override=None):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.headers.get('Host')!=f'127.0.0.1:{self.server.server_port}': self.send_error(403); return
            parsed=urlsplit(self.path)
            try:
                if parsed.path=='/api/report': data=override if override is not None else report(path)
                elif parsed.path=='/api/kb': data={'synthetic':True,'articles':articles(path,parse_qs(parsed.query).get('q',[''])[0])}
                elif parsed.path=='/redirect':
                    self.send_response(302); self.send_header('Location','https://example.invalid/'); self.end_headers(); return
                elif parsed.path=='/':
                    content=(ROOT/'web/index.html').read_bytes(); self.reply(content,'text/html; charset=utf-8'); return
                else: self.send_error(404); return
                self.reply(json.dumps(data).encode(),'application/json')
            except ValueError as error: self.reply(json.dumps({'error':str(error)}).encode(),'application/json',400)
        def reply(self,body,kind,status=200):
            self.send_response(status); self.send_header('Content-Type',kind); self.send_header('Content-Length',str(len(body)))
            self.send_header('X-Content-Type-Options','nosniff'); self.end_headers(); self.wfile.write(body)
        def log_message(self,*args): pass
    http=ThreadingHTTPServer(('127.0.0.1',port),Handler)
    worker=threading.Thread(target=http.serve_forever,daemon=True); worker.start()
    try: yield f'http://127.0.0.1:{http.server_port}'
    finally: http.shutdown(); http.server_close(); worker.join(timeout=3)

if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--port',type=int,default=9880); options=parser.parse_args()
    (ROOT/'data').mkdir(exist_ok=True); database=ROOT/'data/demo.sqlite3'; initialise(database)
    with server(database,options.port) as url:
        print('Synthetic local helpdesk demo: '+url,flush=True)
        try: threading.Event().wait()
        except KeyboardInterrupt: pass
