"""Validasi hasil course plan (BE-14.3).

Validasi dijalankan **setelah** kelas penyimpanan menerima output agent dan
sebelum versi ditampilkan untuk direview. Tujuannya menangkap pelanggaran yang
tidak dapat dijaga Pydantic saja — pelanggaran terhadap RPS dan Activity
Configuration (content-schema §8–§9, §37):

- jumlah dan nomor minggu mengikuti rencana mingguan RPS;
- kode Sub-CPMK yang dipakai benar-benar ada pada RPS Analysis;
- setiap Sub-CPMK RPS tercakup minimal satu kali;
- minggu UTS/UAS tidak memuat topik/materi baru;
- rencana aktivitas hanya memuat jenis yang aktif pada Activity Configuration.

Hasilnya berbentuk ``{"passed": bool, "issues": [...]}`` dan disimpan apa adanya
pada ``course_plans.validation_result`` (issue BE-14.1). Temuan yang sama juga
dapat dipakai sebagai umpan balik retry oleh Course Planning Service (BE-15.3);
karena itu setiap temuan membawa ``code``, ``week``, dan ``message``.

``ponytail:`` aturan di sini adalah himpunan minimum yang dibutuhkan BE-14.2
(approve hanya untuk rencana yang lolos validasi). BE-15.1 dapat menambah aturan
akademik lain di fungsi ini tanpa mengubah penyimpanan maupun endpoint review.
"""

from __future__ import annotations

from collections.abc import Mapping

from src.schemas.course_plan import CoursePlanOutput

__all__ = ["EXAM_WEEK_TYPES", "normalize_rps_weeks", "validate_plan"]

#: Minggu ujian yang tidak boleh memuat materi baru (content-schema §9).
EXAM_WEEK_TYPES = frozenset({"uts", "uas"})


def normalize_rps_weeks(structured: Mapping | None) -> dict[int, Mapping]:
    """Indeks rencana mingguan RPS berdasarkan nomor minggu.

    Entri cacat (bukan object, atau nomor minggu bukan bilangan bulat) dilewati:
    RPS Structured Data sudah divalidasi saat disimpan, sehingga entri seperti
    itu hanya mungkin berasal dari data lama dan tidak boleh menggagalkan
    generasi course plan.
    """
    weeks: dict[int, Mapping] = {}
    entries = (structured or {}).get("weeks") or []
    if not isinstance(entries, list):
        return weeks

    for entry in entries:
        if not isinstance(entry, Mapping):
            continue
        number = entry.get("week")
        if isinstance(number, bool) or not isinstance(number, int):
            continue
        weeks[number] = entry
    return weeks


def validate_plan(
    output: CoursePlanOutput,
    *,
    rps_structured: Mapping | None,
    activity_configuration: Mapping | None,
) -> dict:
    """Validasi akademik satu course plan terhadap RPS dan preferensi aktivitas."""
    issues: list[dict] = []
    rps_weeks = normalize_rps_weeks(rps_structured)
    planned_numbers = {week.week_number for week in output.weeks}

    issues.extend(_week_number_issues(rps_weeks, planned_numbers))
    issues.extend(_sub_cpmk_issues(output, rps_structured))
    issues.extend(_exam_week_issues(output, rps_weeks))
    issues.extend(_activity_issues(output, activity_configuration))

    issues.sort(key=lambda issue: (issue["week"] or 0, issue["code"]))
    return {"passed": not issues, "issues": issues}


def _week_number_issues(
    rps_weeks: Mapping[int, Mapping], planned_numbers: set[int]
) -> list[dict]:
    """Nomor minggu rencana harus sama persis dengan minggu RPS."""
    if not rps_weeks:
        return []

    issues: list[dict] = []
    for number in sorted(set(rps_weeks) - planned_numbers):
        issues.append(
            {
                "code": "WEEK_MISSING",
                "week": number,
                "message": f"Minggu {number} pada RPS belum ada di course plan.",
            }
        )
    for number in sorted(planned_numbers - set(rps_weeks)):
        issues.append(
            {
                "code": "WEEK_NOT_IN_RPS",
                "week": number,
                "message": f"Minggu {number} tidak ada pada rencana mingguan RPS.",
            }
        )
    return issues


def _sub_cpmk_issues(
    output: CoursePlanOutput, rps_structured: Mapping | None
) -> list[dict]:
    """Kode Sub-CPMK yang dipakai harus ada, dan seluruh Sub-CPMK harus tercakup."""
    declared = {
        entry.get("id")
        for entry in (rps_structured or {}).get("sub_cpmk") or []
        if isinstance(entry, Mapping) and isinstance(entry.get("id"), str)
    }
    if not declared:
        return []

    issues: list[dict] = []
    used: set[str] = set()
    for week in sorted(output.weeks, key=lambda item: item.week_number):
        for code in week.learning_outcomes:
            used.add(code)
            if code not in declared:
                issues.append(
                    {
                        "code": "UNKNOWN_SUB_CPMK",
                        "week": week.week_number,
                        "message": (
                            f"Sub-CPMK {code} pada minggu {week.week_number} "
                            "tidak ada pada hasil analisis RPS."
                        ),
                    }
                )

    for code in sorted(declared - used):
        issues.append(
            {
                "code": "SUB_CPMK_NOT_COVERED",
                "week": None,
                "message": f"Sub-CPMK {code} belum tercakup pada course plan.",
            }
        )
    return issues


def _exam_week_issues(
    output: CoursePlanOutput, rps_weeks: Mapping[int, Mapping]
) -> list[dict]:
    """Minggu UTS/UAS tidak boleh memuat topik materi baru.

    Aktivitas evaluasi (mis. quiz) tetap boleh direncanakan; yang dilarang
    adalah menambahkan materi baru pada minggu ujian (BE-15.1).
    """
    issues: list[dict] = []
    for week in sorted(output.weeks, key=lambda item: item.week_number):
        rps_week = rps_weeks.get(week.week_number) or {}
        if rps_week.get("week_type") not in EXAM_WEEK_TYPES:
            continue

        if week.topics:
            issues.append(
                {
                    "code": "EXAM_WEEK_HAS_MATERIAL",
                    "week": week.week_number,
                    "message": (
                        f"Minggu {week.week_number} adalah minggu ujian dan tidak "
                        "boleh memuat topik materi baru."
                    ),
                }
            )
    return issues


def _activity_issues(
    output: CoursePlanOutput, activity_configuration: Mapping | None
) -> list[dict]:
    """Rencana aktivitas hanya boleh berisi jenis yang aktif untuk dosen."""
    configuration = activity_configuration or {}
    issues: list[dict] = []
    for week in sorted(output.weeks, key=lambda item: item.week_number):
        for activity in week.planned_activities:
            enabled = configuration.get(activity.value)
            if enabled is False:
                issues.append(
                    {
                        "code": "ACTIVITY_NOT_ENABLED",
                        "week": week.week_number,
                        "message": (
                            f"Aktivitas {activity.value} pada minggu "
                            f"{week.week_number} tidak aktif pada Activity "
                            "Configuration dosen."
                        ),
                    }
                )
    return issues
