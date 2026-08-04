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

| 8 | v1.10.5-deploy.8 | 2026-08-03 | v1.10.5 | Responsive layout optimization for widescreen monitors | ✅ |
| 9 | v1.10.6-deploy.9 | 2026-08-03 | v1.10.6 | Email notifications debug + local SOC user creation | ✅ |
| 10 | v1.10.7-deploy.10 | 2026-08-04 | v1.10.7 | Improved reminder emails with cancellation instructions | ✅ |
| 11 | v1.10.8-deploy.11 | 2026-08-04 | v1.10.8 | EMAIL_FROM secret configuration + Container App restart | ✅ |
| 12 | v1.10.9-deploy.12 | 2026-08-04 | v1.10.9 | Weekend availability fix + correct Azure tenant ID for SSO | ✅ |

## Current State
- **Latest Deployment:** v1.10.9-deploy.12 (LIVE 🚀)
- **Application Version:** v1.10.9
- **Container App Revision:** parking--0000019
- **Configuration Version:** 12
- **Custom Domain:** https://parking.alintrust.cz
- **Azure Container Registry:** parkingcr.azurecr.io/parking:v1.10.9
- **Key Features:**
  - ✅ SSO via Microsoft Entra ID (tenant: d15176d7-e40c-4cae-bff5-11d57e820fbd)
  - ✅ Email notifications from DoNotReply@alintrust.cz
  - ✅ Reminder emails at 19:00 CEST with cancellation link
  - ✅ Local admin + local SOC user
  - ✅ Responsive widescreen layout
  - ✅ Weekend parking spot availability fix
- **Status:** 🟢 Aplikace je plně funkční a dostupná
