# Content ownership and adoption proposal

This educational proposal uses fictional support documents and role labels. No
actual HR case, health record, stakeholder interview or user response is included.
The SharePoint design is static and has not been deployed to Microsoft 365.

## Understand needs before configuring a site

Use the same short discussion guide with each team. Ask which tasks need an
instruction, where colleagues look today, what is hard to find, which sources
conflict and who can approve an update. Record the team, task, observed problem,
proposed improvement and decision owner. Validate the resulting inventory and
taxonomy with the teams before preparing a real migration. These are planned
questions; no interviews have been conducted in this project.

## Organise information

The example catalogue separates category from document type. The manifest maps
each source to its proposed target path and records its SHA-256 hash. Two files
are ready for local staging. Two duplicate copies need a decision about the
canonical version, and an old item needs both an owner and a review. A due date
equal to the inventory date remains current for that date.

The local staging step copies only ready documents, verifies hashes and leaves
source files intact. A changed source or mismatched existing staging directory
stops the operation. The default command produces a manifest only. This is
migration preparation and a local checked copy, not a SharePoint migration.

## Maintain a reliable knowledge source

| Responsibility | Proposed owner | Check |
|---|---|---|
| Content correctness | Named content owner | Approves task instructions and review dates |
| Taxonomy and duplicate decisions | Content steward | Confirms category, type and canonical source |
| Site operation and permissions | Site administrator | Validates technical configuration and access |
| Publication | Independent reviewer | Checks clarity, metadata and working links |

## Support adoption

Start with a small pilot group. Ask users to find three common instructions and
record whether they reached the expected page. Provide a short walkthrough,
publish a feedback route and assign one steward for questions. Agree review
responsibilities before wider rollout. The existing Teams survey template can
help prepare this feedback, but it has not been sent or connected to Forms.

Track reviewed/total documents, missing owners, duplicate groups and pilot task
completion with clear denominators. This project reports inventory counts only;
it claims no real adoption, satisfaction or organisational improvement result.
