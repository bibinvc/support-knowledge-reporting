# Knowledge Content Planning and Reporting

New **AI-assisted educational project**, created 10 November 2026. It demonstrates a small SQL-backed helpdesk knowledge base and a **compiled C# reporting client**, with a local web interface. Six incidents and three sample articles are entirely fictitious.

## Architecture

1. Python's standard `sqlite3` module stores synthetic incident status/priority records and sample knowledge articles.
2. SQL queries aggregate current-state counts and search article text using bound parameters and literal wildcard escaping.
3. A read-only local HTTP API exposes the synthetic report and knowledge search. The HTML/JavaScript interface displays counts and guide cards.
4. The C# command-line client reads the local API or a saved JSON report, validates the schema, status set, synthetic flag and totals, and exports CSV. It uses the installed Windows .NET Framework compiler and `DataContractJsonSerializer`; it is not an ASP.NET Core application or a SQL Server integration.

## Run on Windows

Python 3.12 and the installed .NET Framework C# compiler are sufficient. No NuGet package, cloud account or global installation is required.

```powershell
python run_validation.py
python app.py --port 9880
```

Open `http://127.0.0.1:9880`. From another terminal, after the build:

```powershell
./build/ReportTool.exe http://127.0.0.1:9880/api/report reports/report.csv
```

The validator accepts `--compiler ABSOLUTE_CSC_PATH` when the compiler is elsewhere. The current build targets the existing Windows .NET Framework runtime, not modern cross-platform .NET. Compiler paths are passed as absolute Windows arguments.

## Results and evidence

- `reports/report.json` and `reports/report.csv` contain the actual generated synthetic report: **Open 2, In progress 1, Resolved 2, Closed 1, Total 6**.
- `evidence/validation-summary.json` records the compiler/Python/SQLite versions, source hashes and **38 passing tests**, with no failures, errors or skips. These include 24 original reporting checks and 14 content-planning checks.
- `evidence/tests.txt` records the named tests. They cover SQL counts, empty data, seed idempotence, database constraints, literal search, invalid C# payloads, preserved output on rejection, report/API agreement, external-URL refusal and redirect refusal.
- The initial run caught an unclosed SQLite connection on Windows. Connections now explicitly close after their transaction, and the full corrected suite passed.
- Browser validation, when present in `evidence/browser-validation.json`, records the separately tested UI behaviour.

The report contains current-state counts only. It does not measure resolution time, SLA compliance, user satisfaction or service performance.

## Prepared survey material

`docs/teams-survey-template.json` contains two feedback questions and a draft invitation for a Teams channel. It is a **prepared template**, not an executed Microsoft Forms/Teams workflow. No Teams tenant was connected and no real responses were collected.

The sample articles demonstrate clear troubleshooting guidance. They are not a real company's approved procedures. No AML, fraud or financial-compliance training was delivered; such content must come from the responsible compliance team.

## Scope

The server binds to `127.0.0.1`, checks its Host header and exposes read-only fixtures. It has no user authentication, ticket editing, production deployment, enterprise integration or scheduled service. Keep fictional data in this local exercise. C# HTTP requests accept only explicit literal-loopback URLs, disable proxies and do not follow redirects.

The source archive excludes the local database and compiled build outputs. Rebuild them with `run_validation.py`.

## Content inventory and migration preparation

An extension created on 16 November 2026 inventories five fictional source
documents. It checks category, document type, ownership, review date, duplicate
content and source-to-target mapping. SHA-256 hashes support a checked local
staging copy. No Microsoft tenant is connected.

```powershell
python content_plan.py --as-of 2026-11-16
python content_plan.py --as-of 2026-11-16 --stage reports/staged-documents
```

The first command prepares a migration manifest without copying documents.
The second stages only ready content locally. Both preserve the source files.
The example has two ready documents and three held documents. Duplicate copies
need a canonical-source decision; one old document needs an owner and review.
Changed source hashes and mismatched existing staging content stop publication.
The staging directory is published only after the complete copy passes checks.

`docs/sharepoint-design.json` proposes site navigation, library metadata,
review views and publishing controls. `docs/content-ownership-and-adoption.md`
sets out needs-gathering questions, ownership responsibilities, pilot tasks and
review procedures. These documents are design proposals, with no real
stakeholder responses, adoption measurements or SharePoint deployment.

The extension is AI-assisted educational work. It supports content inventory,
migration preparation and information-governance practice. It does not establish
experience administering a production SharePoint site or migrating real records.

The new tests cover ownership and review holds, duplicate content, duplicate IDs,
case-insensitive target collisions, taxonomy and date validation, missing sources,
unsafe paths, changed-source rejection, verified copies, retries, skipped held
content, existing-output protection and overlapping-directory rejection.

## Primary references

- [Python 3.12 SQLite interface](https://docs.python.org/3.12/library/sqlite3.html)
- [Microsoft: DataContractJsonSerializer](https://learn.microsoft.com/en-us/dotnet/api/system.runtime.serialization.json.datacontractjsonserializer)

All project code and sample documentation are educational work created with AI assistance; no existing employer or customer deployment is claimed.
