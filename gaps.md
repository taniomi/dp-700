# Knowledge Gaps

Aggregated list of gaps and areas to review across all studied modules. Updated after each study session.

## By Learning Path

### Learning Path 1: Ingest data with Microsoft Fabric

#### Module: Orchestrate processes and data movement with Microsoft Fabric

- Activity run input JSON (resolved config, e.g. the dynamic SQL query) vs output JSON (rows, duration, errors) (certyiq-1 Q10) — https://learn.microsoft.com/en-us/fabric/data-factory/monitoring-hub-pipeline-runs

#### Module: Work with real-time data in an Eventhouse in Microsoft Fabric

- KQL `row_rank_dense(col, restart)`: rank restarts when the predicate is true; `sort by` defaults to desc (certyiq-2 Q10) — https://learn.microsoft.com/en-us/kusto/query/row-rank-dense-function?view=microsoft-fabric

### Learning Path 2: Implement a Lakehouse with Microsoft Fabric

#### Module: Get started with lakehouses in Microsoft Fabric

- Shortcut caching: GCS/S3/S3-compatible/gateway only (not ADLS), files ≤ 1 GB, retention 1–28 days; enable → less egress (certyiq-0 Q7-8, certyiq-1 Q6) — https://learn.microsoft.com/en-us/fabric/onelake/onelake-shortcuts#caching

#### Module: Work with Delta Lake tables in Microsoft Fabric

- Delta MERGE load pattern: table missing → overwrite (full load); exists → MERGE upsert (incremental) (certyiq-2 Q8) — https://docs.delta.io/latest/delta-update.html#upsert-into-a-table-using-merge

### Learning Path 5: Manage a Microsoft Fabric environment

#### Module: Implement continuous integration and continuous delivery (CI/CD) in Microsoft Fabric

- Deployment pipelines: folders are part of the item name → moved item's folder is created in the target; other items still deploy (certyiq-1 Q2) — https://learn.microsoft.com/en-us/fabric/cicd/deployment-pipelines/understand-the-deployment-process#folders-in-deployment-pipelines-preview

#### Module: Monitor activities in Microsoft Fabric

- Semantic link (sempy) to run + monitor a semantic model refresh from a notebook; Monitoring hub can't trigger it (certyiq-1 Q4) — https://learn.microsoft.com/en-us/python/api/semantic-link-sempy/sempy.fabric?view=semantic-link-python

#### Module: Secure data access in Microsoft Fabric

- Workspace roles cover every item: Contributor reads/writes all lakehouse data → isolate PII in another workspace (certyiq-1 Q1) — https://learn.microsoft.com/en-us/fabric/fundamentals/roles-workspaces
- Domain roles: only Fabric admin creates domains; domain admin → subdomains + assign workspaces; contributor → assign own workspaces (certyiq-2 Q2) — https://learn.microsoft.com/en-us/fabric/governance/domains#domain-roles

### Outside the course modules

- Direct Lake guardrails: rows per table by SKU (F32 = 300M) → over the limit = fallback/errors → fix with a bigger capacity (certyiq-0 Q2, certyiq-2 Q1) — https://learn.microsoft.com/en-us/fabric/fundamentals/direct-lake-overview#fabric-capacity-requirements

## By Topic

### Pipelines and monitoring

- Activity run input JSON (resolved config, e.g. the dynamic SQL query) vs output JSON (rows, duration, errors) — https://learn.microsoft.com/en-us/fabric/data-factory/monitoring-hub-pipeline-runs
- Semantic link (sempy) to run + monitor a semantic model refresh from a notebook; Monitoring hub can't trigger it — https://learn.microsoft.com/en-us/python/api/semantic-link-sempy/sempy.fabric?view=semantic-link-python

### KQL

- KQL `row_rank_dense(col, restart)`: rank restarts when the predicate is true; `sort by` defaults to desc — https://learn.microsoft.com/en-us/kusto/query/row-rank-dense-function?view=microsoft-fabric

### OneLake and shortcuts

- Shortcut caching: GCS/S3/S3-compatible/gateway only (not ADLS), files ≤ 1 GB, retention 1–28 days; enable → less egress — https://learn.microsoft.com/en-us/fabric/onelake/onelake-shortcuts#caching

### Loading patterns

- Delta MERGE load pattern: table missing → overwrite (full load); exists → MERGE upsert (incremental) — https://docs.delta.io/latest/delta-update.html#upsert-into-a-table-using-merge

### Lifecycle management

- Deployment pipelines: folders are part of the item name → moved item's folder is created in the target; other items still deploy — https://learn.microsoft.com/en-us/fabric/cicd/deployment-pipelines/understand-the-deployment-process#folders-in-deployment-pipelines-preview

### Security and governance

- Workspace roles cover every item: Contributor reads/writes all lakehouse data → isolate PII in another workspace — https://learn.microsoft.com/en-us/fabric/fundamentals/roles-workspaces
- Domain roles: only Fabric admin creates domains; domain admin → subdomains + assign workspaces; contributor → assign own workspaces — https://learn.microsoft.com/en-us/fabric/governance/domains#domain-roles

### Performance

- Direct Lake guardrails: rows per table by SKU (F32 = 300M) → over the limit = fallback/errors → fix with a bigger capacity — https://learn.microsoft.com/en-us/fabric/fundamentals/direct-lake-overview#fabric-capacity-requirements
