"""Preserve the configured cleanup policy; count API failures accurately."""
import os,json,urllib.request,urllib.error
from pathlib import Path
from datetime import datetime,timezone,timedelta
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent/'.env',override=False)
TOKEN=os.environ.get('DISCORD_BOT_TOKEN','')
GUILD_ID='0'
AUTO_ARCHIVE_MINUTES=1440
DELETE_OLDER_THAN_HOURS=24

def api(method,path,body=None):
 request=urllib.request.Request('https://discord.com/api/v10'+path,
  data=json.dumps(body).encode() if body is not None else None,
  headers={'Authorization':'Bot '+TOKEN,'Content-Type':'application/json','User-Agent':'Hermes local cleanup'},method=method)
 try:
  with urllib.request.urlopen(request,timeout=20) as response:
   content=response.read()
   return json.loads(content) if content else {}
 except urllib.error.HTTPError as exc:
  raise RuntimeError(f'Discord HTTP {exc.code} on {method} {path}') from exc

def snowflake_to_datetime(value):
 return datetime.fromtimestamp(((int(value)>>22)+1420070400000)/1000,tz=timezone.utc)

def main():
 if not TOKEN:raise RuntimeError('DISCORD_BOT_TOKEN is not configured')
 channels=api('GET',f'/guilds/{GUILD_ID}/channels')
 text_channels=[c for c in channels if c.get('type')==0]
 enforced=deleted=failed=0
 cutoff=datetime.now(timezone.utc)-timedelta(hours=DELETE_OLDER_THAN_HOURS)
 for channel in text_channels:
  cid=channel['id']
  if channel.get('default_auto_archive_duration')!=AUTO_ARCHIVE_MINUTES:
   try:api('PATCH',f'/channels/{cid}',{'default_auto_archive_duration':AUTO_ARCHIVE_MINUTES});enforced+=1
   except (RuntimeError,urllib.error.URLError):failed+=1
  try:archived=api('GET',f'/channels/{cid}/threads/archived/public')
  except (RuntimeError,urllib.error.URLError):failed+=1;continue
  for thread in archived.get('threads',[]):
   if snowflake_to_datetime(thread['id'])<cutoff:
    try:api('DELETE',f"/channels/{thread['id']}");deleted+=1
    except (RuntimeError,urllib.error.URLError):failed+=1
 if enforced or deleted or failed:
  print(f'Thread cleanup: auto-archive updated={enforced}; deleted={deleted}; failed={failed}')
 else:print('[SILENT]')
 return 1 if failed else 0

if __name__=='__main__':raise SystemExit(main())
