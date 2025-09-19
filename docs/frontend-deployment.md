# Frontend Deployment Guide

The Level Analyst card is built as a standalone React/Vite bundle that can be hosted from any static web service (object storage, CDN, or web server). Follow the steps below to produce and distribute the artifact.

## 1. Build the Artifact

Use the new `web-package` Make target (or the underlying npm script) to compile TypeScript, run Vite, and package the output:

```bash
make web-package
# or
cd web/card && npm install && npm run build:artifact
```

This command produces:

- `web/card/dist/` – directory containing cache-busted JS/CSS/HTML
- `web/card/dist.tar.gz` – tarball of the same contents for upload pipelines

## 2. Publish to Object Storage / CDN

Common approaches:

1. **Amazon S3 + CloudFront**
   - Unpack or sync the `dist/` directory to an S3 bucket (`aws s3 sync dist/ s3://my-analyst-card/ --delete`)
   - Invalidate the CDN cache (`aws cloudfront create-invalidation --distribution-id <id> --paths "/*"`)

2. **Azure Blob Storage + Azure CDN**
   - `az storage blob upload-batch -d '$web' -s dist`
   - Purge CDN endpoint: `az cdn endpoint purge -n <endpoint> -g <resource-group> --content-paths '/*'`

3. **Google Cloud Storage + Cloud CDN**
   - `gsutil -m rsync -r dist gs://my-analyst-card`
   - Purge caches with: `gcloud compute url-maps invalidate-cdn-cache <url-map> --path "/*"`

When uploading, make sure the `index.html` file is served for `/card/` requests. If the CDN cannot serve subdirectory SPAs automatically, configure a rewrite so `/card/*` falls back to `index.html`.

## 3. Point the Backend (Optional)

If you prefer the backend to serve assets directly (e.g., internal deployments), copy the `dist/` directory into `services/analyst/static/iframe/` as part of your release pipeline:

```bash
cp -R web/card/dist/. services/analyst/static/iframe/
```

Otherwise, update your reverse proxy (e.g., nginx) to point `/card/` to the CDN origin instead of the local static directory.

## 4. Cache Busting

Vite generates hashed filenames (e.g., `index-8c5ae011.js`), which allows long-lived CDN caching. After publishing a new build, purge the CDN or configure versioned paths to guarantee clients pull the latest bundle.

## 5. Environment Overrides

At runtime, the card expects `VITE_API_URL` to be set when building if the API is hosted somewhere other than `http://localhost:8080`. For CDN builds, run:

```bash
VITE_API_URL=https://api.example.com npm run build:artifact
```

This will bake the production API URL into the generated bundle.

---

By packaging the frontend separately, you can promote the API and UI on independent release cadences, leverage global CDNs for low-latency delivery, and avoid bundling static assets inside backend containers unless required.

