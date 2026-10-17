"""DTO amplop error API (design-api §18).

Seluruh response error aplikasi memakai satu bentuk:

```json
{
  "error": {
    "code": "AUTHENTICATION_FAILED",
    "message": "Autentikasi gagal.",
    "details": []
  }
}
```

Schema di modul ini dipakai untuk **mendokumentasikan** bentuk tersebut pada
OpenAPI (``responses={...: {"model": ErrorResponse}}``) dan untuk memberi contoh
yang dapat dijalankan dari Swagger UI. Response error sebenarnya dibangun oleh
``src.middlewares.error_handlers`` sebagai ``JSONResponse``, sehingga schema ini
tidak menambah validasi pada jalur error dan tetap bebas SQLAlchemy.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["ErrorDetail", "ErrorEnvelope", "ErrorResponse"]


class ErrorDetail(BaseModel):
    """Satu item pada ``error.details`` (mis. kesalahan validasi per field)."""

    field: str = Field(
        description="Lokasi nilai yang bermasalah, contoh: ``password``.",
        examples=["password"],
    )
    message: str = Field(
        description="Penjelasan yang aman ditampilkan ke pengguna.",
        examples=["Field required"],
    )


class ErrorEnvelope(BaseModel):
    """Isi objek ``error`` pada response gagal."""

    code: str = Field(
        description="Kode error stabil dari design-api §18.",
        examples=["AUTHENTICATION_FAILED"],
    )
    message: str = Field(
        description="Pesan publik yang aman ditampilkan ke pengguna.",
        examples=["Autentikasi gagal."],
    )
    details: list[ErrorDetail] = Field(
        default_factory=list,
        description="Rincian tambahan; kosong bila tidak ada.",
    )


class ErrorResponse(BaseModel):
    """Body response gagal sesuai design-api §18."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "error": {
                    "code": "AUTHENTICATION_FAILED",
                    "message": "Autentikasi gagal.",
                    "details": [],
                }
            }
        }
    )

    error: ErrorEnvelope
