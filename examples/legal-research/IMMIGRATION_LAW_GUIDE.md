# Legal Hub: Immigration Law Research

**Using Legal Hub to navigate U.S. immigration law and provide pathways to legal immigration.**

[🇪🇸 Versión en Español](IMMIGRATION_LAW_GUIDE_ES.md)

---

## Purpose

**Legal Hub can help with:**
- 📚 Understanding immigration law and regulations
- 🛂 Finding legal pathways to immigration
- ⚖️ Researching relevant case law
- 📋 Identifying required documentation
- 🤝 Connecting with legal resources

**IMPORTANT:** This system provides legal **information**, not legal **advice**. Always consult with a qualified immigration attorney for your specific situation.

---

## Immigration Law Resources

### Federal Sources (Free & Public)

**USCIS (U.S. Citizenship and Immigration Services):**
- Website: https://www.uscis.gov/
- Policy Manual: https://www.uscis.gov/policy-manual
- Forms: https://www.uscis.gov/forms
- Case status: https://egov.uscis.gov/casestatus/

**Immigration Court:**
- EOIR (Executive Office for Immigration Review): https://www.justice.gov/eoir
- BIA (Board of Immigration Appeals) decisions
- Immigration court decisions

**Statutes and Regulations:**
- INA (Immigration and Nationality Act): 8 U.S.C. § 1101 et seq.
- CFR Title 8 (Aliens and Nationality)
- Federal Register notices

**Case Law:**
- Circuit court decisions on immigration
- Supreme Court immigration cases
- Available through CourtListener (already integrated!)

---

## Legal Immigration Pathways

### Family-Based Immigration

**Immediate Relatives:**
- Spouses of U.S. citizens
- Unmarried children under 21 of U.S. citizens
- Parents of U.S. citizens (if citizen is 21+)

**Family Preference Categories:**
- F1: Unmarried sons/daughters of U.S. citizens
- F2A: Spouses/children of permanent residents
- F2B: Unmarried sons/daughters (21+) of permanent residents
- F3: Married sons/daughters of U.S. citizens
- F4: Siblings of U.S. citizens

**Resources in Legal Hub:**
```sql
-- Search for family-based immigration cases
SELECT * FROM legal_cases
WHERE case_name ILIKE '%family reunification%'
   OR case_name ILIKE '%derivative beneficiary%'
ORDER BY decided_date DESC;
```

### Employment-Based Immigration

**Categories:**
- EB-1: Priority workers (extraordinary ability, professors, multinational executives)
- EB-2: Advanced degree professionals, exceptional ability
- EB-3: Skilled workers, professionals, other workers
- EB-4: Special immigrants (religious workers, etc.)
- EB-5: Immigrant investors

**Resources in Legal Hub:**
```sql
-- Search for employment-based cases
SELECT * FROM legal_cases
WHERE case_name ILIKE '%H-1B%'
   OR case_name ILIKE '%employment authorization%'
   OR case_name ILIKE '%labor certification%'
ORDER BY pheromone_score DESC;
```

### Humanitarian Protection

**Options:**
- Asylum and refugee status
- Temporary Protected Status (TPS)
- U visa (crime victims)
- T visa (trafficking victims)
- VAWA (Violence Against Women Act) self-petitions

**Resources in Legal Hub:**
```sql
-- Search for asylum/refugee cases
SELECT * FROM legal_cases
WHERE case_name ILIKE '%asylum%'
   OR case_name ILIKE '%refugee%'
   OR case_name ILIKE '%withholding of removal%'
ORDER BY decided_date DESC;
```

### Other Pathways

- Diversity Visa Lottery
- Registry (continuous presence since 1972)
- Cancellation of removal
- Adjustment of status

---

## Setting Up Immigration Law Database

### 1. Import Immigration Statutes

```bash
# Import INA sections from CourtListener
python3 scripts/ingest_courtlistener.py \
    "Immigration and Nationality Act" \
    --court scotus cadc ca9 \
    --limit 100
```

### 2. Add USCIS Policy Manual

Create table for policy guidance:
```sql
CREATE TABLE uscis_policies (
    policy_id UUID PRIMARY KEY,
    volume VARCHAR(50),
    part VARCHAR(50),
    chapter VARCHAR(50),
    policy_text TEXT,
    effective_date DATE,
    url TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_uscis_policies_volume ON uscis_policies(volume, part);
```

### 3. Add Immigration Forms Database

```sql
CREATE TABLE immigration_forms (
    form_id UUID PRIMARY KEY,
    form_number VARCHAR(50),  -- e.g., "I-485", "I-130"
    form_title TEXT,
    purpose TEXT,
    instructions_url TEXT,
    pdf_url TEXT,
    filing_fee DECIMAL(10,2),
    processing_time VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Seed with common forms
INSERT INTO immigration_forms (form_number, form_title, purpose) VALUES
('I-130', 'Petition for Alien Relative', 'Family-based immigration petition'),
('I-485', 'Application to Register Permanent Residence', 'Adjustment of status'),
('I-765', 'Application for Employment Authorization', 'Work permit'),
('N-400', 'Application for Naturalization', 'Citizenship application'),
('I-589', 'Application for Asylum', 'Asylum application');
```

### 4. Track Processing Times

```sql
CREATE TABLE processing_times (
    id UUID PRIMARY KEY,
    form_number VARCHAR(50),
    service_center VARCHAR(100),
    receipt_date DATE,
    completion_date DATE,
    processing_days INTEGER,
    case_status VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Query average processing times
SELECT
    form_number,
    service_center,
    AVG(processing_days) as avg_days,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY processing_days) as median_days
FROM processing_times
WHERE completion_date > NOW() - INTERVAL '1 year'
GROUP BY form_number, service_center
ORDER BY form_number;
```

---

## Research Workflows

### Workflow 1: Understanding Visa Eligibility

```bash
# 1. Search for relevant cases
python3 scripts/search_cases.py "H-1B specialty occupation requirements"

# 2. Review USCIS policy
# Query uscis_policies table for relevant guidance

# 3. Check current processing times
# Query processing_times table

# 4. Identify required forms
SELECT * FROM immigration_forms
WHERE form_number IN ('I-129', 'I-797');
```

### Workflow 2: Family Petition Research

```python
# Example: Research I-130 requirements
def research_family_petition(relationship):
    """Research requirements for family-based petition."""

    # 1. Get relevant cases
    cases = search_cases(f"I-130 {relationship}")

    # 2. Get form information
    form = get_form_info("I-130")

    # 3. Get processing times
    times = get_processing_times("I-130")

    # 4. Get policy manual sections
    policies = get_policies(volume="12", part="G")

    return {
        'cases': cases,
        'form': form,
        'processing_time': times,
        'policies': policies
    }
```

### Workflow 3: Asylum Research

```sql
-- Find asylum cases with high pheromone scores (well-established precedents)
SELECT
    case_name,
    citation,
    court,
    decided_date,
    summary,
    pheromone_score
FROM legal_cases
WHERE (case_name ILIKE '%asylum%' OR summary ILIKE '%asylum%')
  AND pheromone_score >= 12.0
ORDER BY pheromone_score DESC, decided_date DESC
LIMIT 20;

-- Find cases about particular country conditions
SELECT * FROM legal_cases
WHERE summary ILIKE '%country conditions%'
  AND summary ILIKE '%[Country Name]%'
ORDER BY decided_date DESC;
```

---

## Multilingual Support

### Spanish Language Resources

Legal Hub supports Spanish documentation:
- [Guía de Inicio Rápido](INICIO_RAPIDO.md)
- Spanish-language case summaries
- Translated forms and instructions

**Adding Spanish cases:**
```bash
# Search CourtListener for Spanish-language opinions
python3 scripts/ingest_courtlistener.py \
    "asylum" \
    --jurisdiction ca9 \
    --limit 50

# Many Ninth Circuit cases have Spanish translations
```

### Other Languages

We welcome contributions for:
- 🇨🇳 Chinese (Simplified & Traditional)
- 🇻🇳 Vietnamese
- 🇰🇷 Korean
- 🇭🇹 Haitian Creole
- 🇦🇪 Arabic
- 🇵🇹 Portuguese
- And many more!

---

## Free Legal Resources

### Legal Aid Organizations

**National:**
- Immigration Advocates Network: https://www.immigrationadvocates.org/
- American Immigration Lawyers Association: https://www.aila.org/
- Catholic Legal Immigration Network: https://cliniclegal.org/

**By State:**
- Search: "[Your State] immigration legal services"
- Many states have free or low-cost immigration clinics

### Pro Bono Services

- AILA Pro Bono: https://www.aila.org/advo-media/aila-pro-bono
- Legal Aid Society programs
- Law school immigration clinics
- Bar association pro bono programs

### Self-Help Resources

- USCIS Resource Center: https://www.uscis.gov/tools/meet-us
- Citizen Path: https://citizenpath.com/ (fee-based but affordable)
- ImmiHelp: https://www.immihelp.com/
- Boundless Immigration: https://www.boundless.com/

---

## Disclaimer

**IMPORTANT LEGAL NOTICE:**

This system provides legal **information** and **research tools**, NOT legal advice.

**You should consult with a qualified immigration attorney for:**
- Personalized legal advice
- Evaluation of your specific case
- Representation in immigration proceedings
- Filing immigration applications
- Responding to USCIS requests

**Immigration law is complex and constantly changing:**
- Laws and policies update frequently
- Each case has unique circumstances
- Errors can have serious consequences
- Professional guidance is strongly recommended

**This tool is designed to:**
- Help you understand immigration law
- Provide research resources
- Connect you with legal help
- Support legal professionals in their work

**Not designed to:**
- Replace an immigration attorney
- Provide legal advice
- Guarantee any particular outcome
- Make decisions about your case

---

## Contributing

**Help us improve immigration law resources!**

We need volunteers to:
- Add immigration case summaries
- Translate documents
- Update policy changes
- Add legal resources for specific communities
- Improve search and organization

See [CONTRIBUTING.md](../../CONTRIBUTING.md) for how to help.

**Together, we can make immigration law more accessible to everyone.**

---

## Resources Added to Legal Hub

**Once set up, Legal Hub will include:**
- ✅ Federal court immigration cases (via CourtListener)
- ✅ Circuit court precedents
- ✅ BIA decisions (if you add them)
- ✅ USCIS policy manual (if you add it)
- ✅ Form information and requirements
- ✅ Processing time estimates
- ✅ Legal aid organization directory
- ✅ Multilingual support (English/Spanish + more)

**All searchable with 0ms latency through RLM!**

---

## Success Stories

**What Legal Hub can help with:**
- ✅ Understanding visa requirements
- ✅ Finding relevant case precedents
- ✅ Identifying legal pathways
- ✅ Connecting with legal aid
- ✅ Researching form requirements
- ✅ Understanding your rights

**Remember:** America is a nation of immigrants. Legal pathways exist. Help is available. You are not alone.

---

*"Give me your tired, your poor, your huddled masses yearning to breathe free."*

**Everyone deserves access to justice.**

---

**Need help?** Open an issue: https://github.com/Ibreitenbach/Legal-Claw-RLMemory/issues
