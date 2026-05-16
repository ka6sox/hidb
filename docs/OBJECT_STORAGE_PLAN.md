# Object storage plan

Planning document for making item photo storage pluggable: **local filesystem**, **S3-compatible object storage**, or similar backends without changing the core data model.

## Current behavior

- Uploads are handled in `hidb/items.py` via Flask/Werkzeug `request.files` and `FileStorage.save()`.
- Files are written to `UPLOAD_FOLDER` (`hidb/static/photos`), configured in `hidb/__init__.py`.
- The database stores only the **filename/key** in `Item.photo` (text column).
- Templates build image URLs as Flask static paths (`/static/photos/...` or `url_for('static', filename='photos/'+...)`).
- Docker Compose persists photos with a volume on `hidb/static/photos`.

## Goals

- One codebase supports **local disk** (dev, simple deploy) and **object storage** (production, scale).
- The **database schema stays the same**: `Item.photo` remains an object key (e.g. `uuid.jpg`), not a full URL.
- Templates and routes do not hard-code `/static/photos/`; they use a single way to get a display URL.
- Optional: S3-compatible endpoints (MinIO, etc.) for local parity with production.

## Non-goals (for initial work)

- Storing image bytes in the database.
- Image processing (resize, thumbnails, HEIC conversion) unless added later.
- Changing how uploads are validated (extensions, size) beyond centralizing existing checks.

---

## Architecture

### Storage abstraction

Introduce a small backend interface used only from item create/update/delete and from URL generation for templates:

| Method | Responsibility |
|--------|----------------|
| `save(upload_file)` | Persist bytes; return **object key** to store in `Item.photo`. |
| `delete(key)` | Remove object if it exists; safe when key is empty or missing. |
| `url(key)` | Return the string to use in `<img src="...">` (static path, public URL, or presigned URL). |

### Implementations

1. **LocalStorage** (current behavior)
   - `save`: write to `UPLOAD_FOLDER` with a secure UUID filename (same as today).
   - `delete`: remove file from disk.
   - `url`: `url_for('static', filename='photos/' + key)` or equivalent.

2. **S3Storage**
   - `save`: `put_object` (boto3) with bucket, optional key prefix, content-type from extension.
   - `delete`: `delete_object`.
   - `url`: either a **public base URL** + key (bucket policy / CDN) or a **presigned GET** URL if the bucket is private.

3. **Future / other**
   - Any S3-compatible API (MinIO, R2, etc.) via custom endpoint URL in config.
   - Additional backends only need to implement the three methods above.

### Wiring

- Choose backend via config/env (e.g. `STORAGE_BACKEND=local` | `s3`).
- Register one instance on the Flask app (e.g. `app.extensions['photo_storage']`) or expose `get_photo_storage()` using `current_app`.
- Factory reads config at app startup in `create_app()`.

---

## Configuration

Add to app config / `.env` (names are illustrative):

| Variable | Purpose |
|----------|---------|
| `STORAGE_BACKEND` | `local` or `s3` (default: `local`). |
| `UPLOAD_FOLDER` | Local path (existing; used when backend is local). |
| `S3_BUCKET` | Bucket name. |
| `S3_PREFIX` | Optional key prefix (e.g. `photos/`). |
| `AWS_REGION` | Region for boto3. |
| `S3_ENDPOINT_URL` | Optional; for MinIO / non-AWS. |
| `S3_PUBLIC_BASE_URL` | Optional; CDN or public bucket base for `url()` when not using presigned URLs. |
| Standard AWS credentials | Via env, instance role, or profile (boto3 default chain). |

Document in `.env.example` and README (or cross-link from `DEVPATH.md`).

---

## Code changes

### New module

- `hidb/storage.py` (or `hidb/storage/` package): protocol/ABC, `LocalStorage`, `S3Storage`, `get_storage(app)`.

### `hidb/__init__.py`

- Load storage-related config.
- Instantiate and attach the selected backend after config is final.

### `hidb/items.py`

Replace direct filesystem calls with the backend:

| Location | Today | After |
|----------|--------|--------|
| Create | `photo.save(fullpath)` | `key = storage.save(photo)` |
| Update | save new file; `os.remove` old | `storage.save`; `storage.delete(old_key)` |
| Delete | `os.path.join` + `os.remove` | `storage.delete(key)` |

Keep existing validation: `allowed_file_type`, optional upload, UUID + extension naming.

### Templates

Stop assuming static files for item photos:

| File | Change |
|------|--------|
| `hidb/templates/items/index.html.j2` | Use resolved photo URL, not `url_for('static', filename='photos/'+...)`. |
| `hidb/templates/items/details.html.j2` | Same. |
| `hidb/templates/search/results.html.j2` | Replace hardcoded `/static/photos/...`. |

**Options for templates:**

- Pass `photo_url` from views/query helpers when building item dicts, or
- Jinja filter `photo_url(key)` that calls `storage.url(key)` (requires app context).

Use existing `no_image.png` static asset when `photo` is empty.

### Dependencies

- Add `boto3` when the `s3` backend is used.

### Docker / deploy

- **Local:** keep `hidb-photos` volume in `docker-compose.yml` (optional).
- **S3:** photos volume not required; ensure IAM/credentials and env vars are set on the web service.

### Data migration (existing deployments)

When switching from local to S3 on a live system:

1. Script: for each `Item` with `photo` set, upload `UPLOAD_FOLDER/<photo>` to bucket (preserve key if possible).
2. Verify objects and spot-check URLs in the UI.
3. Set `STORAGE_BACKEND=s3` and redeploy.
4. Retain local files until confident; then archive or remove.

No Alembic migration needed if `photo` remains a key string.

---

## Security and product choices

Decide before implementing S3:

| Choice | Implication |
|--------|-------------|
| **Public bucket / CDN** | Simple `<img src>`; stable URLs; bucket policy must allow read. |
| **Private bucket + presigned URLs** | URLs expire; may need regeneration per request or short TTL; better for sensitive photos. |
| **ACL vs bucket policy** | Prefer bucket policy / IAM; avoid legacy public ACLs on AWS. |

---

## Testing

- Unit tests with a fake/in-memory backend or temp directory for local.
- Integration test: local save/delete/url round-trip.
- Optional: moto or MinIO for S3 backend in CI.
- Manual: create item with photo, view index/details/search, update photo, delete item.

---

## Checklist

- [ ] Define storage interface and factory
- [ ] Implement `LocalStorage` (parity with current behavior)
- [ ] Implement `S3Storage` + config
- [ ] Refactor `hidb/items.py` (create, update, delete)
- [ ] Unify template image URLs (index, details, search)
- [ ] Add `boto3` to requirements; document env vars
- [ ] Update Docker/docs for S3 deploy
- [ ] Optional: migration script for existing local files
- [ ] Tests

---

## Related docs

- [DEVPATH.md](../DEVPATH.md) — high-level direction for storage and database pluggability.
