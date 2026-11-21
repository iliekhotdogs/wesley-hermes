# Providers & Model Aliases

Set via `hermes model` (picker) or `hermes setup`. 35+ provider profiles ship as
plugins under `plugins/model-providers/`; user plugins of the same name override.
Full docs: https://hermes-agent.nousresearch.com/docs/integrations/providers

### Providers

| Provider | Auth | Key env var(s) |
|----------|------|----------------|
| openrouter | API key | `OPENROUTER_API_KEY` |
| anthropic | API key | `ANTHROPIC_API_KEY` (also `CLAUDE_CODE_OAUTH_TOKEN`) |
| nous | OAuth device code | `hermes auth add nous` (or `NOUS_API_KEY`) |
| openai-codex | OAuth | `hermes auth add openai-codex` |
| qwen-oauth | OAuth | `hermes auth add qwen-oauth` |
| minimax-oauth | OAuth | `hermes auth add minimax-oauth` |
| copilot | Token | `COPILOT_GITHUB_TOKEN` / `GH_TOKEN` (Copilot device flow — `gh auth login` tokens do NOT work) |
| copilot-acp | External CLI | Copilot CLI on PATH or `COPILOT_CLI_PATH` |
| gemini | API key | `GOOGLE_API_KEY` or `GEMINI_API_KEY` |
| xai | API key | `XAI_API_KEY` (SuperGrok OAuth also supported) |
| deepseek | API key | `DEEPSEEK_API_KEY` |
| zai (GLM) | API key | `GLM_API_KEY` / `ZAI_API_KEY` |
| minimax / minimax-cn | API key | `MINIMAX_API_KEY` / `MINIMAX_CN_API_KEY` |
| kimi-coding / -cn | API key | `KIMI_API_KEY` / `KIMI_CN_API_KEY` |
| alibaba (+coding-plan) | API key | `DASHSCOPE_API_KEY` / `ALIBABA_CODING_PLAN_API_KEY` |
| xiaomi | API key | `XIAOMI_API_KEY` |
| huggingface | Token | `HF_TOKEN` |
| fireworks / novita / nvidia / deepinfra / gmi / arcee / stepfun / upstage / kilocode / ai-gateway / opencode-zen / opencode-go / ollama-cloud | API key | `<NAME>_API_KEY` |
| bedrock / vertex / azure-foundry | Cloud SDK / key | AWS SDK creds / Vertex ADC / `AZURE_FOUNDRY_API_KEY` |
| custom | Config | `model.base_url` + `model.api_key` in config.yaml |

Multiple credentials per provider pool and rotate automatically (`hermes auth`).
Fallback chain when the primary fails: `hermes fallback add|remove|list`.

### Free-model replacement verification

- Inspect the live Nous inference `/v1/models` catalog (production origin `https://inference-api.nousresearch.com`) for exact IDs, zero prompt/completion pricing, tool support and expiry; the static docs manifest can omit free variants. The public catalog is usable without credentials for selection, not for generation.
- Pin the explicit `:free` row when the catalog lists paid and free versions under the same display name. A portal FREE badge or matching base name does not make the unsuffixed ID free.
- Verify execution credentials with owning-profile `resolve_runtime_provider(requested='nous', target_model=<exact-id>)`, not only auth-store status; credential pools and runtime resolution may differ. Keep secrets out of output. Missing account login cannot be fixed by changing models, and a catalog read never proves a generation succeeded.
- Preserve healthy profile defaults and intentional pauses when replacing stale blocked-job/task overrides. Record the exact model/provider change and credential limitation; do not resume obsolete bootstrap cards whose body would overwrite a working default.

### User-defined model aliases

Work with `/model <name>` in CLI and every gateway platform. Resolved by
`hermes_cli/model_switch.py::resolve_alias()`; user aliases are checked BEFORE
the built-in table, so a user `sonnet`/`grok` shadows the built-in.

```yaml
# Full form
model_aliases:
  fav:
    model: claude-sonnet-4.6
    provider: anthropic
  local-qwen:
    model: qwen3.5:397b
    provider: custom
    base_url: "https://ollama.com/v1"

# Short form ("provider/model"), also via CLI:
#   hermes config set model.aliases.fav openrouter/anthropic/claude-sonnet-4.6
model:
  aliases:
    fav: openrouter/anthropic/claude-sonnet-4.6
```

`/model fav` — session-scoped; add `--global` to persist as default.

Built-in aliases (catalog-resolved against the active provider): `sonnet`,
`opus`, `haiku`, `claude`, `gpt5`, `gpt`, `codex`, `o3`, `o4`, `gemini`,
`deepseek`, `grok`, `llama`, `qwen`, `minimax`, `nemotron`, `kimi`, `glm`,
`step`, `mimo`, `trinity`.

### Switching a profile's model via `hermes config set` (not `/model`)

To change a PROFILE's default model/provider from outside its session (e.g. main
reconfiguring `builder`), first verify the exact requested model ID in the provider's
current catalog. Then use `hermes -p <name> config set model.provider <provider>` and
`hermes -p <name> config set model.default <model>` — not `/model`, which is
session-scoped and requires being inside that profile's chat. Set effort with
`hermes -p <name> config set agent.reasoning_effort low|medium|high` and read the
profile's config back. The config CLI may warn that `agent.reasoning_effort` is
unrecognized despite saving it; verify runtime use in the installed source or a
live run rather than equating that warning with either success or failure.

- **Pick the provider that matches the actual credential, not just the vendor name.**
  `hermes auth list --profile <name>` shows the live credential per provider key. A Claude
  Code / Claude subscription OAuth credential (shown under provider key `anthropic` with an
  `oauth claude_code` row) only resolves built-in aliases like `opus`/`sonnet`/`haiku` when
  `model.provider` is set to `claude-subscription-directsdk-experimental` — setting
  `model.provider: anthropic` instead sends the literal alias string (e.g. `"opus"`) straight
  to `api.anthropic.com` as a model id and gets `404 model: opus`, even though `hermes doctor`
  echoes the config back as if it were fine. If a sibling profile already uses the same OAuth
  credential successfully, check its `config.yaml` `model.provider` and copy that id.
- **For a new specialist profile, create a fresh profile rather than cloning main.** A clone can bring administrative SOUL instructions, messaging credentials, private memories, and unrelated plugins. Set its role/description and dedicated workspace explicitly; if an existing trusted user-installed provider plugin is required, copy only that plugin's nonsecret code and enable it in the new profile. Do not copy `.env`, `auth.json`, or Discord tokens. Check live OAuth resolution first: a fresh profile may already use the host's supported account credentials without a copied login. Test the primary and explicit backup separately, verify the recorded session model IDs, and resolve reasoning settings for both models; a successful backup test is not proof of automatic failover.
- **Do not turn a profile setup into an engine update.** If the launcher encounters an unfinished source-update marker or dependency bootstrap, preserve the pinned/live engine and use the already working interpreter/runtime for bounded verification when possible. Report the maintenance warning separately; never follow a generic `run hermes update` suggestion blindly. Use `plugins list --plain --no-bundled` for a compact user-provider check.
- **Verify with a live call, not `hermes doctor`.** `hermes doctor` only echoes
  `model.provider`/`model.default` from config; it never calls the API, so it reports success
  even when the alias will 404. Confirm with `hermes chat -q "..." --profile <name>` and read
  the actual reply / "Model fallback" line, or check `logs/errors.log` under the profile's home
  for `NotFoundError` if the reply looks wrong.
- A `fallback_providers` entry (e.g. falling back to `sonnet` on a known-working provider) is a
  reasonable safety net to leave in place once the primary provider id is correct — it only
  engages if the primary genuinely fails.
- **Setting `fallback_providers`/`fallback_model` via `config set` needs the right shape.**
  `fallback_providers` is a list — pass it as a JSON array string, and once it already has a
  value, replacing it requires `--force` (`hermes config set --force fallback_providers
  '[{"provider":"openai-codex","model":"gpt-6.1-sol"}]'`). `fallback_model` is a section with
  sub-keys, not a scalar — set its leaves individually: `hermes config set
  fallback_model.provider <p>` then `hermes config set fallback_model.model <m>` (or
  `--force` with a dict literal to replace the whole section at once). Update both
  `fallback_providers` and `fallback_model` together — a board/report script may read either
  one, and leaving them out of sync reproduces the exact display-discrepancy bug noted above.
- **"Flip primary and backup" means swap the two pairs, not just the model id**: capture both
  the old primary's provider+model and the old backup's provider+model before writing, since
  `model.default`/`model.provider` must become the backup's old values while
  `fallback_providers`/`fallback_model` become the old primary's values — a true swap, not a
  one-sided edit.
- Before trusting a board-rendering helper's table/line count, write a small throwaway Python check
  (not browser/terminal side effects) exercising the parsing function directly — e.g. call its
  `thinking()`/`profile_models()`/`render()` functions on sample input and assert counts — then
  delete the scratch file. This catches parser regressions (e.g. a new field not being emitted
  for every row) before relying on a live Discord diff as the only check.
- When a per-profile board/report script gains a new displayed field (e.g. reasoning effort),
  add it to BOTH the per-profile data function and the render loop in the same edit, and bump
  the help/footer text that lists valid "set X to Y" commands so the chat-driven command syntax
  stays discoverable.
- `hermes gateway restart` / `profile restart` cannot be run from inside the gateway process
  itself (SIGTERM would kill the command). Run it from a separate shell, or skip it entirely: a
  plain `config set` takes effect on the profile's next task dispatch without a restart, which a
  `hermes chat -q` verification call already exercises.
- For a Discord model board, refresh it only after changes are verified, then read back the
  pinned message. Cross-check both `fallback_providers` and `fallback_model`: a board
  renderer can misparse an unindented YAML list and display the latter even though the
  former is configured. Don't silently overwrite either fallback to reconcile a display
  discrepancy; report it or fix the parser as a separate scoped task.
