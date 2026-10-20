# openai-codex entitlement gate — condensed evidence

## Symptom
After `hermes auth add openai-codex` succeeds (`openai-codex: logged in`),
every model call fails identically:
```
HTTP 400: {"detail":"The 'gpt-5' model is not supported when using Codex with a ChatGPT account."}
```
The model name in the error tracks the model tried (gpt-5, gpt-5-codex,
gpt-4.1, gpt-4o, o3, o4-mini, gpt-4.1-mini, gpt-4o-mini, …). All fail the same
way. The IDENTICAL error across every model is the diagnostic — it means an
account/entitlement gate, NOT a wrong model name.

## Root cause (OpenAI server-side)
The Codex backend Hermes hits for this provider is
`https://chatgpt.com/backend-api/codex` (codex_responses mode, OAuth external).
It only serves accounts that have **Codex entitlement**:
- ChatGPT **Pro**, or
- Plus/Team with Codex enabled.

A basic Plus or Free account completes the OAuth device-code login but the
model call is rejected. Some gpt-5.x variants additionally require a paid
**API key** rather than the subscription.

## Sources (all corroborate: OAuth login OK, model call blocked by plan)
- OpenAI Dev Community thread "The 'gpt-5.2-codex' model is not supported when
  using Codex with a ChatGPT account" (community.openai.com/t/1378986).
- GitHub issue (openclaw) "[Bug]: openai-codex gpt-5.1/5.2/5.3 rejected on
  ChatGPT ..." — notes even if OAuth login works the account still needs Codex
  entitlement, else "model not supported with a ChatGPT account".
- AnswerOverflow/OpenClaw Q&A: "even if OAuth login works, your OpenAI account
  still needs Codex entitlement for the Codex model(s)". Confirms some models
  'require an API key' rather than working through ChatGPT-account Codex.
- Reddit r/opencodeCLI: multiple "FIXED: model not supported when using Codex
  with a ChatGPT account" threads.

## Practical conclusion
- The fix is at the account/plan layer (upgrade to Pro / enable Codex) OR switch
  Hermes to the `openai` provider with a real API key.
- Do NOT brute-force a list of model names expecting one to work — none will
  while the entitlement gate is in place.
