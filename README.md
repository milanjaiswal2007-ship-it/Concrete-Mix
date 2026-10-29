# ConcreteMix AI — IS 10262:2019 Concrete Mix Design Platform

An AI-assisted concrete mix design and review platform built to support concrete mix design using Indian Standards, particularly **IS 10262:2019** and **IS 456:2000**.

ConcreteMix AI aims to make concrete mix design more accessible by combining engineering calculations, standards-based checks, knowledge retrieval, and recommendations in a single web application.

## Key Features

- **Natural-language problem interpretation:** Interpret concrete construction requirements described in ordinary language.
- **Concrete mix design assistance:** Support the concrete mix design workflow using relevant engineering inputs.
- **Indian Standards-based checks:** Help evaluate design requirements against applicable provisions of IS 10262:2019 and IS 456:2000.
- **Material and mix recommendations:** Assist with selecting appropriate materials and mix parameters based on the specified requirements.
- **Knowledge retrieval:** Use available concrete mix design examples and reference data to support relevant recommendations.
- **Mix design review:** Help identify potential inconsistencies, missing inputs, and compliance concerns.
- **Data-driven approach:** Organize concrete mix design examples and supporting datasets for retrieval and analysis.

## Intended Use

The platform is intended for students, civil engineering professionals, researchers, and users learning about concrete mix design.

It aims to support workflows involving:

- Conventional concrete mix design
- High-strength concrete requirements
- Workability and material selection
- Exposure-condition considerations
- Preliminary mix design review
- Standards-based engineering checks

The actual design must be evaluated against the project requirements, applicable standards, material test results, and trial mix results.

## Standards and References

The platform is designed around the following Indian Standards:

- **IS 10262:2019** — Concrete Mix Proportioning: Guidelines
- **IS 456:2000** — Plain and Reinforced Concrete: Code of Practice

Always consult the applicable official standards and amendments for authoritative requirements.

## Technology and Project Structure

The repository contains the application code, supporting data, and resources used by the platform.

Main directories and resources include:

- `app/` — Application modules and core functionality
- `data/` — Concrete mix design datasets and supporting data
- `data/tfidf_index/` — Text retrieval index resources
- `data/examples/` — Example concrete mix design records
- `tests/` — Test files, where available
- `scripts/` — Supporting scripts, where available
- `requirements.txt` — Python dependencies, if present

The exact modules and available functionality may evolve as the project develops.

## Running the Project Locally

1. Install a compatible version of Python.
2. Clone this repository.
3. Open a terminal in the project directory.
4. Install the dependencies listed in `requirements.txt`.
5. Follow the application's entry-point instructions and configuration requirements.

Example:

```bash
git clone https://github.com/milanjaiswal2007-ship-it/Concrete-Mix.git
cd Concrete-Mix
pip install -r requirements.txt
```

The exact command to start the application depends on the entry point configured in the project.

## Engineering Disclaimer

ConcreteMix AI is an engineering assistance tool, not a replacement for professional engineering judgment or mandatory compliance checks.

Its outputs and recommendations must be independently verified against the applicable standards, approved project specifications, material properties, laboratory testing, and trial mix results before construction use.

## Project Status

This project is under development. Features, datasets, calculations, and recommendations may be refined as validation and testing progress.

## Author

**Milan Jaiswal**

Civil Engineering | Concrete Technology | AI-Assisted Engineering
