from flask import Flask, render_template, request, session, Response
import io
from nlp_pipeline import run_analysis, get_article_text
import pandas as pd
import re
from datetime import datetime
import warnings
from export_report import html_to_pdf

warnings.filterwarnings("ignore")

app = Flask(__name__)
# Set a secret key for session management
app.secret_key = 'your_super_secret_key_goes_here_12345'

# --- Helper Function ---
def is_url(string: str) -> bool:
    """Check if a string is a valid URL."""
    return re.match(r'https?://[^\s/$.?#].[^\s]*', string) is not None

# --- Routes ---

@app.route('/')
def index():
    """Renders the main search/input page."""
    session.pop('latest_report_html', None) 
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze():
    """
    Handles the analysis request.
    Saves the *rendered HTML* to the session for download.
    """
    query = request.form['query']
    urls_to_process = []
    
    if is_url(query):
        print(f"Input is a URL: {query}")
        urls_to_process = [query]
    else:
        # Search-as-query functionality removed to simplify and shrink the project.
        # Require users to paste a full article URL. Return no results for search queries.
        print(f"Search queries are not supported in this minimal build: {query}")
        urls_to_process = []

    if not urls_to_process:
        print("No URLs found to process.")
        return render_template('results.html', all_reports=[])

    all_reports_data = []
    for url in urls_to_process:
        print(f"--- Processing URL: {url} ---")
        try:
            # 1. Scrape text and heading
            scrape_data = get_article_text(url)
            text = scrape_data['text']
            
            # 2. Run analysis
            report_data = run_analysis(text)
            report_data['url'] = url
            
            # 3. Add heading to report
            report_data['heading'] = scrape_data['heading']
        
            # 4. Convert DataFrame to HTML table (for the web view)
            if not report_data['financial_facts'].empty:
                report_data['financial_facts_table'] = report_data['financial_facts'].to_html(
                    classes='financial-facts-table', 
                    index=False,
                    border=0
                )
            else:
                report_data['financial_facts_table'] = None

            all_reports_data.append(report_data)
        
        except Exception as e:
            print(f"Unhandled error processing {url}: {e}")
            error_report = {
                'url': url,
                'summary': f'A critical error occurred during analysis: {e}',
                'entities': {},
                'article_type': 'Analysis Failed',
                'financial_facts': pd.DataFrame(),
                'financial_facts_table': None,
                'heading': 'Analysis Failed'
            }
            all_reports_data.append(error_report)
        
        print(f"--- Finished processing {url} ---")

    # 1. Render the HTML content as a string
    html_content = render_template('results.html', all_reports=all_reports_data)
    
    # 2. Save this HTML string in the user's session
    session['latest_report_html'] = html_content
    
    # 3. Return the HTML to the browser
    return html_content


@app.route('/download_report')
def download_report():
    """
    Provides the last generated report as a downloadable PDF file.
    Converts HTML to PDF on-the-fly.
    """
    import os
    import tempfile
    
    # Get the HTML content we saved in the session
    html_content = session.get('latest_report_html', '<p>No report to download. Please analyze an article first.</p>')
    
    # Create temporary files for HTML and PDF
    with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as html_file:
        html_file.write(html_content)
        html_temp_path = html_file.name
    
    pdf_temp_path = html_temp_path.replace('.html', '.pdf')
    
    try:
        # Convert HTML to PDF
        html_to_pdf(html_temp_path, pdf_temp_path)
        
        # Read the PDF file
        with open(pdf_temp_path, 'rb') as pdf_file:
            pdf_data = pdf_file.read()
        
        # Return the PDF as a download
        return Response(
            pdf_data,
            mimetype="application/pdf",
            headers={
                "Content-disposition": "attachment; filename=Insight_Miner_Report.pdf"
            }
        )
    
    finally:
        # Clean up temporary files
        try:
            if os.path.exists(html_temp_path):
                os.remove(html_temp_path)
            if os.path.exists(pdf_temp_path):
                os.remove(pdf_temp_path)
        except Exception as e:
            print(f"Warning: Could not clean up temp files: {e}")

if __name__ == '__main__':
    print("Starting Flask app...")
    print("Models were loaded at startup.")
    print("NOTE: Spacy model 'en_core_web_lg' is required.")
    print("Run 'python -m spacy download en_core_web_lg' if you haven't.")
    app.run(debug=True, port=5000)