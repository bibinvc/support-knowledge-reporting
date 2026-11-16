from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,io,json,os,platform,sqlite3,subprocess,tempfile,unittest
from app import initialise,report,server

ROOT=Path(__file__).resolve().parent
if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--compiler',default='C:/Windows/Microsoft.NET/Framework64/v4.0.30319/csc.exe'); options=parser.parse_args()
    for folder in ['build','evidence','reports']: (ROOT/folder).mkdir(exist_ok=True)
    binary=ROOT/'build/ReportTool.exe'; source=ROOT/'src/ReportTool.cs'
    command=[options.compiler,'/nologo','/warnaserror','/target:exe','/reference:System.Runtime.Serialization.dll','/out:'+str(binary),str(source)]
    built=subprocess.run(command,capture_output=True,text=True,timeout=45)
    (ROOT/'evidence/build.txt').write_text(built.stdout+built.stderr,encoding='utf-8')
    if built.returncode: raise RuntimeError(built.stdout+built.stderr)
    os.environ['LAB_CS_BIN']=str(binary)
    stream=io.StringIO(); suite=unittest.defaultTestLoader.discover(str(ROOT/'tests')); result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
    (ROOT/'evidence/tests.txt').write_text(stream.getvalue(),encoding='utf-8')
    if not result.wasSuccessful(): print(stream.getvalue()[-6000:]); raise RuntimeError('Reporting tests failed; see evidence/tests.txt')
    with tempfile.TemporaryDirectory() as temporary:
        database=Path(temporary)/'demo.sqlite3'; initialise(database); data=report(database)
        with server(database) as url:
            exported=subprocess.run([str(binary),url+'/api/report',str(ROOT/'reports/report.csv')],capture_output=True,text=True,timeout=8)
        if exported.returncode: raise RuntimeError(exported.stderr)
    (ROOT/'reports/report.json').write_text(json.dumps(data,indent=2),encoding='utf-8')
    version=subprocess.run([options.compiler,'/help'],capture_output=True,text=True,timeout=10).stdout.splitlines()[:2]
    summary={'status':'passed','validated_utc':datetime.now(timezone.utc).isoformat(),'tests':{'run':result.testsRun,'passed':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'skipped':len(result.skipped)},'csharp_compiled':True,'compiler':version,'target':'.NET Framework, existing Windows compiler','python':platform.python_version(),'sqlite':sqlite3.sqlite_version,'fixtures':{'incidents':6,'knowledge_articles':3},'scope':{'synthetic':True,'local_web_service':True,'csharp_api_csv_export_executed':True,'teams_survey_deployed':False,'aml_fraud_training_delivered':False},'source_sha256':{path.name:hashlib.sha256(path.read_bytes()).hexdigest() for path in [source,ROOT/'app.py']}}
    summary['source_sha256']['content_plan.py']=hashlib.sha256((ROOT/'content_plan.py').read_bytes()).hexdigest()
    summary['fixtures']['content_documents']=5
    summary['scope']['sharepoint_provisioned']=False
    summary['scope']['real_stakeholder_responses']=False
    summary['scope']['local_content_staging']=True
    (ROOT/'evidence/validation-summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    print(json.dumps(summary,indent=2))
