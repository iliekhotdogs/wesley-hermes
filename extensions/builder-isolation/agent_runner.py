"""One isolated named-Builder turn using explicit, inference-only credentials."""
import json
import os
from pathlib import Path
import sys

sys.path.insert(0, '/opt/hermes')
from run_agent import AIAgent


def main():
    request_path, result_path = map(Path, sys.argv[1:3])
    request = json.loads(request_path.read_text())
    os.chdir(request['workspace'])
    os.environ['TERMINAL_CWD'] = request['workspace']
    os.environ['TERMINAL_ENV'] = 'local'
    os.environ['HERMES_WRITE_SAFE_ROOT'] = request['workspace']
    for key in list(os.environ):
        if key.startswith('HERMES_KANBAN_'):
            os.environ.pop(key)
    agent = AIAgent(
        model=os.environ['BUILDER_MODEL'], provider='openai-codex', api_mode='codex_responses',
        api_key=os.environ['INFERENCE_PROXY_TOKEN'], base_url='http://hermes-inference:8766',
        max_iterations=30, enabled_toolsets=['file', 'terminal', 'code_execution', 'workflow-policy'],
        disabled_toolsets=['kanban', 'memory', 'session_search', 'delegation', 'messaging'],
        quiet_mode=True, save_trajectories=False, platform='cli', load_soul_identity=True,
        skip_memory=True, skip_background_review=True, fallback_model=None,
        reasoning_config={'enabled': True, 'effort': 'medium'},
        run_budget_seconds=request['timeout'],
    )
    instruction = '''Main assigned this Builder task through the trusted isolation bridge. The context below is the complete selected task, not a request to find other boards or profiles. Work only in your current selected workspace. You have no shared Kanban database, credentials, vault, or unassigned projects. The trusted bridge owns task status, heartbeat and completion; do not call Kanban tools. Call workflow_checkpoint before execution as usual.
When finished, your FINAL RESPONSE MUST be a JSON object (no Markdown fence) with keys: status (done or blocked), summary (string), tests (list of strings), risks (list of strings). Use blocked if you cannot perform or verify the assignment. Never claim inaccessible host paths were inspected. The bridge will return changed workspace files to Main after validating them.
\n'''
    try:
        location = ('\nYour actual workspace inside this container is ' + request['workspace']
                    + '. Host workspace paths in the task context are metadata; use this container path instead. '
                    'Git internals are excluded from snapshots, so Git status/history may be unavailable.\n\n')
        result = agent.run_conversation(instruction + location + request['context'])
        text = result.get('final_response') or ''
        try:
            outcome = json.loads(text)
            assert outcome['status'] in ('done', 'blocked')
            assert isinstance(outcome['summary'], str) and outcome['summary'].strip()
            assert isinstance(outcome.get('tests', []), list)
        except (ValueError, KeyError, AssertionError, TypeError):
            outcome = {'status': 'blocked', 'summary': 'Builder returned no valid structured completion. ' + str(text)[:3000], 'tests': []}
        if not result.get('completed') or result.get('failed'):
            outcome['status'] = 'blocked'
        result_path.write_text(json.dumps(outcome))
    except Exception as exc:
        result_path.write_text(json.dumps({'status': 'blocked', 'summary': 'Isolated Builder failed: ' + type(exc).__name__, 'tests': []}))
        raise
    finally:
        agent.close()


if __name__ == '__main__':
    main()
