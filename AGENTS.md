# AGENTS.md

## Cursor Cloud specific instructions

### Running the Application

```bash
./scripts/init-secrets.sh
cp .env.example .env   # edit Exchange server config (NO secrets needed in .env)
docker compose --profile local-db --profile local-redis up -d
```

Default login: `admin` / `123456` — Dashboard at http://localhost, API docs at http://localhost:18001/docs

### Docker in Cloud Agent VM

```bash
sudo mkdir -p /etc/docker
echo '{"storage-driver":"fuse-overlayfs"}' | sudo tee /etc/docker/daemon.json
sudo update-alternatives --set iptables /usr/sbin/iptables-legacy
sudo update-alternatives --set ip6tables /usr/sbin/ip6tables-legacy
sudo dockerd &>/tmp/dockerd.log &
sudo chmod 666 /var/run/docker.sock
```

### Lint / Test / Build

```bash
ruff check app/ tests/ scripts/       # lint
ruff format app/ tests/ scripts/      # format
pytest tests/ -v --ignore=tests/integration/ --ignore=tests/manual/   # 189 tests
docker compose --profile local-db --profile local-redis build         # build images
```

### Frontend

```bash
cd web && pnpm install && pnpm build    # install + build
cd web && pnpm lint                     # ESLint (has pre-existing prettier warnings)
cd web && pnpm dev                      # Vite dev server (port 3000)
```

### Gotchas

- MySQL and Redis use Docker Compose profiles — pass `--profile local-db --profile local-redis`.
- `.env` has NO secrets — passwords/keys are read from `secrets/` directory via Docker Secrets.
- `uvicorn --reload` locally needs `--reload-exclude ".docker-data/*"`.
- `pnpm install` may warn about ignored build scripts (`es5-ext`, `esbuild`, `vue-demi`); safe to ignore.
- Frontend `pnpm lint` reports ~600 pre-existing prettier/formatting errors; these do not block the build.
