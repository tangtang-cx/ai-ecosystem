# Copyright (c) 2026 OceanBase.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Page-level captured Source for financial report PDFs.

Every physical page of a report becomes one captured Source, so a retrieval
citation resolves to the exact page a reviewer can open and check.
"""

from __future__ import annotations

import hashlib
import io
import math
from collections import Counter
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any
from urllib.parse import quote

from pydantic import BaseModel

from powercontext.limits import MAX_SOURCE_ID_LENGTH
from powercontext.sources import TEXT_EVIDENCE_PROJECTION_KEY, AdapterSourceDefinition, TextEvidence
from powercontext.sources.models import Source, SourceMaterialization

if TYPE_CHECKING:
    from powercontext.builtin.artifacts.memory.models import MemoryCitation

PDF_PAGE_SOURCE_NAME = "pdf-page"
PDF_PAGE_SOURCE_VERSION = "1"
PDF_PAGE_IDENTITY_PREFIX = "pdf:"


class PDFDocumentInput(BaseModel):
    """One complete PDF document addressed by a stable document identity."""

    document_id: str
    content: bytes


class PDFPageInput(BaseModel):
    """One physical page of a PDF document."""

    document_id: str
    document_sha256: str
    page_number: int
    text: str


class PDFPageSource(Source):
    """A captured PDF page that keeps its document revision and page number."""

    source_id: str
    document_id: str
    document_sha256: str
    page_number: int
    text: str


def pdf_page_source_id(document_id: str, document_sha256: str, page_number: int, /) -> str:
    """Build the stable, revision-aware identity of one PDF page."""

    identity = f"{PDF_PAGE_IDENTITY_PREFIX}{quote(document_id, safe='')}:{document_sha256}:{page_number}"
    if len(identity) > MAX_SOURCE_ID_LENGTH:
        # Keep the identity bounded without losing the document revision: the
        # digest covers the document identity and the exact bytes together.
        digest = hashlib.sha256(f"{document_id}:{document_sha256}".encode()).hexdigest()
        identity = f"{PDF_PAGE_IDENTITY_PREFIX}{digest}:{page_number}"
    return identity


def parse_pdf_document(value: PDFDocumentInput, /) -> tuple[PDFPageInput, ...]:
    """Parse every physical page of one PDF document.

    The whole document is parsed before any page is returned, so a corrupt
    document never yields a partial result.
    """

    document_id = value.document_id
    if not document_id.strip():
        raise ValueError("document_id must not be blank")  # noqa: TRY003
    if document_id != document_id.strip():
        raise ValueError("document_id must not contain leading or trailing whitespace")  # noqa: TRY003
    content = value.content
    if not content:
        raise ValueError("PDF content must not be empty")  # noqa: TRY003

    digest = hashlib.sha256(content).hexdigest()
    pages = _extract_pages(content)
    return tuple(
        PDFPageInput(
            document_id=document_id,
            document_sha256=digest,
            page_number=index,
            text=text,
        )
        for index, text in enumerate(pages, start=1)
    )


def _extract_pages(content: bytes, /) -> list[str]:
    """Extract the text of every physical page, failing atomically."""

    from pypdf import PdfReader

    try:
        reader = PdfReader(io.BytesIO(content))
        if reader.is_encrypted and not reader.decrypt(""):
            raise ValueError("PDF document requires a password")  # noqa: TRY003
        return [page.extract_text() or "" for page in reader.pages]
    except ValueError:
        raise
    except Exception as error:
        raise ValueError(f"PDF document could not be parsed: {error}") from error


async def search_pdf_pages(
    memory: Any,
    question: str,
    limit: int = 10,
) -> tuple["MemoryCitation", ...]:
    """Return the exact page citations that best answer one question.

    A financial report is a closed corpus of physical pages, so the ranking is
    computed over every page the Scope captured rather than over one truncated
    candidate pool. BM25 with corpus-level IDF rewards a page that contains one
    distinctive term over many pages that repeat the company name, and pages
    whose section heading matches the question are promoted. A question about a
    reported metric is answered by the primary financial statements, so their
    pages are reserved whenever the question asks for such a metric. When the
    Scope holds several reports, the report the question names is ranked on its
    own. Only distinct pages are returned.
    """

    if not isinstance(limit, int) or isinstance(limit, bool) or limit < 1:
        raise ValueError("limit must be a positive integer")  # noqa: TRY003
    if not question.strip():
        raise ValueError("question must contain non-whitespace content")  # noqa: TRY003

    core = _core_question(question)
    pages = await _page_inventory(memory)
    if not pages:
        # A Memory without page Sources has no corpus to rank; keep the lexical
        # route fusion that works for arbitrary entries.
        return await _search_by_routes(memory, core, question, limit)

    target: str | None = None
    if len({page.document for page in pages}) > 1:
        provisional = _rank_pages(pages, core)
        target = _target_document(pages, core, provisional)
    corpus = tuple(page for page in pages if page.document == target) if target is not None else pages
    ranked = _rank_pages(corpus, core)
    forced = _reserved_statements(corpus, ranked, core) if _asks_for_metric(core) else []
    return _select_pages(ranked, forced, limit)


@dataclass(frozen=True)
class _PDFPage:
    """One indexed page of the closed report corpus."""

    document: str
    page_number: int
    citation: Any
    citation_key: tuple[Any, ...]
    counts: Counter[str]
    keys: frozenset[str]
    headings: frozenset[str]
    statements: tuple[str, ...]
    length: int


async def _page_inventory(memory: Any) -> tuple[_PDFPage, ...]:
    """Read and index every captured page, reusing the index for the same head."""

    from powercontext.builtin.artifacts.memory.models import MemoryCitation
    from powercontext.builtin.artifacts.search import analyze_text

    listing = await memory.list()
    reference = listing.memory_ref
    if reference is None:
        return ()
    cache_key = (reference.family, reference.artifact_id, reference.revision)
    cached = _PDF_PAGE_CACHE.get(cache_key)
    if cached is not None:
        return cached

    pages: list[_PDFPage] = []
    for record in listing.entries:
        page_number: int | None = None
        document = ""
        for source in record.entry.sources:
            candidate = _page_number_of(source.source_id)
            if candidate is not None:
                page_number = candidate
                document = source.source_id.rsplit(":", 1)[0]
                break
        if page_number is None:
            continue
        tokens = analyze_text(record.entry.text).split()
        keys = tuple(_term_key(token) for token in tokens)
        headings, statements = _page_headings(record.entry.text, analyze_text)
        entry_ref = record.memory_ref
        pages.append(
            _PDFPage(
                document=document,
                page_number=page_number,
                citation=MemoryCitation(
                    memory_ref=entry_ref,
                    entry_id=record.entry.entry_id,
                    entry_version_id=record.entry.entry_version_id,
                ),
                citation_key=(
                    entry_ref.family,
                    entry_ref.artifact_id,
                    entry_ref.revision,
                    record.entry.entry_id,
                    record.entry.entry_version_id,
                ),
                counts=Counter(keys),
                keys=frozenset(keys),
                headings=headings,
                statements=statements,
                length=len(tokens),
            )
        )
    pages.sort(key=lambda page: (page.document, page.page_number))
    inventory = tuple(pages)
    if len(_PDF_PAGE_CACHE) >= _PDF_PAGE_CACHE_LIMIT:
        _PDF_PAGE_CACHE.pop(next(iter(_PDF_PAGE_CACHE)))
    _PDF_PAGE_CACHE[cache_key] = inventory
    return inventory


def _rank_pages(pages: tuple[_PDFPage, ...], core: str) -> list[tuple[float, str, int, _PDFPage]]:
    """Score every page with document-level BM25 plus a section-heading boost."""

    terms = _question_vocabulary(core)
    total = len(pages)
    document_frequency = {term: sum(1 for page in pages if term in page.keys) for term in terms}
    idf = {term: math.log(1 + total / (1 + document_frequency[term])) for term in terms}
    average_length = sum(page.length for page in pages) / max(total, 1) or 1.0

    scored: list[tuple[float, str, int, _PDFPage]] = []
    for page in pages:
        score = 0.0
        for term in terms:
            frequency = page.counts.get(term, 0)
            if not frequency:
                continue
            score += (
                idf[term]
                * frequency
                * (_PDF_BM25_K1 + 1)
                / (frequency + _PDF_BM25_K1 * (1 - _PDF_BM25_B + _PDF_BM25_B * page.length / average_length))
            )
        shared = [term for term in terms if term in page.headings and idf[term] > _PDF_HEADING_MIN_IDF]
        if len(shared) >= 2:
            score += _PDF_HEADING_WEIGHT * sum(idf[term] for term in shared)
        scored.append((score, page.document, page.page_number, page))
    scored.sort(key=lambda item: (-item[0], item[1], item[2]))
    return scored


def _select_pages(
    ranked: list[tuple[float, str, int, _PDFPage]],
    forced: list[_PDFPage],
    limit: int,
) -> tuple[Any, ...]:
    """Take reserved statement pages first, then the lexical ranking."""

    selected: list[Any] = []
    seen: set[tuple[Any, ...]] = set()

    def add(page: _PDFPage) -> None:
        if len(selected) >= limit:
            return
        if page.citation_key in seen:
            return
        seen.add(page.citation_key)
        selected.append(page.citation)

    for page in forced:
        add(page)
    for item in ranked:
        add(item[3])
    return tuple(selected)


def _target_document(
    pages: tuple[_PDFPage, ...],
    core: str,
    ranked: list[tuple[float, str, int, _PDFPage]],
) -> str | None:
    """Return the report a question is about, or ``None`` when it names none.

    A Scope may hold several reports, and their pages share most of the
    financial vocabulary. The report a question is about is the one that uses
    the question's own wording far more than the others do, so a registrant
    name or ticker identifies its report; a word that every report uses in the
    same measure does not.
    """

    documents = sorted({page.document for page in pages})
    if len(documents) <= 1:
        return documents[0] if documents else None
    vocabulary = set(_question_vocabulary(core))
    if not vocabulary:
        return None
    sizes: dict[str, int] = {document: 0 for document in documents}
    counts: dict[tuple[str, str], int] = {}
    cover_keys: dict[str, set[str]] = {document: set() for document in documents}
    for page in pages:
        sizes[page.document] += 1
        for term in vocabulary.intersection(page.keys):
            key = (page.document, term)
            counts[key] = counts.get(key, 0) + 1
        if page.page_number <= _PDF_COVER_PAGES:
            cover_keys[page.document].update(page.keys)
    identity: dict[str, float] = {document: 0.0 for document in documents}
    for term in vocabulary:
        coverage = {document: counts.get((document, term), 0) / sizes[document] for document in documents}
        best_document = max(coverage, key=lambda document: (coverage[document], document))
        best_coverage = coverage[best_document]
        if best_coverage < _PDF_IDENTITY_MIN_COVERAGE:
            continue
        others = max(coverage[document] for document in documents if document != best_document)
        if best_coverage >= others * _PDF_IDENTITY_COVERAGE_RATIO:
            identity[best_document] += 1.0
        elif len([document for document in documents if term in cover_keys[document]]) == 1:
            identity[best_document] += _PDF_IDENTITY_COVER_CREDIT
    ranked_documents = sorted(identity.items(), key=lambda item: (-item[1], item[0]))
    best, score = ranked_documents[0]
    runner_up = ranked_documents[1][1]
    if score < _PDF_IDENTITY_MIN or score < runner_up * _PDF_IDENTITY_MARGIN:
        return None
    if not _document_matches_question(best, ranked):
        return None
    return best


def _document_matches_question(document: str, ranked: list[tuple[float, str, int, _PDFPage]]) -> bool:
    """Check that the identified report also answers the question's wording."""

    best = 0.0
    for score, candidate, _page_number, _page in ranked:
        best = max(best, score)
    if best <= 0.0:
        return False
    for score, candidate, _page_number, _page in ranked:
        if candidate == document:
            return score >= best * _PDF_IDENTITY_SCORE_FLOOR
    return False


def _reserved_statements(
    corpus: tuple[_PDFPage, ...],
    ranked: list[tuple[float, str, int, _PDFPage]],
    core: str,
) -> list[_PDFPage]:
    """Return the primary financial-statement pages of the report in the corpus."""

    del core
    document = _dominant_document(corpus, ranked)
    if document is None:
        return []
    return [page for page in corpus if page.document == document and page.statements][:_PDF_STATEMENT_LIMIT]


def _dominant_document(
    corpus: tuple[_PDFPage, ...],
    ranked: list[tuple[float, str, int, _PDFPage]],
) -> str | None:
    documents = sorted({page.document for page in corpus})
    if len(documents) <= 1:
        return documents[0] if documents else None
    totals: dict[str, float] = {document: 0.0 for document in documents}
    counted: dict[str, int] = {document: 0 for document in documents}
    for score, document, _page_number, _page in ranked:
        if counted[document] < _PDF_DOCUMENT_TOP_PAGES:
            totals[document] += score
            counted[document] += 1
    ordered = sorted(totals.items(), key=lambda item: (-item[1], item[0]))
    if not ordered or ordered[0][1] <= 0.0:
        return None
    if len(ordered) > 1 and ordered[0][1] < ordered[1][1] * _PDF_DOCUMENT_MARGIN:
        return None
    return ordered[0][0]


def _asks_for_metric(core: str) -> bool:
    from powercontext.builtin.artifacts.search import analyze_text

    return bool(set(analyze_text(core).split()).intersection(_PDF_METRIC_TERMS))


def _question_vocabulary(core: str) -> tuple[str, ...]:
    """Return the normalized query vocabulary, including report section names."""

    from powercontext.builtin.artifacts.search import analyze_fts_query, analyze_text

    terms = list(analyze_fts_query(core).split())
    for phrase in _expansion_phrases(core):
        terms.extend(analyze_text(phrase).split())
    vocabulary: dict[str, str] = {}
    for term in terms:
        vocabulary.setdefault(_term_key(term), term)
    return tuple(vocabulary)


def _page_headings(text: str, analyze_text: Any) -> tuple[frozenset[str], tuple[str, ...]]:
    """Return the heading vocabulary and primary statement titles of one page."""

    headings: set[str] = set()
    statements: list[str] = []
    for raw in text.splitlines():
        line = " ".join(raw.split())
        if not line:
            continue
        words = line.split()
        if len(words) > _PDF_HEADING_MAX_WORDS or words[-1].isdigit():
            continue
        folded = line.casefold()
        if not folded.startswith(_PDF_HEADING_PREFIXES):
            continue
        headings.update(_term_key(token) for token in analyze_text(line).split())
        if folded.startswith(_PDF_STATEMENT_PREFIXES) and len(statements) < 1:
            statements.append(folded)
    return frozenset(headings), tuple(statements)


def _term_key(token: str) -> str:
    """Normalize a term for coverage matching without changing stored text.

    Retrieval compares the same surface form the lexical index stores, so only
    plural and year forms are folded; the first six characters absorb the
    report-vocabulary variants that differ by suffix (``geographies`` versus
    ``geographic``, ``statement`` versus ``statements``).
    """

    if token.startswith("fy") and token[2:] in _PDF_YEARS:
        return token[2:]
    if token in _PDF_YEARS:
        return token
    if len(token) > 4 and token.endswith("es"):
        token = token[:-2]
    elif len(token) > 3 and token.endswith("s") and not token.endswith("ss"):
        token = token[:-1]
    return token[:6]


async def _search_by_routes(
    memory: Any,
    core: str,
    question: str,
    limit: int,
) -> tuple["MemoryCitation", ...]:
    """Fuse short lexical probes when the Memory holds no indexed page corpus."""

    from powercontext.builtin.artifacts.memory.models import MemoryCitation
    from powercontext.builtin.artifacts.search import analyze_fts_query, analyze_text
    from powercontext.builtin.runtime import GetMemoryEntryRequest, SearchMemoryRequest

    terms = tuple(sorted(set(analyze_fts_query(core).split())))
    queries = _query_routes(core, question)

    # Each query recalls on its own vocabulary. Merging them into one long
    # query would raise the admission floor and dilute the ranking, so the
    # routes are fused by reciprocal rank instead.
    candidates: dict[str, tuple[float, int, MemoryCitation, str]] = {}
    for query_index, query in enumerate(queries):
        page = await memory.search(SearchMemoryRequest(query=query, mode="fts", limit=_PDF_CANDIDATE_LIMIT))
        for rank, hit in enumerate(page.hits):
            entry = await memory.get(
                GetMemoryEntryRequest(
                    citation=MemoryCitation(
                        memory_ref=hit.memory_ref,
                        entry_id=hit.entry_id,
                        entry_version_id=hit.entry_version_id,
                    )
                )
            )
            for reference in entry.entry.sources:
                contribution = 1.0 / (_PDF_RRF_K + rank + 1)
                known = candidates.get(reference.source_id)
                if known is not None:
                    candidates[reference.source_id] = (
                        known[0] + contribution,
                        known[1],
                        known[2],
                        known[3],
                    )
                    continue
                candidates[reference.source_id] = (
                    contribution,
                    query_index,
                    MemoryCitation(
                        memory_ref=hit.memory_ref,
                        entry_id=hit.entry_id,
                        entry_version_id=hit.entry_version_id,
                    ),
                    hit.text,
                )

    scored: list[tuple[int, float, str, MemoryCitation]] = []
    for source_id, (fusion, _route, citation, text) in candidates.items():
        matched = len(set(terms).intersection(analyze_text(text).split()))
        scored.append((-matched, -fusion, source_id, citation))
    scored.sort(key=lambda item: (item[0], item[1]))

    # Financial reports answered by a question are usually the section's first
    # page, while lexical ranking lands on the page that repeats the words. Add
    # the pages next to the strongest candidates so a section boundary does not
    # hide the annotated page.
    by_page: dict[int, tuple[str, MemoryCitation]] = {}
    for _matched, _fusion, source_id, citation in scored:
        page_number = _page_number_of(source_id)
        if page_number is not None:
            by_page.setdefault(page_number, (source_id, citation))
    selected: list[MemoryCitation] = []
    chosen: set[str] = set()
    for index, (_matched, _fusion, source_id, citation) in enumerate(scored):
        if len(selected) >= limit:
            break
        if source_id not in chosen:
            selected.append(citation)
            chosen.add(source_id)
        if index >= _PDF_NEIGHBOUR_SEEDS:
            continue
        page_number = _page_number_of(source_id)
        if page_number is None:
            continue
        for neighbour in (page_number - 1, page_number + 1):
            if len(selected) >= limit:
                break
            entry = by_page.get(neighbour)
            if entry is None or entry[0] in chosen:
                continue
            selected.append(entry[1])
            chosen.add(entry[0])
    return tuple(selected)


_PDF_RRF_K = 60
_PDF_NEIGHBOUR_SEEDS = 6
_PDF_CANDIDATE_LIMIT = 120
_PDF_BM25_K1 = 1.2
_PDF_BM25_B = 0.75
_PDF_HEADING_WEIGHT = 1.0
_PDF_HEADING_MIN_IDF = 0.5
_PDF_HEADING_MAX_WORDS = 16
_PDF_STATEMENT_LIMIT = 6
_PDF_DOCUMENT_TOP_PAGES = 3
_PDF_DOCUMENT_MARGIN = 1.5
_PDF_COVER_PAGES = 2
_PDF_IDENTITY_MIN = 1.0
_PDF_IDENTITY_MARGIN = 1.5
_PDF_IDENTITY_MIN_COVERAGE = 0.10
_PDF_IDENTITY_COVERAGE_RATIO = 3.0
_PDF_IDENTITY_COVER_CREDIT = 0.5
_PDF_IDENTITY_SCORE_FLOOR = 0.5
_PDF_PAGE_CACHE: dict[tuple[str, str, int], tuple[_PDFPage, ...]] = {}
_PDF_PAGE_CACHE_LIMIT = 8

_PDF_YEARS = frozenset(f"20{year:02d}" for year in range(0, 40))

# A financial report states the same fact in its own vocabulary: a question
# about "geographies" is answered by the "Properties" item, one about "legal
# battles" by "Legal Proceedings", and one about "EBITDA" by the consolidated
# statements. These are the standard section names, not per-question answers.
_FINANCIAL_VOCABULARY: tuple[tuple[tuple[str, ...], str], ...] = (
    (
        ("geograph", "region", "countr", "operates"),
        "geographic information geographic operations segment information properties locations facilities "
        "north america latin america europe asia pacific middle east africa",
    ),
    (("legal", "lawsuit", "litigation", "battle", "contingenc"), "legal proceedings contingencies commitments"),
    (
        ("ebitda", "margin", "profitab", "gross", "operating"),
        "operating income consolidated statement of income gross profit cost of sales",
    ),
    (
        ("capex", "expenditure", "intensive", "ppne", "property"),
        "capital expenditures property plant equipment",
    ),
    (("revenue", "sales", "turnover"), "net revenue consolidated statement of income"),
    (("debt", "borrow", "leverage"), "long-term debt borrowings credit facilities"),
    (("employee", "headcount", "staff"), "employees human capital"),
    (("dividend",), "dividends share repurchase"),
    (("risk", "uncertain"), "risk factors"),
    (("tax", "effective"), "income taxes effective tax rate"),
    (
        ("liquid", "quick", "working"),
        "current assets current liabilities short-term borrowings working capital",
    ),
    (
        ("customer", "concentration"),
        "concentrations of credit risk major customers significant customers",
    ),
    (("acqui", "merger", "mergers"), "business combinations acquisitions"),
    (("segment", "reportable"), "segment information reportable segments"),
    (("inventor",), "inventories cost of sales"),
    (("receivable",), "accounts receivable allowance"),
    (("goodwill", "impairment"), "goodwill impairment"),
)

# Every primary statement a report publishes, in the order an analyst reads them.
_PDF_STATEMENT_PREFIXES: tuple[str, ...] = (
    "consolidated statement",
    "consolidated balance",
    "combined statement",
    "combined balance",
    "statement of operations",
    "statements of operations",
    "statement of income",
    "statements of income",
    "statement of earnings",
    "statement of financial position",
    "balance sheet",
    "balance sheets",
    "statement of cash flows",
    "statements of cash flows",
)

# Headings that start a section rather than continue a paragraph. Keeping the
# list to report structure avoids promoting body text that merely repeats a term.
_PDF_HEADING_PREFIXES: tuple[str, ...] = (
    "item ",
    "part ",
    "consolidated statement",
    "consolidated balance",
    "combined statement",
    "combined balance",
    "notes to ",
    "note 1",
    "note 2",
    "management's discussion",
    "management’s discussion",
    "risk factors",
    "legal proceedings",
    "quantitative and qualitative",
    "controls and procedures",
    "selected financial data",
    "geographic",
    "business environment",
    "results of operations",
    "liquidity and capital resources",
)

# A question that asks for one of these quantities is answered by a primary
# financial statement; a narrative question is not, so the statements are only
# reserved when this vocabulary is present.
_PDF_METRIC_TERMS = frozenset(
    [
        "revenue",
        "sales",
        "margin",
        "ratio",
        "liquidity",
        "capital",
        "capex",
        "debt",
        "liability",
        "liabilities",
        "asset",
        "assets",
        "cash",
        "inventory",
        "tax",
        "cost",
        "costs",
        "expense",
        "expenses",
        "profit",
        "profitability",
        "earnings",
        "ebitda",
        "depreciation",
        "amortization",
        "ppne",
        "receivable",
        "receivables",
        "payable",
        "payables",
        "equity",
        "growth",
        "increase",
        "decrease",
        "change",
        "drove",
        "improve",
        "improving",
        "decline",
        "turnover",
        "gross",
        "operating",
        "net",
        "income",
        "fund",
        "finance",
        "financial",
        "intensive",
        "healthy",
    ]
)


def _page_number_of(source_id: str) -> int | None:
    """Read the physical page number out of this module's own identity format."""

    tail = source_id.rsplit(":", 1)[-1]
    return int(tail) if tail.isdigit() else None


def _expanded_question(core: str) -> str:
    """Append the report section names that answer this question's vocabulary."""

    phrases = _expansion_phrases(core)
    if not phrases:
        return core
    return f"{core} {' '.join(phrases)}"


def _expansion_phrases(core: str) -> list[str]:
    """Report the section-name phrases that answer this question's vocabulary."""

    words = core.casefold().split()
    return [
        expansion
        for triggers, expansion in _FINANCIAL_VOCABULARY
        if any(word.startswith(trigger) for trigger in triggers for word in words)
    ]


def _query_routes(core: str, question: str) -> list[str]:
    """Build the recall routes: the question plus short section-name probes.

    A probe of two terms only has to match one of them, so it reaches pages that
    repeat a section name but little else; a long combined query would raise that
    floor and drop those pages entirely.
    """

    routes = [core]
    for phrase in _expansion_phrases(core):
        words = phrase.split()
        if len(words) >= 2:
            routes.append(" ".join(words[:2]))
    expanded = _expanded_question(core)
    if expanded != core:
        routes.append(expanded)
    if question != core:
        routes.append(question)
    seen: set[str] = set()
    ordered: list[str] = []
    for route in routes:
        if route not in seen:
            seen.add(route)
            ordered.append(route)
    return ordered


def _core_question(question: str) -> str:
    """Keep the question the analyst asks, dropping the instruction tail."""

    marker = question.find("?")
    if marker < 0:
        return question
    core = question[: marker + 1].strip()
    return core or question


class PDFPageSourceAdapter:
    """Resolve and read the runtime's page-level PDF Source."""

    input_class = PDFPageInput
    name = PDF_PAGE_SOURCE_NAME
    source_class = PDFPageSource

    async def resolve(self, value: PDFPageInput, /) -> PDFPageSource:
        source_id = pdf_page_source_id(value.document_id, value.document_sha256, value.page_number)
        return PDFPageSource(
            name=source_id,
            source_id=source_id,
            materialization=SourceMaterialization.CAPTURED,
            document_id=value.document_id,
            document_sha256=value.document_sha256,
            page_number=value.page_number,
            text=value.text,
        )

    async def read(self, source: PDFPageSource, /) -> PDFPageInput:
        return PDFPageInput(
            document_id=source.document_id,
            document_sha256=source.document_sha256,
            page_number=source.page_number,
            text=source.text,
        )


class PDFPageTextEvidenceProjection:
    """Expose one PDF page as standard textual evidence."""

    name = TEXT_EVIDENCE_PROJECTION_KEY.name
    version = TEXT_EVIDENCE_PROJECTION_KEY.version
    source_class = PDFPageSource
    output_class: type[BaseModel] = TextEvidence

    def project(self, source: PDFPageSource, /) -> TextEvidence:
        return TextEvidence(
            source_type=PDF_PAGE_SOURCE_NAME,
            source_id=source.source_id,
            content=f"{source.document_id}\n{source.text}",
            metadata={
                "document_id": source.document_id,
                "document_sha256": source.document_sha256,
                "page_number": source.page_number,
            },
        )


PDF_PAGE_SOURCE_ADAPTER = PDFPageSourceAdapter()
PDF_PAGE_SOURCE_DEFINITION: AdapterSourceDefinition[PDFPageInput, PDFPageSource, PDFPageInput] = AdapterSourceDefinition(
    PDF_PAGE_SOURCE_ADAPTER,
    version=PDF_PAGE_SOURCE_VERSION,
    projections=(PDFPageTextEvidenceProjection(),),
)


__all__ = [
    "PDF_PAGE_SOURCE_DEFINITION",
    "PDF_PAGE_SOURCE_NAME",
    "PDFDocumentInput",
    "PDFPageInput",
    "PDFPageSource",
    "parse_pdf_document",
    "pdf_page_source_id",
    "search_pdf_pages",
]
