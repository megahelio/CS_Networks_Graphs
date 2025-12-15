# Networks_CS
## Installation

1.  **Create a virtual environment (recommended):**
    ```bash
    python -m venv .venv
    # Windows
    .venv\Scripts\activate
    # Linux/Mac
    source .venv/bin/activate
    ```

2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

## Usage

The main analysis and data processing are located in the `jupyter/` directory.

1.  **Data Download**: Run `jupyter/download data bluesky.ipynb`

2.  **Analysis**: Run `jupyter/resume_of_datset.ipynb`



## FAQ

### Why some keywords exceed 1000 posts?

Some keywords exceed 1000 posts because the limit applies to the download phase per keyword. In the analysis notebook, we count how many times each keyword appears across the entire collected dataset.

Example:

You download 1000 posts for "climate".
You download 1000 posts for "energy".
If 500 of the "energy" posts also contain the word "climate", the total count for "climate" becomes 1000 (original) + 500 (from "energy" posts) = 1500.
This is expected behavior.