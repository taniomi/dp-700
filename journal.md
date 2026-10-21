# Study Journal

Study journal tracking detailed learning from DP-700 Microsoft Learn modules.

## Learning Path 1: Ingest data with Microsoft Fabric

### Module: Ingest Data with Dataflows Gen2 in Microsoft Fabric

**Session 1 (2026-10-21)**

- **Studied:** https://learn.microsoft.com/en-us/training/modules/use-dataflow-gen-2-fabric/ (quick review; covered in DP-600 Session 7)

- **Key concepts:**
  - **Dataflow Gen2**: A low-code ETL tool
  - **Dataflow activity in pipelines**: ELT enabled when adding dataflow to a pipeline as an activity (Copy → Dataflow). Easy orchestration through the pipeline's schedule when dataflow is present in the pipeline.
  - **Destinations vs dataflow connector**: Output readable via the dataflow connector (e.g. Power BI source); recommended: write to a Lakehouse/Warehouse destination and consume from there
  - **On-premises data gateway**: Only path to on-prem sources. Only the last 6 monthly versions are supported → outdated gateway fails the refresh; pipeline settings can't fix it

- **Gaps/To review:**
