# Model Profiles và Reranking

Cập nhật: 19/09/2026; bổ sung provider tùy chọn ngày 27/09/2026. DeepSeek là cấu hình hỏi đáp mặc định; embedding mặc định Gemini. Học viên dùng API key tự mua và có thể chọn provider tùy chọn tại [mục dưới](#provider-tuy-chon). Chất lượng AI cần được kiểm chứng AEV trên corpus sử dụng.

<a id="api-key-do-hoc-vien-tu-mua"></a>

## API key do học viên tự mua

- Học viên tự mua hoặc tạo API key cho provider đã chọn (DeepSeek mặc định, hoặc provider tùy chọn bên dưới) và tự chịu chi phí.
- Đặt spending limit hoặc hạn mức ngân sách trên tài khoản provider trước khi chạy `RAG_MODE=real`.
- Chỉ giữ key trong `.env` tại máy; không commit, không gửi trong chat, không dán key vào Claude hay công cụ AI khác. Nếu lộ key, thu hồi và tạo key mới.
- Chỉ gửi corpus giả và dữ liệu thử tới provider.

## Một file `.env`

Tạo `.env` từ `.env.example` một lần. Chỉ ba biến cần cấu hình để chạy AI thật:

```env
RAG_MODE=real
DEEPSEEK_API_KEY=<key DeepSeek>
GEMINI_API_KEY=<key Gemini>
```

`RAG_MODE=fixture` chạy hoàn toàn offline, kể cả khi đã điền key. `RAG_MODE=real` mặc định chọn DeepSeek cho generation, Gemini cho embedding và tắt reranker. Thiếu key sẽ dừng startup, không tự chuyển sang fixture.

| Cấu hình | Mặc định trong code | Biến override nếu cần |
| --- | --- | --- |
| Chat model | `deepseek-flash` | `DEEPSEEK_CHAT_MODEL` |
| DeepSeek endpoint | `https://api.deepseek.com` | `DEEPSEEK_BASE_URL` |
| Embedding model | `gemini-embedding-2` | `GEMINI_EMBEDDING_MODEL` |
| Embedding dimension | 1024 | `EMBEDDING_DIM` |
| Reranker | Tắt | `RERANKER_PROVIDER` |
| Cổng API/Web | 8107 / 3107 | `API_PORT` / `WEB_PORT` |

Adapter DeepSeek dùng `/chat/completions`, JSON output, `max_tokens` và tắt thinking cho luồng trả lời ngắn có nguồn. Chỉ nhận completion kết thúc bằng `stop`; output rỗng, bị cắt, sai JSON hoặc citation không hợp lệ bị từ chối. Không đưa reasoning content vào câu trả lời. Endpoint, model và tham số được đối chiếu với [DeepSeek API](https://api-docs.deepseek.com/) và [Chat Completion](https://api-docs.deepseek.com/api/create-chat-completion/) ngày 19/09/2026. Chọn model mặc định chưa phải kết quả đánh giá chất lượng hoặc chi phí.

Các giới hạn và tham số tuning nằm trong [Settings](../api/app/core/config.py); không phải điền lại trong `.env`. Compose chuyển biến override vào API, giá trị rỗng dùng mặc định của Settings. Biến đặt trong shell có thể ghi đè giá trị ở env file theo cơ chế Compose, nên kiểm `/system/profile` sau mỗi lần áp dụng cấu hình.

## Dữ liệu và profile thực thi

| Profile tự sinh | Embedding | Generation | Reranker |
| --- | --- | --- | --- |
| `fixture-offline` | Fixture | Fixture | Không |
| `classroom-deepseek-gemini` | Gemini | DeepSeek | Không |
| `classroom-deepseek-gemini-local-reranker` | Gemini | DeepSeek | TEI local |
| `classroom-deepseek-gemini-cohere` | Gemini | DeepSeek | Cohere |

Nội dung tài liệu và câu hỏi dùng tạo embedding được gửi tới Gemini. Câu hỏi và các đoạn nguồn được chọn được gửi tới DeepSeek để trả lời. Khi bật Cohere, câu hỏi và candidate chunks còn được gửi tới Cohere để rerank. UI hiển thị thông tin này qua runtime profile. Chỉ dùng dữ liệu thực hành được phép gửi tới các provider đã chọn.

Các adapter Gemini generation, OpenAI-compatible, Anthropic, Voyage và Ollama vẫn được giữ cho bài học mở rộng. Chúng không yêu cầu key khi không được chọn. Muốn sử dụng, khai báo tường minh `LLM_PROVIDER`/`EMBEDDING_PROVIDER` cùng key, model và endpoint tương ứng; profile tự sinh là `custom` khi ngoài cấu hình lớp. `LLM_MODEL` và `EMBEDDING_MODEL` là override chung có ưu tiên cao hơn model riêng từng provider, chỉ dùng khi có chủ đích.

<a id="provider-tuy-chon"></a>

## Provider tùy chọn thay cho DeepSeek

Học viên chọn DeepSeek (mặc định) hoặc một phương án dưới đây, tùy tài khoản và ngân sách của mình (quyết định D12). Ghi provider đã chọn vào evidence; áp dụng cùng quy tắc key ở mục [API key do học viên tự mua](#api-key-do-hoc-vien-tu-mua) và chỉ dùng dữ liệu giả lập.

Các profile dưới đây chỉ đổi **generation**, giữ Gemini embedding nên embedding identity không đổi và **không cần ingest lại**. Chỉ dùng adapter đã có trong [`llm.py`](../api/app/services/llm.py); không cần sửa code. Thêm biến vào chính `.env`, áp dụng lại Compose rồi kiểm `/system/profile`.

| Phương án | Biến trong `.env` | Profile tự sinh | Dữ liệu gửi ra ngoài |
| --- | --- | --- | --- |
| A. Gemini cho cả hai (ít key nhất) | `LLM_PROVIDER=gemini`; `GEMINI_CHAT_MODEL` tùy chọn (mặc định `gemini-3.1-flash-lite`) | `classroom-gemini` | Chỉ Google Gemini |
| B. Anthropic API | `LLM_PROVIDER=anthropic`, `ANTHROPIC_API_KEY`, `ANTHROPIC_CHAT_MODEL` (bắt buộc, không có mặc định) | `custom` | Gemini (embedding), Anthropic (câu hỏi và đoạn nguồn) |
| C. Gateway OpenAI-compatible do học viên chọn | `LLM_PROVIDER=openai`, `OPENAI_API_KEY`, `OPENAI_BASE_URL` (bắt buộc), `OPENAI_CHAT_MODEL` | `custom` | Gemini và gateway đã chọn |
| D. Ollama local | `LLM_PROVIDER=ollama`, `OLLAMA_CHAT_MODEL`; `OLLAMA_BASE_URL` mặc định `http://ollama:11434` (profile `ollama`) hoặc `http://host.docker.internal:11434` (Ollama cài trên máy) | `custom` | Chỉ Gemini (embedding) |

Ví dụ phương án A:

```env
RAG_MODE=real
LLM_PROVIDER=gemini
GEMINI_API_KEY=<key Gemini>
```

Ví dụ phương án B:

```env
RAG_MODE=real
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=<key Anthropic API>
ANTHROPIC_CHAT_MODEL=<model id Anthropic học viên chọn>
GEMINI_API_KEY=<key Gemini>
```

Lưu ý:

- `DEEPSEEK_API_KEY` không cần khi `LLM_PROVIDER` khác `deepseek`.
- Key Anthropic API tính phí riêng, không phải tài khoản Claude Pro/Max dùng cho Claude.ai/Claude Code.
- Gateway phương án C phải hỗ trợ `/chat/completions`, `response_format` JSON và `max_completion_tokens`; kiểm bằng AEV trước khi dùng cho bài làm.
- Muốn chạy hoàn toàn offline, thêm `EMBEDDING_PROVIDER=ollama` (chỉ hỗ trợ `mxbai-embed-large`, `EMBEDDING_DIM=1024`). Cách này đổi embedding identity nên phải ingest lại trong Compose project riêng; evidence gate `RETRIEVAL_MIN_SIMILARITY` về -1 và cần hiệu chỉnh bằng AEV. Máy cần đủ RAM/CPU cho model local.
- Đổi generation provider là thay đổi cấu hình AI: chạy lại `python3 scripts/run_aev.py`, ghi provider, model, prompt version và kết quả vào evidence. Không so sánh trực tiếp kết quả AEV giữa các provider khi chưa review từng claim.

## Reranker tùy chọn

Chỉ bật sau khi đo baseline. Không có file env riêng; thêm biến vào chính `.env` hiện tại.

**Local TEI:**

```env
RERANKER_PROVIDER=local
LOCAL_RERANKER_URL=http://host.docker.internal:8187
```

```sh
make reranker-local-up
docker compose --env-file .env -p insighthub-c07-starter up --build -d --wait
```

TEI dùng `Alibaba-NLP/gte-multilingual-reranker-base`, tải model ở lần chạy đầu. Cần thêm disk, RAM và thời gian download. Script chọn image CPU theo kiến trúc máy. Endpoint local bị giới hạn vào `localhost`, `127.0.0.1`, `host.docker.internal` hoặc service `reranker`. Dừng TEI bằng `make reranker-local-down`.

**Cohere:**

```env
RERANKER_PROVIDER=cohere
COHERE_API_KEY=<key Cohere>
```

Áp dụng lại Compose. Adapter dùng model mặc định `rerank-v4.0-fast`; `COHERE_RERANKER_MODEL` chỉ cần đặt khi đổi model. Key Cohere không cần cho cấu hình mặc định.

Bật/tắt reranker hoặc đổi chat model không đổi embedding identity. Thay embedding provider, model, dimension, endpoint hoặc revision cần ingest lại tài liệu trong không gian vector tương ứng. Không xóa volume để né kiểm tra identity.

## Kiểm chứng và tuning

1. Chạy fixture để kiểm setup và regression.
2. Điền hai key, đổi `RAG_MODE=real`, áp dụng lại Compose và kiểm `/system/profile`.
3. Chạy `python3 scripts/run_aev.py --api-url http://127.0.0.1:8107` trên corpus mẫu.
4. Đọc câu trả lời và đoạn nguồn của từng claim, kiểm `NoEvidence`, injection, citation, latency và token. Runner tự động không thay thế review grounding.
5. Chỉ thay một nhóm biến mỗi lần, ghi model, corpus hash, prompt version và kết quả đánh giá.

| Biến tuning | Vai trò | Mặc định |
| --- | --- | --- |
| `RETRIEVAL_CANDIDATE_K` | Số candidate lấy từ pgvector | 20 |
| `RETRIEVAL_TOP_K` | Số chunk tối đa đưa vào context | 5 |
| `RETRIEVAL_MIN_SIMILARITY` | Evidence gate trước generation | 0,20 với Gemini embedding real; -1 với fixture |
| `RERANKER_TOP_N` | Số kết quả giữ sau rerank | 5 |
| `RETRIEVAL_MAX_CHUNKS_PER_DOCUMENT` | Giới hạn chunk trên một tài liệu | 3 |
| `CONTEXT_MAX_TOKENS` | Ngân sách context ước lượng | 4000 |

Threshold 0,20 chưa được hiệu chỉnh bằng real AEV của lớp. Không hạ threshold chỉ để tăng tỷ lệ `Answered`. Provider lỗi, timeout hoặc response sai contract là lỗi kỹ thuật; không fallback sang fixture hoặc tự tắt reranker. Fixture không chứng minh chất lượng semantic.

<a id="fallback-usage"></a>

## Retry, provider dự phòng và usage (IH-AI-005)

Starter chỉ cấp phần chung; fallback là việc của học viên ở LR-18. **Không sửa `validate_configuration` trong `config.py`** khi làm phần này: hàm là baseline của phần legacy trong ASG01 ở M5. Cấu hình của provider dự phòng đặt trong module hoặc file cấu hình riêng của bài làm.

| Phần | Starter có sẵn | Học viên làm |
| --- | --- | --- |
| Retry có giới hạn | `providers.post_json` retry với timeout, 429, 502, 503, 504, lỗi kết nối, nằm trong deadline còn lại; số lần theo `PROVIDER_RETRY_ATTEMPTS` (mặc định 3) | Không đổi; ghi số lần thử vào usage |
| Provider dự phòng | Chưa có. Profile real vẫn không fallback ngầm | Gọi provider dự phòng đã cấu hình khi provider chính hết retry với lỗi khả dụng; không fallback sang fixture; kết quả qua cùng bước kiểm schema, grounding, citation. Lỗi sai schema hoặc thiếu căn cứ không kích hoạt fallback |
| Usage | `llm.generate` trả `usage` (token vào, ra); `ai_jobs.record_usage` lưu từng lời gọi | Ghi provider, model, `prompt_version`, token, latency, `finish_reason`, chi phí ước tính, `fallback` cho mỗi lời gọi, kể cả lời gọi lỗi |
| Trần token | `LLM_MAX_TOKENS` (mặc định 1024) gửi tới provider | Đầu ra có `finish_reason` báo chạm trần không lưu là `Succeeded` |
| Kiểm thử | `app/core/fault_injection.py`: `inject_provider_faults` trong test, `AI_FIXTURE_FAULTS=deepseek:timeout` khi chạy thủ công ở fixture | Test fallback và ghi usage bằng giả lập, không gọi dịch vụ trả phí |

Provider dự phòng là luồng dữ liệu ra ngoài thứ hai: cập nhật threat model, AI-BOM và AI Usage Charter. Chi tiết cơ chế job tại [AI Job Framework](AI_Job_Framework.md).
