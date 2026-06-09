Deployment options for HomesRug project

Prereqs:
- You have SSH access to your VPS (user@your-vps.com).
- Python 3.11+, virtualenv, pip, and PostgreSQL (or other DB) installed on the VPS, or Docker installed if using containers.

Option A — Push via Git (recommended if you have a bare repo on VPS)

1) On VPS: create a bare repo and a deploy hook (example):

```bash
# on VPS
mkdir -p ~/repos/homesrug.git
cd ~/repos/homesrug.git
git init --bare
# create a post-receive hook to checkout to /var/www/homesrug (example)
cat > hooks/post-receive <<'HOOK'
#!/bin/sh
WORKDIR=/var/www/homesrug
GIT_DIR=$(pwd)
rm -rf $WORKDIR
mkdir -p $WORKDIR
GIT_WORK_TREE=$WORKDIR git checkout -f
cd $WORKDIR
# optional: restart services, run migrations, collectstatic, etc.
# e.g., source /home/ubuntu/.venv/homesrug/bin/activate && pip install -r requirements.txt && python manage.py migrate && python manage.py collectstatic --noinput
HOOK
chmod +x hooks/post-receive
```

2) Locally: add remote and push

```bash
# locally in project root
git remote add vps ssh://user@your-vps.com/~/repos/homesrug.git
git push vps main
```

Option B — Rsync / SCP (simple manual copy)

```bash
# from local machine
# use rsync to copy files (excludes venv, .git, media)
rsync -avz --exclude='.git' --exclude='venv' --exclude='media' --exclude='staticfiles' ./ user@your-vps.com:/var/www/homesrug/
# then ssh into VPS and run:
ssh user@your-vps.com
cd /var/www/homesrug
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# configure env vars and database, run migrations, collectstatic, and restart app server
python manage.py migrate
python manage.py collectstatic --noinput
# restart gunicorn / systemd service
sudo systemctl restart homesrug
```

Option C — Docker / docker-compose (if you prefer containers)

If your VPS has Docker and docker-compose, you can build and run using the provided docker-compose-prod.yml or build image locally and push to a registry.

```bash
# on VPS (in project dir with Dockerfile + docker-compose-prod.yml)
docker compose -f docker-compose-prod.yml up -d --build
# check logs
docker compose -f docker-compose-prod.yml logs -f
```

Notes & next steps
- Environment variables (SECRET_KEY, DATABASE_URL, SHOPIFY credentials, etc.) must be set on the VPS (systemd env or .env file referenced by docker-compose).
- If you want, provide SSH access (user@host) and I can run the deploy steps for you.
- For automated deploys, consider setting up GitHub Actions / CI to push to VPS or to a registry.
