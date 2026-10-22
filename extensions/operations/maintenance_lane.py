"""Pure scheduling and delivery policy for the consolidated maintenance lane."""
def slots(now):
    day=now.date().isoformat()
    result={'health':now.strftime('%Y-%m-%dT%H'),'cleanup':day}
    if (now.hour,now.minute)>=(8,15):result['summary']=day
    if now.weekday()==6 and now.hour>=18:result['lib']=now.strftime('%G-W%V')
    return result

def backup_slot(now):
    if now.hour!=3:return None
    return 'primary' if now.minute<15 else 'supplemental'
