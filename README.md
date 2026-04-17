# A Knowledge-Graph–Driven Evaluation of Political Temporal Reasoning

This repository contains the code and resources to (i) construct a political Knowledge Graph (KG), (ii) generate Temporal Reasoning (TR) benchmarks from the KG and from TRAM, (iii) run TR experiments with language models, and (iv) analyze the results.

## Requirements
Python: `>=3.10,<3.15`

Poetry: `>=2.0.0,<3.0.0`

Install dependencies using Poetry:
```bash
poetry install
```

Download [rmlmapper](https://github.com/RMLio/rmlmapper-java) from the original source.

## Table of Contents
- [Knowledge Graph Construction](#knowledge-graph-construction)
  - [Data Acquisition](#1-data-acquisition)
  - [Knowledge Fusion](#2-knowledge-fusion)
  - [Knowledge Storage](#3-knowledge-storage)
  - [Statistics](#4-statistics)
  - [GraphDB Deployment](#graphdb-deployment)
- [Temporal Reasoning Benchmark Creation](#temporal-reasoning-benchmark-creation)
  - [TRAM Data Setup](#tram-data-setup)
  - [Benchmark Generation](#benchmark-generation)
- [Temporal Reasoning Experiments](#temporal-reasoning-experiments)
- [Results Analysis](#results-analysis)
- [Acknowledgements](#acknowledgements)

## Knowledge Graph Construction

The KG construction pipeline is implemented in the notebook `kgc.ipynb`. After building the KG, it is deployed in a GraphDB Docker container.

### 1. Data Acquisition

Political manifestos are downloaded from the Manifesto Project API.

1. Create a file named `secrets.env`.

2. Set the environment variable:
    
        MANIFESTO_API_KEY=your_api_key

3. Run the notebook. The manifestos for the configured actors and dates are downloaded automatically.


### 2. Knowledge Fusion

The raw data are: 
- Transformed and normalized. 
- Enriched with temporal context extracted from Wikidata. 
- Linked to external entities using their corresponding Wikidata identifiers.

### 3. Knowledge Storage

Declarative mappings (located in the `mappings/` directory) are applied to generate RDF triples from the processed datasets with the `rmlmapper`.

### 4. Statistics

The notebook also includes utilities to extract descriptive statistics from the deployed KG, allowing basic validation and inspection of its contents.


### GraphDB Deployment

A GraphDB Docker setup is provided in the `docker/` directory.

1.  Inside `docker/`, create a folder named `data/`.
2.  Copy into `data/`:
    -   The generated RDF triples.
    -   The required ontologies (recommended to download them from their original sources):
        -   [PODIO](https://w3id.org/podio/v2.0)
        -   [OWL-Time](https://www.w3.org/TR/owl-time/)
        -   [SKOS](https://www.w3.org/2004/02/skos/)
        -   [LKG](https://www.lynx-project.eu/doc/lkg/)
        -   [FOAF](http://xmlns.com/foaf/spec/)
        -   [ELI](https://op.europa.eu/web/eu-vocabularies/dataset/-/resource?uri=http://publications.europa.eu/resource/dataset/eli)
        -   [SIOC](http://rdfs.org/sioc/ns)
3.  Start GraphDB:
    ``` bash
    docker compose -f graphdb.yml up
    ```
4.  Inside GraphDB create a repository named **`politicaltr`** (this name is required for the following steps).
5.  Import all files from the `data/` directory using the *Import → Server files* tab in the GraphDB UI.
6.  Once the import is finished, run the **"4. Statistics"** section of `kgc.ipynb` to verify that the KG is correctly deployed.


## Temporal Reasoning Benchmark Creation

Two TR benchmarks are used: the political TR benchmark generated in this project and the public [TRAM benchmark](https://github.com/EternityYW/TRAM-Benchmark).

### TRAM Data Setup

Before running the notebook:

1.  Manually download the following TRAM datasets:
    -   `nli_mcq`
    -   `ordering`
    -   `storytelling`
    -   `typical_time`

2.  Unzip them into a common directory.

3.  Set the path to this directory in the notebook `TR.ipynb` using the
    variable:

        tram_raw_datapath

    (It is recommended to follow the directory structure defined in the notebook.)

### Benchmark Generation

1.  Make sure the GraphDB container is running.
2.  Execute the full notebook `TR.ipynb`.

The notebook produces two CSV files: one for the political TR benchmark and the other for the TRAM benchmark.

These CSVs are used as input for the experimental stage. The notebook can be extended to include additional tasks or configurations, as long as new CSVs are generated following the same format.

## Temporal Reasoning Experiments

Experiments are launched using the script:

``` bash
./experiments.sh
```

This script loads the models. Executes the experiments defined in the CSV files. Saves intermediate results in batches, allowing interrupted runs to be resumed. Removes checkpoints once execution is complete.

If you modify paths, task names, or configurations in `TR.ipynb`, you must update the script accordingly.

Each model produces a CSV file containing: 
- The prompts. 
- The model outputs. 
- The evaluation results.

## Results Analysis

Results are analyzed in the notebook `Results.ipynb`.

This notebook aggregates the outputs from all models. Generates summary tables and reproduces the figures used in the paper.

If new tasks or paths are added, the notebook may require minor adjustments.

## Acknowledgements
This work is supported by the Predoctoral Grant (PIPF-2022/COM-25947) of the Consejería de Educación, Ciencia y Universidades de la Comunidad de Madrid, Spain. The authors gratefully acknowledge the Universidad Politécnica de Madrid (www.upm.es) for providing computing resources on Magerit Supercomputer, as well as the computing resources provided through Grant IARAG CPP2023-010895 funded by MICIU/AEI/ 10.13039/501100011033 and by ERDF/EU.
