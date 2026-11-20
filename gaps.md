# Knowledge Gaps

Aggregated list of gaps and areas to review across all studied modules. Updated after each study session.

## By Learning Path

### Learning Path 1: Ingest data with Microsoft Fabric

#### Module: Orchestrate processes and data movement with Microsoft Fabric

- Activity run input JSON (resolved config, e.g. the dynamic SQL query) vs output JSON (rows, duration, errors) (certyiq-1 Q10) — https://learn.microsoft.com/en-us/fabric/data-factory/monitoring-hub-pipeline-runs
- Pipeline vs notebook vs Spark job definition: interactive/collaborative load → notebook; repeatable orchestration → pipeline; non-interactive production → SJD (microsoft-1 Q19) — https://learn.microsoft.com/en-us/training/modules/orchestrate-processes-in-fabric/2-choose-between-pipeline-notebook
- ForEach `items` needs an array: JSON string parameter → `@json(...)`; `createArray()` wraps it as a 1-item array (microsoft-1 Q45) — https://learn.microsoft.com/en-us/fabric/data-factory/pipeline-troubleshoot-guide#general

#### Module: Use Apache Spark in Microsoft Fabric

- Native execution engine (C++ vectorized, columnar) → complex joins/aggregations on Delta/Parquet, no code change; AQE is already on by default (microsoft-1 Q49) — https://learn.microsoft.com/en-us/fabric/data-engineering/native-execution-engine-overview
- NEE + UDFs: test key says use the traditional engine (no UDF support); current docs say NEE now supports Python/Scala UDFs → key likely outdated (microsoft-1 Q48) — https://learn.microsoft.com/en-us/fabric/data-engineering/native-execution-engine-overview#limitations

#### Module: Work with real-time data in an Eventhouse in Microsoft Fabric

- KQL `row_rank_dense(col, restart)`: rank restarts when the predicate is true; `sort by` defaults to desc (certyiq-2 Q10) — https://learn.microsoft.com/en-us/kusto/query/row-rank-dense-function?view=microsoft-fabric

### Learning Path 2: Implement a Lakehouse with Microsoft Fabric

#### Module: Work with Delta Lake tables in Microsoft Fabric

- Delta MERGE load pattern: table missing → overwrite (full load); exists → MERGE upsert (incremental) (certyiq-2 Q8) — https://docs.delta.io/latest/delta-update.html#upsert-into-a-table-using-merge
- Delta streaming source `ignoreChanges`: UPDATE/MERGE/DELETE in the source no longer fails the stream; rewritten files re-emitted (duplicates), deletes not propagated (microsoft-1 Q21) — https://learn.microsoft.com/en-us/training/modules/work-delta-lake-tables-fabric/5-use-delta-lake-streaming-data
- Streaming job: Spark job definition + Structured Streaming → Delta table sink + `checkpointLocation` (microsoft-1 Q33) — https://learn.microsoft.com/en-us/training/modules/work-delta-lake-tables-fabric/5-use-delta-lake-streaming-data

#### Module: Organize a Fabric lakehouse using medallion architecture design

- Incremental loads + data quality → medallion layers + Dataflows Gen2 for cleansing (not direct load into the dimensional model) (microsoft-1 Q23) — https://learn.microsoft.com/en-us/training/modules/describe-medallion-architecture/

### Learning Path 3: Implement Real-Time Intelligence with Microsoft Fabric

#### Module: Use Eventstream in Microsoft Fabric

- Event Hubs → lakehouse: eventstream with an Event Hubs source + event processor to filter/transform (not pipelines/ADF, which are batch) (microsoft-1 Q22) — https://learn.microsoft.com/en-us/fabric/real-time-intelligence/event-streams/process-events-using-event-processor-editor

### Learning Path 4: Implement a data warehouse with Microsoft Fabric

#### Module: Get started with data warehouses in Microsoft Fabric

- Store choice: large scans/aggregations + T-SQL stored procs + many concurrent Power BI users → warehouse (lakehouse = Spark-first; eventhouse = KQL/real-time; SQL database = operational) (microsoft-1 Q31) — https://learn.microsoft.com/en-us/fabric/fundamentals/decision-guide-lakehouse-warehouse

#### Module: Load data into a Microsoft Fabric data warehouse

- Combine warehouse + lakehouse data into one table with least effort → CTAS with cross-database query (microsoft-1 Q29) — https://learn.microsoft.com/en-us/training/modules/load-data-into-microsoft-fabric-data-warehouse/4-load-data-using-tsql

### Learning Path 5: Manage a Microsoft Fabric environment

#### Module: Implement continuous integration and continuous delivery (CI/CD) in Microsoft Fabric

- Deployment pipelines: folders are part of the item name → moved item's folder is created in the target; other items still deploy (certyiq-1 Q2) — https://learn.microsoft.com/en-us/fabric/cicd/deployment-pipelines/understand-the-deployment-process#folders-in-deployment-pipelines-preview
- Restrict who edits deployment pipeline settings → deployment pipeline admin role (separate from workspace roles) (microsoft-1 Q9) — https://learn.microsoft.com/en-us/fabric/cicd/deployment-pipelines/understand-the-deployment-process
- Warehouse schema changes via a database project → SDK-style SQL database project + import the existing schema (not DACPAC/non-SDK) (microsoft-1 Q10) — https://learn.microsoft.com/en-us/sql/tools/sql-database-projects/get-started

#### Module: Monitor activities in Microsoft Fabric

- Semantic link (sempy) to run + monitor a semantic model refresh from a notebook; Monitoring hub can't trigger it (certyiq-1 Q4) — https://learn.microsoft.com/en-us/python/api/semantic-link-sempy/sempy.fabric?view=semantic-link-python
- Intermittent failures/delays → Monitor hub filtered by status + start time, plus alerts for future failures (microsoft-1 Q36, Q38, Q39) — https://learn.microsoft.com/en-us/fabric/admin/monitoring-hub
- Semantic model refresh failures → Real-Time hub, Fabric workspace item events → filter on failed status → email alert (microsoft-1 Q37) — https://learn.microsoft.com/en-us/fabric/real-time-hub/set-alerts-fabric-workspace-item-events
- Rule-based alerts on changing data/conditions → Activator (Monitor hub = run status only; capacity app = utilization) (microsoft-1 Q41) — https://learn.microsoft.com/en-us/training/modules/monitor-fabric-items/

#### Module: Secure data access in Microsoft Fabric

- Workspace roles cover every item: Contributor reads/writes all lakehouse data → isolate PII in another workspace (certyiq-1 Q1) — https://learn.microsoft.com/en-us/fabric/fundamentals/roles-workspaces
- Domain roles: only Fabric admin creates domains; domain admin → subdomains + assign workspaces; contributor → assign own workspaces (certyiq-2 Q2) — https://learn.microsoft.com/en-us/fabric/governance/domains#domain-roles
- Per-business-unit governance (data mesh) → delegate tenant settings to the domain level (microsoft-1 Q1) — https://learn.microsoft.com/en-us/fabric/governance/domains#delegate-settings-to-the-domain-level

### Outside the course modules

- Direct Lake guardrails: rows per table by SKU (F32 = 300M) → over the limit = fallback/errors → fix with a bigger capacity (certyiq-0 Q2, certyiq-2 Q1) — https://learn.microsoft.com/en-us/fabric/fundamentals/direct-lake-overview#fabric-capacity-requirements
- Continuous replication of Azure SQL DB into OneLake, analytics-ready → mirroring (not dataflows/ADF) (microsoft-1 Q27) — https://learn.microsoft.com/en-us/fabric/database/mirrored-database/overview

## By Topic

### Pipelines and orchestration

- Activity run input JSON (resolved config, e.g. the dynamic SQL query) vs output JSON (rows, duration, errors) — https://learn.microsoft.com/en-us/fabric/data-factory/monitoring-hub-pipeline-runs
- Pipeline vs notebook vs Spark job definition: interactive/collaborative load → notebook; repeatable orchestration → pipeline; non-interactive production → SJD — https://learn.microsoft.com/en-us/training/modules/orchestrate-processes-in-fabric/2-choose-between-pipeline-notebook
- ForEach `items` needs an array: JSON string parameter → `@json(...)`; `createArray()` wraps it as a 1-item array — https://learn.microsoft.com/en-us/fabric/data-factory/pipeline-troubleshoot-guide#general

### Monitoring and alerts

- Semantic link (sempy) to run + monitor a semantic model refresh from a notebook; Monitoring hub can't trigger it — https://learn.microsoft.com/en-us/python/api/semantic-link-sempy/sempy.fabric?view=semantic-link-python
- Intermittent failures/delays → Monitor hub filtered by status + start time, plus alerts for future failures — https://learn.microsoft.com/en-us/fabric/admin/monitoring-hub
- Semantic model refresh failures → Real-Time hub, Fabric workspace item events → filter on failed status → email alert — https://learn.microsoft.com/en-us/fabric/real-time-hub/set-alerts-fabric-workspace-item-events
- Rule-based alerts on changing data/conditions → Activator (Monitor hub = run status only; capacity app = utilization) — https://learn.microsoft.com/en-us/training/modules/monitor-fabric-items/

### Streaming

- Delta streaming source `ignoreChanges`: UPDATE/MERGE/DELETE in the source no longer fails the stream; rewritten files re-emitted (duplicates), deletes not propagated — https://learn.microsoft.com/en-us/training/modules/work-delta-lake-tables-fabric/5-use-delta-lake-streaming-data
- Streaming job: Spark job definition + Structured Streaming → Delta table sink + `checkpointLocation` — https://learn.microsoft.com/en-us/training/modules/work-delta-lake-tables-fabric/5-use-delta-lake-streaming-data
- Event Hubs → lakehouse: eventstream with an Event Hubs source + event processor to filter/transform (not pipelines/ADF, which are batch) — https://learn.microsoft.com/en-us/fabric/real-time-intelligence/event-streams/process-events-using-event-processor-editor

### KQL

- KQL `row_rank_dense(col, restart)`: rank restarts when the predicate is true; `sort by` defaults to desc — https://learn.microsoft.com/en-us/kusto/query/row-rank-dense-function?view=microsoft-fabric

### Loading patterns

- Delta MERGE load pattern: table missing → overwrite (full load); exists → MERGE upsert (incremental) — https://docs.delta.io/latest/delta-update.html#upsert-into-a-table-using-merge
- Incremental loads + data quality → medallion layers + Dataflows Gen2 for cleansing (not direct load into the dimensional model) — https://learn.microsoft.com/en-us/training/modules/describe-medallion-architecture/

### Data stores and ingestion

- Store choice: large scans/aggregations + T-SQL stored procs + many concurrent Power BI users → warehouse (lakehouse = Spark-first; eventhouse = KQL/real-time; SQL database = operational) — https://learn.microsoft.com/en-us/fabric/fundamentals/decision-guide-lakehouse-warehouse
- Combine warehouse + lakehouse data into one table with least effort → CTAS with cross-database query — https://learn.microsoft.com/en-us/training/modules/load-data-into-microsoft-fabric-data-warehouse/4-load-data-using-tsql
- Continuous replication of Azure SQL DB into OneLake, analytics-ready → mirroring (not dataflows/ADF) — https://learn.microsoft.com/en-us/fabric/database/mirrored-database/overview

### Lifecycle management

- Deployment pipelines: folders are part of the item name → moved item's folder is created in the target; other items still deploy — https://learn.microsoft.com/en-us/fabric/cicd/deployment-pipelines/understand-the-deployment-process#folders-in-deployment-pipelines-preview
- Restrict who edits deployment pipeline settings → deployment pipeline admin role (separate from workspace roles) — https://learn.microsoft.com/en-us/fabric/cicd/deployment-pipelines/understand-the-deployment-process
- Warehouse schema changes via a database project → SDK-style SQL database project + import the existing schema (not DACPAC/non-SDK) — https://learn.microsoft.com/en-us/sql/tools/sql-database-projects/get-started

### Security and governance

- Workspace roles cover every item: Contributor reads/writes all lakehouse data → isolate PII in another workspace — https://learn.microsoft.com/en-us/fabric/fundamentals/roles-workspaces
- Domain roles: only Fabric admin creates domains; domain admin → subdomains + assign workspaces; contributor → assign own workspaces — https://learn.microsoft.com/en-us/fabric/governance/domains#domain-roles
- Per-business-unit governance (data mesh) → delegate tenant settings to the domain level — https://learn.microsoft.com/en-us/fabric/governance/domains#delegate-settings-to-the-domain-level

### Performance

- Direct Lake guardrails: rows per table by SKU (F32 = 300M) → over the limit = fallback/errors → fix with a bigger capacity — https://learn.microsoft.com/en-us/fabric/fundamentals/direct-lake-overview#fabric-capacity-requirements
- Native execution engine (C++ vectorized, columnar) → complex joins/aggregations on Delta/Parquet, no code change; AQE is already on by default — https://learn.microsoft.com/en-us/fabric/data-engineering/native-execution-engine-overview
- NEE + UDFs: test key says use the traditional engine (no UDF support); current docs say NEE now supports Python/Scala UDFs → key likely outdated — https://learn.microsoft.com/en-us/fabric/data-engineering/native-execution-engine-overview#limitations
