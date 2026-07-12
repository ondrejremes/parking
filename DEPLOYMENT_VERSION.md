# Deployment Versions

| # | Version | Date | App Version | Config Changes | Status |
|---|---------|------|-------------|-----------------|--------|
| 1 | v1.0.0-deploy.1 | 2026-07-11 22:32 | v1.0.0+dc753442 | Initial Azure deployment | ✅ |
| 2 | v1.0.0-deploy.2 | 2026-07-11 22:31 | v1.0.0+dc753442 | SSO callback URL → Azure Front Door | ✅ |
| 3 | v1.0.0-deploy.3 | 2026-07-12 00:36 | v1.0.0+dc753442 | Custom domain attempted (conflict with existing) | ❌ |
| 4 | v1.0.0-deploy.4 | 2026-07-12 01:09 | v1.0.0+752a5b6c | Custom domain PRIMARY + BASE_URL fix | ✅ |
| 5 | v1.1.0-deploy.5 | 2026-07-12 01:14 | v1.1.0+078a2a54 | Entra ID user sync + admin panel + XSS fix | ✅ |
| 6 | v1.1.0-deploy.6 | 2026-07-12 01:24 | v1.1.0+0910ce1 | CSP fix: removed inline onclick, add addEventListener | ✅ |
| 7 | v1.1.1-deploy.7 | 2026-07-12 01:38 | v1.1.1+xyz | Version bump to v1.1.1 (patch) | ✅ |

## Current State
- **Latest Deployment:** v1.1.1-deploy.7 (LIVE 🚀)
- **Application Version:** v1.1.1
- **Configuration Version:** 5
- **Azure Front Door:** https://parking-g2ceh5h2abgnhvfr.a03.azurefd.net
- **Custom Domain:** parking.alintrust.cz (exists but managed manually in Azure Portal)
- **Admin Password:** QrV99tIbpdtyHI
- **OAuth Callback:** https://parking-g2ceh5h2abgnhvfr.a03.azurefd.net/auth/callback
- **Status:** 🟢 Aplikace je plně funkční a dostupná
