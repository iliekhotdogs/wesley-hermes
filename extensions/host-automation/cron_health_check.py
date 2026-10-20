"""Report changed actionable failures; retain local metrics without model turns."""
import json, sqlite3
from datetime import datetime, timezone, timedelta
from pathlib import Path

def collect(root,now):
 issues=[]; metrics={}; profiles=[root]+[p for p in sorted((root/'profiles').iterdir()) if not p.name.startswith('.') and (p/'config.yaml').exists()] if (root/'profiles').exists() else [root]
 for home in profiles:
  role=home.name if home!=root else 'default'
  path=home/'cron/jobs.json'
  if not path.exists():continue
  try: jobs=json.loads(path.read_text(encoding='utf-8-sig'))['jobs']
  except (OSError,ValueError,KeyError):
   issues.append(role+': scheduled-job store could not be read');continue
  metrics[role]={'enabled_jobs':sum(j.get('enabled',True) for j in jobs),'paused_jobs':sum(not j.get('enabled',True) for j in jobs),'last_outcomes':{},'last_delivery_failures':0}
  for job in jobs:
   if not job.get('enabled',True) or job.get('id')=='85d20664dc76':continue
   label=role+'/'+job.get('name',job['id']);status=job.get('last_status')
   outcomes=metrics[role]['last_outcomes']; outcomes[str(status or 'not_run')]=outcomes.get(str(status or 'not_run'),0)+1
   if status and status not in ('ok','success','silent','completed','skipped'): issues.append(label+': last status '+str(status))
   if job.get('last_delivery_error') or job.get('last_delivery_unverified'):
    metrics[role]['last_delivery_failures']+=1;issues.append(label+': delivery failed or unverified; inspect delivery record, do not rerun side effects')
   upcoming=job.get('next_run_at')
   if upcoming:
    try:
     due=datetime.fromisoformat(upcoming.replace('Z','+00:00'))
     if not due.tzinfo:issues.append(label+': next scheduled time has no timezone')
     elif (now-due).total_seconds()>600:issues.append(label+': scheduled fire overdue by more than 10 minutes')
    except (ValueError,TypeError):issues.append(label+': invalid next scheduled time')
   if job.get('script') and not (home/'scripts'/job['script']).is_file():issues.append(label+': configured script is missing')
  ledger=home/'cron/executions.db'
  if ledger.exists():
   try:
    with sqlite3.connect('file:'+ledger.as_posix()+'?mode=ro',uri=True) as conn:
     since=(now-timedelta(days=7)).isoformat()
     rows=conn.execute('SELECT status,COUNT(*) FROM executions WHERE claimed_at>=? GROUP BY status',(since,)).fetchall()
     metrics[role]['executions_7d']={str(s):n for s,n in rows}
   except sqlite3.Error:issues.append(role+': execution ledger could not be read')
  stages=home/'state/maintenance_pipeline_state.json'
  if stages.exists():
   try:
    state=json.loads(stages.read_text(encoding='utf-8-sig'))
    for name,value in state.items():
     if value.get('last_error'):issues.append(role+'/maintenance/'+name+': stage failed; inspect its local state record')
   except (OSError,ValueError,AttributeError):issues.append(role+': maintenance state could not be read')
 # Missing-session records need a one-time actionable notice, never silent loss.
 for home in profiles:
  for pending in (home/'pending_messages').glob('pending-*.json'):
   try:
    data=json.loads(pending.read_text(encoding='utf-8-sig'))
    if not data.get('session_id') and (now.timestamp()-pending.stat().st_mtime)>3600:
     issues.append(home.name+': preserved pending message lacks a recovery session identifier')
   except (OSError,ValueError):issues.append(home.name+': pending-message record could not be read')
 board=root/'kanban.db';kanban={}
 if board.exists():
  try:
   with sqlite3.connect('file:'+board.as_posix()+'?mode=ro',uri=True) as conn:
    kanban['task_statuses']={s:n for s,n in conn.execute("SELECT status,COUNT(*) FROM tasks WHERE status!='archived' GROUP BY status")}
    since=int((now-timedelta(days=7)).timestamp())
    kanban['block_causes_7d']={s or 'unspecified':n for s,n in conn.execute("SELECT json_extract(payload,'$.kind'),COUNT(*) FROM task_events WHERE kind IN ('blocked','block_loop_detected') AND created_at>=? GROUP BY json_extract(payload,'$.kind')",(since,))}
    kanban['main_recovery_statuses']={s:n for s,n in conn.execute("SELECT status,COUNT(*) FROM tasks WHERE idempotency_key LIKE 'main-recovery:source:%' OR idempotency_key LIKE 'profile-permission:%' GROUP BY status")}
  except sqlite3.Error:issues.append('shared Kanban recovery metrics could not be read')
 return sorted(set(issues)),{'collected_utc':now.isoformat(),'profiles':metrics,'kanban':kanban,'cost':'unavailable in cron execution ledger; no cost estimate invented'}

def run(home):
 root=home.parent.parent if home.parent.name=='profiles' else home
 issues,metrics=collect(root,datetime.now(timezone.utc))
 state_path=home/'cron/cron_health_check_state.json';state_path.parent.mkdir(parents=True,exist_ok=True)
 try:previous=json.loads(state_path.read_text(encoding='utf-8'))
 except (OSError,ValueError):previous=[]
 for path,value in ((state_path,issues),(home/'cron/reliability_metrics.json',metrics)):
  temp=path.with_suffix('.tmp');temp.write_text(json.dumps(value,indent=2),encoding='utf-8');temp.replace(path)
 if issues==previous:return '[SILENT]'
 if issues:return 'Cron health changed:\n'+'\n'.join('- '+issue for issue in issues)
 return 'Previously reported cron issues have cleared.'

if __name__=='__main__':print(run(Path(__file__).resolve().parent.parent))
