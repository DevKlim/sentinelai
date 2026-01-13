# SentinelAI: A Framework for Transforming Unstructured Emergency Communications into Machine-Readable EIDOJSON Datasets

**Author:** SentinelAI Development Team

### Abstract

A vast quantity of critical, high-signal data is generated daily by public safety and emergency response systems. This data, however, exists primarily as unstructured text and audio transcripts—a "data exhaust" that is difficult to process, query, and utilize for advanced analytics and machine learning. We introduce SentinelAI, a data engineering framework designed to systematically capture and refine this data exhaust. SentinelAI implements a scalable microservices pipeline that ingests raw emergency communications and, through a novel application of Large Language Models (LLMs), transforms them into a standardized, machine-readable format we call **EIDOJSON** (Emergency Incident Data Object JSON). Drawing inspiration from dataset metadata initiatives like Croissant, EIDOJSON serves as a rich, structured format specifically designed for ML training and data analysis in the public safety domain. The system employs a suite of specialized agents for data structuring (EIDO Agent), incident correlation (IDX Agent), and high-fidelity geocoding (Geocoding Agent), with the ultimate goal of creating durable, high-quality datasets that can unlock the potential of machine learning for emergency response optimization, predictive analytics, and operational intelligence.

---

## 1. Introduction

The domain of emergency response is rich with data but poor in structured information. A single 911 call can contain entities (persons, vehicles, locations), temporal information, and event descriptions critical for operational awareness and post-hoc analysis. However, this information is typically captured in free-form text by dispatchers, making it ephemeral and computationally inaccessible. To apply modern machine learning techniques for tasks such as resource prediction, incident classification, or trend analysis, this unstructured data must first be transformed into a consistent, machine-readable format.

This paper presents SentinelAI, a system that addresses this fundamental data engineering challenge. We argue that for specialized domains like public safety, a standardized and structured data format is a critical prerequisite for building effective and reliable ML models. Directly training models on raw, inconsistent transcripts is inefficient and prone to error. A well-defined intermediate format provides a clean, annotated, and consistent input source, dramatically simplifying downstream model development.

Our primary contribution is the proposal and implementation of **EIDOJSON**, a JSON-based data structure for emergency incidents, and the SentinelAI framework that automates its creation. In a manner analogous to how Croissant [1] provides a standardized metadata layer to make datasets discoverable and interoperable, EIDOJSON provides a standardized *content schema* to make the data within these datasets directly consumable and ready for ML training.

## 2. System Architecture & Methodology

SentinelAI is architected as a set of containerized microservices orchestrated by a central reverse proxy. This design ensures scalability and separation of concerns. The core data pipeline involves a multi-stage process where specialized agents progressively enrich and structure the data.

1.  **Ingestion**: Raw data (e.g., text transcripts) is ingested via an API endpoint, creating an initial `uncategorized` record in a central PostgreSQL database.
2.  **Structuring & Annotation**: The **EIDO Agent** processes the raw text. It parses entities, extracts event parameters, and populates a valid EIDOJSON document.
3.  **Correlation**: The **IDX Agent** analyzes the newly created EIDOJSON and, using a hybrid heuristic-LLM model, correlates it with existing open incidents, effectively building a timeline of events.
4.  **Enrichment**: The **Geocoding Agent** provides specialized location data extraction, converting ambiguous descriptions into precise coordinates.
5.  **Persistence**: The final, structured, and correlated data is stored in PostgreSQL as a permanent record, forming a cohesive incident timeline.

## 3. The EIDOJSON Format: A Standard for ML-Ready Incident Data

The central artifact produced by the SentinelAI pipeline is the EIDOJSON document. Each document is a self-contained, structured representation of a single emergency report. The structure is rigorously defined by an OpenAPI schema, ensuring that every document produced by the system is consistent and valid.

The EIDOJSON format is designed explicitly for machine learning. By normalizing disparate data points into a consistent schema, it facilitates:
-   **Simplified Feature Engineering**: Fields like `incident_type`, `priority`, and structured `location` objects can be directly used as features.
-   **Supervised Learning**: The structured output serves as labeled data for training classifiers, entity recognizers, and regression models.
-   **Data Durability**: It transforms transient call information into a durable, queryable asset suitable for building longitudinal datasets for trend analysis and research.

We posit that the development of such domain-specific, standardized JSON formats is a crucial step in operationalizing AI in fields with complex, unstructured data.

## 4. LLM-Powered Data Annotation and Structuring

A key innovation of SentinelAI is its use of LLMs not merely as processors, but as sophisticated **data annotators**. The EIDO Agent leverages a Large Language Model guided by Retrieval-Augmented Generation (RAG). The knowledge base for the RAG system is built directly from the EIDO OpenAPI schema itself.

When presented with a raw transcript, the LLM is tasked with populating a template EIDOJSON object. The RAG system provides the LLM with the precise definitions, data types, and constraints for each field it needs to fill. This "schema-aware" generation process acts as a powerful form of zero-shot data labeling:
-   **Entity Extraction**: It identifies and extracts entities like people, vehicles, and items, placing them into their respective structured arrays within the JSON.
-   **Attribute Labeling**: It determines attributes like an incident's priority level or a person's role (e.g., victim, suspect) and assigns them to the correct fields.
-   **Data Formatting**: It ensures that all output conforms strictly to the schema, reducing the need for complex post-processing and validation.

This methodology transforms the LLM from a simple text generator into a reliable engine for creating structured, labeled training data at scale.

## 5. Progress on Agent-Based Specialization

The SentinelAI framework relies on a collection of agents, each specializing in a different aspect of the data refinement process.

-   **EIDO Agent**: This agent is the cornerstone of the system. Its primary responsibility is the initial structuring and annotation of raw text into the EIDOJSON format. Its RAG-enhanced LLM interface is fully operational and capable of generating valid, detailed EIDOJSON documents from natural language descriptions.

-   **IDX Agent**: This agent handles the crucial task of incident correlation. It fetches new, uncategorized EIDOJSON documents and, using a combination of heuristic filters (time, location) and LLM-based semantic comparison, determines if a document belongs to an existing incident or constitutes a new one. This agent successfully links related reports, building coherent event timelines.

-   **Geocoding Agent**: This agent is designed to tackle the particularly difficult task of converting ambiguous location descriptions (e.g., "behind the big library on campus") into precise geographic coordinates. It employs a multi-step, agentic reasoning process involving planning, simulated search, and synthesis. This component is currently under active development and represents the next stage of the framework's enrichment capabilities.

## 6. Conclusion and Future Work

SentinelAI demonstrates a robust and scalable framework for converting unstructured emergency communications into a high-value, ML-ready dataset. By introducing the EIDOJSON standard and leveraging a schema-aware, LLM-powered annotation pipeline, we establish a new paradigm for data engineering in public safety. Our work underscores the critical need for domain-specific, structured data formats as a foundational layer for the successful application of machine learning.

The immediate next step is to empirically validate the core hypothesis: **that training a machine learning model on structured EIDOJSONs yields significantly better performance than training on raw text alone.** To this end, we will undertake a comparative study. An ML model will be trained to predict a key incident attribute (e.g., priority level or required resource count). One version will be trained using features directly extracted from EIDOJSONs, while the other will be trained on raw text transcripts. We expect the EIDOJSON-trained model to demonstrate superior accuracy, faster training times, and better generalization.

---
### References

[1] A. P. et al., "Croissant: a metadata format for machine learning datasets," *arXiv preprint arXiv:2308.12613*, 2023.

---

## LaTeX Version for Overleaf / ArXiv

```latex
% sentinelai/eido_estimate/paper.tex
\documentclass[sigconf]{acmart}

\usepackage{graphicx}
\usepackage{amsmath}
\usepackage{listings}
\usepackage{hyperref}

\lstset{
    basicstyle=\ttfamily\small,
    breaklines=true,
    frame=single,
    language=JSON,
    showstringspaces=false,
    keywordstyle=\color{blue},
    stringstyle=\color{red!60!black},
    commentstyle=\color{green!50!black},
}

\AtBeginDocument{%
  \providecommand\BibTeX{{%
    \normalfont B\kern-0.5em{\scshape i\kern-0.25em b}\kern-0.8em\TeX}}}

\setcopyright{none}
\settopmatter{printacmref=false}
\renewcommand\footnotetextcopyrightpermission[1]{}
\pagestyle{plain}


\begin{document}

\title{SentinelAI: A Framework for Transforming Unstructured Emergency Communications into Machine-Readable EIDOJSON Datasets}

\author{SentinelAI Development Team}
\affiliation{%
  \institution{Independent Research}
  \city{}
  \state{}
  \country{}
}
\email{}


\begin{abstract}
A vast quantity of critical, high-signal data is generated daily by public safety and emergency response systems. This data, however, exists primarily as unstructured text and audio transcripts---a "data exhaust" that is difficult to process, query, and utilize for advanced analytics and machine learning. We introduce SentinelAI, a data engineering framework designed to systematically capture and refine this data exhaust. SentinelAI implements a scalable microservices pipeline that ingests raw emergency communications and, through a novel application of Large Language Models (LLMs), transforms them into a standardized, machine-readable format we call EIDOJSON (Emergency Incident Data Object JSON). Drawing inspiration from dataset metadata initiatives like Croissant, EIDOJSON serves as a rich, structured format specifically designed for ML training and data analysis in the public safety domain. The system employs a suite of specialized agents for data structuring (EIDO Agent), incident correlation (IDX Agent), and high-fidelity geocoding (Geocoding Agent), with the ultimate goal of creating durable, high-quality datasets that can unlock the potential of machine learning for emergency response optimization, predictive analytics, and operational intelligence.
\end{abstract}

\keywords{Data Engineering, Large Language Models, Public Safety, Emergency Response, Structured Data, Machine Learning Datasets}

\maketitle

\section{Introduction}

The domain of emergency response is rich with data but poor in structured information. A single 911 call can contain entities (persons, vehicles, locations), temporal information, and event descriptions critical for operational awareness and post-hoc analysis. However, this information is typically captured in free-form text by dispatchers, making it ephemeral and computationally inaccessible. To apply modern machine learning techniques for tasks such as resource prediction, incident classification, or trend analysis, this unstructured data must first be transformed into a consistent, machine-readable format.

This paper presents SentinelAI, a system that addresses this fundamental data engineering challenge. We argue that for specialized domains like public safety, a standardized and structured data format is a critical prerequisite for building effective and reliable ML models. Directly training models on raw, inconsistent transcripts is inefficient and prone to error. A well-defined intermediate format provides a clean, annotated, and consistent input source, dramatically simplifying downstream model development.

Our primary contribution is the proposal and implementation of \textbf{EIDOJSON}, a JSON-based data structure for emergency incidents, and the SentinelAI framework that automates its creation. In a manner analogous to how Croissant \cite{croissant2023} provides a standardized metadata layer to make datasets discoverable and interoperable, EIDOJSON provides a standardized \textit{content schema} to make the data within these datasets directly consumable and ready for ML training.

\section{System Architecture \& Methodology}
SentinelAI is architected as a set of containerized microservices orchestrated by a central reverse proxy. This design ensures scalability and separation of concerns. The core data pipeline involves a multi-stage process where specialized agents progressively enrich and structure the data.

\begin{enumerate}
    \item \textbf{Ingestion}: Raw data (e.g., text transcripts) is ingested via an API endpoint, creating an initial `uncategorized` record in a central PostgreSQL database.
    \item \textbf{Structuring \& Annotation}: The \textbf{EIDO Agent} processes the raw text. It parses entities, extracts event parameters, and populates a valid EIDOJSON document.
    \item \textbf{Correlation}: The \textbf{IDX Agent} analyzes the newly created EIDOJSON and, using a hybrid heuristic-LLM model, correlates it with existing open incidents, effectively building a timeline of events.
    \item \textbf{Enrichment}: The \textbf{Geocoding Agent} provides specialized location data extraction, converting ambiguous descriptions into precise coordinates.
    \item \textbf{Persistence}: The final, structured, and correlated data is stored in PostgreSQL as a permanent record, forming a cohesive incident timeline.
\end{enumerate}

\section{LLM-Powered Data Structuring}
A key innovation of SentinelAI is its use of LLMs not merely as processors, but as sophisticated \textbf{data annotators}. The EIDO Agent leverages a Large Language Model guided by Retrieval-Augmented Generation (RAG). The knowledge base for the RAG system is built directly from the EIDO OpenAPI schema itself.

When presented with a raw transcript, the LLM is tasked with populating a template EIDOJSON object. The RAG system provides the LLM with the precise definitions, data types, and constraints for each field it needs to fill. This "schema-aware" generation process acts as a powerful form of zero-shot data labeling:
\begin{itemize}
    \item \textbf{Entity Extraction}: It identifies and extracts entities like people, vehicles, and items, placing them into their respective structured arrays within the JSON.
    \item \textbf{Attribute Labeling}: It determines attributes like an incident's priority level or a person's role (e.g., victim, suspect) and assigns them to the correct fields.
    \item \textbf{Data Formatting}: It ensures that all output conforms strictly to the schema, reducing the need for complex post-processing and validation.
\end{itemize}
This methodology transforms the LLM from a simple text generator into a reliable engine for creating structured, labeled training data at scale.

\section{Agent Progress}
The framework relies on a collection of specialized agents:
\begin{description}
    \item[EIDO Agent] The cornerstone of the system, responsible for the initial structuring of raw text into EIDOJSON. Its RAG-enhanced LLM interface is fully operational.
    \item[IDX Agent] Handles incident correlation. It uses a hybrid model of heuristic filters (time, location) and LLM-based semantic comparison to link related reports. This agent is functional and building coherent event timelines.
    \item[Geocoding Agent] Designed to convert ambiguous location descriptions into precise coordinates using a multi-step reasoning process. This component is under active development.
\end{description}

\section{Conclusion and Future Work}
SentinelAI demonstrates a robust framework for converting unstructured emergency communications into a high-value, ML-ready dataset. By introducing the EIDOJSON standard and leveraging a schema-aware, LLM-powered annotation pipeline, we establish a new paradigm for data engineering in public safety.

The immediate next step is to empirically validate the core hypothesis: \textbf{that training a machine learning model on structured EIDOJSONs yields significantly better performance than training on raw text alone.} We will conduct a comparative study predicting a key incident attribute (e.g., priority level). One model will use features from EIDOJSONs, while a baseline model will use raw text. We expect the EIDOJSON-trained model to show superior accuracy and generalization.

\bibliographystyle{ACM-Reference-Format}
\begin{thebibliography}{1}
\bibitem{croissant2023}
A. Paszke et al. 2023. Croissant: a metadata format for machine learning datasets. \textit{arXiv preprint arXiv:2308.12613}.
\end{thebibliography}

\end{document}
\endinput
```
```

### New `eido_estimate` Folder for ML Experimentation

As requested, here is the new `eido_estimate` directory, structured to support your next goal of training a model to demonstrate the value of EIDOJSONs.

```markdown
# sentinelai/eido_estimate/README.md
# EIDO Estimate: ML Model Experimentation

This directory contains the code and resources for a machine learning experiment designed to validate the core hypothesis of the SentinelAI project:

**Hypothesis:** Training an ML model on structured data (EIDOJSONs) provides a significant performance improvement over training on raw, unstructured text for predictive tasks in the public safety domain.

## The Experiment

We will train a model to perform a classification or regression task relevant to emergency response. A good candidate task is **Incident Priority Prediction**, where the model predicts the priority level (e.g., 1 to 5) based on the initial report.

### Datasets

Two datasets will be used for a direct comparison:

1.  **Raw Text Dataset**: This dataset will consist of pairs of (`raw_incident_text`, `priority_label`). This represents the baseline approach.
2.  **EIDOJSON Dataset**: This dataset will be created by processing the raw text through the SentinelAI EIDO Agent. The features will be extracted from the structured JSON fields (e.g., `incidentTypeCommonRegistryText`, number of `personComponent` objects with role "Victim", etc.). This represents the SentinelAI-enhanced approach.

### Methodology

1.  **Data Collection**: Gather a corpus of incident reports with known priority levels.
2.  **Data Processing**:
    *   For the EIDOJSON dataset, run all text through the EIDO Agent.
    *   Create a feature vector for each incident from the resulting JSON.
3.  **Model Training**:
    *   Train a classifier (e.g., Gradient Boosting, simple Neural Network) on the Raw Text Dataset, likely using TF-IDF or word embeddings as features.
    *   Train the same classifier architecture on the EIDOJSON Dataset using the engineered features.
4.  **Evaluation**: Compare the models on a held-out test set using metrics like accuracy, F1-score, and confusion matrices.

### Expected Outcome

We expect the model trained on EIDOJSON features to outperform the raw text model, demonstrating that the structured, annotated data created by SentinelAI provides a richer, less noisy signal for machine learning tasks.
```

```python
# sentinelai/eido_estimate/train_model.py
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import classification_report
from sklearn.preprocessing import OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
import json

def load_data(filepath):
    """
    Loads the dataset. Assumes a JSONL file where each line is a JSON object
    containing 'raw_text' and 'eido_json' and a 'priority_label'.
    """
    # This is a placeholder. You'll need to adapt this to your actual data source.
    # For example, you might query the PostgreSQL database.
    # records = ... query from db ...
    # return pd.DataFrame(records)
    print("Placeholder for data loading.")
    return pd.DataFrame()

def feature_engineer_from_eido(df):
    """
    Extracts features from the 'eido_json' column.
    """
    features = []
    for index, row in df.iterrows():
        eido = row['eido_json']
        if not isinstance(eido, dict):
            eido = json.loads(eido)

        # Example features - expand this list based on what's useful
        num_victims = sum(1 for p in eido.get('personComponent', []) if "Victim" in p.get('personIncidentRoleRegistryText', []))
        num_suspects = sum(1 for p in eido.get('personComponent', []) if "Suspect" in p.get('personIncidentRoleRegistryText', []))
        incident_type = eido.get('incidentComponent', {}).get('incidentTypeCommonRegistryText', 'Unknown')
        
        features.append({
            'num_victims': num_victims,
            'num_suspects': num_suspects,
            'incident_type': incident_type,
        })
    
    return df.join(pd.DataFrame(features))


def train_baseline_model(df):
    """
    Trains a model using only raw text.
    """
    print("\n--- Training Baseline Model (Raw Text) ---")
    X = df['raw_text']
    y = df['priority_label']

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

    pipeline = Pipeline([
        ('tfidf', TfidfVectorizer(stop_words='english', max_features=5000)),
        ('clf', GradientBoostingClassifier(random_state=42))
    ])

    pipeline.fit(X_train, y_train)

    print("Baseline Model Performance:")
    y_pred = pipeline.predict(X_test)
    print(classification_report(y_test, y_pred))


def train_eido_model(df):
    """
    Trains a model using features extracted from EIDOJSON.
    """
    print("\n--- Training EIDO-Enhanced Model (Structured Features) ---")
    df_featured = feature_engineer_from_eido(df)

    # Define feature columns and the target
    feature_cols = ['num_victims', 'num_suspects', 'incident_type']
    X = df_featured[feature_cols]
    y = df_featured['priority_label']

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    
    # Preprocessing for categorical features
    categorical_features = ['incident_type']
    preprocessor = ColumnTransformer(
        transformers=[
            ('cat', OneHotEncoder(handle_unknown='ignore'), categorical_features)],
        remainder='passthrough'
    )

    pipeline = Pipeline([
        ('preprocessor', preprocessor),
        ('clf', GradientBoostingClassifier(random_state=42))
    ])

    pipeline.fit(X_train, y_train)

    print("EIDO-Enhanced Model Performance:")
    y_pred = pipeline.predict(X_test)
    print(classification_report(y_test, y_pred))


if __name__ == '__main__':
    # You would replace this with your actual data loading mechanism
    # df = load_data('path/to/your/data.jsonl')
    
    # For demonstration, we'll create a dummy DataFrame
    dummy_data = {
        'raw_text': [
            'Man down at the library, possible heart attack.',
            'Reports of a shooting near Price Center, one victim seen.',
            'Break-in at the student dorms, suspect fled on foot.',
            'Car fire on I-5 near campus exit.'
        ],
        'eido_json': [
            '{"personComponent": [{"personIncidentRoleRegistryText": ["Victim"]}], "incidentComponent": {"incidentTypeCommonRegistryText": "Medical"}}',
            '{"personComponent": [{"personIncidentRoleRegistryText": ["Victim"]}, {"personIncidentRoleRegistryText": ["Suspect"]}], "incidentComponent": {"incidentTypeCommonRegistryText": "Crime-Violent"}}',
            '{"personComponent": [{"personIncidentRoleRegistryText": ["Suspect"]}], "incidentComponent": {"incidentTypeCommonRegistryText": "Crime-Property"}}',
            '{"vehicleComponent": [{}], "incidentComponent": {"incidentTypeCommonRegistryText": "Fire"}}'
        ],
        'priority_label': [1, 1, 3, 2] # 1=High, 2=Medium, 3=Low
    }
    df = pd.DataFrame(dummy_data)


    if not df.empty:
        train_baseline_model(df.copy())
        train_eido_model(df.copy())
    else:
        print("Data loading failed or DataFrame is empty. Cannot run training.")

```

```markdown
# sentinelai/eido_estimate/data/.gitkeep
# This file is intentionally left blank.
# It exists to ensure the 'data' directory is tracked by Git.
# Place your raw and processed datasets here for the ML experiment.
```
