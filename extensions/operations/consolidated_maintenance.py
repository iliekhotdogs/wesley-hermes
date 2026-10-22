"""Five-minute maintenance lane; preserve hourly health and daily summary/cleanup cadence.
No-change output stays empty. Child delivery targets remain distinct. No agent/secret output is logged.
"""
from __future__ import annotations
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import yaml
from datetime import datetime
from zoneinfo import ZoneInfo
from maintenance_lane import slots
from lane_lock import FileLock, Timeout

HOME = Path(__file__).resolve().parent.parent
ROOT = HOME.parent.parent
MAIN = ROOT/'profiles/main'
_CONFIG = yaml.safe_load((HOME/'config.yaml').read_text()) if (HOME/'config.yaml').exists() else {}
ROUTES = (_CONFIG or {}).get('host_automation', {}).get('routes', {})
STATE = HOME/'state/consolidated_maintenance.json'
LOCK = HOME/'state/consolidated_maintenance.lock'

def suppressed(text):
    return not text.strip() or text.strip() == '[SILENT]'

def due_tasks(now):
    day = now.strftime('%Y-%m-%d')
    due=slots(now)
    tasks = [('completion_log', now.strftime('%Y-%m-%dT%H')+':'+str(now.minute//5), HOME/'scripts/collect_completion_log.py', None, HOME), ('cron_health', due['health'], MAIN/'scripts/cron_health_check.py', ROUTES.get('health'), MAIN)]
    review = MAIN/'docs/PROFILE-REVIEW.json'
    if review.exists():
        plan=json.loads(review.read_text(encoding='utf-8'))
        if plan.get('status')=='scheduled' and now >= datetime.fromisoformat(plan['due_at']):
            tasks.append(('profile_review', plan['due_at'], MAIN/'scripts/profile_metrics_review.py', plan['delivery'], MAIN))
    if (now.hour,now.minute) >= (0,0):
        tasks.append(('thread_cleanup', day, HOME/'scripts/thread_cleanup.py', None, HOME))
    if 'summary' in due:
        tasks.append(('systems_summary', due['summary'], HOME/'scripts/morning_systems_summary.py', ROUTES.get('systems_summary'), HOME))
    if 'lib' in due:
        tasks.append(('lib_curation', due['lib'], HOME/'scripts/weekly_lib_curation.py', None, HOME))
    return tasks

def save(state):
    STATE.parent.mkdir(parents=True,exist_ok=True)
    tmp=STATE.with_suffix('.tmp'); tmp.write_text(json.dumps(state,indent=2),encoding='utf-8'); tmp.replace(STATE)

def main():
    now = datetime.now(ZoneInfo('America/Vancouver'))
    STATE.parent.mkdir(parents=True,exist_ok=True)
    lock=FileLock(str(LOCK))
    try: lock.acquire(timeout=0)
    except Timeout: return 0
    try:
        try: state=json.loads(STATE.read_text(encoding='utf-8'))
        except FileNotFoundError: state={}
        deadline=time.monotonic()+150
        failures=[]
        for name,key,script,target,home in due_tasks(now):
            record=state.get(name,{})
            if record.get('done')==key: continue
            if name=='thread_cleanup' and record.get('retry_after',0)>time.time():
                failures.append('thread_cleanup: permission/capability failure held until next retry')
                continue
            remaining=deadline-time.monotonic()
            if remaining<10: break
            env=dict(os.environ,HERMES_HOME=str(home),HERMES_PROFILE=home.name)
            try:
                # Retry delivery from saved text, never re-execute a child just to resend.
                if record.get('pending_key')==key:
                    text=record['pending_text']
                else:
                    p=subprocess.run([sys.executable,str(script)],env=env,cwd=script.parent,capture_output=True,text=True,timeout=min(145 if name=='lib_curation' else 80,remaining-2))
                    if p.returncode:
                        # Keep child diagnostics private; scheduled output exposes only a class/code.
                        error_path=HOME/'state'/('maintenance-'+name+'-error.txt')
                        error_path.write_text((p.stderr or p.stdout)[-4000:],encoding='utf-8')
                        error_path.chmod(0o600)
                        raise RuntimeError('child exit '+str(p.returncode)+'; inspect private '+error_path.name)
                    text=p.stdout.strip()
                    record={'pending_key':key,'pending_text':text}
                    state[name]=record; save(state)
                if target and not suppressed(text):
                    p=subprocess.run(['hermes','send','--to',target,'--json'],input=text,env=env,capture_output=True,text=True,timeout=25)
                    if p.returncode: raise RuntimeError('delivery failed; child output retained privately for retry')
                    receipt=json.loads(p.stdout)
                    record['delivery_receipt']=receipt
                state[name]={'done':key,'completed_at':now.isoformat(),**({'delivery_receipt':record['delivery_receipt']} if 'delivery_receipt' in record else {})}
                save(state)
            except Exception as exc:
                # Persist a bounded error class; avoid leaking child stdout/stderr or repeating actions.
                state.setdefault(name,record)['last_error']=str(exc)[:200]; save(state)
                if name=='thread_cleanup':
                    state[name]['retry_after']=time.time()+6*3600; save(state)
                failures.append(name+': '+str(exc)[:150])
        # Preserve the original serial Kanban/Obsidian pipeline and its own lock/state.
        remaining=deadline-time.monotonic()
        if remaining>10:
            p=subprocess.run([sys.executable,str(HOME/'scripts/maintenance_pipeline.py')],cwd=HOME/'scripts',capture_output=True,text=True,timeout=remaining)
            if not suppressed(p.stdout): print(p.stdout.strip())
            if p.returncode: failures.append('existing maintenance pipeline failed; inspect its state')
        # Due-dated profile review and lib curation share this lane; no extra cron jobs.
        if failures: print('\n'.join(failures)); return 1
        return 0
    finally:
        lock.release()

if __name__=='__main__': raise SystemExit(main())
