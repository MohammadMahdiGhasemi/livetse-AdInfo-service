---
name: project-review
description: "Perform a full-stack project review: analyze codebase structure, tech stack, module completeness, architecture patterns, issues, and provide a structured report."
---

# Project Review Skill

A systematic workflow for reviewing any project's codebase and producing a structured analysis report.

## Trigger

User says: "check this project", "look at this project", "project review", "analyze this project", or similar.

## Workflow

### Step 1: Project Discovery
1. Read the project root directory to understand top-level structure
2. Read config files: `pyproject.toml`, `setup.py`, `requirements.txt`, `package.json`, `Cargo.toml`, `go.mod`, `README.md`
3. Check for `.env*` files to understand environment configuration
4. Check for Docker files (`Dockerfile`, `docker-compose.yml`)

### Step 2: Module Mapping
1. Identify the main source directory (`app/`, `src/`, `lib/`, `pkg/`, `cmd/`)
2. Glob for all source files by language extension
3. For each module/package: read the directory listing to understand its structure
4. Identify the architecture pattern (e.g., model→repo→service→router, or MVC, or clean architecture)

### Step 3: Deep Read
For each module, read key files to understand:
- Models/schemas (data structures)
- Repository/data layer (database access)
- Service layer (business logic)
- Router/handler layer (API endpoints)
- Tests (coverage, quality)
- Configuration (how config is loaded)

### Step 4: Quality Assessment
Check for:
- Empty/placeholder files (skeleton code)
- Missing tests or low test coverage
- Incomplete modules (models exist but handlers don't)
- Security issues (unprotected endpoints, hardcoded secrets)
- Missing dependencies or requirements files
- Inconsistent patterns across modules

### Step 5: Report Generation

Output a structured report with these sections:

```
## [Project Name] — [one-line description]

### Stack
- Framework: ...
- Database: ...
- Auth: ...
- Key dependencies: ...

### Modules

| Module | Status | Description |
|--------|--------|-------------|
| name | Complete/Partial/Skeleton | brief description |

### Architecture Pattern
[describe the pattern used]

### Issues Found
[bulleted list of issues, grouped by severity: Critical / Warning / Info]

### What would you like to do with this project?
[offer next steps]
```

## Output Rules
- Use tables for module status
- Group issues by severity (Critical, Warning, Info)
- Be specific: cite file paths and line numbers when relevant
- End with actionable next steps
- No emojis unless user requests them
