"""Retry-safe Calendar/Tasks creation shared by profiles of one Google account."""
import hashlib, json, sqlite3
from contextlib import contextmanager
from pathlib import Path

def digest(value):
 return hashlib.sha256(value.encode('utf-8')).hexdigest()

def operation(home, token_path, service, target, body, explicit_key=None):
 token=json.loads(Path(token_path).read_text(encoding='utf-8-sig'))
 account=digest(str(token.get('client_id',''))+':'+str(token.get('refresh_token','')))
 payload=digest(json.dumps(body,sort_keys=True,separators=(',',':'),ensure_ascii=False))
 key=digest(':'.join((account,service,target,explicit_key or payload)))
 home=Path(home)
 root=home.parent.parent if home.parent.name=='profiles' else home
 path=root/'state/google-create-idempotency.db'
 path.parent.mkdir(parents=True,exist_ok=True)
 return path,key,payload

@contextmanager
def ledger(path):
 conn=sqlite3.connect(path,timeout=30)
 conn.execute('CREATE TABLE IF NOT EXISTS operations (key TEXT PRIMARY KEY,payload TEXT NOT NULL,state TEXT NOT NULL,resource_id TEXT)')
 conn.commit()
 conn.execute('BEGIN IMMEDIATE')
 try:
  yield conn
  conn.commit()
 except BaseException:
  conn.rollback()
  raise
 finally: conn.close()

def _existing(conn,key,payload):
 row=conn.execute('SELECT payload,state,resource_id FROM operations WHERE key=?',(key,)).fetchone()
 if row and row[0]!=payload:
  raise ValueError('Idempotency key already belongs to a different request; use the original payload or a new key for an intentionally different operation.')
 return row

def _status(exc):
 return getattr(getattr(exc,'resp',None),'status',None)

def calendar_once(service,home,token_path,calendar,body,explicit_key=None):
 path,key,payload=operation(home,token_path,'calendar',calendar,body,explicit_key)
 # Hex is valid Calendar base32hex; a stable remote ID closes the crash window.
 event_id=key
 event=dict(body,id=event_id,extendedProperties={'private':{'hermesOperation':key,'hermesPayload':payload}})
 with ledger(path) as conn:
  _existing(conn,key,payload)
  try:
   result=service.events().get(calendarId=calendar,eventId=event_id).execute()
   status='existing'
  except Exception as exc:
   if _status(exc)!=404:raise
   try:
    result=service.events().insert(calendarId=calendar,body=event).execute()
    status='created'
   except Exception as insert_exc:
    if _status(insert_exc)!=409:raise
    result=service.events().get(calendarId=calendar,eventId=event_id).execute()
    status='existing'
  if result.get('status')=='cancelled':
   raise ValueError('This operation refers to a deleted event. Main must review it; do not recreate it automatically.')
  remote_payload=result.get('extendedProperties',{}).get('private',{}).get('hermesPayload')
  if remote_payload and remote_payload!=payload:
   raise ValueError('Remote event uses this operation key for a different request.')
  conn.execute('INSERT OR REPLACE INTO operations VALUES (?,?,?,?)',(key,payload,'complete',result['id']))
 return status,result

def tasks_once(service,home,token_path,tasklist,body,explicit_key=None):
 path,key,payload=operation(home,token_path,'tasks',tasklist,body,explicit_key)
 marker='[hermes-operation:'+key+']'
 request=dict(body,notes=((body.get('notes','')+'\n\n') if body.get('notes') else '')+marker)
 if len(request['notes'])>8192:raise ValueError('Task notes plus retry marker exceed Google Tasks notes limit.')
 with ledger(path) as conn:
  row=_existing(conn,key,payload)
  if row and row[1]=='complete' and row[2]:
   try:return 'existing',service.tasks().get(tasklist=tasklist,task=row[2]).execute()
   except Exception as exc:
    if _status(exc)!=404:raise
    raise ValueError('MAIN_REQUIRED: the previously created task was deleted; do not recreate it automatically.') from exc
  # Reserve durably BEFORE the request. A crash can leave an uncertain result.
  fresh=row is None
  if fresh:
   conn.execute('INSERT INTO operations VALUES (?,?,?,NULL)',(key,payload,'attempted'))
   conn.commit()
   conn.execute('BEGIN IMMEDIATE')
  page=None
  while True:
   response=service.tasks().list(tasklist=tasklist,maxResults=100,showCompleted=True,showHidden=True,pageToken=page).execute()
   match=next((item for item in response.get('items',[]) if marker in item.get('notes','')),None)
   if match:
    conn.execute('UPDATE operations SET state=?,resource_id=? WHERE key=?',('complete',match['id'],key))
    return 'existing',match
   page=response.get('nextPageToken')
   if not page:break
  if not fresh:
   raise ValueError('MAIN_REQUIRED: previous task creation is complete or uncertain but its remote marker is absent. Inspect the task list; do not blindly create another task or change the operation key.')
  # No automatic insert retry: Google Tasks has no caller-supplied resource ID.
  result=service.tasks().insert(tasklist=tasklist,body=request).execute()
  conn.execute('UPDATE operations SET state=?,resource_id=? WHERE key=?',('complete',result['id'],key))
  return 'created',result
