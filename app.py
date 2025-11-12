import streamlit as st
import os
import json
import re 
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate 
from streamlit_mermaid import st_mermaid
from markdown_it import MarkdownIt # --- NEW: For HTML export ---

# Load environment variables from .env file
load_dotenv()

# --- Page Configuration ---
st.set_page_config(
    page_title="Python Code Analyzer 🐍",
    page_icon="🤖",
    layout="wide"
)

# --- System Prompt ---
# I've added a new rule under "Output Formatting" to make the diagrams more stable
SYSTEM_PROMPT = """
Act as a senior software architect and expert developer. Your goal is to deeply understand the entire codebase provided, as if you must maintain, refactor, or extend it confidently. Become an expert on this project.

**Note:** The user has provided a single file. Your analysis will be limited to this file, but apply the following principles to it. When you mention "codebase" or "project," refer to the contents of this single file.

Task Breakdown
1. Indexing, Structure, and Hierarchy

* Recursively read all files and folders. (In this case, just analyze the provided file). For this file, summarize:
* Purpose and key responsibilities
* Main classes, functions, and their interactions
* Any special items (config, entrypoints, pipelines, scripts)

2. Entry Points and Termination Paths

* Identify all code entry points (main functions, HTTP endpoints, CLI commands, etc.)
* For each, trace all major execution flows, both normal and exceptional (successful return, error, or exit)
* Explicitly call out "start" (how code launches/receives) and "end" (shutdown, success, error reply, exit) for each flow

3. Multi-Lens Deep Analysis (PRSM)
For each layer or major component/module, analyze from multiple perspectives:

* **Architecture Lens:** Components/modules, their boundaries, and connections (including imports, service calls, data sharing, cross-cutting concerns)
* **Data Flow Lens:** How information and data objects move through the system (inputs, main processing, outputs, interactions, state management, data transformations)
* **Security Lens:** Points with authentication, authorization, validation, sanitization, sensitive data flows, and major trust boundaries
* **Business Logic Lens:** Core domain logic, main workflows, high-value actions (e.g. {{"order processing,"}} {{"workflow run"}}), and where logic is concentrated

4. Call Graphs and Cross-File Relationships

* Map out call graphs: which functions/methods/classes call or depend on each other.
* Explicitly list highly coupled areas, utility/helper layers, and dependency injection points.

5. Visualizations and Step-by-Step Codes

* Create a component/architecture diagram (using Mermaid.js), showing modules/services/controllers and their dependencies or interactions.
* For at least one important workflow (e.g. login, task run), create a sequence diagram with all actors/components, messages, branches (alt/opt), and data transfers.
* Include at least one data flow chart or block diagram for how key data structures are created, processed, and persisted.

6. Explanations and Quick Reference

* Write high-level AND detailed summaries for each perspective.
* Produce a “Navigating This Codebase” section: best entry points for new devs, most central files, things to be careful about (tricky logic, fragile integrations, security hotspots)

7. Output Formatting

* Use markdown headers for each section (as above).
* For diagrams, include the code block (e.g., ```mermaid ... ```).
* All lists should be bulleted and concise.
* **--- NEW RULE ---** * **Ensure all Mermaid syntax is 100% valid.** For sequence diagrams, use `sequenceDiagram`. For flowcharts or component diagrams, use `graph LR` (Left-to-Right). **Avoid using `graph TD` (Top-Down)** as it can cause rendering errors.
"""

# --- NEW: Function to generate HTML report ---
def generate_html_report(raw_markdown_content, file_name):
    """
    Converts the raw markdown+mermaid report from the LLM into a standalone
    HTML file that can be downloaded.
    """
    md_parser = MarkdownIt()
    mermaid_pattern = re.compile(r"```mermaid\n(.*?)\n```", re.DOTALL)
    
    html_parts = []
    
    # Add HTML header, styles, and Mermaid.js script
    html_parts.append(f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Code Analysis for {file_name}</title>
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; line-height: 1.6; padding: 20px; max-width: 1000px; margin: auto; background-color: #f9f9f9; }}
            h1, h2, h3, h4 {{ color: #333; border-bottom: 1px solid #ddd; padding-bottom: 5px; }}
            pre {{ background: #2d2d2d; color: #f1f1f1; padding: 15px; border-radius: 5px; overflow-x: auto; }}
            code {{ font-family: "Courier New", Courier, monospace; }}
            .mermaid {{ text-align: center; margin-bottom: 20px; padding: 10px; border: 1px solid #ddd; border-radius: 5px; background-color: #fff; }}
            ul, ol {{ padding-left: 20px; }}
            blockquote {{ border-left: 4px solid #ddd; padding-left: 10px; color: #555; margin-left: 0; }}
        </style>
    </head>
    <body>
        <h1>Code Analysis for {file_name}</h1>
    """)
    
    # Split the content by mermaid blocks
    parts = re.split(mermaid_pattern, raw_markdown_content)
    
    for i, part in enumerate(parts):
        if i % 2 == 0:
            # This is a regular text part (Markdown)
            # Convert Markdown to HTML
            html_parts.append(md_parser.render(part))
        else:
            # This is a mermaid code part
            # Add the mermaid div for rendering
            html_parts.append(f'<div class="mermaid">\n{part.strip()}\n</div>')
    
    # Add the Mermaid.js script at the end
    html_parts.append("""
        <script type="module">
            import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
            mermaid.initialize({ startOnLoad: true });
        </script>
    </body>
    </html>
    """)
    
    return "".join(html_parts)

# --- Main Application Logic ---

st.title("🤖 Advanced Python Code Analyzer")
st.markdown("Upload your Python file for a deep architectural analysis by Gemini.")

if "GOOGLE_API_KEY" not in os.environ:
    st.error("🚨 GOOGLE_API_KEY not found. Please add it to your .env file.")
else:
    uploaded_file = st.file_uploader("Upload your Python file (.py)", type="py")

    if uploaded_file is not None:
        try:
            code_content = uploaded_file.read().decode("utf-8")
            
            with st.expander("Show Uploaded Code", expanded=False):
                st.code(code_content, language="python")

            llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.1)
            
            prompt = ChatPromptTemplate.from_messages([
                ("system", SYSTEM_PROMPT),
                ("human", "Here is the Python code I need you to analyze:\n\n```python\n{python_code}\n```")
            ])
            
            chain = prompt | llm

            with st.spinner("🤖 AI is performing a deep analysis of your code... This might take a moment."):
                response = chain.invoke({"python_code": code_content})
                raw_output = response.content

            st.subheader("✅ Analysis Complete")
            
            # --- NEW: Add Download Button ---
            try:
                html_content = generate_html_report(raw_output, uploaded_file.name)
                st.download_button(
                    label="📥 Download Full HTML Report",
                    data=html_content,
                    file_name=f"{os.path.splitext(uploaded_file.name)[0]}_analysis.html",
                    mime="text/html"
                )
            except Exception as e:
                st.error(f"Could not generate HTML report: {e}")
            
            st.divider() # --- NEW: Add a visual separator ---

            # --- Rendering Logic (same as before) ---
            mermaid_pattern = re.compile(r"```mermaid\n(.*?)\n```", re.DOTALL)
            parts = re.split(mermaid_pattern, raw_output)
            
            for i, part in enumerate(parts):
                if i % 2 == 0:
                    st.markdown(part)
                else:
                    try:
                        with st.container(border=True):
                            st_mermaid(part.strip(), height="500px")
                        with st.expander("Show Mermaid Code"):
                            st.code(part.strip(), language="mermaid")
                    except Exception as e:
                        st.error(f"Failed to render a Mermaid diagram. Syntax may be invalid.\nError: {e}")
                        st.code(part.strip(), language="mermaid")

        except Exception as e:
            st.error(f"An unexpected error occurred: {e}")
            if 'response' in locals():
                st.error("Raw LLM output:")
                st.text(response.content)