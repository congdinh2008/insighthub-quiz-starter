# Quy trình yêu cầu thay đổi sản phẩm

Dữ liệu giả lập. Mỗi yêu cầu thay đổi phải nêu vấn đề người dùng, hành vi mong muốn, tiêu chí chấp nhận và phạm vi không thực hiện.

Developer làm rõ tình huống lỗi trước khi viết code, cập nhật API contract nếu có thay đổi và đính kèm kết quả kiểm thử khi gửi review. Người review kiểm tra tính đúng đắn, tương thích và xử lý dữ liệu nhạy cảm.

Một bản phát hành cần có danh sách thay đổi, hướng dẫn migration dữ liệu và các giới hạn đã biết. Lỗi nghiêm trọng được tái hiện bằng regression test trước khi sửa.
