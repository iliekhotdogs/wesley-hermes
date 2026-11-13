# Delivering a non-main profile's cron jobs to Discord

Use when a scheduled job under a profile other than main/cron (e.g. lib) must post to a dedicated channel.

## Steps
1. **Create one channel per job** in the AUTOMATIONS category (existing convention: emoji + name, topic `<Job name> | cron:<id> | <schedule>. Dedicated direct-channel cron output.`). `discord_admin` cannot create channels; POST `/guilds/<id>/channels` (type 0, `parent_id` = category) with the bot token from the profile `.env`, read inside the script and never printed. Send a `User-Agent` header or Discord's edge rejects the call.
2. **Give the profile delivery credentials.** The cron preflight blocks with `delivery platform 'discord' has no gateway credentials configured` unless the profile has `DISCORD_BOT_TOKEN` in its `.env` AND `platforms.discord.enabled: true` in its `config.yaml`. A job-level `deliver: discord:<channel_id>` alone is not enough. `bot-chat:<profile>` is the credential-free alternative (relayed by that profile).
3. **Stop the profile answering chat.** Reusing main's token starts a second gateway on the same bot; set the profile's `DISCORD_ALLOWED_USERS` to a non-matching value (e.g. `0`) so it ignores inbound messages. Back up `.env`/`config.yaml` first.
4. `hermes -p <profile> cron edit <job> --deliver discord:<channel_id>`, run once with `hermes -p <profile> cron run <job>`, then read the channel via REST to confirm the post landed.

## Model pitfall
A `cron:` block in the profile `config.yaml` with `model:` / `model_provider:` overrides the profile's model for every cron job, so a stale free-tier entry keeps being used (and falling back) long after the profile model was changed. Remove the override, or pin per job with `cron edit --model X --provider Y`.

## Agent capability pitfalls for scheduled jobs
- Check the profile's `platform_toolsets` before designing a job: a profile without `terminal` cannot run scripts, so move deterministic work (diffing, indexing, logging) into the job's pre-run `--script`, whose stdout is injected into the prompt, and leave only file reads/writes to the agent.
- `write_file` refuses to overwrite a file last read with offset/limit pagination; have the agent `read_file` fully first, use `patch`, or take the file out of the agent's hands entirely (generate it in the pre-run script).
- Low `agent.max_turns` (16) silently truncates multi-file batches; size the batch to the turn budget.
