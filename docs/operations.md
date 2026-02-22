# Operations Runbook

## Backup

1. Export MinIO bucket data:
```bash
mc alias set local http://127.0.0.1:9000 "$MINIO_ROOT_USER" "$MINIO_ROOT_PASSWORD"
mc mirror local/rmbg-assets ./backups/rmbg-assets
```

2. Backup Redis snapshot:
```bash
docker compose exec redis redis-cli BGSAVE
docker cp rmbg-redis-1:/data/dump.rdb ./backups/dump.rdb
```

## Restore

1. Restore MinIO bucket:
```bash
mc alias set local http://127.0.0.1:9000 "$MINIO_ROOT_USER" "$MINIO_ROOT_PASSWORD"
mc mirror ./backups/rmbg-assets local/rmbg-assets
```

2. Restore Redis dump:
```bash
docker compose down
cp ./backups/dump.rdb ./redis-data/dump.rdb
docker compose up -d
```

## Secret Rotation

1. Update `.env.prod` with new keys/passwords.
2. Restart stack:
```bash
docker compose --env-file .env.prod up -d --build
```
3. Validate with:
```bash
curl -fsS http://127.0.0.1:8000/api/health
```
