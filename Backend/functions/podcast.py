from google.cloud import texttospeech 
from langchain.schema.document import Document
from langchain_community.retrievers import ArxivRetriever, PubMedRetriever, WikipediaRetriever
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode
from pydub import AudioSegment
import os
from typing import Dict, Any
from dataclasses import dataclass
import re
from dotenv import load_dotenv

load_dotenv()
os.environ["GOOGLE_API_KEY"] = os.getenv("GOOGLE_API_KEY")
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] =r"google.json"
# Prompts

OUTLINE_PROMPT = """You are an expert writer tasked with writing a high level outline of an engaging 5-minute podcast.
Write such an outline for the user provided topic. Give an outline of the podcast along with any
relevant notes or instructions for the sections."""
RESEARCH_PLAN_PROMPT = """You are a researcher tasked with providing information that can
be used when writing the following podcast. Generate one search query consisting of a few
keywords that will be used to gather any relevant information. Do not output any information
other than the query consisting of a few words.

These were the past queries, do not repeat keywords from past queries in your newly generated query:
---
{queries}"""
RESEARCH_TASK_PROMPT = """Use the available search tools and search queries to find information
relevant to the podcast. Try searching different sources to obtain different articles. Try using
different search tools than what was used previously so that you can obtain a broader range of
information.

These are the previous tool calls, so you can choose a different tool:
---
{tool_calls}
---
These are the previous search results, so you can aim for different sources and content:
---
{content}"""
WRITER_PROMPT = """
You are a writing assistant tasked with writing engaging 2-minute podcast scripts.

- Generate the best podcast script possible for the user's request and the initial outline.
- The script MUST strictly alternate lines between the two hosts, separating each host's line with a newline.
- Add an intro phrase and outro phrase to start and end the podcast, and use a fun, random name for the podcast show.
- Given a critique, respond with a revised version of your previous script.
- Include lively back-and-forth chatter, reflections, and expressions of amazement between the hosts.
- Cite at least THREE pieces of research throughout the script, choosing the most relevant research for each point.
- DO NOT include ANY of the following:
    - Speaker labels (e.g., "Host 1:", "Host 2:")
    - Sound effect descriptions (e.g., "[Sound of waves]")
    - Formatting instructions (e.g., "(Emphasis)", "[Music fades in]")
    - Any other non-dialogue text.
- Use this format for citations, including the month and year if available:
    "In [Month, Year], [Organization] found that..."
    "Research from [Organization] in [Month, Year] showed that..."
    "Back in [Month, Year], a study by [Organization] suggested that..."
---
Utilize all of the following search results and context as needed:
{content}
---
If this is a revision, the critique will be provided below:
{critique}"""
CRITIQUE_PROMPT = """You are a producer grading a podcast script.
Generate critique and recommendations for the user's submission.
Provide detailed recommendations, including requests for conciceness, depth, style, etc."""
RESEARCH_CRITIQUE_PROMPT = """You are a writing assistant tasked with providing information that can
be used when making any requested revisions (as outlined below).
Generate one search query consisting of a few keywords that will be used to gather any relevant
information. Do not output any information other than the query consisting of a few words.

---

These were the past queries, so you can vary the query that you generate:

{queries}
"""

@dataclass
class AgentState:
    task: str
    revision_number: int = 1
    max_revisions: int = 2
    search_count: int = 0
    max_searches: int = 2
    content: list = None
    queries: list = None
    tool_calls: list = None
    outline: str = None
    draft: str = None
    critique: str = None

    def __post_init__(self):
        if self.content is None:
            self.content = []
        if self.queries is None:
            self.queries = []
        if self.tool_calls is None:
            self.tool_calls = []

    def __getitem__(self, key):
        return getattr(self, key)

    def __setitem__(self, key, value):
        setattr(self, key, value)
        
    def get(self, key, default=None):
        try:
            return getattr(self, key)
        except AttributeError:
            return default

class PodcastGenerator:
    def __init__(self, google_api_key: str):
        self.memory = MemorySaver()
        self.model = ChatGoogleGenerativeAI(
            model="gemini-1.5-flash-latest",
            temperature=0,
            api_key=google_api_key
        )
        self.tts_client = texttospeech.TextToSpeechClient()
        self.setup_tools()
        self.setup_workflow()

    def setup_tools(self):
        @tool
        def search_arxiv(query: str) -> list[Document]:
            """
            Search for relevant academic publications on arXiv.
            
            Args:
                query (str): The search query string
                
            Returns:
                list[Document]: List of relevant documents from arXiv
            """
            retriever = ArxivRetriever(load_max_docs=2, get_full_documents=True)
            docs = retriever.invoke(query)
            return docs if docs else ["No results found on arXiv"]

        @tool
        def search_pubmed(query: str) -> list[Document]:
            """
            Search for medical and scientific publications on PubMed.
            
            Args:
                query (str): The search query string
                
            Returns:
                list[Document]: List of relevant documents from PubMed
            """
            retriever = PubMedRetriever()
            docs = retriever.invoke(query)
            return docs if docs else ["No results found on PubMed"]

        @tool
        def search_wikipedia(query: str) -> list[Document]:
            """
            Search for general information on Wikipedia.
            
            Args:
                query (str): The search query string
                
            Returns:
                list[Document]: List of relevant documents from Wikipedia
            """
            retriever = WikipediaRetriever()
            docs = retriever.invoke(query)
            return docs if docs else ["No results found on Wikipedia"]

        self.tools = [search_arxiv, search_pubmed, search_wikipedia]

    def podcast_outline_node(self, state: Dict[str, Any]):
        messages = [
            SystemMessage(content=OUTLINE_PROMPT),
            HumanMessage(content=state["task"]),
        ]
        response = self.model.invoke(messages)
        return {"outline": response.content}

    def research_plan_node(self, state: Dict[str, Any]):
        messages = [
            SystemMessage(content=RESEARCH_PLAN_PROMPT.format(queries=state["queries"])),
            HumanMessage(content=state["task"]),
        ]
        response = self.model.invoke(messages)
        # Always append the new query regardless of current list content.
        state["queries"].append(response.content)
        return {"queries": state["queries"]}

    def research_agent_node(self, state: Dict[str, Any]):
        tool_calls = state["tool_calls"]
        content = state["content"]
        # Ensure there is at least one query before indexing
        if not state["queries"]:
            raise ValueError("No query available for research_agent_node")
        query = state["queries"][-1]
        
        messages = [
            SystemMessage(content=RESEARCH_TASK_PROMPT.format(
                tool_calls=tool_calls,
                content=content
            )),
            HumanMessage(content=query),
        ]

        model_with_tools = self.model.bind_tools(self.tools)
        response_tool_calls = model_with_tools.invoke(messages)
        
        state["tool_calls"].append(response_tool_calls)
        
        tool_node = ToolNode(self.tools)
        response = tool_node.invoke({"messages": [response_tool_calls]})
        
        for message in response.get("messages", []):
            if isinstance(message, ToolMessage):
                content.insert(0, message.content)

        return {
            "content": content,
            "tool_calls": state["tool_calls"],
            "search_count": state["search_count"] + 1,
        }

    def generate_script_node(self, state: Dict[str, Any]):
        messages = [
            SystemMessage(content=WRITER_PROMPT.format(
                content=state["content"],
                critique=state.get("critique", "")
            )),
            HumanMessage(content=f"{state['task']}\n\nHere is my outline:\n\n{state['outline']}")
        ]
        response = self.model.invoke(messages)
        return {
            "draft": response.content,
            "search_count": 0,
            "revision_number": state.get("revision_number", 1) + 1,
        }

    def perform_critique_node(self, state: Dict[str, Any]):
        messages = [
            SystemMessage(content=CRITIQUE_PROMPT),
            HumanMessage(content=state["draft"]),
        ]
        response = self.model.invoke(messages)
        return {"critique": response.content}

    def research_critique_node(self, state: Dict[str, Any]):
        messages = [
            SystemMessage(content=RESEARCH_CRITIQUE_PROMPT.format(queries=state["queries"])),
            HumanMessage(content=state["critique"]),
        ]
        response = self.model.invoke(messages)
        state["queries"].append(response.content)
        return {"queries": state["queries"]}

    def setup_workflow(self):
        workflow = StateGraph(AgentState)
        
        # Add nodes
        workflow.add_node("podcast_outline", self.podcast_outline_node)
        workflow.add_node("research_plan", self.research_plan_node)
        workflow.add_node("research_agent", self.research_agent_node)
        workflow.add_node("generate_script", self.generate_script_node)
        workflow.add_node("perform_critique", self.perform_critique_node)
        workflow.add_node("research_critique", self.research_critique_node)
        
        # Set entry point
        workflow.set_entry_point("podcast_outline")
        
        # Add edges
        workflow.add_edge("podcast_outline", "research_plan")
        workflow.add_edge("research_plan", "research_agent")
        workflow.add_edge("perform_critique", "research_critique")
        workflow.add_edge("research_critique", "research_agent")
        
        # Add conditional edges
        workflow.add_conditional_edges(
            "research_agent",
            self.should_continue_tools,
            {"generate_script": "generate_script", "research_plan": "research_plan"}
        )
        
        workflow.add_conditional_edges(
            "generate_script",
            self.should_continue,
            {END: END, "perform_critique": "perform_critique"}
        )
        
        self.graph = workflow.compile(checkpointer=self.memory)

    @staticmethod
    def should_continue_tools(state: Dict[str, Any]):
        return "generate_script" if state["search_count"] > state["max_searches"] else "research_plan"

    @staticmethod
    def should_continue(state: Dict[str, Any]):
        return END if state["revision_number"] > state["max_revisions"] else "perform_critique"

    def generate_audio(self, script_lines):
        audio_files = []
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3
        )

        for count, line in enumerate(script_lines):
            synthesis_input = texttospeech.SynthesisInput(text=line)
            
            # Alternate between voices
            voice_name = "en-US-Journey-O" if count % 2 == 0 else "en-US-Journey-D"
            
            voice = texttospeech.VoiceSelectionParams(
                language_code="en-US",
                name=voice_name,
            )
            
            response = self.tts_client.synthesize_speech(
                input=synthesis_input,
                voice=voice,
                audio_config=audio_config
            )
            
            filename = f"part-{count}.mp3"
            audio_files.append(filename)
            with open(filename, "wb") as out:
                out.write(response.audio_content)

        # Combine audio files
        full_audio = AudioSegment.silent(duration=200)
        for file in audio_files:
            sound = AudioSegment.from_mp3(file)
            silence = AudioSegment.silent(duration=200)
            full_audio += sound + silence
            os.remove(file)

        return full_audio

    def generate_podcast(self, topic: str, output_filename: str = "podcast.mp3"):
        """
        Generate a podcast from a given topic.
        
        Args:
            topic (str): The topic for the podcast
            output_filename (str): The filename for the output audio file
            
        Returns:
            str: Path to the generated audio file
        """
        initial_state = {
            "task": topic,
            "revision_number": 1,
            "max_revisions": 2,
            "search_count": 0,
            "max_searches": 3,
            "content": [],
            "queries": [],
            "tool_calls": [],
        }
        
        thread = {"configurable": {"thread_id": "1"}}
        
        # Run the workflow
        final_state = None
        for state in self.graph.stream(initial_state, thread):
            final_state = state
        
        # Get the final script
        script = final_state["generate_script"]["draft"]
        script_lines = [line.strip() for line in script.splitlines() if line.strip()]
        
        # Generate audio
        audio = self.generate_audio(script_lines)
        audio.export(output_filename, format="mp3")
        
        return output_filename
