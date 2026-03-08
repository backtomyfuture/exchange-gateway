# AGENTS.md

## Cursor Cloud specific instructions

### Running the Application

```bash
make init                 # generate secrets, copy .env, install deps
docker compose up -d      # start all services
```

Default login: `admin` / `123456` — Dashboard at http://localhost, API docs at http://localhost:18001/docs

### Docker in Cloud Agent VM

The VM runs inside a Firecracker container with cgroupv2 in threaded mode, which breaks `runc`. Use `crun` 1.20+ with `--cgroup-manager=disabled` as the default OCI runtime:

```bash
sudo apt-get update && sudo apt-get install -y fuse-overlayfs iptables crun
sudo curl -L https://github.com/containers/crun/releases/download/1.20/crun-1.20-linux-amd64 -o /usr/local/bin/crun && sudo chmod +x /usr/local/bin/crun
sudo mkdir -p /etc/docker
echo '{"storage-driver":"fuse-overlayfs","default-runtime":"crun","runtimes":{"crun":{"path":"/usr/local/bin/crun","runtimeArgs":["--cgroup-manager=disabled"]}},"default-cgroupns-mode":"host"}' | sudo tee /etc/docker/daemon.json
sudo update-alternatives --set iptables /usr/sbin/iptables-legacy
sudo update-alternatives --set ip6tables /usr/sbin/ip6tables-legacy
sudo dockerd &>/tmp/dockerd.log &
sleep 5 && sudo chmod 666 /var/run/docker.sock
```

The `deploy.resources` limits in docker-compose.yml require the `io` cgroup controller which is unavailable in the VM. Create a temporary override to remove them:

```bash
cat > docker-compose.override.yml << 'EOF'
services:
  app:
    deploy: { resources: { limits: { cpus: "0", memory: "0" }, reservations: { memory: "0" } } }
  webhook-worker:
    deploy: { resources: { limits: { cpus: "0", memory: "0" }, reservations: {} } }
  arq-worker:
    deploy: { resources: { limits: { cpus: "0", memory: "0" }, reservations: {} } }
EOF
```

**Do NOT commit `docker-compose.override.yml`** — it is only for the cloud VM environment.

### Lint / Test / Build

```bash
make lint       # ruff check + eslint
make test       # pytest (189 tests)
make build      # build Docker images
```

### Frontend

```bash
cd web && pnpm install && pnpm build    # install + build
cd web && pnpm lint                     # ESLint (has pre-existing prettier warnings)
cd web && pnpm dev                      # Vite dev server (port 3000)
```

### Gotchas

- `.env` has NO secrets — passwords/keys are read from `secrets/` directory via Docker Secrets.
- To use an external MySQL/Redis, comment out the service in docker-compose.yml and update `.env`.
- `uvicorn --reload` locally needs `--reload-exclude ".docker-data/*"`.
- `pnpm install` may warn about ignored build scripts (`es5-ext`, `esbuild`, `vue-demi`); safe to ignore.
- Frontend `pnpm lint` reports ~700 pre-existing prettier/formatting errors; these do not block the build.
