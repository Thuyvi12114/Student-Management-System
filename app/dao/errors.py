"""Lỗi phát sinh ở tầng truy cập dữ liệu."""


class DataAccessError(RuntimeError):
    """Kết nối, câu lệnh SQL hoặc ràng buộc dữ liệu gặp lỗi."""


class DuplicateRecordError(DataAccessError):
    """Bản ghi vi phạm ràng buộc UNIQUE."""
