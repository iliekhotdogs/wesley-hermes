# Wesley's Hermes Setup

This is a backup of my personal [Hermes Agent](https://github.com/NousResearch/hermes-agent) configuration. If you clone this repo and set it up on your own machine, you will get the same Hermes setup I use -- same model, same personality, same skills, same scheduled jobs, same Discord behavior.

## What is Hermes?

Hermes is an AI agent that runs in your terminal (or as a desktop app, or connected to Discord/Slack/Telegram/etc.). You talk to it, and it can:

- Answer questions using any AI model you choose (OpenAI, Anthropic, local models, etc.)
- Run commands on your computer
- Read and write files
- Search the web
- Do scheduled tasks (like daily reminders, automated checks)
- Remember things across conversations (memory)

Think of it like a super-configurable AI assistant that lives on your machine and can do real work, not just chat.

## What is in this repo

This repo contains my personal configuration for Hermes -- not the Hermes app itself. Specifically:

- config.yaml -- the main settings: which AI model I use, how it behaves, Discord settings, approvals, etc.
- SOUL.md -- my personality prompt that tells Hermes how to act
- profiles/ -- configs and personalities for different Hermes profiles (main, builder, speedy, etc.)
- skills/ -- the skills I have installed
- plugins/ -- custom plugins I use
- cron-main/jobs.json -- my scheduled jobs
- assets/avatar.png -- my Hermes avatar
- .env.placeholder-note / auth.placeholder-note -- notes for what secrets to add

## Requirements

1. Hermes Agent installed -- see https://hermes-agent.nousresearch.com
2. A GitHub account (for the gh CLI)
3. API keys for your AI model provider (OpenAI, Anthropic, OpenRouter, etc.)
4. Discord bot token (optional, if you want Hermes on Discord)
5. Any other service credentials for skills you want to use

You do NOT need: the Hermes source code (Hermes installs itself).

## Setup on a new machine

### For Mac / Linux

#### Step 1: Install Hermes

```bash
curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash
hermes setup   # first time only -- picks model, connects accounts
```

#### Step 2: Clone this repo

```bash
git clone https://github.com/iliekhotdogs/wesley-hermes.git
cd wesley-hermes
```

#### Step 3: Copy files into your Hermes home (~/.hermes)

```bash
# Main config + personality
cp config.yaml SOUL.md ~/.hermes/

# Profiles (optional -- copy the ones you want)
mkdir -p ~/.hermes/profiles/{main,builder,speedy,cowsearcher,cron,lib}
cp -r profiles/* ~/.hermes/profiles/

# Skills
cp -r skills-main ~/.hermes/profiles/main/skills/
cp -r skills-builder ~/.hermes/profiles/builder/skills/
# ... etc for other skill dirs

# Plugins
cp -r plugins/* ~/.hermes/plugins/
cp -r plugins-main ~/.hermes/profiles/main/plugins/
cp -r plugins-lib ~/.hermes/profiles/lib/plugins/

# Cron jobs
cp cron-main/jobs.json ~/.hermes/cron/
cp cron-cron/jobs.json ~/.hermes/cron/

# Optional extras
cp assets/avatar.png ~/.hermes/assets/
cp channel_directory.json discord_threads.json gateway_state.json ~/.hermes/
```

#### Step 4: Add your secrets

This repo has NO secrets. Create two files in ~/.hermes:

```bash
# .env -- your API keys
echo "OPENAI_API_KEY=sk-..." >> ~/.hermes/.env
echo "ANTHROPIC_API_KEY=sk-..." >> ~/.hermes/.env
# ... whatever your provider needs
```

```bash
# auth.json -- OAuth tokens ({} is fine to start)
echo '{}' > ~/.hermes/auth.json
```

See .env.placeholder-note and auth.placeholder-note in this repo for details.

#### Step 5: Discord (if you use it)

Replace discord_threads.json and channel_directory.json with your own channel IDs, or set up Discord from scratch with `hermes setup`.

#### Step 6: Start Hermes

```bash
hermes
# or: hermes chat -q "What can you do?"
```

### For Windows

#### Step 1: Install Hermes

Run PowerShell as Administrator and run:

```powershell
curl -fsSL https://hermes-agent.nousresearch.com/install.sh -o install.sh
bash install.sh
hermes setup   # first time only -- picks model, connects accounts
```

Or use Git Bash / WSL terminal:

```bash
curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash
hermes setup   # first time only -- picks model, connects accounts
```

#### Step 2: Clone this repo

In Git Bash, PowerShell, or WSL:

```bash
git clone https://github.com/iliekhotdogs/wesley-hermes.git
cd wesley-hermes
```

#### Step 3: Copy files into your Hermes home

On Windows, your Hermes home is at:
`C:\Users\<your-username>\AppData\Local\hermes`

Replace `<your-username>` with your actual Windows username (e.g. wesle).

**In Git Bash:**
```bash
# Main config + personality
cp config.yaml SOUL.md /c/Users/<your-username>/AppData/Local/hermes/

# Profiles (optional -- copy the ones you want)
mkdir -p /c/Users/<your-username>/AppData/Local/hermes/profiles/{main,builder,speedy,cowsearcher,cron,lib}
cp -r profiles/* /c/Users/<your-username>/AppData/Local/hermes/profiles/

# Skills
cp -r skills-main /c/Users/<your-username>/AppData/Local/hermes/profiles/main/skills/
cp -r skills-builder /c/Users/<your-username>/AppData/Local/hermes/profiles/builder/skills/
# ... etc for other skill dirs

# Plugins
cp -r plugins/* /c/Users/<your-username>/AppData/Local/hermes/plugins/
cp -r plugins-main /c/Users/<your-username>/AppData/Local/hermes/profiles/main/plugins/
cp -r plugins-lib /c/Users/<your-username>/AppData/Local/hermes/profiles/lib/plugins/

# Cron jobs
cp cron-main/jobs.json /c/Users/<your-username>/AppData/Local/hermes/cron/
cp cron-cron/jobs.json /c/Users/<your-username>/AppData/Local/hermes/cron/

# Optional extras
cp assets/avatar.png /c/Users/<your-username>/AppData/Local/hermes/assets/
cp channel_directory.json discord_threads.json gateway_state.json /c/Users/<your-username>/AppData/Local/hermes/
```

**In PowerShell (run as your normal user, not admin):**
```powershell
# Main config + personality
cp config.yaml, SOUL.md -Destination "$env:APPDATA\hermes\"

# Profiles
$mHermes = "$env:APPDATA\hermes"
foreach ($p in @("main","builder","speedy","cowsearcher","cron","lib")) {
    if (!(Test-Path "$mHermes\profiles\$p")) { New-Item -ItemType Directory -Path "$mHermes\profiles\$p" | Out-Null }
}
Copy-Item -Path "profiles\*" -Destination "$mHermes\profiles\" -Recurse -Force

# Skills
Copy-Item -Path "skills-main" -Destination "$mHermes\profiles\main\skills\" -Recurse -Force
Copy-Item -Path "skills-builder" -Destination "$mHermes\profiles\builder\skills\" -Recurse -Force
# ... etc for other skill dirs

# Plugins
Copy-Item -Path "plugins\*" -Destination "$mHermes\plugins\" -Recurse -Force
Copy-Item -Path "plugins-main" -Destination "$mHermes\profiles\main\plugins\" -Recurse -Force
Copy-Item -Path "plugins-lib" -Destination "$mHermes\profiles\lib\plugins\" -Recurse -Force

# Cron jobs
Copy-Item "cron-main/jobs.json" -Destination "$mHermes\cron\"
Copy-Item "cron-cron/jobs.json" -Destination "$mHermes\cron\"

# Optional extras
Copy-Item "assets/avatar.png" -Destination "$mHermes\assets\"
Copy-Item "channel_directory.json","discord_threads.json","gateway_state.json" -Destination "$mHermes\"
```

#### Step 4: Add your secrets

This repo has NO secrets. Create two files in your Hermes home:

**In Git Bash:**
```bash
# .env -- your API keys
echo "OPENAI_API_KEY=sk-..." >> /c/Users/<your-username>/AppData/Local/hermes/.env
echo "ANTHROPIC_API_KEY=sk-..." >> /c/Users/<your-username>/AppData/Local/hermes/.env
# ... whatever your provider needs
```

```bash
# auth.json -- OAuth tokens ({} is fine to start)
echo '{}' > /c/Users/<your-username>/AppData/Local/hermes/auth.json
```

**In PowerShell:**
```powershell
# .env
@"OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-...
"@ | Out-File -FilePath "$env:APPDATA\hermes\.env" -Encoding UTF8

# auth.json
"{}" | Out-File -FilePath "$env:APPDATA\hermes\auth.json" -Encoding UTF8
```

See .env.placeholder-note and auth.placeholder-note in this repo for details.

#### Step 5: Discord (if you use it)

Replace discord_threads.json and channel_directory.json with your own channel IDs, or set up Discord from scratch with `hermes setup`.

#### Step 6: Start Hermes

In Git Bash, PowerShell, or WSL:

```bash
hermes
# or: hermes chat -q "What can you do?"
```

## What this setup does (simple terms)

- Uses stepfun/step-3.7-flash:free model via the nous provider (changeable in config.yaml)
- Technical personality by default (others available: helpful, concise, creative, teacher, kawaii, catgirl, pirate, shakespeare, surfer, noir, uwu, philosopher, hype)
- 6 Hermes profiles: main, builder, speedy, cowsearcher, cron, lib
- Many skills installed: GitHub, PDF editing, productivity, creative tools, research, web search, and more
- 2 scheduled cron jobs (see cron-main/jobs.json, cron-cron/jobs.json)
- second-brain-retrieval plugin for memory
- Custom hermes-token-router plugin for API token routing

## Customizing

- Model: change model.default in config.yaml
- Personality: change display.personality
- Discord: update the discord section with your bot token + channel IDs
- Skills: toggle in skills.disabled list or install new ones
- Cron: edit cron/jobs.json

## Keeping in sync

```bash
cd wesley-hermes
cp ~/.hermes/config.yaml .       # Mac/Linux
# or: cp /c/Users/<you>/AppData/Local/hermes/config.yaml .   # Windows (Git Bash)

git add -A
git commit -m "Update: what changed"
git push
```

The .gitignore blocks secrets (.env, auth.json) and conversation history (state.db), so git add -A is safe.

## Questions

This is my personal setup. If something does not work for you, check config.yaml and add any missing credentials. For general help: https://hermes-agent.nousresearch.com/docs
