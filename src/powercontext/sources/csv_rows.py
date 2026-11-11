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

"""Row-level captured Source for offline CSV documents.

Every data row becomes one captured Source identified by its document and
primary-key value, so a retrieval citation can be resolved back to the exact
original record even after the rows are reordered or re-scored.
"""

from __future__ import annotations

import csv
import io
import json
from urllib.parse import quote

from pydantic import BaseModel, field_validator

from powercontext.limits import MAX_SOURCE_ID_LENGTH
from powercontext.sources import TEXT_EVIDENCE_PROJECTION_KEY, AdapterSourceDefinition, TextEvidence
from powercontext.sources.models import Source, SourceMaterialization

CSV_ROW_SOURCE_NAME = "csv-row"
CSV_ROW_SOURCE_VERSION = "1"
CSV_ROW_IDENTITY_PREFIX = "csv:"


class CSVDocumentInput(BaseModel):
    """One offline CSV document addressed by a stable document identity."""

    document_id: str
    primary_key: str
    content: bytes

    @field_validator("document_id")
    @classmethod
    def validate_document_id(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("document_id must not be blank")  # noqa: TRY003
        if value != value.strip():
            raise ValueError("document_id must not contain leading or trailing whitespace")  # noqa: TRY003
        return value

    @field_validator("primary_key")
    @classmethod
    def validate_primary_key(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("primary_key must not be blank")  # noqa: TRY003
        return value


class CSVRowInput(BaseModel):
    """One parsed CSV record with its header order and raw field values."""

    document_id: str
    primary_key: str
    primary_key_value: str
    columns: tuple[str, ...]
    values: tuple[str, ...]


class CSVRowSource(Source):
    """A captured CSV row that keeps the original column order and values."""

    source_id: str
    document_id: str
    primary_key: str
    primary_key_value: str
    columns: tuple[str, ...]
    values: tuple[str, ...]


def csv_row_source_id(document_id: str, primary_key_value: str, /) -> str:
    """Build the stable, delimiter-safe identity of one CSV row."""

    if not isinstance(document_id, str) or not document_id.strip():
        raise ValueError("document_id must be a non-empty string")  # noqa: TRY003
    if document_id != document_id.strip():
        raise ValueError("document_id must not contain leading or trailing whitespace")  # noqa: TRY003
    if not isinstance(primary_key_value, str) or not primary_key_value.strip():
        raise ValueError("primary_key_value must be a non-empty string")  # noqa: TRY003
    identity = (
        f"{CSV_ROW_IDENTITY_PREFIX}{quote(document_id, safe='')}:{quote(primary_key_value, safe='')}"
    )
    if len(identity) > MAX_SOURCE_ID_LENGTH:
        raise ValueError(f"CSV row identity must not exceed {MAX_SOURCE_ID_LENGTH} characters")  # noqa: TRY003
    return identity


def parse_csv_document(value: CSVDocumentInput, /) -> tuple[CSVRowInput, ...]:
    """Parse one offline CSV document into validated row inputs.

    The whole document is validated before any row is returned, so a malformed
    document never yields a partial result.
    """

    document_id = value.document_id
    primary_key = value.primary_key
    if not document_id.strip():
        raise ValueError("document_id must not be blank")  # noqa: TRY003
    if document_id != document_id.strip():
        raise ValueError("document_id must not contain leading or trailing whitespace")  # noqa: TRY003
    if not primary_key.strip():
        raise ValueError("primary_key must not be blank")  # noqa: TRY003

    text = value.content.decode("utf-8")
    if text.startswith("\ufeff"):
        text = text[1:]

    records = _read_records(text)
    if not records:
        raise ValueError("CSV document must contain a header row")  # noqa: TRY003

    columns = tuple(records[0])
    if not columns:
        raise ValueError("CSV header row must not be empty")  # noqa: TRY003
    for column in columns:
        if not column.strip():
            raise ValueError("CSV header names must not be blank")  # noqa: TRY003
    if len(set(columns)) != len(columns):
        raise ValueError("CSV header names must be unique")  # noqa: TRY003
    if primary_key not in columns:
        raise ValueError("primary_key must match one CSV header name exactly")  # noqa: TRY003

    key_index = columns.index(primary_key)
    width = len(columns)
    seen_keys: set[str] = set()
    rows: list[CSVRowInput] = []
    for record in records[1:]:
        if not record:
            continue
        if len(record) != width:
            raise ValueError("CSV rows must match the header width exactly")  # noqa: TRY003
        primary_key_value = record[key_index]
        if not primary_key_value.strip():
            raise ValueError("primary key values must not be blank")  # noqa: TRY003
        if primary_key_value in seen_keys:
            raise ValueError("primary key values must be unique within one document")  # noqa: TRY003
        seen_keys.add(primary_key_value)
        rows.append(
            CSVRowInput(
                document_id=document_id,
                primary_key=primary_key,
                primary_key_value=primary_key_value,
                columns=columns,
                values=tuple(record),
            )
        )
    return tuple(rows)


def _read_records(text: str) -> list[list[str]]:
    """Read CSV records with the fixed standard-library dialect semantics."""

    try:
        reader = csv.reader(
            io.StringIO(text, newline=""),
            delimiter=",",
            quotechar='"',
            doublequote=True,
            strict=True,
        )
        return list(reader)
    except csv.Error as error:
        raise ValueError(f"CSV document is malformed: {error}") from error


class CSVRowSourceAdapter:
    """Resolve and read the runtime's row-level CSV Source."""

    input_class = CSVRowInput
    name = CSV_ROW_SOURCE_NAME
    source_class = CSVRowSource

    async def resolve(self, value: CSVRowInput, /) -> CSVRowSource:
        source_id = csv_row_source_id(value.document_id, value.primary_key_value)
        return CSVRowSource(
            name=source_id,
            source_id=source_id,
            materialization=SourceMaterialization.CAPTURED,
            document_id=value.document_id,
            primary_key=value.primary_key,
            primary_key_value=value.primary_key_value,
            columns=value.columns,
            values=value.values,
        )

    async def read(self, source: CSVRowSource, /) -> CSVRowInput:
        return CSVRowInput(
            document_id=source.document_id,
            primary_key=source.primary_key,
            primary_key_value=source.primary_key_value,
            columns=source.columns,
            values=source.values,
        )


class CSVRowTextEvidenceProjection:
    """Expose one CSV row as standard textual evidence."""

    name = TEXT_EVIDENCE_PROJECTION_KEY.name
    version = TEXT_EVIDENCE_PROJECTION_KEY.version
    source_class = CSVRowSource
    output_class: type[BaseModel] = TextEvidence

    def project(self, source: CSVRowSource, /) -> TextEvidence:
        row = dict(zip(source.columns, source.values, strict=True))
        return TextEvidence(
            source_type=CSV_ROW_SOURCE_NAME,
            source_id=source.source_id,
            content=json.dumps(row, ensure_ascii=False, separators=(",", ":")),
            metadata={
                "document_id": source.document_id,
                "primary_key": source.primary_key,
                "primary_key_value": source.primary_key_value,
                "columns": list(source.columns),
                "row": row,
            },
        )


CSV_ROW_SOURCE_ADAPTER = CSVRowSourceAdapter()
CSV_ROW_SOURCE_DEFINITION: AdapterSourceDefinition[CSVRowInput, CSVRowSource, CSVRowInput] = AdapterSourceDefinition(
    CSV_ROW_SOURCE_ADAPTER,
    version=CSV_ROW_SOURCE_VERSION,
    projections=(CSVRowTextEvidenceProjection(),),
)


__all__ = [
    "CSV_ROW_SOURCE_DEFINITION",
    "CSV_ROW_SOURCE_NAME",
    "CSVDocumentInput",
    "CSVRowInput",
    "CSVRowSource",
    "csv_row_source_id",
    "parse_csv_document",
]
