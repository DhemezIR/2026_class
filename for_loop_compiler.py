"""
=========================================================================
 TUGAS PROYEK AKHIR - TEKNIK KOMPILASI
 Representasi Tahapan Kompilasi untuk Konstruksi: PERULANGAN (FOR LOOP)
=========================================================================

Tahapan yang direpresentasikan:
    1. Analisis Leksikal   -> memecah source code menjadi token
    2. Analisis Sintaksis  -> membentuk Abstract Syntax Tree (AST)
    3. Analisis Semantik   -> validasi keberadaan & tipe variabel
    4. Generasi Kode Antara -> Three-Address Code (TAC)

Konstruksi yang dipilih : for ( init ; kondisi ; update ) { statements }

Grammar (BNF):
    <for_stmt>  ::= "for" "(" <init> ";" <cond> ";" <update> ")" "{" <stmts> "}"
    <init>      ::= <id> "=" <expr>
    <cond>      ::= <id> <relop> <expr>
    <update>    ::= <id> "++" | <id> "--" | <id> "+=" <expr>
    <stmts>     ::= <stmt> | <stmt> <stmts>
    <stmt>      ::= <id> "=" <expr> ";"
    <expr>      ::= <term> (("+" | "-") <term>)*
    <term>      ::= <id> | <number>
    <relop>     ::= "<" | ">" | "<=" | ">=" | "==" | "!="
"""

import re
import sys


# =========================================================================
# 1. ANALISIS LEKSIKAL (LEXICAL ANALYSIS)
# =========================================================================

class Token:
    def __init__(self, type_, value, pos):
        self.type = type_
        self.value = value
        self.pos = pos

    def __repr__(self):
        return f"<{self.type}:{self.value}>"


# Daftar pola token (urutan penting: pola yang lebih spesifik didahulukan)
TOKEN_SPEC = [
    ("FOR",       r"\bfor\b"),
    ("NUMBER",    r"\d+(\.\d+)?"),
    ("ID",        r"[A-Za-z_][A-Za-z0-9_]*"),
    ("LE",        r"<="),
    ("GE",        r">="),
    ("EQ",        r"=="),
    ("NEQ",       r"!="),
    ("INC",       r"\+\+"),
    ("DEC",       r"--"),
    ("PLUSEQ",    r"\+="),
    ("MINUSEQ",   r"-="),
    ("LT",        r"<"),
    ("GT",        r">"),
    ("ASSIGN",    r"="),
    ("PLUS",      r"\+"),
    ("MINUS",     r"-"),
    ("LPAREN",    r"\("),
    ("RPAREN",    r"\)"),
    ("LBRACE",    r"\{"),
    ("RBRACE",    r"\}"),
    ("SEMI",      r";"),
    ("SKIP",      r"[ \t\n]+"),
    ("MISMATCH",  r"."),
]

MASTER_PATTERN = "|".join(f"(?P<{name}>{pattern})" for name, pattern in TOKEN_SPEC)


class LexicalError(Exception):
    pass


def lexical_analysis(source_code):
    """Tahap 1: memecah source code menjadi daftar Token."""
    tokens = []
    for match in re.finditer(MASTER_PATTERN, source_code):
        kind = match.lastgroup
        value = match.group()
        pos = match.start()
        if kind == "SKIP":
            continue
        if kind == "MISMATCH":
            raise LexicalError(f"Karakter tidak dikenal '{value}' pada posisi {pos}")
        tokens.append(Token(kind, value, pos))
    tokens.append(Token("EOF", None, len(source_code)))
    return tokens


# =========================================================================
# 2. ANALISIS SINTAKSIS (SYNTAX ANALYSIS) -> AST
# =========================================================================

class ASTNode:
    """Kelas dasar untuk semua node AST."""
    pass


class ForNode(ASTNode):
    def __init__(self, init, cond, update, body):
        self.init = init
        self.cond = cond
        self.update = update
        self.body = body

    def __repr__(self):
        return f"ForNode(init={self.init}, cond={self.cond}, update={self.update}, body={self.body})"


class AssignNode(ASTNode):
    def __init__(self, target, expr):
        self.target = target
        self.expr = expr

    def __repr__(self):
        return f"Assign({self.target} = {self.expr})"


class UpdateNode(ASTNode):
    def __init__(self, target, op, expr=None):
        self.target = target
        self.op = op          # '++', '--', '+=', '-='
        self.expr = expr

    def __repr__(self):
        return f"Update({self.target}{self.op}{self.expr if self.expr else ''})"


class CondNode(ASTNode):
    def __init__(self, left, op, right):
        self.left = left
        self.op = op
        self.right = right

    def __repr__(self):
        return f"Cond({self.left} {self.op} {self.right})"


class BinOpNode(ASTNode):
    def __init__(self, op, left, right):
        self.op = op
        self.left = left
        self.right = right

    def __repr__(self):
        return f"BinOp({self.left} {self.op} {self.right})"


class IdNode(ASTNode):
    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return self.name


class NumNode(ASTNode):
    def __init__(self, value):
        self.value = value

    def __repr__(self):
        return str(self.value)


class SyntaxErrorC(Exception):
    pass


class Parser:
    """Recursive-descent parser sederhana khusus untuk konstruksi for-loop."""

    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0

    def current(self):
        return self.tokens[self.pos]

    def eat(self, type_):
        tok = self.current()
        if tok.type != type_:
            raise SyntaxErrorC(f"Diharapkan token '{type_}' tetapi ditemukan '{tok.type}' ({tok.value})")
        self.pos += 1
        return tok

    def parse_for(self):
        self.eat("FOR")
        self.eat("LPAREN")
        init = self.parse_assign()
        self.eat("SEMI")
        cond = self.parse_cond()
        self.eat("SEMI")
        update = self.parse_update()
        self.eat("RPAREN")
        self.eat("LBRACE")
        body = self.parse_stmts()
        self.eat("RBRACE")
        return ForNode(init, cond, update, body)

    def parse_assign(self):
        target = self.eat("ID").value
        self.eat("ASSIGN")
        expr = self.parse_expr()
        return AssignNode(target, expr)

    def parse_cond(self):
        left = self.parse_expr()
        op_tok = self.current()
        if op_tok.type not in ("LT", "GT", "LE", "GE", "EQ", "NEQ"):
            raise SyntaxErrorC(f"Operator relasional diharapkan, ditemukan '{op_tok.type}'")
        self.pos += 1
        right = self.parse_expr()
        return CondNode(left, op_tok.value, right)

    def parse_update(self):
        target = self.eat("ID").value
        tok = self.current()
        if tok.type == "INC":
            self.pos += 1
            return UpdateNode(target, "++")
        elif tok.type == "DEC":
            self.pos += 1
            return UpdateNode(target, "--")
        elif tok.type in ("PLUSEQ", "MINUSEQ"):
            op = tok.value
            self.pos += 1
            expr = self.parse_expr()
            return UpdateNode(target, op, expr)
        elif tok.type == "ASSIGN":
            # bentuk: i = i + 1
            self.pos += 1
            expr = self.parse_expr()
            return UpdateNode(target, "=", expr)
        else:
            raise SyntaxErrorC(f"Bentuk update tidak valid: '{tok.type}'")

    def parse_stmts(self):
        stmts = []
        while self.current().type == "ID":
            stmts.append(self.parse_stmt())
        return stmts

    def parse_stmt(self):
        target = self.eat("ID").value
        self.eat("ASSIGN")
        expr = self.parse_expr()
        # ';' bersifat opsional untuk statement terakhir sebelum '}'
        if self.current().type == "SEMI":
            self.eat("SEMI")
        return AssignNode(target, expr)

    def parse_expr(self):
        node = self.parse_term()
        while self.current().type in ("PLUS", "MINUS"):
            op = self.current().value
            self.pos += 1
            right = self.parse_term()
            node = BinOpNode(op, node, right)
        return node

    def parse_term(self):
        tok = self.current()
        if tok.type == "ID":
            self.pos += 1
            return IdNode(tok.value)
        elif tok.type == "NUMBER":
            self.pos += 1
            return NumNode(tok.value)
        else:
            raise SyntaxErrorC(f"Term tidak valid: '{tok.type}'")


def syntax_analysis(tokens):
    """Tahap 2: membangun AST dari daftar token."""
    parser = Parser(tokens)
    ast = parser.parse_for()
    return ast


# =========================================================================
# 3. ANALISIS SEMANTIK (SEMANTIC ANALYSIS)
# =========================================================================

class SemanticError(Exception):
    pass


class SymbolTable:
    def __init__(self):
        self.symbols = {}  # nama_variabel -> tipe

    def declare(self, name, type_="int"):
        self.symbols[name] = type_

    def is_declared(self, name):
        return name in self.symbols

    def get_type(self, name):
        return self.symbols.get(name)


def semantic_check_expr(expr, symtab):
    if isinstance(expr, IdNode):
        if not symtab.is_declared(expr.name):
            raise SemanticError(f"Variabel '{expr.name}' digunakan sebelum dideklarasikan")
    elif isinstance(expr, BinOpNode):
        semantic_check_expr(expr.left, symtab)
        semantic_check_expr(expr.right, symtab)
    elif isinstance(expr, NumNode):
        pass  # angka literal selalu valid
    else:
        raise SemanticError(f"Node ekspresi tidak dikenal: {expr}")


def semantic_analysis(ast, symtab=None):
    """
    Tahap 3: melakukan pengecekan dasar:
      - variabel pada init dianggap dideklarasikan otomatis (idiom umum for-loop)
      - variabel lain (di kondisi, update, body) wajib sudah dideklarasikan
    Mengembalikan symbol table yang telah diperbarui.
    """
    if symtab is None:
        symtab = SymbolTable()

    # variabel kontrol loop dideklarasikan melalui init
    semantic_check_expr(ast.init.expr, symtab)
    symtab.declare(ast.init.target, "int")

    # kondisi harus memakai variabel yang sudah dikenal
    semantic_check_expr(ast.cond.left, symtab)
    semantic_check_expr(ast.cond.right, symtab)

    # update harus memakai variabel yang sudah dikenal
    if not symtab.is_declared(ast.update.target):
        raise SemanticError(f"Variabel '{ast.update.target}' digunakan sebelum dideklarasikan")
    if ast.update.expr is not None:
        semantic_check_expr(ast.update.expr, symtab)

    # body: setiap assignment memvalidasi RHS, lalu mendeklarasikan LHS jika baru
    for stmt in ast.body:
        semantic_check_expr(stmt.expr, symtab)
        if not symtab.is_declared(stmt.target):
            symtab.declare(stmt.target, "int")

    return symtab


# =========================================================================
# 4. GENERASI KODE ANTARA (THREE-ADDRESS CODE / TAC)
# =========================================================================

class TACGenerator:
    def __init__(self):
        self.code = []
        self.temp_count = 0
        self.label_count = 0

    def new_temp(self):
        self.temp_count += 1
        return f"t{self.temp_count}"

    def new_label(self):
        self.label_count += 1
        return f"L{self.label_count}"

    def emit(self, instr):
        self.code.append(instr)

    def gen_expr(self, node):
        """Menghasilkan TAC untuk ekspresi, mengembalikan nama variabel/temp hasil."""
        if isinstance(node, IdNode):
            return node.name
        if isinstance(node, NumNode):
            return node.value
        if isinstance(node, BinOpNode):
            left = self.gen_expr(node.left)
            right = self.gen_expr(node.right)
            temp = self.new_temp()
            self.emit(f"{temp} = {left} {node.op} {right}")
            return temp
        raise ValueError(f"Node ekspresi tidak dikenal: {node}")

    def gen_for(self, ast):
        # 1) inisialisasi
        init_val = self.gen_expr(ast.init.expr)
        self.emit(f"{ast.init.target} = {init_val}")

        label_start = self.new_label()
        label_end = self.new_label()

        self.emit(f"{label_start}:")

        # 2) evaluasi kondisi -> lompat keluar jika salah
        cond_left = self.gen_expr(ast.cond.left)
        cond_right = self.gen_expr(ast.cond.right)
        self.emit(f"ifFalse ({cond_left} {ast.cond.op} {cond_right}) goto {label_end}")

        # 3) badan perulangan
        for stmt in ast.body:
            val = self.gen_expr(stmt.expr)
            self.emit(f"{stmt.target} = {val}")

        # 4) update
        u = ast.update
        if u.op == "++":
            self.emit(f"{u.target} = {u.target} + 1")
        elif u.op == "--":
            self.emit(f"{u.target} = {u.target} - 1")
        elif u.op == "+=":
            val = self.gen_expr(u.expr)
            self.emit(f"{u.target} = {u.target} + {val}")
        elif u.op == "-=":
            val = self.gen_expr(u.expr)
            self.emit(f"{u.target} = {u.target} - {val}")
        elif u.op == "=":
            val = self.gen_expr(u.expr)
            self.emit(f"{u.target} = {val}")

        # 5) lompat kembali ke pengecekan kondisi
        self.emit(f"goto {label_start}")
        self.emit(f"{label_end}:")

        return self.code


def generate_tac(ast):
    """Tahap 4: menghasilkan Three-Address Code dari AST."""
    generator = TACGenerator()
    return generator.gen_for(ast)


# =========================================================================
# FUNGSI ORKESTRASI (menjalankan seluruh pipeline kompilasi)
# =========================================================================

def compile_for_loop(source_code, symtab=None, verbose=True):
    if verbose:
        print(f"\nSOURCE CODE:\n  {source_code}\n")

    # 1. Leksikal
    tokens = lexical_analysis(source_code)
    if verbose:
        print("=== 1. ANALISIS LEKSIKAL (TOKEN) ===")
        print(tokens)

    # 2. Sintaksis
    ast = syntax_analysis(tokens)
    if verbose:
        print("\n=== 2. ANALISIS SINTAKSIS (AST) ===")
        print(ast)

    # 3. Semantik
    symtab = semantic_analysis(ast, symtab)
    if verbose:
        print("\n=== 3. ANALISIS SEMANTIK ===")
        print("Status: VALID")
        print("Tabel Simbol:", symtab.symbols)

    # 4. Generasi TAC
    tac = generate_tac(ast)
    if verbose:
        print("\n=== 4. THREE-ADDRESS CODE (TAC) ===")
        print("\n".join(tac))

    return tokens, ast, symtab, tac


# =========================================================================
# CONTOH PENGGUNAAN / DEMO
# =========================================================================

if __name__ == "__main__":
    print("#" * 70)
    print("DEMO 1: For-loop VALID")
    print("#" * 70)
    source_valid = "for ( i = 0 ; i < 5 ; i++ ) { total = total + i }"
    symtab_awal = SymbolTable()
    symtab_awal.declare("total", "int")  # 'total' dideklarasikan di luar loop
    compile_for_loop(source_valid, symtab=symtab_awal)

    print("\n" + "#" * 70)
    print("DEMO 2: For-loop dengan KESALAHAN SEMANTIK (variabel belum dideklarasikan)")
    print("#" * 70)
    source_invalid = "for ( i = 0 ; i < 10 ; i = i + 1 ) { hasil = hasil + i }"
    try:
        compile_for_loop(source_invalid)
    except SemanticError as e:
        print(f"\n[SEMANTIC ERROR] {e}")

    print("\n" + "#" * 70)
    print("DEMO 3: For-loop dengan KESALAHAN SINTAKSIS")
    print("#" * 70)
    source_bad_syntax = "for ( i = 0 ; i < 5 i++ ) { total = total + i }"  # kurang ';'
    try:
        compile_for_loop(source_bad_syntax)
    except SyntaxErrorC as e:
        print(f"\n[SYNTAX ERROR] {e}")
