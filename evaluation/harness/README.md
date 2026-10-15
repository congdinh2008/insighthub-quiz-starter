# Eval harness (Kit K9)

Skeleton cho **eval-driven development** ở M4 (LR-23, C02-U05-T04): golden set có version, grader bằng code, pass^k, báo cáo có commit và hash nguồn. Starter cấp khung và adapter Chat; học viên viết case, adapter Summary/Quiz và grader bổ sung.

| File | Vai trò | Ai hoàn thiện |
| --- | --- | --- |
| `suites/*.json` | Golden set: nguồn, input, cấu hình, `expected_status`, 3-5 `expected_points`, `forbidden`, `repeat` | Học viên (12 lượt nội dung theo LR-23) |
| `adapters.py` | Gọi API và chuẩn hóa output. `ChatAdapter` chạy được với Starter | Học viên viết `SummaryAdapter`, `QuizAdapter` |
| `graders.py` | Grader bằng code: status, citation trong phạm vi, claim trỏ citation, độ dài Summary, cấu trúc Quiz, gợi ý từ khóa | Học viên bổ sung grader theo schema của mình |
| `passk.py` | pass^k (mọi lượt đạt) và pass@k | Starter |
| `run_eval.py` | Chạy live, replay, validate; ghi `reports/evaluation/harness-*.json` | Starter |

## Lệnh

```sh
python3 evaluation/harness/run_eval.py --suite evaluation/harness/suites/<suite>.json --validate
make eval SUITE=evaluation/harness/suites/<suite>.json K=2        # cần RAG_MODE=real
python3 evaluation/harness/run_eval.py --replay reports/evaluation/harness-<time>.json   # chấm lại, không gọi API
```

Sau khi thêm Auth, đặt session cookie của tài khoản test A trong shell: `export INSIGHTHUB_EVAL_COOKIE='<tên>=<giá trị>'`. Harness gửi cookie khi gọi API, không ghi vào report.

## Nguyên tắc

- Cố định nguồn, input và `expected_points` **trước** khi chạy; sửa expected thì tăng `version` của suite và ghi lý do.
- Grader bằng code chỉ kiểm phần máy kiểm được. Report luôn có `semantic_review: pending`; người kiểm đối chiếu từng claim, câu hỏi, lựa chọn, đáp án, giải thích với nguồn và ghi verdict vào report đã review. Không dùng LLM-as-judge làm căn cứ duy nhất.
- Lượt lặp báo pass^k (k = 2: đạt khi cả hai lần đạt). Giữ mọi lượt, kể cả lượt lỗi.
- Fixture chỉ kiểm pipeline (`--allow-fixture`), không phải evidence chất lượng nội dung.
- Replay dùng được trong CI để chống regression của grader và parser trên output đã ghi.
