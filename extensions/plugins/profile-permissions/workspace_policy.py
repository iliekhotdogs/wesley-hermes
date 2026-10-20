"""Cron workspace_api request policy; shared by the hook and workspace_api.py itself."""
import re

DENIED = 'Google sharing, email sending, deletion, or authentication changes require main'
PUBLIC = re.compile(r'^[A-Za-z][A-Za-z0-9]*$')
# Sharing, invitations, moves, trash, deletes, and local-file uploads ride inside otherwise routine methods.
DENIED_KEYS = {'trashed', 'deleted', 'addparents', 'removeparents', 'parents', 'conferencedata', 'attendees',
               'media_body', 'media_mime_type', 'media', 'writerscanshare', 'copyrequireswriterpermission',
               'viewerscancopycontent'}
NOTIFY_KEYS = {'sendupdates', 'sendnotifications'}


def _denied_field(value):
    if isinstance(value, list):
        return any(_denied_field(v) for v in value)
    if not isinstance(value, dict):
        return False
    for key, inner in value.items():
        lowered = str(key).lower()
        if lowered in DENIED_KEYS:
            return True
        if lowered in NOTIFY_KEYS and inner not in ('none', False):
            return True
        if _denied_field(inner):
            return True
    return False


def workspace_request_reason(items, policy):
    """Return a block reason for a request object or list, or None when every request is routine."""
    routine = policy['cron_workspace_routine']
    docs_requests = set(policy['docs_batch_update_requests'])
    for item in items if isinstance(items, list) else [items]:
        if not isinstance(item, dict):
            return DENIED
        service, method, resource = item.get('service'), item.get('method'), item.get('resource')
        if not isinstance(service, str) or not isinstance(method, str) or not PUBLIC.fullmatch(method) \
                or not isinstance(resource, list) or not all(isinstance(s, str) and PUBLIC.fullmatch(s) for s in resource):
            return DENIED
        name = '.'.join(resource + [method])
        if name not in routine.get(service, ()):
            return DENIED
        if _denied_field([item.get('params'), item.get('body')]):
            return DENIED
        if service == 'docs' and name == 'documents.batchUpdate':
            body = item.get('body')
            requests = body.get('requests') if isinstance(body, dict) else None
            if not isinstance(requests, list) or not all(
                    isinstance(r, dict) and r and set(r) <= docs_requests for r in requests):
                return DENIED
    return None
