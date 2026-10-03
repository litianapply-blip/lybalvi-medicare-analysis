# Three-minute portfolio walkthrough

I built an independent analysis of US LYBALVI prescribing using public Medicare Part D data. Observed claims increased from 39,134 in 2023 to 57,090 in 2024, or 45.9%. I used Python for retrieval and validation, DuckDB SQL for reporting, and Tableau for visualization. Because CMS suppresses low-volume records, I distinguish observed record changes from confirmed prescribing adoption.

**0:00-0:30: Business question.** "This independent project asks how observed US LYBALVI prescribing changed in public Medicare Part D records, and which city or specialty segments merit further investigation. I chose a small, explicitly defined comparison set so the denominator can be explained."

**0:30-1:15: Data and scope.** Show config.json and one source manifest entry. Explain service year versus publication year, the year/NPI/brand/generic row grain, and suppression of records with fewer than 11 claims. State that the data do not represent all payers or unique patients. Explain why the comparison set is not called oral-only or total market share.

**1:15-2:00: Pipeline and reliability.** Show the SQL that computes selected-set share. Explain Python orchestration versus DuckDB as the database engine. Demonstrate an offline rerun and the controlled failure evidence. Describe the switch from a staged, validated bundle to current outputs and why malformed input cannot replace the last good CSVs.

**2:00-2:40: Findings and dashboard.** Use docs/findings.md and the completed Tableau workbook. Show a single-year city or specialty filter, explain the ratio denominator, and check one displayed number against docs/tableau_reconciliation.md. Use "newly observed records," not "new prescribers" or "adoption."

**2:40-3:00: Limits and next decision.** Explain that claims, provider attributes and reporting visibility can all change. Current all-payer claims, access information and appropriate business context would be needed before resource allocation. State which code and verification Codex assisted with and what you personally reviewed and authored.

## Practice questions

- Change the analyst-chosen segment volume threshold, rerun, and explain what changes.
- Explain why combining city and specialty summaries double-counts the same underlying claims.
- Explain why distinct NPIs across products or years cannot simply be added.
- Trace a chart value from Tableau to the exported CSV, SQL table and raw snapshot.
- Explain the manual Tableau refresh process without claiming it is automatic or real-time.
