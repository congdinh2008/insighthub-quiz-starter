# ADR-002 - Lưu source provenance trong PostgreSQL

- Status: Accepted
- Date: 19/09/2026

Starter local lưu original bytes, extracted text, segment và locator trong PostgreSQL. Cách này tạo một transaction boundary rõ cho tài liệu nhỏ tối đa 10 MiB và đủ để học viên quan sát. Production extension có thể chuyển object bytes sang object storage nhưng phải giữ checksum, lifecycle và liên kết segment tương đương.
