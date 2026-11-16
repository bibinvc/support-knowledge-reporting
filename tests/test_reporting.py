from pathlib import Path
import copy,csv,json,os,sqlite3,subprocess,tempfile,unittest
from urllib.request import Request,urlopen
from urllib.error import HTTPError
from app import connect,initialise,report,articles,server

class LabTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.root=Path(self.temp.name); self.db=self.root/'lab.sqlite3'; initialise(self.db)
    def tearDown(self): self.temp.cleanup()
    def tool(self,*args): return subprocess.run([os.environ['LAB_CS_BIN'],*map(str,args)],capture_output=True,text=True,timeout=8)
    def from_json(self,data):
        file=self.root/'input.json'; file.write_text(json.dumps(data),encoding='utf-8'); output=self.root/'output.csv'; output.write_text('unchanged',encoding='utf-8')
        result=self.tool('--input-json',file,output)
        return result,output
    def test_known_sql_counts(self):
        data=report(self.db); self.assertEqual(data['total'],6); self.assertEqual({row['status']:row['count'] for row in data['rows']},{'Open':2,'In progress':1,'Resolved':2,'Closed':1})
    def test_seed_idempotent(self):
        initialise(self.db); self.assertEqual(report(self.db)['total'],6); self.assertEqual(len(articles(self.db)),3)
    def test_database_status_constraint(self):
        with self.assertRaises(sqlite3.IntegrityError),connect(self.db) as db: db.execute("INSERT INTO tickets VALUES('BAD','unknown','High')")
        self.assertEqual(report(self.db)['total'],6)
    def test_empty_report_has_zero_counts(self):
        with connect(self.db) as db: db.execute('DELETE FROM tickets')
        data=report(self.db); self.assertEqual(data['total'],0); self.assertTrue(all(row['count']==0 for row in data['rows']))
    def test_case_insensitive_knowledge_search(self): self.assertEqual([row['id'] for row in articles(self.db,'NETWORK')],['KB-001'])
    def test_search_injection_is_literal(self): self.assertEqual(articles(self.db,"%' OR 1=1 --"),[])
    def test_wildcards_are_literal(self): self.assertEqual(articles(self.db,'%'),[]); self.assertEqual(articles(self.db,'_'),[])
    def test_search_bound(self):
        with self.assertRaises(ValueError): articles(self.db,'x'*101)
    def test_csharp_json_to_csv(self):
        result,output=self.from_json(report(self.db)); self.assertEqual(result.returncode,0,result.stderr)
        rows=list(csv.reader(output.read_text(encoding='utf-8').splitlines())); self.assertEqual(rows,[['status','count'],['Open','2'],['In progress','1'],['Resolved','2'],['Closed','1'],['Total','6']])
    def test_csharp_empty_report(self):
        data=report(self.db); data['total']=0
        for row in data['rows']: row['count']=0
        result,_=self.from_json(data); self.assertEqual(result.returncode,0,result.stderr)
    def test_csharp_rejects_live_marker(self):
        data=report(self.db); data['synthetic']=False; result,output=self.from_json(data)
        self.assertEqual(result.returncode,2); self.assertEqual(output.read_text(),'unchanged')
    def test_csharp_rejects_wrong_schema(self):
        data=report(self.db); data['schema_version']=2; result,_=self.from_json(data); self.assertEqual(result.returncode,2)
    def test_csharp_requires_fields(self):
        data=report(self.db); del data['synthetic']; result,_=self.from_json(data); self.assertEqual(result.returncode,2)
    def test_csharp_rejects_inconsistent_total(self):
        data=report(self.db); data['total']=7; result,_=self.from_json(data); self.assertEqual(result.returncode,2)
    def test_csharp_rejects_duplicate_states(self):
        data=report(self.db); data['rows'][1]['status']='Open'; result,_=self.from_json(data); self.assertEqual(result.returncode,2)
    def test_csharp_rejects_negative_count(self):
        data=report(self.db); data['rows'][0]['count']=-1; result,_=self.from_json(data); self.assertEqual(result.returncode,2)
    def test_csharp_rejects_csv_formula_status(self):
        data=report(self.db); data['rows'][0]['status']='=1+1'; result,_=self.from_json(data); self.assertEqual(result.returncode,2)
    def test_csharp_rejects_large_input(self):
        file=self.root/'large.json'; file.write_text(' '*9000); result=self.tool('--input-json',file,self.root/'out.csv'); self.assertEqual(result.returncode,2)
    def test_csharp_rejects_external_url(self):
        result=self.tool('http://example.invalid:8080/api/report',self.root/'out.csv'); self.assertEqual(result.returncode,2)
    def test_csharp_http_round_trip(self):
        output=self.root/'http.csv'
        with server(self.db) as url: result=self.tool(url+'/api/report',output)
        self.assertEqual(result.returncode,0,result.stderr); self.assertIn('Total,6',output.read_text())
    def test_csharp_does_not_follow_redirect(self):
        with server(self.db) as url: result=self.tool(url+'/redirect',self.root/'out.csv')
        self.assertEqual(result.returncode,2)
    def test_http_report_and_webpage(self):
        with server(self.db) as url:
            with urlopen(url+'/api/report') as response: self.assertEqual(json.load(response),report(self.db))
            with urlopen(url) as response: self.assertIn(b'Synthetic data only',response.read())
    def test_http_rejects_wrong_host(self):
        with server(self.db) as url,self.assertRaises(HTTPError) as caught: urlopen(Request(url+'/api/report',headers={'Host':'example.invalid'}))
        self.assertEqual(caught.exception.code,403)
    def test_http_invalid_search(self):
        with server(self.db) as url,self.assertRaises(HTTPError) as caught: urlopen(url+'/api/kb?q='+'x'*101)
        self.assertEqual(caught.exception.code,400)
