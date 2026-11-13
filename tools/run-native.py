"""Execute the prepared fixture on a real macOS/Xcode Simulator environment."""
from pathlib import Path
import json,os,platform,shutil,subprocess,sys,time

ROOT=Path(__file__).resolve().parents[1]
OUT=Path(os.environ.get('TEST_OUTPUT',str(ROOT/'evidence'))).resolve();OUT.mkdir(parents=True,exist_ok=True)
report={'platform':platform.platform(),'status':'not_started','native_execution':False,'passed_tests':0,'total_tests':0}
def finish(status,code):
    report['status']=status
    (OUT/'run.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2));sys.exit(code)
if platform.system()!='Darwin' or not shutil.which('xcodebuild') or not shutil.which('xcrun'):
    report['reason']='macOS with Xcode and an installed iOS Simulator runtime is required; this is not a passed or skipped native test'
    finish('environment_unavailable',2)
subprocess.run([sys.executable,str(ROOT/'tools/generate-project.py')],check=True)
report['xcode']=subprocess.check_output(['xcodebuild','-version'],text=True).strip()
devices=json.loads(subprocess.check_output(['xcrun','simctl','list','devices','available','--json'],text=True))['devices']
candidates=[]
for runtime,items in devices.items():
    if 'iOS-' not in runtime:continue
    for device in items:
        if device.get('isAvailable') and device['name'].startswith('iPhone'):candidates.append((runtime,device))
if not candidates:
    report['reason']='No available iPhone Simulator runtime; do not count this condition as approval'
    finish('environment_unavailable',2)
runtime,device=sorted(candidates,key=lambda item:(item[0],item[1]['name']))[-1]
report['simulator']={'runtime':runtime,'name':device['name'],'udid':device['udid']}
if device['state']!='Booted':subprocess.run(['xcrun','simctl','boot',device['udid']],check=True)
subprocess.run(['xcrun','simctl','bootstatus',device['udid'],'-b'],check=True)
bundle=OUT/('Notas-'+str(int(time.time()))+'.xcresult')
cmd=['xcodebuild','-project',str(ROOT/'Notas.xcodeproj'),'-scheme','Notas','-destination','platform=iOS Simulator,id='+device['udid'],'-parallel-testing-enabled','NO','-resultBundlePath',str(bundle),'CODE_SIGNING_ALLOWED=NO','test']
report['command']=cmd;report['result_bundle']=str(bundle);report['native_execution']=True
with (OUT/'xcodebuild.log').open('w',encoding='utf-8') as log:
    result=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,timeout=1500)
report['xcodebuild_exit']=result.returncode
if result.returncode!=0:finish('native_test_or_build_failed',1)
summary=subprocess.run(['xcrun','xcresulttool','get','test-results','summary','--path',str(bundle)],capture_output=True,text=True)
if summary.returncode!=0:
    report['reason']='xcodebuild returned0 but structured test summary could not be read; inspect xcresult before approval'
    report['summary_error']=summary.stderr;finish('result_unverified',3)
try:
    data=json.loads(summary.stdout)
    (OUT/'test-summary.json').write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')
    passed=int(data['passedTests']);failed=int(data['failedTests']);skipped=int(data.get('skippedTests',0))
    total=int(data.get('totalTestCount',passed+failed+skipped))
    expected=json.loads((ROOT/'project-model.json').read_text(encoding='utf-8'))['source_test_methods']
except (ValueError,KeyError,TypeError) as error:
    report['reason']='Unrecognized xcresult summary; no successful count inferred: '+str(error);finish('result_unverified',3)
report.update(passed_tests=passed,failed_tests=failed,skipped_tests=skipped,total_tests=total,expected_test_methods=expected)
if total<expected or passed<expected or failed>0:
    report['reason']='Full planned set did not pass; skipped or missing tests are not successful evidence'
    finish('native_checks_incomplete_or_failed',1)
finish('passed',0)
