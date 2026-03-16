# Legal Notices / Mentions Légales

Replace this file with your actual legal notices.

This file is passed to PrevMed via the mandatory `--terms-md` argument.
It is displayed at the bottom of the questionnaire page in a collapsible
`<details>` element.  You **must** customise it to reflect your actual
deployment — PrevMed refuses to start without it (GDPR Art. 13/14).

## Minimum required content (GDPR Art. 13/14)

Your legal notices should include **at least** the following:

1. **Identity and contact details of the data controller** (association, company, etc.)
2. **Contact details of the DPO** (Data Protection Officer), if applicable
3. **Purposes of the processing** (e.g. "calculation of a clinical risk score and generation of a PDF report")
4. **Legal basis** for processing (e.g. explicit consent under Art. 9(2)(a) for health data)
5. **Recipients or categories of recipients** of the data
6. **Retention period** (e.g. "no data is retained" or the actual duration if `--save-user-data` is enabled)
7. **Data subject rights** (access, rectification, erasure, restriction, portability, objection)
8. **Right to lodge a complaint with a supervisory authority** (e.g. CNIL in France: https://www.cnil.fr/)
9. **Hosting provider** identity and location

## If `--save-user-data` is enabled

When this flag is active, PrevMed stores survey answers, scoring results,
and pseudonymised client hashes (salted SHA-256 of IP, user-agent, etc.)
in JSON and CSV files.  Your privacy notice must disclose this, including
the retention period and the fact that pseudonymised data is still personal
data under GDPR Art. 4(5).

## If Umami analytics is enabled (`--umami-website-id`)

PrevMed supports optional integration with Umami, an open-source audience
measurement tool.  The GDPR implications depend on how Umami is deployed:

- **Self-hosted on the same server (or same hosting provider / same country):**
  No third-party data transfer occurs.  Umami does not set cookies and respects
  the Do Not Track (DNT) browser signal by default.  Under CNIL deliberation
  n° 2020-091, strictly necessary audience measurement tools that are
  self-hosted and produce only aggregate statistics may be exempt from
  cookie consent.  You should still mention Umami in your privacy notice.

- **Using Umami Cloud (cloud.umami.is) or an external instance:**
  This constitutes a transfer of personal data (IP address, browser fingerprint,
  page views) to a third party.  You must:
  - Identify Umami as a data processor in your privacy notice
  - Verify where Umami Cloud servers are located (EU adequacy / SCCs)
  - Consider whether a Data Processing Agreement (DPA) is needed
  - Disclose this transfer to users

- **If `--umami-ignore-dnt` is used:**
  Users who set Do Not Track in their browser will be tracked anyway.
  This is **not recommended** and should be disclosed in your privacy notice
  if used.

## Example template

**Editor / Éditeur :** Your Organization Name

**Contact:** contact@example.com

**Hosting / Hébergement :** Your hosting provider

**Data protection / Protection des données :** This application does not store any personal data.

**Audience measurement / Mesure d'audience :** [Describe your Umami setup if applicable, or state "No audience measurement tools are used."]

**Right to complain / Droit de réclamation :** You may lodge a complaint with the CNIL (https://www.cnil.fr/) or your local supervisory authority.
