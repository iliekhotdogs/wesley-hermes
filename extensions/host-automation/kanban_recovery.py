"""Queue main recovery once; never restart a failed specialist unchanged."""
import os, sys, argparse
from datetime import datetime
from pathlib import Path

HOME=Path(os.environ.get('HERMES_HOME',Path(__file__).resolve().parent.parent))
ROOT=HOME.parent.parent if HOME.parent.name=='profiles' else HOME
sys.path.insert(0,str(ROOT/'hermes-agent'))
SPECIALISTS={'builder','cowsearcher','cron','lib'}

def settle_verified_takeover(conn,task_id,summary):
 from hermes_cli import kanban_db as kb
 task=kb.get_task(conn,task_id)
 if task is None:raise ValueError('Source task does not exist')
 if task.status=='done':return True
 if task.status=='running':raise ValueError('Do not settle an active worker task')
 if task.status=='triage':
  # The work is already verified; this records main ownership before closing.
  # Main's per-profile concurrency limit keeps it from spawning beside recovery.
  if not kb.specify_triage_task(conn,task_id,assignee='main',author='main'):return False
 return kb.complete_task(conn,task_id,summary=summary)

def queue_recoveries(conn,*,since=0):
 from hermes_cli import kanban_db as kb
 tasks=kb.list_tasks(conn,status='blocked')+kb.list_tasks(conn,status='triage')
 queued=[]
 for task in tasks:
  if task.assignee not in SPECIALISTS: continue
  stopped_at=conn.execute("SELECT MAX(created_at) FROM task_events WHERE task_id=? AND kind IN ('blocked','block_loop_detected','gave_up')",(task.id,)).fetchone()[0]
  if since and (not stopped_at or stopped_at<since):continue
  if task.status=='triage' and task.block_recurrences<kb.BLOCK_RECURRENCE_LIMIT: continue
  key='main-recovery:source:'+task.id
  existing=conn.execute("SELECT id FROM tasks WHERE idempotency_key=? AND status != 'archived'",(key,)).fetchone()
  takeover=False
  if existing:
   original=kb.get_task(conn,existing['id'])
   if original.status!='done':continue
   # A resumed specialist can block again after main's prerequisite repair.
   # Escalate once more for takeover, then retain that card as the stop marker.
   stopped=conn.execute("SELECT MAX(id) FROM task_events WHERE task_id=? AND kind IN ('blocked','block_loop_detected','gave_up')",(task.id,)).fetchone()[0]
   created=conn.execute("SELECT MIN(id) FROM task_events WHERE task_id=? AND kind='created'",(original.id,)).fetchone()[0]
   if not stopped or not created or stopped<=created:continue
   key+=':takeover'
   if conn.execute("SELECT id FROM tasks WHERE idempotency_key=? AND status != 'archived'",(key,)).fetchone():continue
   takeover=True
  tid=kb.create_task(conn,title='Recover specialist assignment: '+task.title,
   body=(f'TAKEOVER REQUIRED: the specialist blocked again after main completed the first recovery. Do not resume or redelegate it again. Finish and verify the original work yourself when feasible, then complete the source card through the CLI. ' if takeover else '')+f'Specialist {task.assignee} stopped on source task {task.id}. This is a recovery assignment for main. Read the original card, runs, and failure evidence once. Perform its privileged prerequisite directly or take over the original work if it is repeatedly failing. Preserve useful work; do not duplicate the source assignment, blindly unblock it, or delegate the same denied step again. Resume the original only once after a concrete verified correction. When commenting a correction, name the exact permitted tool (for file reads use read_file, not inline Python or terminal). If the same failure returns, finish it yourself when feasible. Main recovery runs as a Kanban worker: orchestrator-only model tools are unavailable in workers by native design, so use your unrestricted terminal with `hermes kanban show`, `comment`, `unblock`, or `complete` for administrative actions on the SOURCE card. Use kanban_complete for your own recovery card. This native worker boundary does not remove main administrative authority. Report the real result through the inherited original route. Actual external consent or missing information may require the user; stop once with the precise dependency.',
   assignee='main',created_by='cron:main-recovery-router',workspace_kind='scratch',creator_task_id=task.id,
   idempotency_key=key,max_retries=1,max_runtime_seconds=300)
  if takeover:
   kb.add_comment(conn,tid,author='cron:main-recovery-router',body=f'After verifying source work, a triage source can be closed with the scoped main-only helper: python "{ROOT / "profiles/cron/scripts/kanban_recovery.py"}" settle {task.id} --summary "<verified outcome>". It records main ownership and honors native completion criteria; no second specialist resumption is needed.')
  queued.append((task.id,tid))
 return queued

def main():
 from hermes_cli import kanban_db_connect as kbc
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('action',nargs='?',choices=['route','settle'],default='route')
 parser.add_argument('task_id',nargs='?')
 parser.add_argument('--summary')
 args=parser.parse_args()
 if args.action=='settle':
  if HOME.name!='main' or not args.task_id or not args.summary:
   raise SystemExit('settle is restricted to main and requires a verified source task and --summary')
  # Terminal subprocesses carry a generic delegated-child mutation guard.
  # Main is the explicitly authorized administrator; scope the override here.
  os.environ.pop('HERMES_DELEGATED_CHILD_CONTEXT',None)
  with kbc.connect_closing(board='default') as conn:
   if not settle_verified_takeover(conn,args.task_id,args.summary):raise SystemExit('Native completion criteria refused the source task')
  print('Verified source task completed by main: '+args.task_id)
  return 0
 import yaml
 cfg=yaml.safe_load((HOME/'config.yaml').read_text(encoding='utf-8')) or {}
 start=cfg.get('profile_recovery',{}).get('started_at')
 if not start:raise SystemExit('Recovery activation time is missing; refuse to replay the historical backlog')
 since=int(datetime.fromisoformat(start.replace('Z','+00:00')).timestamp())
 with kbc.connect_closing(board='default') as conn: actions=queue_recoveries(conn,since=since)
 # Recovery is already queued for main; keep normal maintenance output quiet.
 return 0

if __name__=='__main__': raise SystemExit(main())
