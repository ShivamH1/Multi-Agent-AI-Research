import sys
from pathlib import Path
import os
import json
import re

# Add the project root to sys.path so agents and tools can be imported successfully
sys.path.append(str(Path(__file__).resolve().parent))

import streamlit as st
from dotenv import load_dotenv

# Load environmental variables
load_dotenv()

# Import pipeline components
try:
    from agents.agents import (
        build_reader_agent,
        build_search_agent,
        writer_chain,
        critic_chain,
    )
    IMPORTS_OK = True
    IMPORT_ERROR_MSG = ""
except Exception as e:
    IMPORTS_OK = False
    IMPORT_ERROR_MSG = str(e)

# ----------------------------------------------------
# Custom Styling & CSS (Outfit font, Premium Dark slate card layouts)
# ----------------------------------------------------
st.set_page_config(
    page_title="AI Research Agent - Workspace",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
<style>
    /* Global styles and typography */
    html, body, [class*="css"], .stApp {
        font-family: 'Outfit', sans-serif !important;
    }
    
    /* Sleek gradient background for main headers */
    .title-container {
        padding: 2rem 0;
        margin-bottom: 2rem;
        background: linear-gradient(135deg, rgba(30, 41, 59, 0.4) 0%, rgba(15, 23, 42, 0.4) 100%);
        border-bottom: 1px solid #1e293b;
        border-radius: 12px;
        text-align: center;
    }
    
    .title-gradient {
        background: linear-gradient(90deg, #818cf8 0%, #a78bfa 50%, #f472b6 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800;
        font-size: 2.8rem;
        margin-bottom: 0.2rem;
        letter-spacing: -0.05em;
    }
    
    .subtitle {
        color: #94a3b8;
        font-size: 1.1rem;
        font-weight: 400;
        max-width: 600px;
        margin: 0 auto;
    }
    
    /* Card layouts */
    .glass-card {
        background-color: #1e293b;
        border: 1px solid #334155;
        border-radius: 16px;
        padding: 1.5rem;
        margin-bottom: 1.5rem;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.3), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
    }
    
    .score-badge {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 70px;
        height: 70px;
        border-radius: 50%;
        font-size: 1.8rem;
        font-weight: 800;
        color: white;
        margin-right: 1.5rem;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.2);
    }
    
    .badge-high {
        background: linear-gradient(135deg, #10b981 0%, #059669 100%);
        border: 2px solid #34d399;
    }
    
    .badge-med {
        background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
        border: 2px solid #fbbf24;
    }
    
    .badge-low {
        background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
        border: 2px solid #f87171;
    }
    
    /* Sidebar styling */
    section[data-testid="stSidebar"] {
        background-color: #0b0f19;
        border-right: 1px solid #1e293b;
    }
    
    /* Status indicators */
    .indicator-active {
        display: inline-block;
        width: 10px;
        height: 10px;
        border-radius: 50%;
        background-color: #10b981;
        box-shadow: 0 0 8px #10b981;
        margin-right: 6px;
    }
    
    .indicator-inactive {
        display: inline-block;
        width: 10px;
        height: 10px;
        border-radius: 50%;
        background-color: #ef4444;
        box-shadow: 0 0 8px #ef4444;
        margin-right: 6px;
    }
</style>
""", unsafe_allow_html=True)


# ----------------------------------------------------
# Helper Functions
# ----------------------------------------------------
def parse_feedback(feedback_str: str) -> dict:
    """Parses structural text feedback from critic chain into dictionary."""
    parsed = {
        "score_val": 0,
        "score_str": "N/A",
        "strengths": [],
        "improvements": [],
        "verdict": ""
    }
    try:
        lines = [line.strip() for line in feedback_str.split("\n") if line.strip()]
        current_section = None
        
        for line in lines:
            # Check for score (e.g. Score: 8/10 or Score: 8)
            score_match = re.search(r'(?:score|rating):\s*(\d+(?:\.?\d+)?)\s*(?:/\s*\d+)?', line, re.IGNORECASE)
            if score_match:
                try:
                    val = float(score_match.group(1))
                    parsed["score_val"] = val
                    parsed["score_str"] = f"{int(val) if val.is_integer() else val}/10"
                except Exception:
                    pass
                continue
                
            if line.lower().startswith("strengths:"):
                current_section = "strengths"
                continue
            elif line.lower().startswith("areas to improve:") or line.lower().startswith("areas to improve"):
                current_section = "improvements"
                continue
            elif line.lower().startswith("one line verdict:") or line.lower().startswith("one-line verdict:") or line.lower().startswith("verdict:"):
                current_section = "verdict"
                # Extract starting right after colon
                colon_parts = line.split(":", 1)
                if len(colon_parts) > 1:
                    parsed["verdict"] = colon_parts[1].strip()
                continue
                
            if current_section == "verdict":
                parsed["verdict"] += " " + line
            elif line.startswith("-") or line.startswith("*"):
                cleaned = line.lstrip("-* ").strip()
                if cleaned:
                    if current_section == "strengths":
                        parsed["strengths"].append(cleaned)
                    elif current_section == "improvements":
                        parsed["improvements"].append(cleaned)
    except Exception as e:
        # Fallback if parsing completely fails
        parsed["verdict"] = feedback_str
        
    return parsed


# ----------------------------------------------------
# Sidebar - Environment & Key Settings
# ----------------------------------------------------
with st.sidebar:
    st.markdown("### 🔬 System Configuration")
    st.markdown("---")
    
    # Check Environment Variables
    mistral_key = os.getenv("MISTRAL_API_KEY")
    tavily_key = os.getenv("TAVILY_API_KEY")
    
    st.write("**API Key Verification Status:**")
    
    if mistral_key:
        st.markdown('<div style="margin-bottom: 8px;"><span class="indicator-active"></span> **Mistral AI Key**: Loaded</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div style="margin-bottom: 8px;"><span class="indicator-inactive"></span> **Mistral AI Key**: Missing</div>', unsafe_allow_html=True)
        
    if tavily_key:
        st.markdown('<div style="margin-bottom: 8px;"><span class="indicator-active"></span> **Tavily Search Key**: Loaded</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div style="margin-bottom: 8px;"><span class="indicator-inactive"></span> **Tavily Search Key**: Missing</div>', unsafe_allow_html=True)
        
    st.markdown("---")
    
    # System info
    st.markdown("#### About the Agents:")
    st.info("""
    - **Search Agent**: Connects to the Web using Tavily to identify latest resources.
    - **Reader Agent**: Scrapes and parses the most relevant web resource using BeautifulSoup.
    - **Writer Agent**: Consolidates research findings into structured markdown.
    - **Critic Agent**: Reviews report quality and provides a scoresheet.
    """)
    
    st.markdown("<br><br><div style='text-align: center; color: #64748b; font-size: 0.8rem;'>🔬 Multi-Agent Research System v1.0</div>", unsafe_allow_html=True)


# ----------------------------------------------------
# Main Layout
# ----------------------------------------------------
st.markdown("""
<div class="title-container">
    <div class="title-gradient">Deep Research Agent Workspace</div>
    <div class="subtitle">An advanced multi-agent research pipeline that conducts search, scrapes data, drafts insights, and evaluates final reports.</div>
</div>
""", unsafe_allow_html=True)

if not IMPORTS_OK:
    st.error(f"❌ **Failed to load Pipeline Agents.** Error: {IMPORT_ERROR_MSG}")
    st.info("Ensure you are running the app in the project root directory and your local virtual environment is active.")
    st.stop()

# Initialize session states for storing results across runs
if "research_results" not in st.session_state:
    st.session_state["research_results"] = None
if "is_running" not in st.session_state:
    st.session_state["is_running"] = False

# Search query form
with st.container():
    col1, col2 = st.columns([4, 1])
    with col1:
        topic_input = st.text_input(
            "Research Topic",
            placeholder="e.g. Latest progress in solid-state battery technology...",
            label_visibility="collapsed"
        )
    with col2:
        run_btn = st.button("🚀 Start Research", use_container_width=True)

# Main action triggers
if run_btn:
    if not topic_input.strip():
        st.warning("⚠️ Please enter a research topic to begin.")
    elif not mistral_key or not tavily_key:
        st.error("❌ Cannot run research. Missing API Keys. Please make sure MISTRAL_API_KEY and TAVILY_API_KEY are configured in your .env file.")
    else:
        st.session_state["is_running"] = True
        st.session_state["research_results"] = None

# Running state handler
if st.session_state["is_running"]:
    # Display step-by-step progress using expander lists
    st.markdown("### ⚙️ Executing Agent Pipelines")
    
    # Placeholder for status indicators
    progress_bar = st.progress(0)
    
    try:
        # Step 1: Web Search
        with st.status("🔍 Phase 1: Search Agent is finding reliable information...", expanded=True) as status_search:
            st.write("Configuring agent tools and querying Tavily search index...")
            search_agent = build_search_agent()
            search_result = search_agent.invoke(
                {
                    "messages": [
                        (
                            "user",
                            f"Find recent, reliable and detailed information about: {topic_input}",
                        )
                    ]
                }
            )
            raw_search_results = search_result["messages"][-1].content
            st.success("Tavily search query returned latest resources successfully.")
            status_search.update(label="✅ Phase 1 Complete: Web search resolved.", state="complete", expanded=False)
        progress_bar.progress(25)
        
        # Step 2: Reader Agent Scrapes Page
        with st.status("📖 Phase 2: Reader Agent is parsing full webpage content...", expanded=True) as status_reader:
            st.write("Extracting URL from search results & executing scraper...")
            reader_agent = build_reader_agent()
            reader_result = reader_agent.invoke(
                {
                    "messages": [
                        (
                            "user",
                            f"Based on the following search results about '{topic_input}', "
                            f"pick the most relevant URL and scrape it for deeper content.\n\n"
                            f"Search Results:\n{raw_search_results[:800]}",
                        )
                    ]
                }
            )
            raw_scraped_content = reader_result["messages"][-1].content
            st.success("Scraper executed successfully using BeautifulSoup4.")
            status_reader.update(label="✅ Phase 2 Complete: Page scraping finished.", state="complete", expanded=False)
        progress_bar.progress(50)
        
        # Step 3: Writer drafts the report
        with st.status("✍️ Phase 3: Writer Agent is synthesising content & drafting...", expanded=True) as status_writer:
            st.write("Combining search logs and scraped documents...")
            research_combined = (
                f"SEARCH RESULTS : \n {raw_search_results} \n\n"
                f"DETAILED SCRAPED CONTENT : \n {raw_scraped_content}"
            )
            report_content = writer_chain.invoke(
                {"topic": topic_input, "research": research_combined}
            )
            st.success("Research report drafted in Markdown.")
            status_writer.update(label="✅ Phase 3 Complete: Markdown report drafted.", state="complete", expanded=False)
        progress_bar.progress(75)
        
        # Step 4: Critic Reviews Report
        with st.status("🧐 Phase 4: Critic Agent is reviewing the report...", expanded=True) as status_critic:
            st.write("Submitting draft to LLM Critique evaluation chain...")
            critic_feedback = critic_chain.invoke({"report": report_content})
            st.success("Critique scorecard and review complete.")
            status_critic.update(label="✅ Phase 4 Complete: Report finalized and reviewed.", state="complete", expanded=False)
        progress_bar.progress(100)
        
        # Save results to session state
        st.session_state["research_results"] = {
            "topic": topic_input,
            "search_results": raw_search_results,
            "scraped_content": raw_scraped_content,
            "report": report_content,
            "feedback": critic_feedback
        }
        st.session_state["is_running"] = False
        st.rerun()
        
    except Exception as pipeline_err:
        st.error(f"❌ Pipeline crashed during execution: {str(pipeline_err)}")
        st.session_state["is_running"] = False

# Display Results
if st.session_state["research_results"]:
    res = st.session_state["research_results"]
    
    st.markdown("### 📊 Research Output & Findings")
    
    # Tabs layout
    tab_report, tab_critic, tab_raw = st.tabs([
        "📝 Final Research Report", 
        "⚖️ Agent Critique & Score", 
        "🔬 Raw Research Log"
    ])
    
    # ---------------- TAB 1: REPORT ----------------
    with tab_report:
        st.markdown(f"## {res['topic']}")
        st.markdown(res["report"])
        
        st.markdown("---")
        # Export option
        st.download_button(
            label="📥 Download Report (.md)",
            data=res["report"],
            file_name=f"research_{res['topic'].replace(' ', '_').lower()}.md",
            mime="text/markdown",
            use_container_width=True
        )
        
    # ---------------- TAB 2: CRITIC ----------------
    with tab_critic:
        feedback_info = parse_feedback(res["feedback"])
        
        # Score banner card
        score_val = feedback_info["score_val"]
        badge_class = "badge-low"
        if score_val >= 8:
            badge_class = "badge-high"
        elif score_val >= 5:
            badge_class = "badge-med"
            
        st.markdown(f"""
        <div class="glass-card" style="display: flex; align-items: center;">
            <div class="score-badge {badge_class}">{feedback_info['score_str']}</div>
            <div>
                <h3 style="margin: 0; color: #f8fafc;">Critic Evaluation Score</h3>
                <p style="margin: 0.2rem 0 0 0; color: #94a3b8; font-style: italic; font-size: 1.1rem;">"{feedback_info['verdict'] or 'Evaluation completed successfully.'}"</p>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Strengths and Improvements in Columns
        col_s, col_i = st.columns(2)
        with col_s:
            st.markdown("### ✅ Strengths")
            if feedback_info["strengths"]:
                for strength in feedback_info["strengths"]:
                    st.markdown(f"⭐ **{strength}**")
            else:
                st.write("No specific strengths listed or feedback format custom.")
                st.info(res["feedback"])
                
        with col_i:
            st.markdown("### ⚠️ Areas to Improve")
            if feedback_info["improvements"]:
                for improvement in feedback_info["improvements"]:
                    st.markdown(f"🔧 **{improvement}**")
            else:
                st.write("No specific improvements listed or feedback format custom.")
                
        st.markdown("---")
        st.markdown("#### Full Feedback Raw Output:")
        st.text(res["feedback"])

    # ---------------- TAB 3: RAW DATA ----------------
    with tab_raw:
        st.write("Below are the intermediate payloads fetched by each agent during the pipeline execution.")
        
        st.markdown("#### 1. Search Agent Outputs (Tavily Search Matches)")
        st.info(res["search_results"])
        
        st.markdown("#### 2. Reader Agent Outputs ( BeautifulSoup Scraped Content)")
        st.text_area(
            "Scraped Text (truncated to 5000 chars)", 
            value=res["scraped_content"], 
            height=300, 
            disabled=True
        )
        
        # Export all states to JSON
        json_data = json.dumps(res, indent=4)
        st.download_button(
            label="📥 Export Full Pipeline State (.json)",
            data=json_data,
            file_name=f"pipeline_state_{res['topic'].replace(' ', '_').lower()}.json",
            mime="application/json"
        )
else:
    # Initial page state (Show help info or prompts)
    st.markdown("""
    <div style="background-color: #1e293b; border-radius: 12px; padding: 2rem; border: 1px solid #334155; margin-top: 1rem; text-align: center;">
        <h3 style="margin-top: 0; color: #f8fafc;">Ready to research?</h3>
        <p style="color: #94a3b8; font-size: 1.1rem; margin-bottom: 1.5rem;">Enter a research topic in the input box above and click "Start Research" to launch the AI agent pipeline.</p>
        <div style="display: flex; gap: 10px; justify-content: center;">
            <span style="background-color: #334155; color: #f8fafc; padding: 4px 12px; border-radius: 9999px; font-size: 0.9rem;">Web Search</span>
            <span style="background-color: #334155; color: #f8fafc; padding: 4px 12px; border-radius: 9999px; font-size: 0.9rem;">BeautifulSoup Scraper</span>
            <span style="background-color: #334155; color: #f8fafc; padding: 4px 12px; border-radius: 9999px; font-size: 0.9rem;">Mistral AI Writer</span>
            <span style="background-color: #334155; color: #f8fafc; padding: 4px 12px; border-radius: 9999px; font-size: 0.9rem;">Critique Scorecard</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
