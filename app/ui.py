import html
import os

import httpx
import streamlit as st


API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")


def timestamp(milliseconds: int) -> str:
    total_seconds = milliseconds // 1000
    return f"{total_seconds // 60:02d}:{total_seconds % 60:02d}"


def render_result(result: dict) -> None:
    sources = " · ".join(result["match_sources"])
    st.markdown(
        f"### {result['rank']}. {html.escape(result['title'])}\n"
        f"**{html.escape(result['speaker'])} · {timestamp(result['start_ms'])}–{timestamp(result['end_ms'])}**  \\n"
        f"`{sources}`{' `literal match`' if result['literal_match'] else ''}"
    )
    st.write(result["text"])
    with st.expander("Conversation context"):
        if result["context_before"]:
            st.caption(f"Previous: {result['context_before']}")
        if result["context_after"]:
            st.caption(f"Next: {result['context_after']}")


st.set_page_config(page_title="Audio Search", page_icon="🎙️", layout="wide")
st.title("🎙️ aud-look")
st.caption("Keyword + semantic retrieval across six diarized podcast clips")

with st.sidebar:
    strategy = st.selectbox("Retrieval strategy", ["hybrid", "hybrid_alt", "lexical", "semantic", "rrf"])
    k = st.slider("Results", min_value=1, max_value=10, value=5)
    try:
        episodes = httpx.get(f"{API_BASE_URL}/api/v1/episodes", timeout=3).json()
        st.caption(f"Indexed episodes: {len(episodes)}")
    except Exception:
        st.warning("API is not ready yet. Run migrations and ingestion first.")

query = st.text_input("Search what was said", placeholder="e.g. money as freedom, Basecamp VC, or rockets")
if query:
    try:
        response = httpx.get(
            f"{API_BASE_URL}/api/v1/search",
            params={"q": query, "k": k, "strategy": strategy},
            timeout=60,
        )
        response.raise_for_status()
        payload = response.json()
        st.caption(f"{len(payload['results'])} results in {payload['elapsed_ms']:.0f} ms")
        if not payload["results"]:
            st.info("No results found. Try fewer terms or a broader concept.")
        for result in payload["results"]:
            render_result(result)
    except httpx.HTTPStatusError as error:
        st.error(error.response.json().get("detail", "Search failed"))
    except Exception as error:
        st.error(f"Could not reach the search API: {error}")
