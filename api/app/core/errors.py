"""Public errors contain fixed messages, never provider bodies or credentials."""


class ServiceError(Exception):
    """Lỗi công khai theo envelope chung (SRS mục 3.3.1): code ổn định, message an toàn,
    request_id, fields[] cho lỗi theo trường và retry_after_seconds khi bị giới hạn."""

    status_code = 500
    code = "internal_error"
    message = "Không thể xử lý yêu cầu."

    def __init__(
        self,
        message: str | None = None,
        *,
        fields: list[dict] | None = None,
        retry_after_seconds: int | None = None,
    ):
        if message is not None:
            self.message = message
        # fields: [{"field": "source_ids", "code": "duplicate"}]. Chỉ mã, không chép dữ liệu người dùng.
        self.fields = list(fields or [])
        self.retry_after_seconds = retry_after_seconds
        super().__init__(self.message)


class ProviderError(ServiceError):
    status_code = 502
    code = "provider_error"
    message = "Dịch vụ AI không khả dụng hoặc trả dữ liệu không hợp lệ."


class ProviderTimeout(ProviderError):
    status_code = 504
    code = "provider_timeout"
    message = "Dịch vụ AI không phản hồi trong thời gian cho phép."


class ProviderRateLimited(ProviderError):
    status_code = 503
    code = "provider_rate_limited"
    message = "Dịch vụ AI đang giới hạn lưu lượng. Hãy thử lại sau."


class InvalidDocument(ServiceError):
    status_code = 422
    code = "invalid_document"
    message = "Tài liệu trống, không hợp lệ hoặc không có nội dung văn bản."


class DocumentNotFound(ServiceError):
    status_code = 404
    code = "document_not_found"
    message = "Không tìm thấy tài liệu."


class DocumentConflict(ServiceError):
    status_code = 409
    code = "document_conflict"
    message = "Document ID đã gắn với nội dung hoặc cấu hình xử lý khác."


class IndexIdentityConflict(ServiceError):
    status_code = 409
    code = "index_identity_conflict"
    message = (
        "Embedding identity không khớp index. Cần rebuild index bằng cấu hình đã chọn."
    )


class SchemaMismatch(ServiceError):
    status_code = 503
    code = "schema_mismatch"
    message = "Schema chưa sẵn sàng hoặc dimension không khớp EMBEDDING_DIM."


class IdempotencyKeyRequired(ServiceError):
    status_code = 400
    code = "idempotency_key_required"
    message = "Thiếu Idempotency-Key hợp lệ."


class IdempotencyConflict(ServiceError):
    status_code = 409
    code = "idempotency_conflict"
    message = "Idempotency-Key đã được dùng cho payload khác."


class OperationInProgress(ServiceError):
    status_code = 409
    code = "operation_in_progress"
    message = "Operation đang được xử lý."


class OperationNotFound(ServiceError):
    status_code = 404
    code = "operation_not_found"
    message = "Không tìm thấy operation còn hiệu lực."


class DeadlineExceeded(ServiceError):
    status_code = 504
    code = "deadline_exceeded"
    message = "Operation vượt quá thời gian xử lý cho phép."


class CitationValidationError(ServiceError):
    status_code = 502
    code = "citation_validation_failed"
    message = "Câu trả lời có citation không hợp lệ."


class SourceSetInvalid(ServiceError):
    status_code = 422
    code = "source_set_invalid"
    message = "Danh sách tài liệu nguồn không hợp lệ hoặc chưa sẵn sàng."


class MailDeliveryError(ServiceError):
    status_code = 502
    code = "mail_delivery_error"
    message = "Không gửi được email. Hãy thử lại sau."


class NotAuthenticated(ServiceError):
    status_code = 401
    code = "not_authenticated"
    message = "Phiên đăng nhập không hợp lệ hoặc đã hết hạn. Hãy đăng nhập lại."


class RequestInvalid(ServiceError):
    status_code = 422
    code = "validation_error"
    message = "Dữ liệu yêu cầu không hợp lệ."


class AiJobRunning(ServiceError):
    """LIM-10: mỗi người dùng tối đa 1 tác vụ AI đang chạy (tính chung hỏi đáp và công cụ)."""
    status_code = 429
    code = "ai_job_running"
    message = "Bạn đang có một tác vụ AI chưa hoàn tất. Hãy chờ tác vụ đó kết thúc rồi thử lại."


class AiRateLimited(ServiceError):
    """LIM-10: tối đa 10 yêu cầu AI mới trong 60 giây."""
    status_code = 429
    code = "ai_rate_limited"
    message = "Bạn đã gửi quá nhiều yêu cầu AI. Hãy thử lại sau."


class AiJobNotFound(ServiceError):
    """Dùng chung cho không tồn tại và không có quyền, để không tiết lộ tác vụ của người khác."""
    status_code = 404
    code = "ai_job_not_found"
    message = "Không tìm thấy tác vụ AI."


class PublishBlocked(ServiceError):
    """BR-08, BR-09: điều kiện công bố không còn (nguồn, Notebook hoặc hội thoại đích đã bị xóa)."""
    status_code = 409
    code = "publish_blocked"
    message = "Kết quả không được lưu vì nguồn hoặc nơi lưu kết quả không còn khả dụng."
