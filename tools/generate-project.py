"""Generate a dependency-free Xcode project; generation is not compilation."""
from pathlib import Path
import hashlib
import json
import re
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
OBJECTS = {}


def identifier(name):
    return hashlib.sha1(name.encode('utf-8')).hexdigest()[:24].upper()


def obj(label, isa, **properties):
    key = identifier(label)
    if key in OBJECTS:
        raise ValueError('Duplicate project object: ' + label)
    OBJECTS[key] = {'isa': isa, **properties}
    return key


def openstep(value, level=0):
    if isinstance(value, dict):
        return '{\n' + ''.join('\t'*(level+1) + json.dumps(str(k)) + ' = ' + openstep(v, level+1) + ';\n' for k,v in value.items()) + '\t'*level + '}'
    if isinstance(value, list):
        return '(\n' + ''.join('\t'*(level+1) + openstep(v, level+1) + ',\n' for v in value) + '\t'*level + ')'
    if isinstance(value, int):
        return str(value)
    return json.dumps(str(value), ensure_ascii=True)


project_id = identifier('project')
targets = {}
products = []
groups = []
test_count = 0
for name, files, kind in [
    ('Notas', ['NotesStore.swift','NotasApp.swift'], 'application'),
    ('NotasTests', ['NotesStoreTests.swift'], 'bundle.unit-test'),
    ('NotasUITests', ['NotasUITests.swift'], 'bundle.ui-testing'),
]:
    refs, build_files = [], []
    for file in files:
        path = ROOT/name/file
        assert path.is_file(), path
        if name != 'Notas':
            test_count += len(re.findall(r'func\s+(test\w+)\s*\(', path.read_text(encoding='utf-8')))
        ref = obj('file:'+name+'/'+file, 'PBXFileReference', lastKnownFileType='sourcecode.swift', path=file, sourceTree='<group>')
        refs.append(ref)
        build_files.append(obj('build:'+name+'/'+file, 'PBXBuildFile', fileRef=ref))
    groups.append(obj('group:'+name, 'PBXGroup', path=name, sourceTree='<group>', children=refs))
    ext = '.app' if name == 'Notas' else '.xctest'
    product = obj('product:'+name, 'PBXFileReference', explicitFileType='wrapper.application' if name == 'Notas' else 'wrapper.cfbundle', includeInIndex=0, path=name+ext, sourceTree='BUILT_PRODUCTS_DIR')
    products.append(product)
    phases = [obj('sources:'+name,'PBXSourcesBuildPhase',buildActionMask=2147483647,files=build_files,runOnlyForDeploymentPostprocessing=0),obj('frameworks:'+name,'PBXFrameworksBuildPhase',buildActionMask=2147483647,files=[],runOnlyForDeploymentPostprocessing=0),obj('resources:'+name,'PBXResourcesBuildPhase',buildActionMask=2147483647,files=[],runOnlyForDeploymentPostprocessing=0)]
    configurations = []
    for config in ['Debug','Release']:
        settings = {'PRODUCT_NAME':'$(TARGET_NAME)','PRODUCT_BUNDLE_IDENTIFIER':'com.designcraft.'+name.lower(),'SWIFT_VERSION':'5.0','IPHONEOS_DEPLOYMENT_TARGET':'17.0','SDKROOT':'iphoneos','TARGETED_DEVICE_FAMILY':'1,2','GENERATE_INFOPLIST_FILE':'YES','CODE_SIGNING_ALLOWED':'NO','CODE_SIGN_STYLE':'Automatic','CURRENT_PROJECT_VERSION':'1','MARKETING_VERSION':'1.0'}
        if name == 'Notas':
            settings.update({'INFOPLIST_KEY_CFBundleDisplayName':'Notas de trabalho','INFOPLIST_KEY_UIApplicationSceneManifest_Generation':'YES','INFOPLIST_KEY_UILaunchScreen_Generation':'YES','INFOPLIST_KEY_UISupportedInterfaceOrientations_iPhone':'UIInterfaceOrientationPortrait UIInterfaceOrientationLandscapeLeft UIInterfaceOrientationLandscapeRight','INFOPLIST_KEY_UISupportedInterfaceOrientations_iPad':'UIInterfaceOrientationPortrait UIInterfaceOrientationPortraitUpsideDown UIInterfaceOrientationLandscapeLeft UIInterfaceOrientationLandscapeRight'})
        elif name == 'NotasTests':
            settings.update({'TEST_HOST':'$(BUILT_PRODUCTS_DIR)/Notas.app/Notas','BUNDLE_LOADER':'$(TEST_HOST)'})
        else:
            settings['TEST_TARGET_NAME']='Notas'
        if config == 'Debug':
            settings.update({'SWIFT_OPTIMIZATION_LEVEL':'-Onone','ENABLE_TESTABILITY':'YES','SWIFT_ACTIVE_COMPILATION_CONDITIONS':'DEBUG'})
        configurations.append(obj('config:'+name+':'+config,'XCBuildConfiguration',name=config,buildSettings=settings))
    config_list = obj('configs:'+name,'XCConfigurationList',buildConfigurations=configurations,defaultConfigurationIsVisible=0,defaultConfigurationName='Release')
    dependencies=[]
    if name != 'Notas':
        proxy=obj('proxy:'+name,'PBXContainerItemProxy',containerPortal=project_id,proxyType=1,remoteGlobalIDString=identifier('target:Notas'),remoteInfo='Notas')
        dependencies.append(obj('dependency:'+name,'PBXTargetDependency',target=identifier('target:Notas'),targetProxy=proxy))
    targets[name]=obj('target:'+name,'PBXNativeTarget',name=name,productName=name,productType='com.apple.product-type.'+kind,productReference=product,buildConfigurationList=config_list,buildPhases=phases,buildRules=[],dependencies=dependencies)

product_group=obj('products','PBXGroup',name='Products',sourceTree='<group>',children=products)
main_group=obj('main','PBXGroup',sourceTree='<group>',children=groups+[product_group])
project_configs=[]
for config in ['Debug','Release']:
    project_configs.append(obj('config:project:'+config,'XCBuildConfiguration',name=config,buildSettings={'CLANG_ENABLE_MODULES':'YES','SWIFT_VERSION':'5.0','IPHONEOS_DEPLOYMENT_TARGET':'17.0'}))
project_config_list=obj('configs:project','XCConfigurationList',buildConfigurations=project_configs,defaultConfigurationIsVisible=0,defaultConfigurationName='Release')
attrs={'BuildIndependentTargetsInParallel':'YES','LastUpgradeCheck':'1500','TargetAttributes':{key:{'CreatedOnToolsVersion':'15.0',**({'TestTargetID':targets['Notas']} if name!='Notas' else {})} for name,key in targets.items()}}
obj('project','PBXProject',attributes=attrs,buildConfigurationList=project_config_list,compatibilityVersion='Xcode 14.0',developmentRegion='pt',knownRegions=['pt','en','Base'],mainGroup=main_group,productRefGroup=product_group,projectDirPath='',projectRoot='',targets=list(targets.values()))

# Check the project reference graph before serializing it. This does not validate SDK APIs.
for properties in OBJECTS.values():
    def verify(value):
        if isinstance(value, dict):
            for v in value.values(): verify(v)
        elif isinstance(value, list):
            for v in value: verify(v)
        elif isinstance(value, str) and re.fullmatch('[A-F0-9]{24}',value):
            assert value in OBJECTS, value
    verify(properties)

project=ROOT/'Notas.xcodeproj';project.mkdir(exist_ok=True)
(project/'project.pbxproj').write_text('// !$*UTF8*$!\n'+openstep({'archiveVersion':1,'classes':{},'objectVersion':56,'objects':OBJECTS,'rootObject':project_id})+'\n',encoding='utf-8')
scheme=ET.Element('Scheme',LastUpgradeVersion='1500',version='1.7')
build=ET.SubElement(scheme,'BuildAction',parallelizeBuildables='YES',buildImplicitDependencies='YES')
entries=ET.SubElement(build,'BuildActionEntries')
def ref(parent,name):
    return ET.SubElement(parent,'BuildableReference',BuildableIdentifier='primary',BlueprintIdentifier=targets[name],BuildableName=name+('.app' if name=='Notas' else '.xctest'),BlueprintName=name,ReferencedContainer='container:Notas.xcodeproj')
for name in targets:
    entry=ET.SubElement(entries,'BuildActionEntry',buildForTesting='YES',buildForRunning='YES' if name=='Notas' else 'NO',buildForProfiling='YES' if name=='Notas' else 'NO',buildForArchiving='YES' if name=='Notas' else 'NO',buildForAnalyzing='YES')
    ref(entry,name)
test=ET.SubElement(scheme,'TestAction',buildConfiguration='Debug',shouldUseLaunchSchemeArgsEnv='YES')
testables=ET.SubElement(test,'Testables')
for name in ['NotasTests','NotasUITests']:ref(ET.SubElement(testables,'TestableReference',skipped='NO'),name)
ref(ET.SubElement(test,'MacroExpansion'),'Notas')
launch=ET.SubElement(scheme,'LaunchAction',buildConfiguration='Debug',launchStyle='0',useCustomWorkingDirectory='NO',ignoresPersistentStateOnLaunch='NO',debugDocumentVersioning='YES',debugServiceExtension='internal',allowLocationSimulation='YES')
ref(ET.SubElement(launch,'BuildableProductRunnable',runnableDebuggingMode='0'),'Notas')
ET.SubElement(scheme,'AnalyzeAction',buildConfiguration='Debug')
ET.SubElement(scheme,'ArchiveAction',buildConfiguration='Release',revealArchiveInOrganizer='YES')
destination=project/'xcshareddata/xcschemes';destination.mkdir(parents=True,exist_ok=True)
ET.indent(scheme)
ET.ElementTree(scheme).write(destination/'Notas.xcscheme',encoding='utf-8',xml_declaration=True)
(ROOT/'project-model.json').write_text(json.dumps({'generated_object_count':len(OBJECTS),'targets':targets,'source_test_methods':test_count,'project_graph':'closed references verified','compilation':'not performed by generator'},indent=2)+'\n',encoding='utf-8')
print(json.dumps({'project':str(project),'objects':len(OBJECTS),'test_methods_planned':test_count,'native_execution':False}))
