# Dokumentasi Tugas Proyek Akhir — Teknik Kompilasi
## Representasi Tahapan Kompilasi untuk Konstruksi **Perulangan (For-Loop)**

---

## 1. Pilihan Konstruksi

Konstruksi sintaksis yang dipilih adalah **Perulangan (`for` loop)**, dengan bentuk umum:

```
for ( inisialisasi ; kondisi ; update ) { statements }
```

Contoh konkret yang digunakan sebagai kasus uji:

```
for ( i = 0 ; i < 5 ; i++ ) { total = total + i }
```

---

## 2. Pattern (Pola Sintaksis) — BNF

```
<for_stmt>  ::= "for" "(" <init> ";" <cond> ";" <update> ")" "{" <stmts> "}"
<init>      ::= <id> "=" <expr>
<cond>      ::= <id> <relop> <expr>
<update>    ::= <id> "++" | <id> "--" | <id> "+=" <expr> | <id> "=" <expr>
<stmts>     ::= <stmt> | <stmt> <stmts>
<stmt>      ::= <id> "=" <expr> ";"?
<expr>      ::= <term> ( ("+" | "-") <term> )*
<term>      ::= <id> | <number>
<relop>     ::= "<" | ">" | "<=" | ">=" | "==" | "!="
```

Catatan: tanda `;` pada akhir statement terakhir di dalam `{ }` bersifat opsional,
mengikuti gaya penulisan pada contoh soal (`{ y = 1 }` tanpa titik koma penutup).

---

## 3. Implementasi Program

Program diimplementasikan dalam **Python 3** pada file `for_loop_compiler.py`,
dan dibagi menjadi empat tahapan yang saling berurutan (pipeline), sesuai dengan
tahapan kompilasi sesungguhnya.

### 3.1 Tahap Leksikal (`lexical_analysis`)

- Menggunakan **regular expression** (modul `re`) untuk memindai *source code*
  karakter demi karakter dan mengelompokkannya menjadi **token**.
- Setiap token memiliki `type` (misal `FOR`, `ID`, `NUMBER`, `LT`, `ASSIGN`, dst.)
  dan `value` (teks aslinya).
- Token spasi/tab/baris baru diabaikan (`SKIP`), sedangkan karakter yang tidak
  dikenali akan memicu `LexicalError`.
- Urutan pola token disusun dari yang paling spesifik (misalnya `<=` sebelum `<`)
  agar tidak terjadi salah pengelompokan (*maximal munch*).

**Contoh hasil token** dari `for ( i = 0 ; i < 5 ; i++ ) { total = total + i }`:

```
[<FOR:for>, <LPAREN:(>, <ID:i>, <ASSIGN:=>, <NUMBER:0>, <SEMI:;>,
 <ID:i>, <LT:<>, <NUMBER:5>, <SEMI:;>, <ID:i>, <INC:++>, <RPAREN:)>,
 <LBRACE:{>, <ID:total>, <ASSIGN:=>, <ID:total>, <PLUS:+>, <ID:i>,
 <RBRACE:}>, <EOF:None>]
```

### 3.2 Tahap Sintaksis (`syntax_analysis` / kelas `Parser`)

- Menggunakan pendekatan **recursive-descent parsing**: setiap simbol non-terminal
  pada grammar BNF direpresentasikan sebagai satu method (`parse_for`,
  `parse_assign`, `parse_cond`, `parse_update`, `parse_stmts`, `parse_expr`, dst).
- Parser membaca token satu per satu (`current()`/`eat()`), memverifikasi urutan
  token sesuai grammar, dan sekaligus membangun **Abstract Syntax Tree (AST)**.
- Node AST yang digunakan: `ForNode`, `AssignNode`, `UpdateNode`, `CondNode`,
  `BinOpNode`, `IdNode`, `NumNode`.
- Kesalahan urutan token (misalnya titik koma yang hilang) akan memicu
  `SyntaxErrorC` beserta pesan yang menjelaskan token apa yang diharapkan.

**Contoh AST** (representasi tekstual) untuk contoh di atas:

```
ForNode(
  init  = Assign(i = 0),
  cond  = Cond(i < 5),
  update= Update(i++),
  body  = [Assign(total = BinOp(total + i))]
)
```

### 3.3 Tahap Semantik (`semantic_analysis`)

- Menggunakan struktur **Symbol Table** (`SymbolTable`) berupa *dictionary*
  nama variabel → tipe data.
- Aturan pengecekan yang diterapkan:
  1. Variabel kontrol loop (misalnya `i`) dianggap **otomatis dideklarasikan**
     saat muncul pada bagian inisialisasi (`init`), mengikuti idiom umum for-loop.
  2. Variabel yang dipakai pada **kondisi** dan **update** wajib sudah ada di
     tabel simbol; jika tidak, dilempar `SemanticError`.
  3. Variabel pada **badan perulangan** yang berada di sisi kanan (`expr`)
     wajib sudah dideklarasikan; variabel di sisi kiri (`target`) akan
     didaftarkan ke tabel simbol jika belum ada.
- Jika seluruh variabel valid, tahap ini menghasilkan tabel simbol akhir dan
  status `VALID`.

**Contoh kasus gagal semantik**: variabel `hasil` dipakai (`hasil = hasil + i`)
padahal belum pernah dideklarasikan sebelumnya sehingga menghasilkan:

```
[SEMANTIC ERROR] Variabel 'hasil' digunakan sebelum dideklarasikan
```

### 3.4 Tahap Generasi Kode Antara / TAC (`generate_tac`)

- Mengubah AST menjadi **Three-Address Code**, dengan pola penerjemahan
  for-loop standar (mirip pendekatan buku Aho/Ullman - *Dragon Book*):

```
     <init>
L1:  ifFalse (<kondisi>) goto L2
     <badan perulangan>
     <update>
     goto L1
L2:
```

- Ekspresi biner (`a + b`) diterjemahkan menjadi variabel sementara (*temporary*,
  `t1`, `t2`, ...) menggunakan method `gen_expr`, sesuai prinsip TAC bahwa setiap
  instruksi hanya boleh memiliki maksimal satu operator.
- Label (`L1`, `L2`, ...) dan temporary dibuat otomatis melalui counter pada
  kelas `TACGenerator`.

**Contoh hasil TAC** untuk `for ( i = 0 ; i < 5 ; i++ ) { total = total + i }`:

```
i = 0
L1:
ifFalse (i < 5) goto L2
t1 = total + i
total = t1
i = i + 1
goto L1
L2:
```

---

## 4. Hasil Uji Coba (Demo)

Program menyertakan 3 skenario demo pada bagian `if __name__ == "__main__":`.

| Demo | Input | Hasil |
|------|-------|-------|
| 1 | `for ( i = 0 ; i < 5 ; i++ ) { total = total + i }` (dengan `total` dideklarasikan lebih dulu) | Lolos semua tahap, menghasilkan TAC lengkap |
| 2 | `for ( i = 0 ; i < 10 ; i = i + 1 ) { hasil = hasil + i }` | Gagal di tahap **Semantik** — variabel `hasil` belum dideklarasikan |
| 3 | `for ( i = 0 ; i < 5 i++ ) { total = total + i }` (titik koma hilang) | Gagal di tahap **Sintaksis** — token `;` diharapkan tetapi ditemukan `ID` |

Output lengkap ketiga demo dapat dilihat pada file `demo_output.txt` yang
dihasilkan dengan menjalankan:

```bash
python3 for_loop_compiler.py
```

---

## 5. Struktur Berkas

```
tugas_UAS/
├── for_loop_compiler.py   # source code implementasi 4 tahapan kompilasi
├── demo_output.txt        # contoh output hasil eksekusi program
└── DOKUMENTASI.md         # dokumen penjelasan ini
```

---

## 6. Kesimpulan

Program ini berhasil menyimulasikan keempat tahapan utama proses kompilasi
untuk konstruksi **for-loop**:

1. **Leksikal** — memecah kode sumber menjadi token menggunakan regex.
2. **Sintaksis** — membangun AST melalui recursive-descent parser sesuai
   grammar BNF yang telah didefinisikan.
3. **Semantik** — memvalidasi keberadaan variabel melalui tabel simbol
   sebelum kode dianggap benar secara makna.
4. **Generasi Kode Antara** — menerjemahkan AST menjadi Three-Address Code
   yang merepresentasikan logika lompatan (`goto`) dan label layaknya kode
   antara pada kompilator sungguhan.

Pendekatan modular (satu fungsi/kelas per tahap) mempermudah penelusuran
kesalahan, karena setiap tahap melempar jenis *exception* yang berbeda
(`LexicalError`, `SyntaxErrorC`, `SemanticError`) sesuai letak kesalahannya.
