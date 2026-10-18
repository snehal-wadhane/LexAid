from fpdf import FPDF

ARIAL    = 'C:/Windows/Fonts/arial.ttf'
ARIAL_B  = 'C:/Windows/Fonts/arialbd.ttf'
ARIAL_I  = 'C:/Windows/Fonts/ariali.ttf'
ARIAL_BI = 'C:/Windows/Fonts/arialbi.ttf'
MONO     = 'C:/Windows/Fonts/consola.ttf'
MONO_B   = 'C:/Windows/Fonts/consolab.ttf'

class PDF(FPDF):
    def setup_fonts(self):
        self.add_font('Arial',    '',   ARIAL,    uni=True)
        self.add_font('Arial',    'B',  ARIAL_B,  uni=True)
        self.add_font('Arial',    'I',  ARIAL_I,  uni=True)
        self.add_font('Arial',    'BI', ARIAL_BI, uni=True)
        self.add_font('Mono',     '',   MONO,     uni=True)
        self.add_font('Mono',     'B',  MONO_B,   uni=True)

    def header(self):
        self.set_fill_color(36, 36, 37)
        self.rect(0, 0, 210, 12, 'F')
        self.set_font('Arial', 'B', 10)
        self.set_text_color(209, 163, 86)
        self.set_y(3)
        self.cell(0, 6, 'LexAid -- Team Contributions (Code Level)', align='C')
        self.set_text_color(0, 0, 0)
        self.ln(10)

    def footer(self):
        self.set_y(-12)
        self.set_font('Arial', 'I', 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 6, f'Page {self.page_no()}', align='C')

    def member_header(self, name, role, color):
        self.set_fill_color(*color)
        self.set_text_color(255, 255, 255)
        self.set_font('Arial', 'B', 14)
        self.cell(0, 10, f'  {name}  --  {role}', ln=True, fill=True)
        self.set_text_color(0, 0, 0)
        self.ln(3)

    def one_liner(self, text):
        self.set_fill_color(209, 163, 86)
        self.set_font('Arial', 'BI', 10)
        self.set_text_color(36, 36, 37)
        self.cell(0, 8, f'  {text}', ln=True, fill=True)
        self.set_text_color(0, 0, 0)
        self.ln(4)

    def section_title(self, title):
        self.set_font('Arial', 'B', 11)
        self.set_text_color(144, 91, 62)
        self.cell(0, 7, title, ln=True)
        self.set_text_color(0, 0, 0)

    def body(self, text):
        self.set_font('Arial', '', 10)
        self.set_text_color(50, 50, 50)
        self.multi_cell(0, 6, text)
        self.ln(2)

    def code_block(self, code):
        self.set_fill_color(245, 245, 245)
        self.set_draw_color(200, 200, 200)
        self.set_font('Mono', '', 8)
        self.set_text_color(30, 30, 30)
        self.multi_cell(0, 5, code, border=1, fill=True)
        self.ln(3)

    def bullet(self, text):
        self.set_font('Arial', '', 10)
        self.set_text_color(50, 50, 50)
        self.cell(6, 6, '-')
        self.multi_cell(0, 6, text)


pdf = PDF()
pdf.set_auto_page_break(auto=True, margin=15)
pdf.set_margins(15, 18, 15)
pdf.setup_fonts()

# =============================================================
# MEMBER 1 -- SNEHAL
# =============================================================
pdf.add_page()
pdf.member_header('Snehal', 'Backend API + LLM Streaming', (36, 36, 37))
pdf.one_liner('Built the FastAPI backend with Groq LLM streaming and REST API layer')

pdf.section_title('1. FastAPI Application Setup  (main.py)')
pdf.body(
    'Created the FastAPI application with a lifespan context manager that pre-warms '
    'the embedding model and ChromaDB connection on startup. This eliminates cold-start '
    'latency -- the first user query is as fast as every subsequent one.'
)
pdf.code_block(
    '@asynccontextmanager\n'
    'async def lifespan(app: FastAPI):\n'
    '    loop = asyncio.get_event_loop()\n'
    '    await loop.run_in_executor(None, _get_embed_model)  # loads multilingual-e5-small\n'
    '    await loop.run_in_executor(None, _get_collection)   # connects ChromaDB\n'
    '    yield\n'
    '\n'
    'app = FastAPI(title="LexAid API", version="0.1.0", lifespan=lifespan)'
)

pdf.section_title('2. CORS Middleware')
pdf.body(
    'Configured Cross-Origin Resource Sharing so the Next.js frontend on localhost:3000 '
    'can call the FastAPI backend on localhost:8000 without being blocked by the browser '
    'same-origin policy.'
)
pdf.code_block(
    'app.add_middleware(\n'
    '    CORSMiddleware,\n'
    '    allow_origins=["http://localhost:3000"],\n'
    '    allow_methods=["*"],\n'
    '    allow_headers=["*"],\n'
    ')'
)

pdf.section_title('3. SSE Streaming Endpoint -- /api/query')
pdf.body(
    'The core endpoint. Instead of waiting for the full LLM answer, it streams tokens '
    'back to the frontend as Server-Sent Events (SSE), giving the real-time typewriter '
    'effect. Three SSE event types are sent in order: "sources" (act names, sent first '
    'so badges appear instantly), "token" (each word from Groq), "done" (final chunk scores).'
)
pdf.code_block(
    '@app.post("/api/query")\n'
    'def query(req: QueryRequest):\n'
    '    def generate():\n'
    '        yield from stream_answer(req.question, category=req.category)\n'
    '    return StreamingResponse(\n'
    '        generate(),\n'
    '        media_type="text/event-stream",\n'
    '        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}\n'
    '    )'
)

pdf.section_title('4. Groq LLM Integration  (rag.py)')
pdf.body(
    'Integrated Groq cloud LLM using the official groq Python SDK. Primary model is '
    'gpt-oss-120b with automatic fallback to gpt-oss-20b if the primary fails. '
    'Temperature set to 0.1 for consistent, factual legal answers. max_tokens=2048 '
    'to prevent response truncation mid-sentence.'
)
pdf.code_block(
    'stream = groq.chat.completions.create(\n'
    '    model="openai/gpt-oss-120b",\n'
    '    messages=messages,\n'
    '    temperature=0.1,\n'
    '    max_tokens=2048,\n'
    '    stream=True,\n'
    ')\n'
    'for chunk in stream:\n'
    '    delta = chunk.choices[0].delta.content\n'
    '    if delta:\n'
    '        yield f\'data: {{"type":"token","text":{delta!r}}}\\n\\n\''
)

pdf.section_title('5. System Prompt Engineering')
pdf.body(
    'Designed the LLM system prompt with strict grounding rules to prevent hallucination '
    'and ensure every answer cites actual statute text.'
)
pdf.bullet('Answer ONLY from statutory sections provided -- no outside knowledge\n')
pdf.bullet('Cite Act name + section number for every legal point made\n')
pdf.bullet('Use plain language -- explain legal jargon when it must be used\n')
pdf.bullet('If retrieved sections do not answer the question, say so explicitly\n')
pdf.bullet('Always end with the standard legal disclaimer on its own line\n')

pdf.section_title('6. Additional API Endpoints')
pdf.body(
    '/api/acts  -- Returns all 17 acts from ACT_MAP dynamically (no hardcoding in frontend)\n'
    '/api/retrieve  -- Debug endpoint: returns raw ChromaDB chunks without LLM (used for testing retrieval quality)\n'
    '/health  -- Status check used by deployment health monitors'
)

# =============================================================
# MEMBER 2 -- SURAJ
# =============================================================
pdf.add_page()
pdf.member_header('Suraj', 'Data Ingestion + Vector Database', (144, 91, 62))
pdf.one_liner('Collected and ingested 17 Indian statutes into ChromaDB with 2,255 chunks')

pdf.section_title('1. PDF Collection & ACT_MAP Setup')
pdf.body(
    'Collected 17 official Indian statute PDFs covering criminal law, consumer rights, '
    'labour rights, property, RTI, civil rights, disability, and commercial law. '
    'Identified two image-scanned PDFs (original IPC and old POCSO) with zero extractable '
    'text -- replaced them with text-based versions.'
)
pdf.code_block(
    'ACT_MAP = {\n'
    '    "1742378582_Indian_Penal_Code_1860.pdf":  { "act_name": "Indian Penal Code, 1860",\n'
    '                                                 "short": "IPC", "category": "criminal" },\n'
    '    "250883_english_01042024.pdf":             { "act_name": "Bharatiya Nyaya Sanhita, 2023",\n'
    '                                                 "short": "BNS", "category": "criminal" },\n'
    '    "domviolence.pdf":                         { "act_name": "Protection of Women from DV Act, 2005",\n'
    '                                                 "short": "PWDVA", "category": "civil_rights" },\n'
    '    "NI.pdf":                                  { "act_name": "Negotiable Instruments Act, 1881",\n'
    '                                                 "short": "NIA", "category": "commercial" },\n'
    '    # ... 13 more acts\n'
    '}'
)

pdf.section_title('2. PyMuPDF Text Extraction')
pdf.body(
    'Used PyMuPDF to extract raw text from each PDF page by page. Applied clean_text() '
    'to remove form-feed characters (\\x0c), control characters, and excessive whitespace '
    'before passing text to the chunker.'
)
pdf.code_block(
    'def extract_text(pdf_path: Path) -> str:\n'
    '    doc = pymupdf.open(str(pdf_path))\n'
    '    return clean_text("\\n".join(p.get_text() for p in doc))\n'
    '\n'
    'def clean_text(text: str) -> str:\n'
    '    text = text.replace("\\x0c", "\\n")                         # form-feed\n'
    '    text = re.sub(r"[\\x00-\\x08\\x0b\\x0e-\\x1f\\x7f]", "", text) # control chars\n'
    '    text = re.sub(r"\\n{3,}", "\\n\\n", text)                    # excess newlines\n'
    '    text = re.sub(r"[ \\t]{2,}", " ", text)                      # extra spaces\n'
    '    return text.strip()'
)

pdf.section_title('3. Section-Based Chunker')
pdf.body(
    'Indian statutes are structured by numbered sections (e.g., "11. Standard rent"). '
    'Built a regex boundary detector that splits on section numbers, keeping each legal '
    'section as one chunk. Small sections (< 80 words) are merged with the next. '
    'Falls back to sliding window if fewer than 3 section boundaries are found.'
)
pdf.code_block(
    'boundary = re.compile(\n'
    '    r"(?:^|\\n)\\s*"\n'
    '    r"(?:Section\\s+|Article\\s+|Sec\\.\\s*)?"\n'
    '    r"(\\d{1,3}[A-Z]{0,2})\\s*"\n'
    '    r"[\\.---]\\s*"\n'
    '    r"(?=[A-Z\\(\\[])",\n'
    '    re.MULTILINE,\n'
    ')\n'
    '# Sections < 80 words are merged with the next one\n'
    '# Result: 200-800 word chunks, each = one complete legal section'
)

pdf.section_title('4. Sliding Window Fallback')
pdf.body(
    'For PDFs without clear section headers (textbooks, guides), falls back to overlapping '
    'word windows. 600 words per chunk with 60-word overlap ensures context is not lost '
    'at chunk boundaries.'
)
pdf.code_block(
    'def sliding_window(text: str, max_words=600, overlap=60):\n'
    '    words = text.split()\n'
    '    chunks, start = [], 0\n'
    '    while start < len(words):\n'
    '        end = min(start + max_words, len(words))\n'
    '        chunks.append(" ".join(words[start:end]))\n'
    '        if end >= len(words): break\n'
    '        start = end - overlap  # 60-word overlap prevents context loss\n'
    '    return chunks'
)

pdf.section_title('5. Embedding + ChromaDB Batch Insertion')
pdf.body(
    'Each chunk is embedded with the "passage: " prefix (required by multilingual-e5-small '
    'for indexed documents), normalized to unit length, then inserted into ChromaDB with '
    'act name, short code, category, and chunk index as metadata. Inserted in batches of 100.'
)
pdf.code_block(
    'embeddings = model.encode(\n'
    '    [f"passage: {s}" for s in sections],\n'
    '    batch_size=32,\n'
    '    normalize_embeddings=True,   # L2 norm required for cosine similarity\n'
    ')\n'
    'for b in range(0, len(ids), 100):\n'
    '    col.add(\n'
    '        ids=ids[b:b+100],\n'
    '        documents=docs[b:b+100],\n'
    '        metadatas=metas[b:b+100],\n'
    '        embeddings=embeds[b:b+100],\n'
    '    )'
)

pdf.section_title('6. Incremental Topup Script  (topup_new3.py)')
pdf.body(
    'Built a topup script to add the 3 new acts without dropping and re-ingesting all '
    '17 acts. Chunk IDs are md5(filename_index) so duplicates are impossible. '
    'Final collection: 2,255 chunks across 17 acts.'
)
pdf.bullet('IPC 1860 (text-based replacement): 367 chunks\n')
pdf.bullet('Negotiable Instruments Act 1881: 128 chunks\n')
pdf.bullet('Protection of Women from Domestic Violence Act 2005: 25 chunks\n')

# =============================================================
# MEMBER 3 -- SUYASH
# =============================================================
pdf.add_page()
pdf.member_header('Suyash', 'Frontend + Chat UI', (26, 86, 130))
pdf.one_liner('Developed Next.js 14 frontend with chat UI, Triage Wizard, and real-time streaming')

pdf.section_title('1. Next.js 14 App Router Setup')
pdf.body(
    'Set up the Next.js 14 project with App Router, TypeScript, and Tailwind CSS. '
    'Configured NEXT_PUBLIC_API_URL environment variable so the backend URL is '
    'injectable at build time for both local dev and cloud deployment.'
)
pdf.code_block(
    '// frontend/.env.local\n'
    'NEXT_PUBLIC_API_URL=http://localhost:8000\n'
    '\n'
    '// Used in ChatInterface.tsx\n'
    'const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"'
)

pdf.section_title('2. SSE Stream Reading  (ChatInterface.tsx)')
pdf.body(
    'Used the browser Streams API to read SSE response token by token instead of '
    'waiting for the full answer. Each line is parsed as a JSON event and dispatched '
    'by type: "sources" populates badge list, "token" appends to the message, '
    '"done" finalises and stops the blinking cursor.'
)
pdf.code_block(
    'const res = await fetch(`${API}/api/query`, { method:"POST", body: JSON.stringify({...}) })\n'
    'const reader = res.body!.getReader()\n'
    'const decoder = new TextDecoder()\n'
    'while (true) {\n'
    '  const { done, value } = await reader.read()\n'
    '  if (done) break\n'
    '  for (const line of decoder.decode(value).split("\\n")) {\n'
    '    if (!line.startsWith("data: ")) continue\n'
    '    const ev = JSON.parse(line.slice(6))\n'
    '    if (ev.type === "sources") setSources(ev.sources)\n'
    '    if (ev.type === "token")   appendToken(ev.text)\n'
    '    if (ev.type === "done")    setStreaming(false)\n'
    '  }\n'
    '}'
)

pdf.section_title('3. MessageBubble Component  (MessageBubble.tsx)')
pdf.body(
    'User messages: orange bubble, right-aligned. Assistant messages: white card, '
    'left-aligned, source badges above. Loading state: 3 bouncing dots. '
    'Streaming state: blinking orange cursor after the last token. '
    'Uses react-markdown + remark-gfm so tables, bold, lists render correctly.'
)
pdf.code_block(
    'import ReactMarkdown from "react-markdown"\n'
    'import remarkGfm from "remark-gfm"\n'
    '\n'
    '<div className="prose prose-sm ... prose-table:w-full prose-th:bg-orange-50\n'
    '                prose-td:border prose-td:border-gray-200">\n'
    '  <ReactMarkdown remarkPlugins={[remarkGfm]}>\n'
    '    {msg.content}\n'
    '  </ReactMarkdown>\n'
    '  {msg.streaming && <span className="blinking-cursor" />}\n'
    '</div>'
)

pdf.section_title('4. Source Citation Badges')
pdf.body(
    'When the SSE "sources" event arrives before tokens start, renders coloured pill '
    'badges above the answer showing exactly which acts were retrieved. Gives users '
    'transparency about which laws back the answer before they finish reading it.'
)
pdf.code_block(
    '{msg.sources?.map(s => (\n'
    '  <span key={s}\n'
    '    className="text-xs bg-blue-100 text-blue-800 border border-blue-200\n'
    '               rounded-full px-2 py-0.5 font-medium">\n'
    '    {s}\n'
    '  </span>\n'
    '))}'
)

pdf.section_title('5. Triage Wizard  (TriageWizard.tsx)')
pdf.body(
    'Collapsible sidebar panel with 6 legal categories. Clicking a category expands '
    '3-4 sub-categories. Each sub-category has a pre-written legal prompt and a '
    'category tag. Clicking fires the query into the chat with the correct category '
    'filter applied -- bypassing the need for the user to type anything.'
)
pdf.code_block(
    'const CATEGORIES = [\n'
    '  { id: "labour", label: "Labour Rights", subs: [\n'
    '    { label: "Unpaid Salary",\n'
    '      prompt: "My employer has not paid my salary for X months...",\n'
    '      cat: "labour" },\n'
    '    { label: "Wrongful Termination",\n'
    '      prompt: "I was fired without notice or reason...",\n'
    '      cat: "labour" },\n'
    '  ]},\n'
    '  { id: "property", label: "Property & Rent", subs: [...] },\n'
    '  // 4 more categories: Consumer, Criminal, RTI, Civil Rights\n'
    ']'
)

pdf.section_title('6. Tailwind Typography Plugin Configuration')
pdf.body(
    'Installed @tailwindcss/typography and configured prose classes with custom overrides '
    'for table styling. Before this fix, LLM-generated markdown tables rendered as raw '
    '| pipe | dash | text -- unreadable. After: proper HTML tables with borders, '
    'alternating row colours, and orange header tint matching the brand.'
)
pdf.code_block(
    '// tailwind.config.ts\n'
    'plugins: [require("@tailwindcss/typography")]\n'
    '\n'
    '// MessageBubble.tsx -- prose overrides\n'
    'prose-table:w-full prose-table:text-sm\n'
    'prose-th:bg-orange-50 prose-th:border prose-th:border-gray-300\n'
    'prose-td:border prose-td:border-gray-200\n'
    'prose-tr:even:bg-gray-50'
)

# =============================================================
# MEMBER 4 -- AVISHKAR
# =============================================================
pdf.add_page()
pdf.member_header('Avishkar', 'RAG Pipeline + Smart Retrieval', (46, 125, 50))
pdf.one_liner('Implemented RAG retrieval logic with category auto-detection and cosine similarity tuning')

pdf.section_title('1. multilingual-e5-small Integration')
pdf.body(
    'Chose intfloat/multilingual-e5-small as the local embedding model -- small enough '
    'to run on CPU without a GPU, supports Hindi and Indian regional languages, and '
    'outperforms generic English models on multilingual legal text. Critical discovery: '
    'e5 models need DIFFERENT text prefixes for indexing vs retrieval.'
)
pdf.code_block(
    '# Indexing time (ingest.py): "passage: " prefix\n'
    'model.encode(f"passage: {chunk}", normalize_embeddings=True)\n'
    '\n'
    '# Query time (rag.py): "query: " prefix\n'
    'model.encode(f"query: {user_question}", normalize_embeddings=True)\n'
    '\n'
    '# Using wrong prefix degrades similarity scores significantly.\n'
    '# normalize_embeddings=True converts to unit vectors for cosine distance.'
)

pdf.section_title('2. ChromaDB Cosine Similarity Setup')
pdf.body(
    'Configured ChromaDB with cosine distance metric (hnsw:space="cosine"). '
    'At query time, retrieves top-K chunks sorted by similarity score. '
    'Converts raw distance to human-readable relevance score for source badges.'
)
pdf.code_block(
    '# Collection created with cosine space\n'
    'col = client.create_collection(\n'
    '    COLLECTION,\n'
    '    metadata={"hnsw:space": "cosine"}\n'
    ')\n'
    '\n'
    '# Convert distance to similarity score for display\n'
    'score = round(1 - distance, 4)   # distance=0 means identical, score=1.0'
)

pdf.section_title('3. Category Auto-Detector  (_detect_category)')
pdf.body(
    'Solved the critical retrieval bug: without a category filter, BNS and IPC dominate '
    'search results by sheer volume (367 chunks each), even for rent or labour queries. '
    'Built keyword-based domain router that detects the legal category from the query '
    'and applies the ChromaDB "where" filter automatically -- no user action needed.'
)
pdf.code_block(
    '_CATEGORY_KEYWORDS = {\n'
    '    "property": ["rent", "landlord", "tenant", "1rk", "1bhk",\n'
    '                 "paying rent", "security deposit", "eviction", ...],\n'
    '    "labour":   ["salary", "wage", "fired", "dismissed", "epf",\n'
    '                 "gratuity", "minimum wage", "termination", ...],\n'
    '    "criminal": ["murder", "theft", "fir", "arrest", "bail", ...],\n'
    '    "consumer": ["refund", "defective", "consumer", "amazon", ...],\n'
    '    # 4 more categories\n'
    '}\n'
    '\n'
    'def _detect_category(query: str) -> Optional[str]:\n'
    '    q = query.lower()\n'
    '    scores = {cat: sum(1 for kw in kws if kw in q)\n'
    '              for cat, kws in _CATEGORY_KEYWORDS.items()}\n'
    '    scores = {k: v for k, v in scores.items() if v > 0}\n'
    '    if not scores: return None\n'
    '    best, top = max(scores.items(), key=lambda x: x[1])\n'
    '    # Only filter if one clear winner -- prevents wrong routing\n'
    '    return best if list(scores.values()).count(top) == 1 else None'
)

pdf.section_title('4. Retrieve Function with Auto-Routing')
pdf.body(
    'The retrieve() function uses category from the Triage Wizard if provided, otherwise '
    'calls _detect_category(). When filtered, fetches 8 chunks instead of 6 -- '
    'filtered searches cover fewer acts so more chunks per act gives richer legal context.'
)
pdf.code_block(
    'def retrieve(query, k=TOP_K, category=None):\n'
    '    embedding = model.encode(\n'
    '        f"query: {query}", normalize_embeddings=True\n'
    '    ).tolist()\n'
    '\n'
    '    # Explicit (Triage Wizard) takes priority over auto-detected\n'
    '    effective_category = category or _detect_category(query)\n'
    '    where = {"category": effective_category} if effective_category else None\n'
    '\n'
    '    # Fetch more chunks when filtered (fewer competing acts)\n'
    '    actual_k = min(k + 2, 10) if effective_category else k\n'
    '\n'
    '    results = collection.query(\n'
    '        query_embeddings=[embedding],\n'
    '        n_results=actual_k,\n'
    '        where=where,\n'
    '        include=["documents", "metadatas", "distances"]\n'
    '    )'
)

pdf.section_title('5. Context Builder + Source Deduplication')
pdf.body(
    'Builds the LLM context by numbering each retrieved chunk with its act name. '
    'Deduplicates source act names for the SSE "sources" event -- the same act may '
    'appear in multiple top-K chunks. Sources are sent BEFORE tokens so the UI '
    'shows act badges immediately, before the answer starts streaming.'
)
pdf.code_block(
    '# Deduplicated act names for source badges (sent first)\n'
    'sources = list({c["act_name"] for c in chunks})\n'
    'yield f\'data: {{"type":"sources","sources":{sources}}}\\n\\n\'\n'
    '\n'
    '# Numbered context string for LLM\n'
    'context = "\\n\\n---\\n\\n".join(\n'
    '    f"[Source {i} -- {c[\'act_name\']}]\\n{c[\'text\']}"\n'
    '    for i, c in enumerate(chunks, 1)\n'
    ')'
)

pdf.section_title('6. Groq Fallback + Token Tuning')
pdf.body(
    'Implemented try/except fallback: if gpt-oss-120b is unavailable or rate-limited, '
    'automatically retries with gpt-oss-20b. Both models were confirmed by querying '
    'the /v1/models endpoint during development. max_tokens raised from 1024 to 2048 '
    'after truncation bug was caught mid-sentence ("He **cannot...").'
)
pdf.code_block(
    'try:\n'
    '    stream = groq.chat.completions.create(\n'
    '        model="openai/gpt-oss-120b",\n'
    '        max_tokens=2048,     # raised from 1024 to fix truncation\n'
    '        temperature=0.1,\n'
    '        stream=True, ...)\n'
    'except Exception:\n'
    '    stream = groq.chat.completions.create(\n'
    '        model="openai/gpt-oss-20b",   # fallback model\n'
    '        max_tokens=2048,\n'
    '        stream=True, ...)'
)

# =============================================================
# SUMMARY PAGE
# =============================================================
pdf.add_page()
pdf.set_fill_color(36, 36, 37)
pdf.rect(0, 0, 210, 297, 'F')

pdf.set_y(30)
pdf.set_font('Arial', 'B', 22)
pdf.set_text_color(209, 163, 86)
pdf.cell(0, 12, 'LexAid -- Team Summary', align='C', ln=True)
pdf.set_font('Arial', '', 12)
pdf.set_text_color(200, 200, 200)
pdf.cell(0, 8, 'AI-Powered Indian Legal Aid Platform', align='C', ln=True)
pdf.ln(15)

members = [
    ('Snehal',   'Backend API + LLM Streaming',      (209, 163, 86),  'FastAPI + Groq SSE + System Prompt + CORS'),
    ('Suraj',    'Data Ingestion + Vector Database',  (144, 91,  62),  'PyMuPDF + ChromaDB + 17 Acts + 2,255 Chunks'),
    ('Suyash',   'Frontend + Chat UI',                (100, 160, 200), 'Next.js 14 + Triage Wizard + react-markdown + remark-gfm'),
    ('Avishkar', 'RAG Pipeline + Smart Retrieval',    (100, 180, 100), 'multilingual-e5-small + Category Auto-Detect + Cosine Tuning'),
]

for name, role, color, tech in members:
    pdf.set_fill_color(*color)
    pdf.set_font('Arial', 'B', 13)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 10, f'  {name}  --  {role}', ln=True, fill=True)
    pdf.set_font('Arial', '', 10)
    pdf.set_text_color(180, 180, 180)
    pdf.cell(0, 7, f'       {tech}', ln=True)
    pdf.ln(5)

pdf.ln(12)
pdf.set_font('Arial', 'B', 12)
pdf.set_text_color(209, 163, 86)
pdf.cell(0, 8, 'Complete Tech Stack', align='C', ln=True)
pdf.ln(3)
pdf.set_font('Arial', '', 10)
pdf.set_text_color(180, 180, 180)
stack = [
    'Backend:       FastAPI 0.115  |  Python 3.10  |  Uvicorn',
    'AI / LLM:      Groq gpt-oss-120b  |  multilingual-e5-small (local)',
    'Database:      ChromaDB 0.5  |  Supabase Postgres (planned)',
    'Frontend:      Next.js 14  |  TypeScript  |  Tailwind CSS',
    'Libraries:     PyMuPDF  |  sentence-transformers  |  react-markdown  |  remark-gfm',
    'Corpus:        17 Indian Acts  |  2,255 vector chunks  |  Cosine similarity',
    'Deployment:    Vercel (frontend)  |  Railway/Render (backend)  -- Planned Phase 2',
]
for line in stack:
    pdf.cell(0, 7, f'    {line}', ln=True)

out = 'D:\\LexAid\\LexAid_Team_Contributions.pdf'
pdf.output(out)
print(f'Saved: {out}')
