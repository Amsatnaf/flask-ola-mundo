# Flask Olá Mundo (prod) — GHCR automático + Fleet (CD)

Projeto **mínimo** para estudo:
- App Flask simples ("Olá, mundo!")
- Build **automático** da imagem no **GitHub Container Registry (GHCR)**
- **CD** via Rancher Fleet usando apenas o diretório `prod/`

## 📦 App
- `app/app.py` expõe `/` na porta **8080**
- `Dockerfile` instala `flask` e executa o app

## 🏷️ Imagem
Publicada como: `ghcr.io/Amsatnaf/flask-ola-mundo:latest`
> O workflow usa `GITHUB_TOKEN` com permissão `packages: write`, então **não precisa** criar PAT.

## 🤖 CI (build-and-push)
- Arquivo: `.github/workflows/build-and-push.yml`
- Dispara em **push/PR** que toquem `app/**` ou `Dockerfile`
- Em **PR**: apenas **builda** (sem `push`)
- Em **push na main**: **builda e publica** em `ghcr.io/Amsatnaf/flask-ola-mundo:latest`

## 🚀 CD (Fleet)
Crie **um GitRepo** no Rancher Fleet apontando para `prod/`:
- `repo`: `https://github.com/Amsatnaf/flask-ola-mundo-prod-only.git`
- `branch`: `main`
- `paths`: `["prod"]`
- (não use `prune: true`)

O `prod/kustomization.yaml` define `namespace: flask-prod` e aplica **Deployment + Service + Ingress**.

### URL de exemplo
- `http://flask.prod.129.213.28.76.sslip.io/`
> Ajuste o host no `prod/ingress.yaml` se quiser outro domínio.

## 🧪 Fluxo sugerido
```bash
# 1) suba o repositório
git init
git add .
git commit -m "init minimal flask"
git branch -M main
git remote add origin https://github.com/Amsatnaf/flask-ola-mundo-prod-only.git
git push -u origin main

# 2) (opcional) branch + PR
git checkout -b feature/muda-texto
echo "# edite app/app.py -> retorne outro texto"
git add app/app.py
git commit -m "muda texto"
git push -u origin feature/muda-texto
# abra PR no GitHub; o CI builda (sem publicar)

# 3) após merge na main, o workflow publicará a imagem e o Fleet aplicará prod/
```

## Observações
- Se seu cluster exigir **pull secret** para GHCR, crie um `imagePullSecret` com um token que tenha `packages:read` e referencie no `Deployment`.
- TLS opcional: descomente o bloco em `prod/ingress.yaml` e configure `cert-manager` com seu ClusterIssuer.
