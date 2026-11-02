======================================================================
PROSES
======================================================================
[  0.00s] Memulai analisis     Memulai analisis RPS
[  0.00s] Membaca struktur RPS Membaca dan memeriksa struktur RPS
[  0.02s] RPS terbaca          RPS terbaca: 16 minggu, 1 CPMK, 10 Sub-CPMK, 5 komponen penilaian
[  0.02s] Mengirim ke model    Mengirim RPS ke model (percobaan 1/3)
[ 36.59s] Respons model diterima Respons model diterima
[ 36.59s] Memvalidasi hasil    Memvalidasi hasil terhadap schema
[ 36.59s] Analisis selesai     Analisis selesai

======================================================================
[SUKSES] HASIL RPS STRUCTURED DATA
======================================================================
{
  "schema_version": "2.0",
  "course": {
    "name": "MATEMATIKA DISKRIT",
    "code": "IF201402",
    "credits": 3,
    "semester": 2,
    "description": "Pada mata kuliah ini, mahasiswa diberikan wawasan mengenai struktur diskrit yang merupakan pondasi dari informatika. Lebih lanjut, dalam mata kuliah ini dibahas mengenai logika, proposisi, ekuivalensi, predikat dan quantifier, aturan penarikan kesimpulan, metode pembuktian dan induksi"
  },
  "cpl": [
    {
      "id": "CPL-2",
      "description": "Mampu mengidentifikasi, merumuskan, menganalisa, menyelesaikan permasalahan kompleks, serta mengambil keputusan dengan mempertimbangkan dampaknya pada aspek hukum, ekonomi, lingkungan, sosial, politik, kesehatan, keselamatan, dan keberlanjutan serta memanfaatkan teknologi informasi dan potensi sumber daya nasional dalam perspektif global."
    },
    {
      "id": "CPL-4",
      "description": "Mampu mengaplikasikan nilai Pancasila, etika dan tanggung jawab professional."
    },
    {
      "id": "CPL-5",
      "description": "Mampu menunjukkan kemampuan belajar sepanjang hayat dan menerapkan pengetahuan tersebut sesuai kebutuhan dengan strategi pembelajaran yang tepat."
    },
    {
      "id": "CPL-6",
      "description": "Mampu memahami konsep matematika, statistika, struktur diskrit, struktur data dan algoritma, dalam menyelesaikan berbagai masalah berkaitan dengan keteknikan dengan prinsip-prinsip komputasi secara efektif dan efisien."
    }
  ],
  "cpmk": [
    {
      "id": "CPMK-1",
      "description": "Mahasiswa mampu memahami dan menerapkan konsep matematika diskrit.",
      "cpl_ids": [
        "CPL-4",
        "CPL-5",
        "CPL-6"
      ]
    }
  ],
  "sub_cpmk": [
    {
      "id": "SUB-1",
      "description": "Mahasiswa menerapkan konsep proposisi, ekivalensi, predikat dan quantifier pada suatu pernyataan.",
      "cpmk_ids": [
        "CPMK-1"
      ]
    },
    {
      "id": "SUB-2",
      "description": "Mahasiswa mampu menganalisis suatu kesimpulan dari beberapa pernyataan matematika.",
      "cpmk_ids": [
        "CPMK-1"
      ]
    },
    {
      "id": "SUB-3",
      "description": "Mahasiswa mampu mengimplemen tasikan teknik - teknik pembuktian pada sebuah pernyataan",
      "cpmk_ids": [
        "CPMK-1"
      ]
    },
    {
      "id": "SUB-4",
      "description": "Mahasiswa mampu menerapkan dan mengimplemen tasikan konsep himpunan.",
      "cpmk_ids": [
        "CPMK-1"
      ]
    },
    {
      "id": "SUB-5",
      "description": "Mahasiswa mampu menerapkan dan mengimplemae ntasikan relasi dan fungsi.",
      "cpmk_ids": [
        "CPMK-1"
      ]
    },
    {
      "id": "SUB-6",
      "description": "Mahasiswa mampu menerapkan konsep induksi matematika.",
      "cpmk_ids": [
        "CPMK-1"
      ]
    },
    {
      "id": "SUB-7",
      "description": "Mahasiswa mampu menerapkan rekursi dan relasi rekurens",
      "cpmk_ids": [
        "CPMK-1"
      ]
    },
    {
      "id": "SUB-8",
      "description": "Mahasiswa mampu menerapkan dan mengaplikaasik an konsep aljabar boolean",
      "cpmk_ids": [
        "CPMK-1"
      ]
    },
    {
      "id": "SUB-9",
      "description": "Mahasiswa mampu menganalisis dan menerapkan konsep teori bilangan",
      "cpmk_ids": [
        "CPMK-1"
      ]
    },
    {
      "id": "SUB-10",
      "description": "Mahasiswa mampu menerapkan dan menganalisis konsep kombinatorial pada sebuah kasus",
      "cpmk_ids": [
        "CPMK-1"
      ]
    }
  ],
  "topics": [
    {
      "id": "TOP-1",
      "name": "Logika, Proposisi, dan Ekuivalensi"
    },
    {
      "id": "TOP-2",
      "name": "Predikat dan Quantifier"
    },
    {
      "id": "TOP-3",
      "name": "Aturan Penentuan Kesimpulan"
    },
    {
      "id": "TOP-4",
      "name": "Metode Pembuktian dan Induksi Matematika"
    },
    {
      "id": "TOP-5",
      "name": "Teori Himpunan"
    },
    {
      "id": "TOP-6",
      "name": "Relasi dan Fungsi"
    },
    {
      "id": "TOP-7",
      "name": "Aljabar Boolean"
    },
    {
      "id": "TOP-8",
      "name": "Kombinatorial dan Teori Bilangan"
    },
    {
      "id": "TOP-9",
      "name": "Konsep logika proposisi"
    },
    {
      "id": "TOP-10",
      "name": "Konsep ekuivalensi"
    },
    {
      "id": "TOP-11",
      "name": "Konsep dan penggunaan predikat dan quantifier"
    },
    {
      "id": "TOP-12",
      "name": "Konsep aturan penentuan kesimpulan"
    },
    {
      "id": "TOP-13",
      "name": "Pembuktian secara langsung"
    },
    {
      "id": "TOP-14",
      "name": "Pembuktian dengan kontraposisi"
    },
    {
      "id": "TOP-15",
      "name": "Pembuktian dengan kontradiksi"
    },
    {
      "id": "TOP-16",
      "name": "Definisi himpunan"
    },
    {
      "id": "TOP-17",
      "name": "Cara penyajian himpunan"
    },
    {
      "id": "TOP-18",
      "name": "Operasi pada himpunan"
    },
    {
      "id": "TOP-19",
      "name": "Hukum - hukum pada himpunan"
    },
    {
      "id": "TOP-20",
      "name": "Prinsip inklusi - eksklusi"
    },
    {
      "id": "TOP-21",
      "name": "Definisi relasi"
    },
    {
      "id": "TOP-22",
      "name": "Representasi relasi"
    },
    {
      "id": "TOP-23",
      "name": "Sifat - sifat relasi"
    },
    {
      "id": "TOP-24",
      "name": "Definisi fungsi"
    },
    {
      "id": "TOP-25",
      "name": "Komposisi dari dua fungsi"
    },
    {
      "id": "TOP-26",
      "name": "Konsep induksi matematis"
    },
    {
      "id": "TOP-27",
      "name": "Konsep induksi matematis kuat"
    },
    {
      "id": "TOP-28",
      "name": "Rekursi dan Fungsi Rekursif"
    },
    {
      "id": "TOP-29",
      "name": "Relasi Rekurens"
    },
    {
      "id": "TOP-30",
      "name": "Peta Karnaguh"
    },
    {
      "id": "TOP-31",
      "name": "Algoritma Euclidean"
    },
    {
      "id": "TOP-32",
      "name": "Aritmatika Modulo"
    },
    {
      "id": "TOP-33",
      "name": "Sistem kekongruena n linier"
    },
    {
      "id": "TOP-34",
      "name": "Bilangan Prima"
    },
    {
      "id": "TOP-35",
      "name": "Teorema Formato"
    },
    {
      "id": "TOP-36",
      "name": "Aplikasi Teori Bilangan"
    },
    {
      "id": "TOP-37",
      "name": "Koefisien binomial dan identitas"
    },
    {
      "id": "TOP-38",
      "name": "Pigeonhole Principle"
    }
  ],
  "weeks": [
    {
      "week": 1,
      "week_type": "regular",
      "topics": [
        "TOP-9",
        "TOP-10"
      ],
      "cpmk": [],
      "sub_cpmk": [
        "SUB-1"
      ],
      "teaching_method": [
        "Kuliah/ceramah",
        "diskusi",
        "latihan soal"
      ],
      "media": [],
      "assessment": {
        "type": "Tugas",
        "description": "Ketepatan dalam menjawab",
        "weight_percent": 100.0
      }
    },
    {
      "week": 2,
      "week_type": "regular",
      "topics": [
        "TOP-11",
        "TOP-12"
      ],
      "cpmk": [],
      "sub_cpmk": [
        "SUB-2"
      ],
      "teaching_method": [
        "Kuliah/ceramah",
        "diskusi",
        "latihan soal"
      ],
      "media": [],
      "assessment": {
        "type": "Tugas",
        "description": "Ketepatan dalam menjawab",
        "weight_percent": 100.0
      }
    },
    {
      "week": 3,
      "week_type": "regular",
      "topics": [
        "TOP-13",
        "TOP-14",
        "TOP-15"
      ],
      "cpmk": [],
      "sub_cpmk": [
        "SUB-3"
      ],
      "teaching_method": [
        "Kuliah/ceramah",
        "diskusi",
        "latihan soal"
      ],
      "media": [],
      "assessment": {
        "type": "Tugas",
        "description": "Ketepatan dalam menjawab",
        "weight_percent": 100.0
      }
    },
    {
      "week": 4,
      "week_type": "kuis",
      "topics": [],
      "cpmk": [],
      "sub_cpmk": [],
      "teaching_method": [],
      "media": [],
      "assessment": null
    },
    {
      "week": 5,
      "week_type": "regular",
      "topics": [
        "TOP-16",
        "TOP-17",
        "TOP-18",
        "TOP-19",
        "TOP-20"
      ],
      "cpmk": [],
      "sub_cpmk": [
        "SUB-4"
      ],
      "teaching_method": [
        "Kuliah/ceramah",
        "diskusi",
        "latihan soal",
        "uji kompetensi"
      ],
      "media": [],
      "assessment": {
        "type": "Tugas",
        "description": "Ketepatan dalam menjawab",
        "weight_percent": 100.0
      }
    },
    {
      "week": 6,
      "week_type": "regular",
      "topics": [
        "TOP-21",
        "TOP-22",
        "TOP-23"
      ],
      "cpmk": [],
      "sub_cpmk": [
        "SUB-5"
      ],
      "teaching_method": [
        "Kuliah/ceramah",
        "diskusi",
        "latihan soal",
        "uji kompetensi"
      ],
      "media": [],
      "assessment": {
        "type": "Tugas",
        "description": "Ketepatan dalam menjawab",
        "weight_percent": 100.0
      }
    },
    {
      "week": 7,
      "week_type": "regular",
      "topics": [
        "TOP-24",
        "TOP-25"
      ],
      "cpmk": [],
      "sub_cpmk": [],
      "teaching_method": [
        "Kuliah/ceramah",
        "diskusi",
        "latihan soal",
        "uji kompetensi"
      ],
      "media": [],
      "assessment": {
        "type": "Tugas",
        "description": "Ketepatan dalam menyelesaikan masalah",
        "weight_percent": 100.0
      }
    },
    {
      "week": 8,
      "week_type": "uts",
      "topics": [],
      "cpmk": [],
      "sub_cpmk": [],
      "teaching_method": [],
      "media": [],
      "assessment": null
    },
    {
      "week": 9,
      "week_type": "regular",
      "topics": [
        "TOP-26",
        "TOP-27"
      ],
      "cpmk": [],
      "sub_cpmk": [
        "SUB-6"
      ],
      "teaching_method": [
        "Kuliah/Ceramah",
        "diskusi",
        "latihan soal",
        "uji kompetensi"
      ],
      "media": [],
      "assessment": {
        "type": "Tugas",
        "description": "Ketepatan dalam menjawab",
        "weight_percent": 100.0
      }
    },
    {
      "week": 10,
      "week_type": "regular",
      "topics": [
        "TOP-28",
        "TOP-29"
      ],
      "cpmk": [],
      "sub_cpmk": [
        "SUB-7"
      ],
      "teaching_method": [
        "Kuliah/Ceramah",
        "diskusi",
        "latihan soal",
        "uji kompetensi"
      ],
      "media": [],
      "assessment": {
        "type": "Tugas",
        "description": "Ketepatan dalam menjawab",
        "weight_percent": 100.0
      }
    },
    {
      "week": 11,
      "week_type": "regular",
      "topics": [
        "TOP-7",
        "TOP-30"
      ],
      "cpmk": [],
      "sub_cpmk": [
        "SUB-8"
      ],
      "teaching_method": [
        "Kuliah/ceramah",
        "diskusi",
        "latihan soal"
      ],
      "media": [],
      "assessment": {
        "type": "Tugas",
        "description": "Ketepatan dalam menjawab",
        "weight_percent": 100.0
      }
    },
    {
      "week": 12,
      "week_type": "kuis",
      "topics": [],
      "cpmk": [],
      "sub_cpmk": [],
      "teaching_method": [],
      "media": [],
      "assessment": null
    },
    {
      "week": 13,
      "week_type": "regular",
      "topics": [
        "TOP-31",
        "TOP-32",
        "TOP-33"
      ],
      "cpmk": [],
      "sub_cpmk": [
        "SUB-9"
      ],
      "teaching_method": [
        "Kuliah/ceramah",
        "diskusi",
        "latihan soal"
      ],
      "media": [],
      "assessment": {
        "type": "Tugas",
        "description": "Ketepatan dalam menjawab",
        "weight_percent": 100.0
      }
    },
    {
      "week": 14,
      "week_type": "regular",
      "topics": [
        "TOP-34",
        "TOP-35",
        "TOP-36"
      ],
      "cpmk": [],
      "sub_cpmk": [],
      "teaching_method": [
        "Kuliah/ceramah",
        "diskusi",
        "latihan soal"
      ],
      "media": [],
      "assessment": {
        "type": "Tugas",
        "description": "Ketepatan dalam menjawab",
        "weight_percent": 100.0
      }
    },
    {
      "week": 15,
      "week_type": "regular",
      "topics": [
        "TOP-37",
        "TOP-38"
      ],
      "cpmk": [],
      "sub_cpmk": [
        "SUB-10"
      ],
      "teaching_method": [
        "Kuliah/ceramah",
        "diskusi",
        "latihan soal"
      ],
      "media": [],
      "assessment": {
        "type": "Tugas",
        "description": "Ketepatan dalam menjawab",
        "weight_percent": 100.0
      }
    },
    {
      "week": 16,
      "week_type": "uas",
      "topics": [],
      "cpmk": [],
      "sub_cpmk": [],
      "teaching_method": [],
      "media": [],
      "assessment": null
    }
  ],
  "teaching_methods": [
    "Kuliah/ceramah",
    "diskusi",
    "latihan soal",
    "uji kompetensi"
  ],
  "media": [
    {
      "id": "MED-1",
      "name": "Perangkat Lunak: Microsoft power point, pdf viewer",
      "type": null,
      "description": null
    },
    {
      "id": "MED-2",
      "name": "Perangkat Keras: Laptop, LCD, dan Proyektor",
      "type": null,
      "description": null
    },
    {
      "id": "MED-3",
      "name": "Papan Tulis, LMS (kuliah.itk.ac.id), Jamboard, paint",
      "type": null,
      "description": null
    }
  ],
  "assessments": [
    {
      "id": "A-1",
      "type": "Kehadiran",
      "description": "Kehadiran",
      "week": null,
      "weight_percent": 10.0
    },
    {
      "id": "A-2",
      "type": "Tugas (4x)",
      "description": "Tugas (4x)",
      "week": null,
      "weight_percent": 15.0
    },
    {
      "id": "A-3",
      "type": "Kuis (2x)",
      "description": "Kuis (2x)",
      "week": null,
      "weight_percent": 20.0
    },
    {
      "id": "A-4",
      "type": "UTS",
      "description": "UTS (1x)",
      "week": 8,
      "weight_percent": 25.0
    },
    {
      "id": "A-5",
      "type": "UAS",
      "description": "UAS (1x)",
      "week": 16,
      "weight_percent": 30.0
    }
  ],
  "references": [
    {
      "id": "R-1",
      "citation": "Rosen, K. H. Discrete mathematics and its applications (8th ed.). Boston: McGraw-Hill.",
      "authors": null,
      "year": null,
      "source": null
    },
    {
      "id": "R-2",
      "citation": "Grossman, P. (2009). Discrete mathematics for computing. Basingstoke: Palgrave Macmillan.",
      "authors": null,
      "year": null,
      "source": null
    },
    {
      "id": "R-3",
      "citation": "Epp, S. S. (2010). Discrete Mathematics with Application (4th ed.). Brooks/Cle.",
      "authors": null,
      "year": null,
      "source": null
    }
  ],
  "extraction": {
    "extracted_at": null,
    "extractor": null,
    "extractor_version": null,
    "model_name": null,
    "model_provider": null,
    "source_pages": [],
    "confidence": null,
    "warnings": [
      "cpl: tidak ditemukan pemetaan ke CPMK.",
      "cpmk[]: tidak ditemukan pemetaan ke CPL.",
      "weeks[].cpmk: RPS tidak memuat pemetaan minggu ke CPMK.",
      "media[].type: tidak ditemukan pada RPS.",
      "media[].description: tidak ditemukan pada RPS."
    ]
  }
}

----------------------------------------------------------------------
JEJAK PERCOBAAN
----------------------------------------------------------------------
#1 rps_analysis/v2 | model=gpt-4o-mini | token=6341/4576 | durasi=36569 ms | hasil=success
----------------------------------------------------------------------
Total token   : 6341 masuk, 4576 keluar (10917)
Total durasi  : 36569.35 ms
======================================================================
