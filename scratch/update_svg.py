import re

with open(r'c:\Users\pc\OneDrive\Desktop\nutritrack\paper.html', 'r', encoding='utf-8') as f:
    html = f.read()

svg1 = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 320" width="600" height="320">
  <defs><marker id="arr" markerWidth="7" markerHeight="7" refX="5" refY="3.5" orient="auto"><polygon points="0 0,7 3.5,0 7" fill="#000"/></marker></defs>
  <rect x="50" y="10" width="500" height="40" fill="#fff" stroke="#000" stroke-width="1.2"/>
  <text x="300" y="25" text-anchor="middle" font-size="11" font-weight="bold" font-family="Consolas, monospace">TIER 1 - PRESENTATION TIER (Browser / PWA Client)</text>
  <text x="300" y="40" text-anchor="middle" font-size="11" font-family="Consolas, monospace">Vanilla HTML5/JS SPA * Service Worker * Supabase Auth JS</text>

  <line x1="300" y1="50" x2="300" y2="80" stroke="#000" stroke-width="1.2" marker-end="url(#arr)"/>
  <text x="310" y="70" font-size="11" font-family="Consolas, monospace">HTTPS / REST / SSE</text>

  <rect x="50" y="80" width="500" height="40" fill="#fff" stroke="#000" stroke-width="1.2"/>
  <text x="300" y="95" text-anchor="middle" font-size="11" font-weight="bold" font-family="Consolas, monospace">TIER 2 - APPLICATION TIER (Flask REST API - Port 5000)</text>
  <text x="300" y="110" text-anchor="middle" font-size="11" font-family="Consolas, monospace">JWT Verification * SQLAlchemy ORM * RAG Enrichment Engine</text>

  <line x1="200" y1="120" x2="200" y2="150" stroke="#000" stroke-width="1.2" marker-end="url(#arr)"/>
  <text x="210" y="140" font-size="11" font-family="Consolas, monospace">HTTP</text>

  <line x1="400" y1="120" x2="400" y2="150" stroke="#000" stroke-width="1.2" marker-end="url(#arr)"/>
  <text x="410" y="140" font-size="11" font-family="Consolas, monospace">Supabase SDK</text>

  <rect x="50" y="150" width="260" height="70" fill="#fff" stroke="#000" stroke-width="1.2"/>
  <text x="180" y="165" text-anchor="middle" font-size="11" font-weight="bold" font-family="Consolas, monospace">TIER 3 - INFERENCE SERVER (Port 5002)</text>
  <text x="180" y="180" text-anchor="middle" font-size="11" font-family="Consolas, monospace">* Ollama llava-phi3</text>
  <text x="180" y="195" text-anchor="middle" font-size="11" font-family="Consolas, monospace">* SigLIP Classifier</text>
  <text x="180" y="210" text-anchor="middle" font-size="11" font-family="Consolas, monospace">* Moondream2 Fallback</text>

  <rect x="330" y="150" width="220" height="70" fill="#fff" stroke="#000" stroke-width="1.2"/>
  <text x="440" y="165" text-anchor="middle" font-size="11" font-weight="bold" font-family="Consolas, monospace">SUPABASE CLOUD INFRASTRUCTURE</text>
  <text x="440" y="180" text-anchor="middle" font-size="11" font-family="Consolas, monospace">* Identity &amp; Auth (JWT)</text>
  <text x="440" y="195" text-anchor="middle" font-size="11" font-family="Consolas, monospace">* base_foods Table (RAG DB)</text>
  <text x="440" y="210" text-anchor="middle" font-size="11" font-family="Consolas, monospace">* users &amp; food_logs Tables</text>

  <line x1="200" y1="220" x2="200" y2="250" stroke="#000" stroke-width="1.2" marker-end="url(#arr)"/>

  <rect x="50" y="250" width="260" height="50" fill="#fff" stroke="#000" stroke-width="1.2"/>
  <text x="180" y="265" text-anchor="middle" font-size="11" font-weight="bold" font-family="Consolas, monospace">OLLAMA MODEL SERVER</text>
  <text x="180" y="280" text-anchor="middle" font-size="11" font-family="Consolas, monospace">Port 11434</text>
  <text x="180" y="295" text-anchor="middle" font-size="11" font-family="Consolas, monospace">llava-phi3 Weights</text>
</svg>'''

html = re.sub(r'<svg.*?</svg>', svg1, html, count=1, flags=re.DOTALL)

svg2 = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 330" width="600" height="330">
  <defs><marker id="arr" markerWidth="7" markerHeight="7" refX="5" refY="3.5" orient="auto"><polygon points="0 0,7 3.5,0 7" fill="#000"/></marker></defs>
  
  <text x="300" y="20" text-anchor="middle" font-size="11" font-family="Consolas, monospace">[ Input: Food Image I ]</text>
  
  <line x1="300" y1="30" x2="300" y2="60" stroke="#000" stroke-width="1.2" marker-end="url(#arr)"/>

  <rect x="60" y="60" width="480" height="40" fill="#fff" stroke="#000" stroke-width="1.2"/>
  <text x="300" y="75" text-anchor="middle" font-size="11" font-weight="bold" font-family="Consolas, monospace">SUBTASK 1: Food Recognition (Multilabel Classify)</text>
  <text x="300" y="90" text-anchor="middle" font-size="11" font-family="Consolas, monospace">Identify ontology set C_I = { c_I,1, ..., c_I,k }</text>

  <line x1="300" y1="100" x2="300" y2="130" stroke="#000" stroke-width="1.2" marker-end="url(#arr)"/>

  <rect x="60" y="130" width="480" height="55" fill="#fff" stroke="#000" stroke-width="1.2"/>
  <text x="300" y="145" text-anchor="middle" font-size="11" font-weight="bold" font-family="Consolas, monospace">SUBTASK 2: Portion Size Estimation (Multiclass Class)</text>
  <text x="300" y="160" text-anchor="middle" font-size="11" font-family="Consolas, monospace">Select qualitative descriptors P_I = { p_I,1, ..., p_I,k }</text>
  <text x="300" y="175" text-anchor="middle" font-size="11" font-family="Consolas, monospace">Map to gram equivalents: grams(p_I,j) via database</text>

  <line x1="300" y1="185" x2="300" y2="215" stroke="#000" stroke-width="1.2" marker-end="url(#arr)"/>

  <rect x="60" y="215" width="480" height="55" fill="#fff" stroke="#000" stroke-width="1.2"/>
  <text x="300" y="230" text-anchor="middle" font-size="11" font-weight="bold" font-family="Consolas, monospace">SUBTASK 3: Nutrient Content Estimation (Vector Sum)</text>
  <text x="300" y="245" text-anchor="middle" font-size="11" font-family="Consolas, monospace">Retrieve base nutrient vectors v^(j) per 100g</text>
  <text x="300" y="260" text-anchor="middle" font-size="11" font-family="Consolas, monospace">Calculate total nutrient vector N = { N_1, ..., N_l }</text>

  <line x1="300" y1="270" x2="300" y2="300" stroke="#000" stroke-width="1.2" marker-end="url(#arr)"/>

  <text x="300" y="315" text-anchor="middle" font-size="11" font-family="Consolas, monospace">[ Final Nutrient Vector N ]</text>
</svg>'''

html = re.sub(r'<svg.*?</svg>', svg2, html, count=1, flags=re.DOTALL)

svg3 = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 520" width="600" height="520">
  <defs><marker id="arr" markerWidth="7" markerHeight="7" refX="5" refY="3.5" orient="auto"><polygon points="0 0,7 3.5,0 7" fill="#000"/></marker></defs>

  <text x="300" y="20" text-anchor="middle" font-size="11" font-family="Consolas, monospace">[ Input: Base64 Image Payload ]</text>
  <line x1="300" y1="30" x2="300" y2="60" stroke="#000" stroke-width="1.2" marker-end="url(#arr)"/>

  <rect x="100" y="60" width="400" height="55" fill="#fff" stroke="#000" stroke-width="1.2"/>
  <text x="300" y="75" text-anchor="middle" font-size="11" font-weight="bold" font-family="Consolas, monospace">STAGE 1: Zero-Shot Food Pre-Check</text>
  <text x="300" y="90" text-anchor="middle" font-size="11" font-family="Consolas, monospace">Engine: SigLIP (google/siglip-base-patch16-224)</text>
  <text x="300" y="105" text-anchor="middle" font-size="11" font-family="Consolas, monospace">Task: Compare "a photo of food" vs non-food vectors</text>

  <line x1="300" y1="115" x2="300" y2="145" stroke="#000" stroke-width="1.2" marker-end="url(#arr)"/>

  <rect x="200" y="145" width="200" height="30" fill="#fff" stroke="#000" stroke-width="1.2"/>
  <text x="300" y="165" text-anchor="middle" font-size="11" font-weight="bold" font-family="Consolas, monospace">Confidence Score &gt;= 0.002?</text>

  <line x1="250" y1="175" x2="250" y2="205" stroke="#000" stroke-width="1.2" marker-end="url(#arr)"/>
  <text x="240" y="195" text-anchor="end" font-size="11" font-weight="bold" font-family="Consolas, monospace">NO</text>
  <text x="250" y="220" text-anchor="middle" font-size="11" font-family="Consolas, monospace">[ Abort &amp; Reject ]</text>

  <line x1="350" y1="175" x2="350" y2="205" stroke="#000" stroke-width="1.2" marker-end="url(#arr)"/>
  <text x="360" y="195" text-anchor="start" font-size="11" font-weight="bold" font-family="Consolas, monospace">YES</text>

  <rect x="200" y="205" width="300" height="55" fill="#fff" stroke="#000" stroke-width="1.2"/>
  <text x="350" y="220" text-anchor="middle" font-size="11" font-weight="bold" font-family="Consolas, monospace">STAGE 2: Candidate Vocabulary Rank</text>
  <text x="350" y="235" text-anchor="middle" font-size="11" font-family="Consolas, monospace">Score image vs RAG in-memory seed</text>
  <text x="350" y="250" text-anchor="middle" font-size="11" font-family="Consolas, monospace">Filter candidates &lt; 20% top score</text>

  <line x1="350" y1="260" x2="350" y2="290" stroke="#000" stroke-width="1.2" marker-end="url(#arr)"/>

  <rect x="200" y="290" width="300" height="70" fill="#fff" stroke="#000" stroke-width="1.2"/>
  <text x="350" y="305" text-anchor="middle" font-size="11" font-weight="bold" font-family="Consolas, monospace">STAGE 3: Multimodal Generation</text>
  <text x="350" y="320" text-anchor="middle" font-size="11" font-family="Consolas, monospace">Preprocess: Downscale to max 512px</text>
  <text x="350" y="335" text-anchor="middle" font-size="11" font-family="Consolas, monospace">Primary: Ollama llava-phi3 (2.9GB)</text>
  <text x="350" y="350" text-anchor="middle" font-size="11" font-family="Consolas, monospace">Fallback: Moondream2 (1.8B / 3GB)</text>
  <text x="350" y="365" text-anchor="middle" font-size="11" font-family="Consolas, monospace">Output: Pipe-Delimited via SSE</text>

  <line x1="350" y1="360" x2="350" y2="390" stroke="#000" stroke-width="1.2" marker-end="url(#arr)"/>

  <rect x="200" y="390" width="300" height="70" fill="#fff" stroke="#000" stroke-width="1.2"/>
  <text x="350" y="405" text-anchor="middle" font-size="11" font-weight="bold" font-family="Consolas, monospace">STAGE 4: RAG Database Correction</text>
  <text x="350" y="420" text-anchor="middle" font-size="11" font-family="Consolas, monospace">SQL: iLIKE '%name%' on base_foods</text>
  <text x="350" y="435" text-anchor="middle" font-size="11" font-family="Consolas, monospace">Overwrite approximated macros</text>
  <text x="350" y="450" text-anchor="middle" font-size="11" font-family="Consolas, monospace">Retain MLLM estimated micros</text>

  <line x1="350" y1="460" x2="350" y2="490" stroke="#000" stroke-width="1.2" marker-end="url(#arr)"/>

  <text x="350" y="505" text-anchor="middle" font-size="11" font-family="Consolas, monospace">[ Verified Nutrition JSON ]</text>
</svg>'''

html = re.sub(r'<svg.*?</svg>', svg3, html, count=1, flags=re.DOTALL)

svg4 = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 370" width="600" height="370">
  <defs><marker id="arr" markerWidth="7" markerHeight="7" refX="5" refY="3.5" orient="auto"><polygon points="0 0,7 3.5,0 7" fill="#000"/></marker></defs>

  <text x="300" y="20" text-anchor="middle" font-size="11" font-family="Consolas, monospace">[ LLM Generative Output: "Chicken Biryani|420|18|62..." ]</text>
  
  <line x1="300" y1="30" x2="300" y2="60" stroke="#000" stroke-width="1.2" marker-end="url(#arr)"/>

  <rect x="100" y="60" width="400" height="40" fill="#fff" stroke="#000" stroke-width="1.2"/>
  <text x="300" y="75" text-anchor="middle" font-size="11" font-weight="bold" font-family="Consolas, monospace">Execute SQL: iLIKE '%Chicken Biryani%'</text>
  <text x="300" y="90" text-anchor="middle" font-size="11" font-family="Consolas, monospace">Target: Supabase base_foods table (176 KB seed)</text>

  <line x1="300" y1="100" x2="300" y2="130" stroke="#000" stroke-width="1.2" marker-end="url(#arr)"/>

  <rect x="200" y="130" width="200" height="30" fill="#fff" stroke="#000" stroke-width="1.2"/>
  <text x="300" y="150" text-anchor="middle" font-size="11" font-weight="bold" font-family="Consolas, monospace">Match Found in RAG DB?</text>

  <line x1="220" y1="160" x2="220" y2="190" stroke="#000" stroke-width="1.2" marker-end="url(#arr)"/>
  <text x="210" y="180" text-anchor="end" font-size="11" font-weight="bold" font-family="Consolas, monospace">YES</text>

  <line x1="380" y1="160" x2="380" y2="190" stroke="#000" stroke-width="1.2" marker-end="url(#arr)"/>
  <text x="390" y="180" text-anchor="start" font-size="11" font-weight="bold" font-family="Consolas, monospace">NO</text>

  <rect x="50" y="190" width="240" height="100" fill="#fff" stroke="#000" stroke-width="1.2"/>
  <text x="170" y="205" text-anchor="middle" font-size="11" font-weight="bold" font-family="Consolas, monospace">AUTHORITATIVE OVERWRITE</text>
  <text x="170" y="220" text-anchor="middle" font-size="11" font-family="Consolas, monospace">- Replace Cal, Pro, Carb,</text>
  <text x="170" y="235" text-anchor="middle" font-size="11" font-family="Consolas, monospace">  Fat, Fiber, Sugar, Sod,</text>
  <text x="170" y="250" text-anchor="middle" font-size="11" font-family="Consolas, monospace">  Chol with DB values</text>
  <text x="170" y="265" text-anchor="middle" font-size="11" font-family="Consolas, monospace">- Tag Source:</text>
  <text x="170" y="280" text-anchor="middle" font-size="11" font-family="Consolas, monospace">  "Supabase RAG DB"</text>

  <rect x="310" y="190" width="240" height="100" fill="#fff" stroke="#000" stroke-width="1.2"/>
  <text x="430" y="205" text-anchor="middle" font-size="11" font-weight="bold" font-family="Consolas, monospace">RETAIN AI ESTIMATION</text>
  <text x="430" y="220" text-anchor="middle" font-size="11" font-family="Consolas, monospace">- Keep LLM estimated macros</text>
  <text x="430" y="235" text-anchor="middle" font-size="11" font-family="Consolas, monospace">  and micros</text>
  <text x="430" y="250" text-anchor="middle" font-size="11" font-family="Consolas, monospace">- Tag Source:</text>
  <text x="430" y="265" text-anchor="middle" font-size="11" font-family="Consolas, monospace">  "MLLM Estimation"</text>

  <line x1="170" y1="290" x2="170" y2="320" stroke="#000" stroke-width="1.2"/>
  <line x1="430" y1="290" x2="430" y2="320" stroke="#000" stroke-width="1.2"/>
  <line x1="170" y1="320" x2="430" y2="320" stroke="#000" stroke-width="1.2"/>
  <line x1="300" y1="320" x2="300" y2="350" stroke="#000" stroke-width="1.2" marker-end="url(#arr)"/>
</svg>'''

html = re.sub(r'<svg.*?</svg>', svg4, html, count=1, flags=re.DOTALL)

svg5 = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 240" width="600" height="240">
  <defs><marker id="arr" markerWidth="7" markerHeight="7" refX="5" refY="3.5" orient="auto"><polygon points="0 0,7 3.5,0 7" fill="#000"/></marker></defs>

  <rect x="20" y="20" width="160" height="180" fill="#fff" stroke="#000" stroke-width="1.2"/>
  <text x="100" y="40" text-anchor="middle" font-size="11" font-weight="bold" font-family="Consolas, monospace">BROWSER</text>
  <text x="100" y="55" text-anchor="middle" font-size="11" font-family="Consolas, monospace">(PWA Client)</text>

  <text x="100" y="90" text-anchor="middle" font-size="11" font-family="Consolas, monospace">POST /api/ai/analyze</text>
  <text x="100" y="105" text-anchor="middle" font-size="11" font-family="Consolas, monospace">/stream</text>

  <text x="100" y="160" text-anchor="middle" font-size="11" font-family="Consolas, monospace">Receive final JSON</text>
  <text x="100" y="175" text-anchor="middle" font-size="11" font-family="Consolas, monospace">Render UI result</text>

  <rect x="220" y="20" width="180" height="180" fill="#fff" stroke="#000" stroke-width="1.2"/>
  <text x="310" y="40" text-anchor="middle" font-size="11" font-weight="bold" font-family="Consolas, monospace">FLASK API (Port 5000)</text>

  <text x="310" y="90" text-anchor="middle" font-size="11" font-family="Consolas, monospace">Open SSE connection</text>
  <text x="310" y="105" text-anchor="middle" font-size="11" font-family="Consolas, monospace">Emit heartbeat (5s)</text>

  <text x="310" y="160" text-anchor="middle" font-size="11" font-family="Consolas, monospace">Push enriched JSON</text>
  <text x="310" y="175" text-anchor="middle" font-size="11" font-family="Consolas, monospace">data: {...}</text>

  <rect x="440" y="20" width="140" height="180" fill="#fff" stroke="#000" stroke-width="1.2"/>
  <text x="510" y="40" text-anchor="middle" font-size="11" font-weight="bold" font-family="Consolas, monospace">LLM DAEMON</text>
  <text x="510" y="55" text-anchor="middle" font-size="11" font-family="Consolas, monospace">(Port 5002)</text>

  <text x="510" y="90" text-anchor="middle" font-size="11" font-family="Consolas, monospace">Stages 1 &amp; 2</text>
  <text x="510" y="105" text-anchor="middle" font-size="11" font-family="Consolas, monospace">SigLIP</text>

  <text x="510" y="140" text-anchor="middle" font-size="11" font-family="Consolas, monospace">Stage 3 (MLLM)</text>
  <text x="510" y="155" text-anchor="middle" font-size="11" font-family="Consolas, monospace">Stage 4 (RAG)</text>

  <line x1="180" y1="85" x2="220" y2="85" stroke="#000" stroke-width="1.2" marker-end="url(#arr)"/>
  <line x1="400" y1="85" x2="440" y2="85" stroke="#000" stroke-width="1.2" marker-end="url(#arr)"/>

  <line x1="440" y1="155" x2="400" y2="155" stroke="#000" stroke-width="1.2" marker-end="url(#arr)"/>
  <line x1="220" y1="155" x2="180" y2="155" stroke="#000" stroke-width="1.2" marker-end="url(#arr)"/>

  <line x1="220" y1="110" x2="180" y2="110" stroke="#000" stroke-width="1.2" stroke-dasharray="4,2" marker-end="url(#arr)"/>
  <text x="200" y="105" text-anchor="middle" font-size="9" font-family="Consolas, monospace">heartbeat</text>

</svg>'''

html = re.sub(r'<svg.*?</svg>', svg5, html, count=1, flags=re.DOTALL)

with open(r'c:\Users\pc\OneDrive\Desktop\nutritrack\paper.html', 'w', encoding='utf-8') as f:
    f.write(html)
