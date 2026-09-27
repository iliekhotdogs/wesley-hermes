# Wesley's Hermes Setup

This is a backup of my personal Hermes Agent configuration. If you clone this repo and set it up on your own machine, you will get the same Hermes setup I use -- same model, same personality, same skills, same scheduled jobs, same Discord behavior.

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

### Step 1: Install Hermes

    curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash
    hermes setup   # first time only -- picks model, connects accounts

### Step 2: Clone this repo

    git clone https://github.com/iliekhotdogs/wesley-hermes.git
    cd wesley-hermes

### Step 3: Copy files into your Hermes home (~/.hermes)

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

### Step 4: Add your secrets

This repo has NO secrets. Create two files in ~/.hermes:

    # .env -- your API keys
    OPENAI_API_KEY=sk-...
    ANTHROPIC_API_KEY=sk-...
    # ... whatever your provider needs

    # auth.json -- OAuth tokens ({} is fine to start)
    {}

See .env.placeholder-note and auth.placeholder-note in this repo for details.

### Step 5: Discord (if you use it)

Replace discord_threads.json and channel_directory.json with your own channel IDs, or set up Discord from scratch with hermes setup.

### Step 6: Start Hermes

    hermes
    # or: hermes chat -q "What can you do?"

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

    cd wesley-hermes
    cp ~/.hermes/config.yaml .
    cp ~/.hermes/SOUL.md .
    git add -A
    git commit -m "Update: what changed"
    git push

The .gitignore blocks secrets (.env, auth.json) and conversation history (state.db), so git add -A is safe.

## Questions

This is my personal setup. If something does not work for you, check config.yaml and add any missing credentials. For general help: https://hermes-agent.nousresearch.com/docs
