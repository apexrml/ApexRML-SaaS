# ApexRML: Dual-Model Hybrid SaaS Platform
## Product Roadmap & Business Architecture

**Current Status:** Parts Finder (live) → **Next:** Garage Finder + Recovery Network (SaaS)

---

## 1. PRODUCT PILLARS & REVENUE STREAMS

### Pillar 1: Parts Finder (Existing - Affiliate Model)
- **Revenue:** eBay EPN & Awin commission (25-35% markup)
- **Users:** UK car owners, mechanics, fleet managers
- **Status:** LIVE (apexrml.onrender.com)
- **API:** GSF Car Parts, eBay Partner Network, Awin feeds

### Pillar 2: Garage Finder (NEW - B2B SaaS)
- **Revenue:** £25/month (Starter) | £50/month (Pro)
- **Users:** Independent garages, MOT stations, quick-fit chains
- **Features:**
  - Garage profile + booking system
  - Lead generation from quoted customers
  - DVLA integration (vehicle lookup)
  - Review & ratings system
  - Customer relationship management (CRM)
- **GTM:** Freemium tier (2 leads/month), then paid upgrade

### Pillar 3: Recovery Network (NEW - B2B SaaS)
- **Revenue:** £35/month (Standard) | £60/month (Premium)
- **Users:** Recovery drivers, breakdown services, insurers
- **Features:**
  - Real-time job dispatch system
  - GPS tracking & route optimization
  - Insurance integration
  - Customer communication portal
  - Performance analytics
- **GTM:** White-label offering for existing recovery companies

---

## 2. DUAL-MODEL HYBRID ARCHITECTURE

```
┌─────────────────────────────────────────────────────────────────┐
│                    ApexRML Hybrid Platform                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │         B2C AFFILIATE LAYER (Parts Finder)               │   │
│  │  ├─ eBay EPN API integration                            │   │
│  │  ├─ GSF Car Parts feed                                 │   │
│  │  ├─ Awin network                                        │   │
│  │  └─ Commission tracking & payouts                      │   │
│  └──────────────────────────────────────────────────────────┘   │
│                              ↓                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │         B2B SaaS LAYER (Garage + Recovery)              │   │
│  │  ├─ User authentication (JWT + OAuth2)                  │   │
│  │  ├─ Stripe subscription billing (£25-£60/month)        │   │
│  │  ├─ Multi-tenant database (garage/recovery orgs)       │   │
│  │  ├─ Admin dashboard (revenue, churn, LTV)             │   │
│  │  └─ API endpoints for mobile/web                      │   │
│  └──────────────────────────────────────────────────────────┘   │
│                              ↓                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │      AI DIAGNOSTICS LAYER (Revenue Multiplier)         │   │
│  │  ├─ Vehicle fault detection (symptoms → parts)         │   │
│  │  ├─ Free tier (vehicle owners)                         │   │
│  │  ├─ Premium tier (£15/month for garages)              │   │
│  │  └─ Auto-quote generation                             │   │
│  └──────────────────────────────────────────────────────────┘   │
│                              ↓                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │        SHARED INFRASTRUCTURE LAYER                      │   │
│  │  ├─ PostgreSQL / Supabase (production DB)              │   │
│  │  ├─ Redis cache (API response caching)                 │   │
│  │  ├─ JWT authentication (sign-up/sign-in)              │   │
│  │  ├─ Stripe webhook handler (billing events)           │   │
│  │  ├─ DVLA API integration (vehicle registration)       │   │
│  │  ├─ Email service (SendGrid for notifications)        │   │
│  │  └─ S3-compatible storage (invoice PDFs)             │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. FINANCIAL MODEL (Year 1)

### Revenue Projections
| Model | Users | ARPU | Monthly Revenue | Annual Revenue |
|-------|-------|------|-----------------|----------------|
| **Parts Finder** | 50K | £2.50 | £125K | £1.5M |
| **Garage Finder** | 500 | £37.50 | £18.75K | £225K |
| **Recovery Network** | 200 | £47.50 | £9.5K | £114K |
| **AI Diagnostics** | 1000 | £7.50 | £7.5K | £90K |
| **TOTAL** | 51.7K | - | **£160.75K** | **£1.929M** |

### Cost Structure
- **Infrastructure:** £2K/month (Render, Supabase, Redis)
- **Payment Processing:** 2.9% + £0.30 per transaction (Stripe)
- **Marketing:** £5K/month (SEM, content)
- **Team:** £25K/month (2x full-stack, 1x ops)
- **Support:** £2K/month (Zendesk)

**Year 1 Gross Margin:** ~68%

---

## 4. IMPLEMENTATION TIMELINE

### Phase 1: Foundation (Weeks 1-4)
- [ ] PostgreSQL schema design & migrations
- [ ] JWT authentication system
- [ ] Stripe subscription integration
- [ ] Admin dashboard (revenue metrics)

### Phase 2: Garage Finder MVP (Weeks 5-8)
- [ ] Garage sign-up & onboarding flow
- [ ] Garage profile builder
- [ ] Lead routing algorithm
- [ ] Review system

### Phase 3: Recovery Network MVP (Weeks 9-12)
- [ ] Recovery driver registration
- [ ] Job dispatch system
- [ ] GPS tracking integration
- [ ] Insurer API integration

### Phase 4: AI Diagnostics (Weeks 13-16)
- [ ] OpenAI integration for symptom→parts mapping
- [ ] Fine-tuning with automotive fault codes
- [ ] Quote generation engine
- [ ] Premium tier activation

### Phase 5: PWA Conversion (Weeks 17-20)
- [ ] Service worker implementation
- [ ] manifest.json configuration
- [ ] Offline mode support
- [ ] Push notifications

### Phase 6: Enterprise Scaling (Weeks 21+)
- [ ] Database optimization & indexing
- [ ] API rate limiting & throttling
- [ ] CDN integration (Cloudflare)
- [ ] Load testing & monitoring

---

## 5. KEY METRICS & KPIs

### User Acquisition
- **CAC (Customer Acquisition Cost):** £50 per garage signup
- **Viral Coefficient:** 1.2x (referral from satisfied garages)
- **Churn Rate Target:** <5% monthly

### Revenue
- **LTV (Lifetime Value):** £900 per garage subscriber
- **MRR Growth:** 15% month-over-month
- **Gross Margin:** 72%

### Product
- **Uptime:** 99.9%
- **API Response Time:** <200ms (p95)
- **Mobile Conversion Rate:** 8-12%

---

## 6. COMPETITIVE ADVANTAGES

1. **Integrated Platform:** Parts + Garages + Recovery (competitors focus on 1 pillar)
2. **DVLA Integration:** Real-time vehicle lookup (reduces friction)
3. **AI Diagnostics:** Auto-diagnosis from symptoms (unique feature)
4. **Affiliate Revenue:** No upfront revenue cap (scales with volume)
5. **UK-Focused:** DVLA API, MOT data, Awin partnerships
6. **White-Label Ready:** Recovery network can be rebranded for enterprise partners

---

## 7. TECH STACK SUMMARY

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| Backend | Flask + Python | Rapid SaaS development, rich ecosystem |
| Database | PostgreSQL (Supabase) | ACID compliance, JSON support, managed backups |
| Auth | JWT (PyJWT) + OAuth2 | Stateless, mobile-friendly |
| Payments | Stripe API | Enterprise-grade, UK VAT handling |
| Caching | Redis | Real-time lead notifications, API optimization |
| Storage | AWS S3 / Cloudinary | Invoice PDFs, garage photos |
| Email | SendGrid / Postmark | Transactional emails, templates |
| Frontend | HTML/CSS/JS + Alpine.js | Lightweight, no build step needed |
| Mobile | PWA (service workers) | iOS/Android home screen installation |
| Hosting | Render | Native PostgreSQL, auto-scaling, GitHub integration |
| Monitoring | Sentry + DataDog | Error tracking, performance monitoring |

---

## 8. SECURITY & COMPLIANCE

- [ ] GDPR compliance (UK Data Protection Act 2018)
- [ ] PCI DSS (Stripe handles this, but audit required)
- [ ] HTTPS everywhere (Render + Cloudflare)
- [ ] SQL injection prevention (SQLAlchemy ORM)
- [ ] CSRF protection (Flask-WTF)
- [ ] Rate limiting (Flask-Limiter)
- [ ] API key rotation (quarterly)
- [ ] Database encryption at rest (Supabase default)

---

## 9. SUCCESS CRITERIA (6 months)

✅ **Revenue:** £50K MRR from SaaS (exclude affiliate)
✅ **Users:** 750+ paying subscribers
✅ **Retention:** 95% month-over-month
✅ **Product:** 4/5 stars average rating
✅ **Infrastructure:** 99.95% uptime
✅ **Mobile:** PWA with 10K+ installs

---

**Next Steps:**
1. Review PostgreSQL schema (see next document)
2. Deploy Flask application to Render
3. Configure Supabase PostgreSQL database
4. Integrate Stripe test environment
5. Launch Garage Finder closed beta
