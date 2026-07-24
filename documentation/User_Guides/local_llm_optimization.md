# APEX Account Planner: Local LLM Optimization Guide (8GB & 16GB RAM)

> [!WARNING]
> **Optional / Historical Configuration:** This guide applies only when running APEX in local-inference mode (e.g. using Ollama). By default, the running system is configured to route prompts to the Google Gemini Cloud API for optimal speed and reasoning capability. Use this guide if you are deploying in a strict zero-data-egress network environment that requires fully offline execution.

Running advanced multi-agent workflows locally requires careful resource management. Since CPU/RAM architectures (particularly on 8GB and 16GB devices) experience slow pre-fill times and low token generation speeds (1–15 tokens/sec), this guide details how to optimize the LLM server and the APEX application layer.

---

## 1. Model Selection & Quantization Strategy

For local execution, **quantization** is key. A quantized model compresses weight values (e.g., from 16-bit to 4-bit) which drastically lowers the RAM footprint and speeds up processing times.

| Device RAM | Recommended Models | Quantization Profile | RAM Usage | Notes |
| :--- | :--- | :--- | :--- | :--- |
| **8 GB RAM** | 1. **Llama-3.2-3B-Instruct**<br>2. **Qwen-2.5-3B-Instruct**<br>3. **Qwen-2.5-1.5B-Instruct** | `Q4_K_M` (4-bit medium)<br>`Q4_K_M` (4-bit medium)<br>`Q8_0` (8-bit high quality) | ~2.2 GB<br>~2.2 GB<br>~1.8 GB | Best balance between speed and reasoning. 1.5B Q8 handles structure extremely well. |
| **16 GB RAM** | 1. **Llama-3-8B-Instruct**<br>2. **Qwen-2.5-7B-Instruct**<br>3. **Mistral-7B-Instruct-v0.3** | `Q4_K_M` (4-bit medium)<br>`Q4_K_M` (4-bit medium)<br>`Q4_K_M` (4-bit medium) | ~4.8 GB<br>~4.8 GB<br>~4.6 GB | Superior reasoning capability. Perfect for multi-agent synthesis. |

*Note: Avoid running unquantized FP16 or FP32 models on consumer hardware. Always append `:latest` or use explicit tags (e.g., `llama3.2:3b-instruct-q4_K_M`) when pulling models via Ollama.*

---

## 2. Ollama Server Engine Optimizations

Configure Ollama's execution behavior to prevent it from overwhelming your hardware. Set these system environment variables before starting Ollama:

### Environment Variables
*   **`OLLAMA_NUM_PARALLEL=1`**
    *   *Why*: Forces Ollama to queue requests and process them sequentially instead of trying to generate text for multiple agents concurrently. This prevents CPU cores/RAM from hitting 100% saturation.
*   **`OLLAMA_MAX_LOADED_MODELS=1`**
    *   *Why*: Prevents Ollama from keeping multiple models active in memory. It locks all available RAM context for the active reasoning model.
*   **`OLLAMA_MAX_QUEUE=5`**
    *   *Why*: Drops excessive background requests to prevent memory leakages.

### Customizing Context Size (`num_ctx`)
The default context window size (usually 2048 or 8192) significantly slows down CPU pre-fill times. For the Account Planner, the context window is kept small by the `data_retrieval_layer`. Customize your model's parameters using an Ollama `Modelfile`:

1. Create a file named `Modelfile` containing:
   ```dockerfile
   FROM llama3.2:latest
   # Limit context window to 2048 tokens to speed up CPU pre-fill calculations
   PARAMETER num_ctx 2048
   # Prevent long hallucination chains
   PARAMETER num_predict 512
   PARAMETER temperature 0.0
   ```
2. Build the optimized model:
   ```bash
   ollama create apex-llama -f ./Modelfile
   ```
3. Update your `.env` file to use the new model:
   ```env
   MODEL_NAME=apex-llama
   ```

---

## 3. Application Layer Code Optimizations

### A. Context Pruning (Already in APEX Data retrieval)
Keep the payload small. The system utilizes `summarize_large_dataset()` to filter opportunities down to the top 5 largest deals if the record size exceeds 5.
*   **Goal**: Keep prompts under 800 tokens.
*   **Math**: Pre-fill processing time scales quadratically. Reducing the prompt from 2000 to 500 tokens speeds up the first token response time by **16x** on CPU!

### B. Output Streaming (SSE)
Always stream narrative responses token-by-token using FastAPI's `StreamingResponse` rather than waiting for the complete generation loop to finish:
*   **Benefit**: The frontend client receives feedback instantly, keeping the network connection active and bypassing HTTP timeout limits (which are usually set to 30 or 60 seconds).

### C. Structural Optimization
Because local LLMs struggle with multi-character indentation formatting, use the following directives:
*   Enforce **raw, compact JSON outputs** (e.g., `stream=False` for reasoning packages, with temperature set to `0`).
*   Add prompt filters to reject redundant text wrappers (e.g., `"Respond with raw JSON only. Do not wrap in markdown block code blocks."`).
