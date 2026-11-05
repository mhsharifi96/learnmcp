#!/usr/bin/env bash
# learnmcp deployment helper (Docker Compose).
#
#   ./deploy.sh init --domain learn.example.com   # first time on a server (HTTPS via Caddy)
#   ./deploy.sh init --local                       # local test on http://localhost:8000
#   ./deploy.sh deploy [--pull] [--no-backup]      # build + (re)start + health check
#   ./deploy.sh help                               # all commands
set -euo pipefail

cd "$(dirname "$0")"

ENV_FILE=".env"
BACKUP_DIR="backups"
BACKUP_KEEP="${BACKUP_KEEP:-14}"
HEALTH_TIMEOUT="${HEALTH_TIMEOUT:-180}"

# ------------------------------------------------------------------ output helpers
if [ -t 1 ]; then
  C_RED=$'\033[31m'; C_GRN=$'\033[32m'; C_YEL=$'\033[33m'; C_BLU=$'\033[34m'; C_OFF=$'\033[0m'
else
  C_RED=""; C_GRN=""; C_YEL=""; C_BLU=""; C_OFF=""
fi
info() { echo "${C_BLU}==>${C_OFF} $*"; }
ok()   { echo "${C_GRN}✔${C_OFF} $*"; }
warn() { echo "${C_YEL}!${C_OFF} $*" >&2; }
die()  { echo "${C_RED}✘ $*${C_OFF}" >&2; exit 1; }

# ------------------------------------------------------------------ helpers
compose() { docker compose --env-file "$ENV_FILE" "$@"; }

require_docker() {
  command -v docker >/dev/null 2>&1 || die "Docker is not installed. See https://docs.docker.com/engine/install/"
  docker compose version >/dev/null 2>&1 || die "Docker Compose v2 is required (the 'docker compose' plugin)."
  docker info >/dev/null 2>&1 || die "Cannot talk to the Docker daemon (is it running? are you in the docker group?)."
}

require_env() {
  [ -f "$ENV_FILE" ] || die "$ENV_FILE not found. Run: ./deploy.sh init --domain your.domain (or --local)"
}

get_env() {  # get_env KEY -> value from .env (last occurrence, quotes stripped)
  [ -f "$ENV_FILE" ] || return 0
  grep -E "^$1=" "$ENV_FILE" | tail -n1 | cut -d= -f2- | sed -e 's/^"//' -e 's/"$//' -e "s/^'//" -e "s/'$//"
}

set_env() {  # set_env KEY VALUE  (portable in-place edit)
  local key="$1" value="$2" tmp
  tmp="$(mktemp)"
  if grep -qE "^${key}=" "$ENV_FILE"; then
    awk -v k="$key" -v v="$value" 'BEGIN{FS=OFS="="} $1==k {print k "=" v; next} {print}' "$ENV_FILE" >"$tmp"
  else
    cat "$ENV_FILE" >"$tmp"; echo "${key}=${value}" >>"$tmp"
  fi
  mv "$tmp" "$ENV_FILE"
}

random_secret() {  # random_secret BYTES -> hex
  local n="${1:-32}"
  if command -v openssl >/dev/null 2>&1; then openssl rand -hex "$n"
  elif command -v python3 >/dev/null 2>&1; then python3 -c "import secrets;print(secrets.token_hex($n))"
  else head -c "$n" /dev/urandom | od -An -tx1 | tr -d ' \n'; fi
}

validate_env() {
  local key pw
  key="$(get_env DJANGO_SECRET_KEY)"; pw="$(get_env POSTGRES_PASSWORD)"
  [ -n "$key" ] && [[ "$key" != change-me* ]] || die "DJANGO_SECRET_KEY is not set in $ENV_FILE."
  [ -n "$pw" ] && [[ "$pw" != change-me* ]] || die "POSTGRES_PASSWORD is not set in $ENV_FILE."
  if [[ "$(get_env COMPOSE_PROFILES)" == *https* ]]; then
    local domain; domain="$(get_env DOMAIN)"
    [ -n "$domain" ] && [ "$domain" != "learn.example.com" ] || die "Set DOMAIN in $ENV_FILE (or clear COMPOSE_PROFILES to run without Caddy)."
  fi
  [ "$(get_env DJANGO_DEBUG)" = "true" ] && warn "DJANGO_DEBUG=true — do not use this in production."
  return 0
}

web_container() { compose ps -q web 2>/dev/null | head -n1; }

wait_healthy() {
  local cid status elapsed=0
  info "Waiting for the web container to become healthy (timeout ${HEALTH_TIMEOUT}s)..."
  while [ "$elapsed" -lt "$HEALTH_TIMEOUT" ]; do
    cid="$(web_container)"
    if [ -n "$cid" ]; then
      status="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$cid" 2>/dev/null || echo unknown)"
      case "$status" in
        healthy) ok "web is healthy"; return 0 ;;
        exited|dead) break ;;
      esac
    fi
    sleep 3; elapsed=$((elapsed + 3))
  done
  warn "web did not become healthy. Last logs:"
  compose logs --tail=80 web || true
  return 1
}

db_running() { [ -n "$(compose ps -q --status running db 2>/dev/null)" ]; }

print_urls() {
  local base port; base="$(get_env PUBLIC_BASE_URL)"; port="$(get_env WEB_PORT)"
  [ -n "$base" ] || base="http://localhost:${port:-8000}"
  echo
  ok "learnmcp is up"
  echo "   Home / students : $base/"
  echo "   Instructor panel: $base/admin/   (sign up at $base/signup/)"
  echo "   Health          : $base/healthz"
  echo "   MCP endpoint    : $base/s/<student-token>/mcp"
}

# ------------------------------------------------------------------ commands
cmd_nginx_conf() {
  require_env
  local domain port
  domain="$(get_env DOMAIN)"; port="$(get_env WEB_PORT)"; port="${port:-8000}"
  [ -n "$domain" ] || die "DOMAIN is not set in $ENV_FILE."
  sed -e "s/__DOMAIN__/${domain}/g" -e "s/__PORT__/${port}/g" docker/nginx-host.conf
}

cmd_init() {
  local domain="" local_mode=false force=false external_proxy=false port=""
  while [ $# -gt 0 ]; do
    case "$1" in
      --domain) domain="${2:-}"; shift 2 ;;
      --local) local_mode=true; shift ;;
      --external-proxy) external_proxy=true; shift ;;
      --port) port="${2:-}"; shift 2 ;;
      --force) force=true; shift ;;
      *) die "Unknown option for init: $1" ;;
    esac
  done
  if [ -f "$ENV_FILE" ] && [ "$force" != true ]; then
    die "$ENV_FILE already exists. Use --force to regenerate it (secrets will change!)."
  fi
  [ -f .env.example ] || die ".env.example missing."
  if [ "$local_mode" != true ] && [ -z "$domain" ]; then
    read -r -p "Public domain for learnmcp (e.g. learn.example.com): " domain
    [ -n "$domain" ] || die "A domain is required (or use --local)."
  fi

  cp .env.example "$ENV_FILE"
  chmod 600 "$ENV_FILE"
  set_env DJANGO_SECRET_KEY "$(random_secret 48)"
  set_env POSTGRES_PASSWORD "$(random_secret 24)"

  if [ "$local_mode" = true ]; then
    set_env DJANGO_ALLOWED_HOSTS "localhost,127.0.0.1"
    set_env DJANGO_CSRF_TRUSTED_ORIGINS "http://localhost:8000,http://127.0.0.1:8000"
    set_env PUBLIC_BASE_URL "http://localhost:8000"
    set_env DJANGO_SECURE_COOKIES "false"
    set_env COMPOSE_PROFILES ""
    set_env DOMAIN ""
    ok "Created $ENV_FILE for local use (http://localhost:8000)."
    warn "Claude/ChatGPT need public HTTPS: expose port 8000 with a tunnel (cloudflared/ngrok) and set PUBLIC_BASE_URL + DJANGO_ALLOWED_HOSTS + DJANGO_CSRF_TRUSTED_ORIGINS to the tunnel URL."
  else
    set_env DJANGO_ALLOWED_HOSTS "${domain},localhost,127.0.0.1"
    set_env DJANGO_CSRF_TRUSTED_ORIGINS "https://${domain}"
    set_env PUBLIC_BASE_URL "https://${domain}"
    set_env DJANGO_SECURE_COOKIES "true"
    set_env DOMAIN "$domain"
    if [ "$external_proxy" = true ]; then
      # An existing reverse proxy (e.g. host nginx) terminates TLS and forwards to 127.0.0.1:PORT.
      set_env COMPOSE_PROFILES ""
      set_env WEB_BIND "127.0.0.1"
      [ -n "$port" ] && set_env WEB_PORT "$port"
      ok "Created $ENV_FILE for https://${domain} behind an existing proxy on 127.0.0.1:${port:-8000}."
      echo "   Generate the nginx site with: ./deploy.sh nginx-conf > /tmp/${domain}.conf"
    else
      set_env COMPOSE_PROFILES "https"
      ok "Created $ENV_FILE for https://${domain} (Caddy will fetch a Let's Encrypt certificate)."
      warn "Make sure DNS for ${domain} points at this server and ports 80/443 are open."
    fi
  fi
  echo "   Review $ENV_FILE, then run: ./deploy.sh deploy"
}

cmd_backup() {
  require_docker; require_env
  db_running || die "Database container is not running."
  mkdir -p "$BACKUP_DIR"
  local user db file
  user="$(get_env POSTGRES_USER)"; user="${user:-learnmcp}"
  db="$(get_env POSTGRES_DB)"; db="${db:-learnmcp}"
  file="$BACKUP_DIR/learnmcp-$(date +%Y%m%d-%H%M%S).sql.gz"
  info "Backing up database to $file"
  compose exec -T db pg_dump -U "$user" -d "$db" --clean --if-exists --no-owner | gzip >"$file"
  [ -s "$file" ] || die "Backup file is empty."
  ok "Backup written ($(du -h "$file" | cut -f1))"
  # Keep only the newest $BACKUP_KEEP backups.
  ls -1t "$BACKUP_DIR"/learnmcp-*.sql.gz 2>/dev/null | tail -n +"$((BACKUP_KEEP + 1))" | while read -r old; do
    rm -f -- "$old"
  done
}

cmd_restore() {
  require_docker; require_env
  local file="${1:-}" yes="${2:-}"
  [ -n "$file" ] && [ -f "$file" ] || die "Usage: ./deploy.sh restore backups/<file>.sql.gz [--yes]"
  db_running || die "Database container is not running (run ./deploy.sh up first)."
  if [ "$yes" != "--yes" ]; then
    read -r -p "This REPLACES the current database with $file. Type 'restore' to continue: " answer
    [ "$answer" = "restore" ] || die "Aborted."
  fi
  local user db
  user="$(get_env POSTGRES_USER)"; user="${user:-learnmcp}"
  db="$(get_env POSTGRES_DB)"; db="${db:-learnmcp}"
  info "Stopping web while restoring"
  compose stop web caddy >/dev/null 2>&1 || true
  gunzip -c "$file" | compose exec -T db psql -q -v ON_ERROR_STOP=1 -U "$user" -d "$db"
  compose up -d
  wait_healthy && ok "Restored $file"
}

cmd_deploy() {
  local pull=false backup=true
  while [ $# -gt 0 ]; do
    case "$1" in
      --pull) pull=true; shift ;;
      --no-backup) backup=false; shift ;;
      *) die "Unknown option for deploy: $1" ;;
    esac
  done
  require_docker; require_env; validate_env

  if [ "$pull" = true ]; then
    if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
      info "Pulling latest code"
      git pull --ff-only
    else
      warn "Not a git repository; skipping --pull."
    fi
  fi

  if [ "$backup" = true ] && db_running; then
    cmd_backup
  fi

  # Keep the currently running image as learnmcp:previous for ./deploy.sh rollback.
  if docker image inspect learnmcp:latest >/dev/null 2>&1; then
    docker tag learnmcp:latest learnmcp:previous
  fi
  if docker image inspect learnmcp-frontend:latest >/dev/null 2>&1; then
    docker tag learnmcp-frontend:latest learnmcp-frontend:previous
  fi

  info "Building images"
  IMAGE_TAG=latest compose build --pull web frontend

  info "Starting services"
  IMAGE_TAG=latest compose up -d --remove-orphans

  if ! wait_healthy; then
    die "Deploy failed. Fix the error above, or run ./deploy.sh rollback to restart the previous image."
  fi
  docker image prune -f >/dev/null 2>&1 || true
  print_urls
}

cmd_rollback() {
  require_docker; require_env
  docker image inspect learnmcp:previous >/dev/null 2>&1 || die "No previous image (learnmcp:previous) to roll back to."
  warn "Rolling back the web image. Database migrations are NOT reverted; restore a backup if needed."
  IMAGE_TAG=previous compose up -d --no-build web frontend
  wait_healthy && ok "Rolled back to learnmcp:previous"
}

cmd_seed() {
  require_docker; require_env
  local base; base="$(get_env PUBLIC_BASE_URL)"
  compose exec web python manage.py seed_demo ${base:+--base-url "$base"} "$@"
}

usage() {
  cat <<EOF
learnmcp deploy helper

Setup
  init --domain DOMAIN      Create .env with random secrets for https://DOMAIN (Caddy + Let's Encrypt)
  init --domain DOMAIN --external-proxy [--port N]
                            Same, but behind an existing reverse proxy (host nginx) on 127.0.0.1:N
  nginx-conf                Print a host-nginx site for DOMAIN -> 127.0.0.1:WEB_PORT
  init --local              Create .env for local http://localhost:8000 (no Caddy)
                            add --force to overwrite an existing .env

Deploy
  deploy [--pull] [--no-backup]
                            Backup DB, build image, start everything, wait for health
  rollback                  Restart the previous web image
  up | down | restart       Start / stop / restart services without rebuilding
  status                    Show containers and health
  logs [service]            Follow logs (web, frontend, gateway, db, caddy)

Operations
  migrate                   Run Django migrations
  createsuperuser           Create the platform operator account
  seed [--username U ...]   Create a demo instructor, class and student (prints the MCP URL)
  manage <args>             Run any manage.py command, e.g. ./deploy.sh manage shell
  backup                    Dump Postgres to backups/ (keeps the newest $BACKUP_KEEP)
  restore FILE [--yes]      Restore a backup (replaces the database)
  test                      Run the test suite locally (needs uv)
EOF
}

main() {
  local cmd="${1:-help}"; shift || true
  case "$cmd" in
    init) cmd_init "$@" ;;
    nginx-conf) cmd_nginx_conf ;;
    deploy) cmd_deploy "$@" ;;
    rollback) cmd_rollback ;;
    up) require_docker; require_env; validate_env; compose up -d && wait_healthy && print_urls ;;
    down) require_docker; require_env; compose down "$@" ;;
    restart) require_docker; require_env; compose restart "$@" && wait_healthy ;;
    status|ps) require_docker; require_env; compose ps ;;
    logs) require_docker; require_env; compose logs -f --tail=200 "$@" ;;
    migrate) require_docker; require_env; compose exec web python manage.py migrate --noinput ;;
    createsuperuser) require_docker; require_env; compose exec web python manage.py createsuperuser ;;
    seed) cmd_seed "$@" ;;
    manage) require_docker; require_env; compose exec web python manage.py "$@" ;;
    backup) cmd_backup ;;
    restore) cmd_restore "$@" ;;
    test) command -v uv >/dev/null 2>&1 || die "uv is required: https://docs.astral.sh/uv/"; uv run --group dev pytest "$@" ;;
    help|-h|--help) usage ;;
    *) usage; die "Unknown command: $cmd" ;;
  esac
}

main "$@"
