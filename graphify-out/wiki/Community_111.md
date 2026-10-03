# Community 111

> 8 nodes · cohesion 0.25

## Key Concepts

- **CI Workflow: Product CI** (4 connections) — `.github/workflows/ci.yml`
- **Docker Compose: Production Stack** (4 connections) — `deploy/compose.prod.yaml`
- **Solfège Trainer Application** (4 connections) — `docs/PRODUCT_BRIEF.md`
- **CD Workflow: Deploy Product Release** (3 connections) — `.github/workflows/cd.yml`
- **Publish Product Workflow: Build and Release** (3 connections) — `.github/workflows/publish-product.yml`
- **requirements.txt: Locked Python Dependencies** (1 connections) — `requirements.txt`
- **Publish PWA Prototype Workflow** (1 connections) — `.github/workflows/publish-pwa-prototype.yml`
- **Docker Compose: Proxy Network Overlay** (1 connections) — `deploy/compose.proxy.yaml`

## Relationships

- [[Community 16]] (7 shared connections)

## Source Files

- `.github/workflows/cd.yml`
- `.github/workflows/ci.yml`
- `.github/workflows/publish-product.yml`
- `.github/workflows/publish-pwa-prototype.yml`
- `deploy/compose.prod.yaml`
- `deploy/compose.proxy.yaml`
- `docs/PRODUCT_BRIEF.md`
- `requirements.txt`

## Audit Trail

- EXTRACTED: 10 (48%)
- INFERRED: 11 (52%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*