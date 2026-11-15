"""Exercise failed/repair/pending states; leave approval for a real auditor."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

REPO = Path(__file__).resolve().parents[2]
COORDINATOR = REPO / 'rb-audit-test-suite/scripts/test_loop.py'
SOURCE = REPO / 'rb-audit-test-suite/examples/numerical'
work = Path(tempfile.mkdtemp(prefix='rb-two-skill-demo-')).resolve()
project, state = work / 'project', work / 'state'
shutil.copytree(SOURCE, project, ignore=shutil.ignore_patterns('evidence', '__pycache__', '.pytest_cache'))
strong = (project / 'project/test_model.py').read_text()
weak = strong.replace('assert all(r.a_kg >= 0 and r.b_kg >= 0 for r in rows)', 'assert len(rows) >= 1').replace('assert len(rows) == 2\n    assert rows[-1].time_days == 1e-308\n    assert (rows[-1].a_kg, rows[-1].b_kg) == (1, 0)', 'assert len(rows) >= 1')
assert weak != strong
(project / 'project/test_model.py').write_text(weak)
# Each declared command retains its own native artifacts outside candidate inputs.
entry = """import os, subprocess, sys, tempfile
from pathlib import Path
root = Path(__file__).resolve().parent
out = Path(tempfile.mkdtemp(prefix='check-', dir=root.parent))
command = [sys.executable, '-B', '-m', 'pytest', '-p', 'no:cacheprovider',
           '-c', str(root/'pytest.ini'), '--confcutdir', str(root), '-q',
           '--basetemp', str(out/'tmp'),
           '--junitxml', str(out/'junit.xml'), *sys.argv[1:]]
if any(arg.startswith('audit/') for arg in sys.argv[1:]):
    command.extend(['--evidence', str(out/'children')])
print('native evidence:', out, flush=True)
result = subprocess.run(command, cwd=root, env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'), check=False)
sys.exit(result.returncode)
"""
(project/'check_entry.py').write_text(entry)
base = [sys.executable, '-B', str(project/'check_entry.py')]
plan = {'version':1, 'builder_id':'root-demo-builder', 'max_rounds':3,
        'input_paths':['project/model.py','project/test_model.py','audit/support.py','audit/conftest.py','audit/test_effectiveness.py','audit/test_evidence.py','pytest.ini','REQUIREMENTS.md','check_entry.py'],
        'protected_paths':['REQUIREMENTS.md','audit/support.py','audit/test_effectiveness.py','audit/test_evidence.py'],
        'checks':[
            {'id':'project-tests','kind':'project','argv':base+['project/test_model.py'], 'timeout_seconds':90},
            {'id':'audit-challenges','kind':'audit','argv':base+['audit/test_effectiveness.py::test_suite_exposes_fault'], 'timeout_seconds':90},
            {'id':'audit-evidence-rejection','kind':'audit','argv':base+['audit/test_evidence.py'], 'timeout_seconds':90}]}
(work/'plan.json').write_text(json.dumps(plan,indent=2)+'\n')
receipts=[]
def run(args, expected):
    command=[sys.executable,str(COORDINATOR),*args,'--state-dir',str(state)]
    result=subprocess.run(command,capture_output=True,text=True,timeout=180,check=False,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'))
    receipts.append({'command':command,'exit':result.returncode,'stderr':result.stderr})
    (work/f'command-{len(receipts)}.json').write_text(json.dumps(receipts[-1],indent=2)+'\n')
    (work/f'command-{len(receipts)}.stdout').write_text(result.stdout)
    assert result.returncode == expected,(result.returncode,result.stderr)
    return json.loads(result.stdout)
run(['init','--project',str(project),'--plan',str(work/'plan.json')],0)
failed=run(['run'],1);assert failed['status']=='needs_repair'
assert [x['outcome'] for x in failed['rounds'][0]['checks']]==['passed','failed','passed']
(project/'project/test_model.py').write_text(strong)
pending=run(['run'],3);assert pending['status']=='awaiting_review'
run(['status','--require-verified'],1)
result={'work':str(work),'project':str(project),'state':str(state),'round':2,'candidate_digest':pending['rounds'][-1]['candidate_digest'],'status':'awaiting_review','builder_id':'root-demo-builder','receipts':receipts}
(REPO/'docs/test-suite-system/demo-pending.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:result[k] for k in ('work','state','round','candidate_digest','status')}),flush=True)
