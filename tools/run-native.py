"""Execute the prepared fixture on a real macOS/Xcode Simulator environment."""
from pathlib import Path
import json,os,platform,shutil,subprocess,sys,time

ROOT=Path(__file__).resolve().parents[1]
OUT=Path(os.environ.get('TEST_OUTPUT',str(ROOT/'evidence'))).resolve();OUT.mkdir(parents=True,exist_ok=True)
report={'platform':platform.platform(),'status':'not_started','native_execution':False,'passed_tests':0,'total_tests':0}
def checkpoint(stage):
    report['stage']=stage
    (OUT/'run.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('Native validation stage: '+stage,flush=True)
def finish(status,code):
    report['status']=status
    (OUT/'run.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2));sys.exit(code)
def bounded(command,stage,timeout=60,capture=False,check=True,**kwargs):
    checkpoint(stage)
    try:
        result=subprocess.run(command,timeout=timeout,capture_output=capture,text=capture,**kwargs)
    except subprocess.TimeoutExpired:
        report['reason']=stage+' exceeded '+str(timeout)+'seconds'
        report['timed_out_command']=command
        finish('native_tool_timeout',1)
    except OSError as error:
        report['reason']=stage+': '+str(error)
        finish('native_tool_failed',1)
    if check and result.returncode:
        report['reason']=stage+' exited'+str(result.returncode)
        if capture:report['tool_stderr']=result.stderr
        finish('native_tool_failed',1)
    return result
checkpoint('environment_check')
if platform.system()!='Darwin' or not shutil.which('xcodebuild') or not shutil.which('xcrun'):
    report['reason']='macOS with Xcode and an installed iOS Simulator runtime is required; this is not a passed or skipped native test'
    finish('environment_unavailable',2)
bounded([sys.executable,str(ROOT/'tools/generate-project.py')],'generate_project')
report['xcode']=bounded(['xcodebuild','-version'],'xcode_version',capture=True).stdout.strip()
sdk=bounded(['xcrun','--sdk','iphonesimulator','--show-sdk-version'],'simulator_sdk_version',capture=True).stdout.strip()
requested_runtime=os.environ.get('IOS_RUNTIME',sdk)
report['simulator_sdk_version']=sdk;report['requested_runtime']=requested_runtime
try:devices=json.loads(bounded(['xcrun','simctl','list','devices','available','--json'],'discover_simulators',capture=True).stdout)['devices']
except (ValueError,KeyError,TypeError) as error:
    report['reason']='Simulator inventory could not be verified:'+str(error);finish('result_unverified',3)
candidates=[]
for runtime,items in devices.items():
    if runtime.split('SimRuntime.')[-1]!='iOS-'+requested_runtime.replace('.','-'):continue
    for device in items:
        if device.get('isAvailable') and device['name'].startswith('iPhone'):candidates.append((runtime,device))
if not candidates:
    report['reason']='No available iPhone Simulator for requested runtime '+requested_runtime+'; do not count this condition as approval'
    finish('environment_unavailable',2)
runtime,device=sorted(candidates,key=lambda item:(item[0],item[1]['name']))[-1]
report['simulator']={'runtime':runtime,'name':device['name'],'udid':device['udid']}
if device['state']!='Booted':bounded(['xcrun','simctl','boot',device['udid']],'boot_simulator',timeout=90)
bounded(['xcrun','simctl','bootstatus',device['udid'],'-b'],'wait_for_simulator',timeout=300)
bundle=OUT/('Notas-'+str(int(time.time()))+'.xcresult')
cmd=['xcodebuild','-project',str(ROOT/'Notas.xcodeproj'),'-scheme','Notas','-destination','platform=iOS Simulator,id='+device['udid'],'-parallel-testing-enabled','NO','-resultBundlePath',str(bundle),'CODE_SIGNING_ALLOWED=NO','test']
report['command']=cmd;report['result_bundle']=str(bundle);report['native_execution']=True
with (OUT/'xcodebuild.log').open('w',encoding='utf-8') as log:
    result=bounded(cmd,'xcodebuild_test',timeout=1800,stdout=log,stderr=subprocess.STDOUT,check=False)
report['xcodebuild_exit']=result.returncode
summary=bounded(['xcrun','xcresulttool','get','test-results','summary','--path',str(bundle)],'read_test_summary',capture=True,check=False)
if summary.returncode!=0:
    report['reason']='Structured test summary could not be read; inspect xcresult before approval'
    report['summary_error']=summary.stderr;finish('result_unverified',3)
try:
    data=json.loads(summary.stdout)
    (OUT/'test-summary.json').write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')
    passed=int(data['passedTests']);failed=int(data['failedTests']);skipped=int(data.get('skippedTests',0))
    total=int(data.get('totalTestCount',passed+failed+skipped))
    planned=json.loads((ROOT/'tools/benchmark-test-plan.json').read_text(encoding='utf-8'))
    if not isinstance(planned,list) or not planned or len(planned)!=len(set(planned)):
        raise ValueError('Benchmark plan must contain unique test identifiers')
    expected=len(planned)
except (ValueError,KeyError,TypeError) as error:
    report['reason']='Unrecognized xcresult summary; no successful count inferred: '+str(error);finish('result_unverified',3)
report.update(passed_tests=passed,failed_tests=failed,skipped_tests=skipped,total_tests=total,expected_test_methods=expected)
tree=bounded(['xcrun','xcresulttool','get','test-results','tests','--path',str(bundle)],'read_test_identities',capture=True,check=False)
try:
    if tree.returncode:raise ValueError(tree.stderr)
    nodes=json.loads(tree.stdout)
    (OUT/'test-identities.json').write_text(json.dumps(nodes,indent=2)+'\n',encoding='utf-8')
    cases=[]
    def collect(value):
        if isinstance(value,dict):
            if value.get('nodeType')=='Test Case':cases.append((value['nodeIdentifier'],value.get('result')))
            for child in value.values():collect(child)
        elif isinstance(value,list):
            for child in value:collect(child)
    collect(nodes)
    report['test_identity_plan_matches']=(len(cases)==expected and {name for name,_ in cases}==set(planned))
    report['all_planned_identities_passed']=report['test_identity_plan_matches'] and all(status=='Passed' for _,status in cases)
except (ValueError,KeyError,TypeError) as error:
    report['test_identity_error']=str(error)
    report['all_planned_identities_passed']=False
attachment_out=OUT/'attachments'
export=bounded(['xcrun','xcresulttool','export','attachments','--path',str(bundle),'--output-path',str(attachment_out)],'export_visual_evidence',timeout=120,capture=True,check=False)
report['attachments_export_exit']=export.returncode
report['screenshots']=[str(p.relative_to(OUT)) for p in attachment_out.rglob('*.png')] if attachment_out.exists() else []
report['visual_review_pending']=True
if export.returncode!=0:report['attachments_export_warning']=export.stderr
if result.returncode!=0 or total!=expected or passed!=expected or failed>0 or skipped>0 or not report['all_planned_identities_passed']:
    report['reason']='Full planned set did not pass; skipped or missing tests are not successful evidence'
    finish('native_checks_incomplete_or_failed',1)
finish('passed',0)
