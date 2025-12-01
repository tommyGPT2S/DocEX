# Keystone RAIN Platform Architecture for Novartis MMF Use Cases

## High-Level Architecture Diagram

```mermaid
graph TB
    subgraph "Data Sources"
        A[Model N<br/>Chargebacks/EDI]
        B[SAP 4 HANA<br/>Customer Master]
        C[G-Drive/G-Suite<br/>GPO Rosters/DDD Matrix]
        D[Email Attachments<br/>GPO Rosters]
        E[State Web Portals<br/>Medicaid Invoices]
        F[Federal Databases<br/>DEA/HIBCC/HRSA]
    end

    subgraph "Keystone RAIN Platform"
        subgraph "Ingestion Layer"
            G[Multi-Format<br/>Document Ingestion]
            H[Basket Organization<br/>raw_chargebacks<br/>processed_chargebacks<br/>medicaid_invoices]
        end

        subgraph "Processing Layer"
            I[LLM Adapters<br/>Structured Data Extraction]
            J[Entity Matching<br/>Duplicate Detection]
            K[Processor Framework<br/>Workflow Automation]
            L[External API<br/>Integration]
        end

        subgraph "Storage & Metadata"
            M[Document Storage<br/>Filesystem/S3]
            N[Metadata Management<br/>Key-Value Store]
            O[Operation Tracking<br/>Audit Trail]
        end

        subgraph "RAIN Integration"
            P[Feature Encoding<br/>RAIN Format]
            Q[Cross-Use Case<br/>Feature Reuse]
        end
    end

    subgraph "Output & Integration"
        R[SAP Customer<br/>Creation Requests]
        S[Exception Queues<br/>Human Review]
        T[RAIN Encoded Features<br/>Forecasting Models]
        U[Compliance<br/>Documentation]
    end

    A --> G
    B --> L
    C --> G
    D --> G
    E --> G
    F --> L

    G --> H
    H --> I
    I --> J
    J --> K
    K --> L
    L --> M

    I --> N
    J --> N
    K --> O
    L --> N

    N --> P
    P --> Q

    K --> R
    K --> S
    Q --> T
    O --> U

    style G fill:#3498db,color:#fff
    style I fill:#2ecc71,color:#fff
    style J fill:#2ecc71,color:#fff
    style K fill:#e74c3c,color:#fff
    style L fill:#f39c12,color:#fff
    style P fill:#9b59b6,color:#fff
```

## Detailed Component Architecture

```mermaid
graph LR
    subgraph "Chargeback Workflow"
        A1[Chargeback<br/>Kickout] --> A2[Extract<br/>Identifiers]
        A2 --> A3[Duplicate<br/>Check]
        A3 --> A4[Contract<br/>Eligibility]
        A4 --> A5[GPO Roster<br/>Validation]
        A5 --> A6[Federal DB<br/>Validation]
        A6 --> A7[SAP Customer<br/>Creation]
        A7 --> A8[Chargeback<br/>Resolution]
    end

    subgraph "Medicaid Rebate Workflow"
        B1[Invoice<br/>Ingestion] --> B2[Format<br/>Normalization]
        B2 --> B3[Data<br/>Extraction]
        B3 --> B4[Duplicate<br/>Detection]
        B4 --> B5[Dispute<br/>Flagging]
        B5 --> B6[Payment<br/>Routing]
    end

    subgraph "Platform Services"
        C1[LLM<br/>Extraction]
        C2[Entity<br/>Matching]
        C3[API<br/>Integration]
        C4[Audit<br/>Trail]
    end

    A2 -.-> C1
    A3 -.-> C2
    A6 -.-> C3
    A8 -.-> C4

    B3 -.-> C1
    B4 -.-> C2
    B5 -.-> C3
    B6 -.-> C4

    style C1 fill:#3498db,color:#fff
    style C2 fill:#2ecc71,color:#fff
    style C3 fill:#f39c12,color:#fff
    style C4 fill:#9b59b6,color:#fff
```

## Data Flow Architecture

```mermaid
flowchart TD
    Start[Document Ingestion] --> Extract[LLM Extraction<br/>98%+ Accuracy]
    Extract --> Enrich[Metadata Enrichment]
    Enrich --> Match{Entity<br/>Matching}
    
    Match -->|New Entity| Validate[External Validation<br/>SAP/DEA/HIBCC/HRSA]
    Match -->|Existing Entity| Update[Update Metadata]
    
    Validate --> Encode[RAIN Feature<br/>Encoding]
    Update --> Encode
    
    Encode --> Store[Store in Platform]
    Store --> Route{Workflow<br/>Routing}
    
    Route -->|Success| Complete[Complete &<br/>Audit Trail]
    Route -->|Exception| Review[Exception Queue<br/>Human Review]
    
    Complete --> Forecast[RAIN Features →<br/>Forecasting Models]
    
    style Extract fill:#2ecc71,color:#fff
    style Validate fill:#f39c12,color:#fff
    style Encode fill:#9b59b6,color:#fff
    style Complete fill:#3498db,color:#fff
```

## System Integration Architecture

```mermaid
graph TB
    subgraph "Keystone RAIN Platform"
        Platform[Platform Core<br/>Document Management<br/>Processing Framework]
    end

    subgraph "External Systems"
        SAP[SAP 4 HANA<br/>Customer Master]
        ModelN[Model N<br/>Chargeback System]
        GDrive[Google Drive<br/>GPO Rosters]
        FedDB[Federal Databases<br/>DEA/HIBCC/HRSA]
    end

    subgraph "LLM Services"
        OpenAI[OpenAI GPT-4o<br/>Data Extraction]
    end

    subgraph "RAIN System"
        RAIN[RAIN Encoding<br/>Feature Engineering]
        Forecast[Forecasting<br/>Models]
    end

    Platform <--> SAP
    Platform <--> ModelN
    Platform <--> GDrive
    Platform <--> FedDB
    Platform --> OpenAI
    Platform --> RAIN
    RAIN --> Forecast

    style Platform fill:#3498db,color:#fff
    style RAIN fill:#9b59b6,color:#fff
    style Forecast fill:#e74c3c,color:#fff
```

## Use Case Coverage Matrix

| Platform Capability | Chargeback Use Case | Medicaid Rebate Use Case | Forecasting Use Case |
|---------------------|---------------------|-------------------------|----------------------|
| Document Ingestion | ✅ Model N, G-Drive, Email | ✅ State Portals, Email, NCPDP | ✅ Claim-level data |
| LLM Extraction | ✅ Customer IDs, Contract Info | ✅ Claim Details, NDC | ✅ Feature Extraction |
| Entity Matching | ✅ Duplicate Detection | ✅ Claim Deduplication | ✅ Entity Linking |
| Workflow Automation | ✅ 8-Step Process | ✅ Multi-Stage Pipeline | ✅ Data Prep Pipeline |
| External Integration | ✅ SAP, Federal DBs | ✅ State APIs | ✅ External Data Sources |
| Compliance/Audit | ✅ SOX Compliance | ✅ State Audit Support | ✅ Forecast Audit |
| RAIN Encoding | ✅ Customer Features | ✅ Claim Features | ✅ Forecasting Features |

