# Importing all the required classes :-

import re
from youtube_transcript_api import YouTubeTranscriptApi , TranscriptsDisabled
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.retrievers import BaseRetriever
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
import os
from dotenv import load_dotenv
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableParallel , RunnableLambda , RunnablePassthrough
from langchain_core.runnables import Runnable


# All vector databases for all videos will live inside a folder called vector_store
VECTOR_STORE_DIRECTORY = "vector_store"  # I need a base directory where vector stores will live.

os.makedirs ( VECTOR_STORE_DIRECTORY , exist_ok = True )  # This creates the directory of "vector_store".


#-----------------------------------------------------------
# PHASE 1 :- FETCHING THE TRANSCRIPTS OF THE YOUTUBE VIDEO |
#-----------------------------------------------------------

# 1 . First Function - VIDEO ID EXTRACTOR :-

def extract_video_id ( video_url : str ) -> str :  # The input of the video ( url ) is a "string" and output also a "string" ( id ).
    """
    Extracts the video ID from a YouTube URL.
                                                                                                                                                                               
    Supports:
    - https://www.youtube.com/watch?v=VIDEO_ID
    - https://youtu.be/VIDEO_ID

    Args:
        youtube_url (str): Full YouTube video URL

    Returns: 
        str: Extracted video ID
    """

    # Pattern for standard YouTube Video URLs

    youtube_regex = (                           # Note : YouTube Video IDs are always 11 Characters.

        r"(?:v=|\/)([0-9A-Za-z_-]{11}).*"  # The Regex Pattern to find in the given Input of Video URL.
    )

    match = re.search ( youtube_regex , video_url )

    if not match :
        raise ValueError ( "Invalid Youtube URL !" )

    return match.group ( 1 )



# 2. Second Function - TRANSCRIPT LOADER :-

def load_youtube_transcript ( video_id : str ) -> str :

    """
    Fetches and returns the full transcript of a YouTube video
    as a single concatenated string.

    Args:
        video_id (str): YouTube video ID

    Returns:
        str: Full transcript text
    """

    try :
        ytt_api = YouTubeTranscriptApi ( )
        
        transcript_list = ytt_api.fetch ( 

            video_id,
            languages = [ "en" ]
        )

        # Formatting the fetched "Transcripts" into One Single Large Text

        transcript_text = " ".join ( [ snippet.text for snippet in transcript_list.snippets ] )

        return transcript_text
    
    except TranscriptsDisabled :
        raise ValueError (
            f"No Captions ( Subtitles ) Available for video ID: {video_id}"
        )


# 3. Third Function - TRANSCRIPT ORCHESTRATOR :-

def get_transcript_from_youtube_url ( video_url : str ) -> str :

    """
    Extracts a YouTube video ID from the given URL and loads the
    corresponding transcript as a single concatenated text string.

    This function serves as a connector between the video ID extraction
    and transcript loading steps, providing a clean entry point for
    higher-level components such as a Streamlit application.
    """

    video_id = extract_video_id ( video_url )

    transcripts = load_youtube_transcript ( video_id )

    return transcripts


# So till now Overall 1st Major Step finishes which is "Fetching the Transcripts of The Youtube Video".
# Now moving on to the 2nd Major Step which is "Splitting The Transcript Texts into Chunks".


#--------------------------------------------------------
# PHASE 2 :- SPLITTING THE TRANSCRIPT TEXTS INTO CHUNKS |
#--------------------------------------------------------

# 4. Fourth Function - CHUNK GENERATOR :-

def create_chunks ( transcripts : str ) -> list [ Document ] :

    """
    Splits a single large transcript text into smaller overlapping chunks
    using RecursiveCharacterTextSplitter.

    Args:
        transcript (str): Full transcript text extracted from YouTube video.

    Returns:
        list[Document]: List of LangChain Document objects (chunks).
    """

    splitter = RecursiveCharacterTextSplitter ( 

        chunk_size = 1000 ,
        chunk_overlap = 200  # With these arguments a total of 86 overlapping chunks will be created. 
    )

    chunks = splitter.create_documents ( [ transcripts ] )

    return chunks


#-----------------------------------------------------------------
# PHASE 3 :- VECTORIZATION & STORAGE ( PERSISTENT VECTOR STORE ) |
#-----------------------------------------------------------------

# First Resource - Embedding Model Object :-

embedding_model = HuggingFaceEmbeddings ( model_name = "sentence-transformers/all-MiniLM-L6-v2" )  # This is the "instance" of my embedding model.


# 5. Fifth Function - PERSISTENT VECTOR STORE BUILDER :-

def get_or_create_vector_store ( 
        
        video_id : str ,

        chunks : list [ Document ] ,

        embedding_model : HuggingFaceEmbeddings

) -> FAISS :
    
    """
    Loads a persisted FAISS vector store if it exists for a given video_id.
    Otherwise, creates a new vector store, saves it to disk, and returns it.

    Args:
        video_id (str): Unique YouTube video ID
        chunks (list[Document]): Chunked transcript documents
        embedding_model (HuggingFaceEmbeddings): Embedding model instance

    Returns:
        FAISS: Ready-to-use vector store
    """

    # 1. Create directory path for the video's vector store
    video_store_path = os.path.join ( VECTOR_STORE_DIRECTORY , video_id )  # Ensures one vector store per video.

    # 2. If vector store already exists --> load it
    if os.path.exists ( video_store_path ) :  # This is the core cahcing decision where if it Exists -> load , If Not Exists -> create.

        print ( f"[ INFO ] Loading existing vector store for video_id = { video_id }" )


        vector_store = FAISS.load_local ( 
            
            folder_path = video_store_path ,

            embeddings = embedding_model ,

            allow_dangerous_deserialization = True 
            
        )

        return vector_store

    # 3. Else --> create new vector store and persist it
    print ( f"[ INFO ] Creating new vector store for video_id = { video_id }" )

    vector_store = FAISS.from_documents (

        documents = chunks ,
        
        embedding = embedding_model

    )

    # 4. Persist the vector store to disk ( CACHING )
    vector_store.save_local ( video_store_path )  # This will create "index.faiss" and "index.pkl" to disk - the actual persistent memory.

    print ( f" [ INFO ] Vector store saved at : { video_store_path }" )

    return vector_store


#-----------------------
# PHASE 4 :- Retrieval |
#-----------------------

# 6. Sixth Function - RETRIEVER CREATOR :-

def create_retriever ( vector_store : FAISS ) -> BaseRetriever :

    """
    Creates a retriever from a FAISS vector store.

    Args:
        vectorstore (FAISS): Vector store containing embedded documents.

    Returns:
        BaseRetriever: Configured retriever for similarity search.
    """

    retriever = vector_store.as_retriever ( search_kwargs = { "k" : 4 } )

    return retriever


#---------------------------------------------
# PHASE 5: Prompting , CHAINING & Generation |
#---------------------------------------------

# 7. Seventh Function - CONTEXT FORMATER :-

def format_retrieved_docs ( docs : list [ Document ] ) -> str :

    """
    The retrieved documents from the retriever are not in perfect stucture
    They contain lots of metadata and hierarchy
    This function formats and returns One Single Large Text.
    """

    context_text = "\n\n".join ( [ doc.page_content for doc in docs ] )

    return context_text


# Second Resource - Prompt Template :-

prompt = PromptTemplate (

    template = """

    You are a transcript-grounded AI assistant built using Retrieval-Augmented Generation (RAG).

    Your job is to answer questions using ONLY the information present in the provided transcript context.

    Rules you MUST follow:
    1. Use only the given transcript context. Do NOT use outside knowledge.
    2. Do NOT guess, assume, or hallucinate.
    3. If the answer is NOT present and CANNOT be reasonably derived from the transcript, clearly say so.
    4. For questions about relevance, suitability, or audience (e.g., "Is this video useful for a data analyst?"),
    you MAY infer the answer ONLY based on the topics discussed in the transcript.
    5. When refusing to answer, explain briefly that the information is not discussed in the video.
    6. Be clear, concise, and professional.

    If the transcript context is insufficient, respond with:
    "The video does not discuss this topic, so I cannot answer based on the provided content."

    Context:
    {context_text}

    Question:
    {question}    
""",

    input_variables = [ "context_text" , "question" ]

)


# Third Resource - LLM ( AI Model ) :-

load_dotenv ( )

OPENROUTER_API_KEY = os.getenv ( "OPENROUTER_API_KEY" )

llm = ChatOpenAI (

    model = "openai/gpt-oss-20b:free",
    openai_api_key = OPENROUTER_API_KEY ,
    openai_api_base = "https://openrouter.ai/api/v1"
)


# Fourth Resource - String Output Parser :-

parser = StrOutputParser ( )


# 8. Eight Function - RAG CHAIN BUILDER :-

def build_rag_chain ( retriever ) :

    """
    Builds the complete RAG pipeline using LangChain Runnables.

    Flow:
    User Query
        ├── Retriever → Docs → Formatter → Context
        └── Original Question
            ↓
        Prompt → LLM → Output Parser
    """

    # Parallel Chain --> Gives us CONTEXT and QUESTION :-

    parallel_chain = RunnableParallel (

        { 

            "context_text" : retriever | RunnableLambda ( format_retrieved_docs ) ,

            "question" : RunnablePassthrough ( )

        }
        
    )

    # RAG Chain --> Gives us the Main Output :-

    rag_chain = parallel_chain | prompt | llm | parser

    return rag_chain


#-------------------------------
# PHASE 6: Final Orchestration | ( Specially built for "LOOSE COUPLING" & "SEPRATION OF CONCERNS" for Backend and Frontend )
#-------------------------------

# 9. Ninth Final Function - THE ORCHESTRATOR :-

def prepare_youtube_rag_chain ( video_url : str ) -> Runnable :

    """
    Orchestrates the complete YouTube → RAG pipeline.

    This is the SINGLE entry point for:
    - Streamlit frontend
    - CLI testing
    - Future API (FastAPI, etc.)

    Flow:
    YouTube URL
        → Video ID
        → Transcript
        → Chunks
        → Vector Store (cached)
        → Retriever
        → RAG Chain

    Returns:
        Runnable RAG Chain ready to be invoked with questions
    """

    # 1. Extracts the video's id
    video_id = extract_video_id ( video_url )

    # 2. Fetches the transcripts of the particular video
    transcripts = load_youtube_transcript ( video_id )

    # 3. Splits the transcripts into multiple chunks
    chunks = create_chunks ( transcripts )

    # 4. Loads or Creates vector store ( persistent caching ).
    vector_store = get_or_create_vector_store ( video_id , chunks , embedding_model )

    # 5. Creates the retriever
    retriever = create_retriever ( vector_store )

    # 6. Builds the rag chain.
    rag_chain = build_rag_chain ( retriever )

    return rag_chain


# CODE FOR TESTING WITH DETAILED TIMING FOR EACH STEP ( My Frontend ( Streamlit ) doesn't uses this code ) :-

if __name__ == "__main__":
    
    import datetime
    
    print("\n" + "="*70)
    print("🚀 YOUTUBE RAG PIPELINE - PERFORMANCE TEST")
    print("="*70 + "\n")
    
    overall_start = datetime.datetime.now()
    print(f"⏰ Overall Start Time: {overall_start.strftime('%H:%M:%S')}\n")
    
    # ========== STEP 1: Extract Video ID ==========
    video_url = "https://www.youtube.com/watch?v=rtOvBOTyX00&list=RDrtOvBOTyX00&start_radio=1&pp=oAcB"
    
    step_start = datetime.datetime.now()
    video_id = extract_video_id(video_url)
    step_end = datetime.datetime.now()
    step_duration = (step_end - step_start).total_seconds()
    
    print(f"✅ STEP 1: Extract Video ID")
    print(f"   Video ID: {video_id}")
    print(f"   Duration: {step_duration:.2f} seconds\n")
    
    # ========== STEP 2: Fetch Transcript ==========
    step_start = datetime.datetime.now()
    transcripts = load_youtube_transcript(video_id)
    step_end = datetime.datetime.now()
    step_duration = (step_end - step_start).total_seconds()
    
    print(f"✅ STEP 2: Fetch YouTube Transcript")
    print(f"   Transcript Length: {len(transcripts)} characters")
    print(f"   Duration: {step_duration:.2f} seconds\n")
    
    # ========== STEP 3: Create Chunks ==========
    step_start = datetime.datetime.now()
    chunks = create_chunks(transcripts)
    step_end = datetime.datetime.now()
    step_duration = (step_end - step_start).total_seconds()
    
    print(f"✅ STEP 3: Split into Chunks")
    print(f"   Number of Chunks: {len(chunks)}")
    print(f"   Duration: {step_duration:.2f} seconds\n")
    
    # ========== STEP 4: Create Embeddings & Build Vector Store ( PERSISTENT VECTOR STORE ) ==========
    step_start = datetime.datetime.now()
    vector_store = get_or_create_vector_store ( video_id , chunks , embedding_model )
    step_end = datetime.datetime.now()
    step_duration = (step_end - step_start).total_seconds()
    
    print(f"✅ STEP 4: Load or Create Embeddings & Build Vector Store")
    print(f"   Embeddings Created: {len(chunks)} chunks")
    print(f"   Duration: {step_duration:.2f} seconds (OPTIMIZED)\n")
    
    # ========== STEP 5: Create Retriever ==========
    step_start = datetime.datetime.now()
    retriever = create_retriever(vector_store)
    step_end = datetime.datetime.now()
    step_duration = (step_end - step_start).total_seconds()
    
    print(f"✅ STEP 5: Create Retriever")
    print(f"   Duration: {step_duration:.2f} seconds\n")
    
    # ========== STEP 6: Build RAG Chain ==========
    step_start = datetime.datetime.now()
    rag_chain = build_rag_chain(retriever)
    step_end = datetime.datetime.now()
    step_duration = (step_end - step_start).total_seconds()
    
    print(f"✅ STEP 6: Build RAG Chain")
    print(f"   Duration: {step_duration:.2f} seconds\n")
    
    # ========== STEP 7: Ask Question & Get Answer ==========
    question = "who is demis ?"
    
    step_start = datetime.datetime.now()
    final_answer = rag_chain.invoke(question)
    step_end = datetime.datetime.now()
    step_duration = (step_end - step_start).total_seconds()
    
    print(f"✅ STEP 7: Process Question & Generate Answer")
    print(f"   Question: {question}")
    print(f"   Duration: {step_duration:.2f} seconds\n")
    
    # ========== RESULTS ==========
    print("="*70)
    print("📝 ANSWER:")
    print("="*70)
    print(f"\n{final_answer}\n")
    
    # ========== OVERALL TIMING ==========
    overall_end = datetime.datetime.now()
    total_duration = (overall_end - overall_start).total_seconds()
    
    print("="*70)
    print("⏱️  PERFORMANCE SUMMARY")
    print("="*70)
    print(f"Start Time:     {overall_start.strftime('%H:%M:%S')}")
    print(f"End Time:       {overall_end.strftime('%H:%M:%S')}")
    print(f"Total Duration: {total_duration:.2f} seconds ({total_duration/60:.2f} minutes)")
    print("="*70 + "\n")