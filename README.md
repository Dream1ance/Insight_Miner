# Insight_Miner

Insight_Miner is a small utility for extracting insights from text data and producing shareable HTML reports. It provides a lightweight web interface and CLI helpers to run an NLP pipeline and export results using HTML templates.

## Features

- Run an NLP pipeline to extract insights from text (`nlp_pipeline.py`).
- Start a local web interface (`app.py`) for interacting with the pipeline and viewing results.
- Generate standalone HTML reports with `export_report.py` using templates in the `templates/` folder.

## Repository structure

- `app.py` — application entrypoint (starts the web UI).
- `export_report.py` — script to generate exportable HTML reports.
- `nlp_pipeline.py` — text preprocessing and NLP logic used by the app and exporter.
- `requirements_export.txt` — Python dependencies for running the project.
- `templates/` — HTML templates used to render pages and reports:
	- `index.html` — main UI page
	- `report_template.html` — report layout used by the exporter
	- `results.html` — example or generated results page

## Installation

1. Create and activate a Python virtual environment (recommended):

```bash
python3 -m venv .venv
source .venv/bin/activate
```

2. Install dependencies:

```bash
pip install -r requirements_export.txt
```

## Usage

- Start the application (web UI):

```bash
python app.py
```

Then open the URL shown in the application logs (typically `http://localhost:5000` or similar) to use the interface.

- Generate an HTML report from the command line:

```bash
python export_report.py
```

The exporter will use `templates/report_template.html` and produce an HTML output (e.g., `templates/results.html` or a file in the working directory). Check the script docstring or comments for arguments to control input/output paths.

## Development notes

- `nlp_pipeline.py` contains the core preprocessing and NLP steps. Reuse its functions for batch processing or tests.
- Templates are simple Jinja/HTML files; you can customize `report_template.html` to change the exported report styling.
- If you add new dependencies, update `requirements_export.txt` and re-run the install step.

## Troubleshooting

- If the app fails to start, verify your Python version (3.8+) and that the virtual environment's packages are installed.
- If exports are empty, confirm the input data given to the pipeline and check logs for errors.

## Contributing

Contributions are welcome. Create issues for bugs or feature requests and open pull requests for changes.

## License

This repository does not include a license file. Add a `LICENSE` if you wish to specify usage terms.
