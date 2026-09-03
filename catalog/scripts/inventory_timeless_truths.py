#!/usr/bin/env python3
"""Inventory every Timeless Truths hymn work and MusicXML score setting.

The site catalogs hymn texts (works) separately from one or more tune settings.
This inventory preserves both identities, gates text and score rights
independently, pins every eligible MusicXML payload, and records enough
structure to choose deterministic promotion paths later.
"""

from __future__ import annotations

import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import date
from fractions import Fraction
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
from threading import Lock
import time
import unicodedata
from urllib.error import HTTPError, URLError
from urllib.parse import unquote, urljoin, urlparse
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

from normalize_satb_musicxml import (
    SatbNormalizationError,
    TIMELESS_TRUTHS_NORMALIZER_NAME,
    normalize_timeless_truths_musicxml,
)


INDEX_URL = (
    "https://library.timelesstruths.org/music/_/"
    "?section=_&sortby=title"
)
DATASET_ID = "timeless-truths-public-domain"
PUBLIC_DOMAIN_MARK_URL = "https://creativecommons.org/publicdomain/mark/1.0/"
USER_AGENT = (
    "Transposify catalog audit/1.0 "
    "(+https://github.com/jtpereyda/music-app)"
)
EXPECTED_WORK_COUNT = 1857
EXPECTED_SCORE_COUNT = 1895
EXPECTED_STRICT_PUBLIC_DOMAIN_COUNT = 1869


class TimelessTruthsInventoryError(ValueError):
    """Raised when source data cannot form a deterministic inventory."""


@dataclass(frozen=True)
class WorkReference:
    ordinal: int
    slug: str
    page_url: str


class _RateLimiter:
    def __init__(self, delay: float) -> None:
        self.delay = max(0.0, delay)
        self._lock = Lock()
        self._next_start = 0.0

    def wait(self) -> None:
        if self.delay == 0:
            return
        with self._lock:
            now = time.monotonic()
            wait_for = self._next_start - now
            if wait_for > 0:
                time.sleep(wait_for)
            self._next_start = time.monotonic() + self.delay


def _clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.replace("\xa0", " ")).strip()


def _slug(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "-", ascii_value.lower()).strip("-")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _direct_child(element: ET.Element, name: str) -> ET.Element | None:
    return next(
        (child for child in element if _local_name(child.tag) == name),
        None,
    )


def _direct_children(element: ET.Element, name: str) -> list[ET.Element]:
    return [child for child in element if _local_name(child.tag) == name]


def _first_text(root: ET.Element, name: str) -> str:
    return next(
        (
            (element.text or "").strip()
            for element in root.iter()
            if _local_name(element.tag) == name
        ),
        "",
    )


_PITCH_CLASSES = {
    "C": 0,
    "D": 2,
    "E": 4,
    "F": 5,
    "G": 7,
    "A": 9,
    "B": 11,
}


def _pitch_number(note: ET.Element) -> int | None:
    pitch = _direct_child(note, "pitch")
    if pitch is None:
        return None
    step = _first_text(pitch, "step")
    octave = _first_text(pitch, "octave")
    alter = _first_text(pitch, "alter") or "0"
    if step not in _PITCH_CLASSES or not octave:
        return None
    return (int(octave) + 1) * 12 + _PITCH_CLASSES[step] + int(float(alter))


def _fraction_label(value: Fraction) -> str:
    return f"{value.numerator}/{value.denominator}"


def _music_fingerprint(root: ET.Element) -> str:
    """Hash SATB events independently of key and source formatting."""
    all_events: list[tuple[int, str, int, Fraction, Fraction, int | None]] = []
    for part_index, part in enumerate(_direct_children(root, "part")):
        divisions = 1
        for measure_index, measure in enumerate(_direct_children(part, "measure")):
            attributes = _direct_child(measure, "attributes")
            if attributes is not None:
                division_text = _first_text(attributes, "divisions")
                if division_text:
                    divisions = int(division_text)
            cursor = Fraction(0)
            last_onset = Fraction(0)
            grouped: dict[
                tuple[str, Fraction, Fraction],
                list[int | None],
            ] = {}
            for child in measure:
                name = _local_name(child.tag)
                if name in {"backup", "forward"}:
                    duration_text = _first_text(child, "duration")
                    if duration_text:
                        duration = Fraction(int(duration_text), divisions)
                        cursor += duration if name == "forward" else -duration
                    continue
                if name != "note":
                    continue
                duration_text = _first_text(child, "duration")
                duration = (
                    Fraction(int(duration_text), divisions)
                    if duration_text
                    else Fraction(0)
                )
                is_chord = _direct_child(child, "chord") is not None
                onset = last_onset if is_chord else cursor
                if not is_chord:
                    last_onset = onset
                    cursor += duration
                voice = _first_text(child, "voice") or "1"
                grouped.setdefault((voice, onset, duration), []).append(
                    _pitch_number(child)
                )
            for (voice, onset, duration), pitches in grouped.items():
                for pitch in sorted(
                    pitches,
                    key=lambda value: -1 if value is None else value,
                ):
                    all_events.append(
                        (
                            part_index,
                            voice,
                            measure_index,
                            onset,
                            duration,
                            pitch,
                        )
                    )
    pitched = [event[5] for event in all_events if event[5] is not None]
    anchor = int(pitched[0]) if pitched else 0
    payload = [
        [
            part_index,
            voice,
            measure_index,
            _fraction_label(onset),
            _fraction_label(duration),
            None if pitch is None else pitch - anchor,
        ]
        for part_index, voice, measure_index, onset, duration, pitch in sorted(
            all_events,
            key=lambda event: (
                event[0],
                event[1],
                event[2],
                event[3],
                event[4],
                -1 if event[5] is None else event[5],
            ),
        )
    ]
    return _sha256(
        json.dumps(payload, separators=(",", ":")).encode("utf-8")
    )


def _rights_kind(label: str) -> str:
    normalized = _clean_text(label).casefold()
    if "public domain" in normalized:
        return "public_domain"
    if "cc license" in normalized:
        return "cc_license"
    if "for god's glory" in normalized or "for god’s glory" in normalized:
        return "for_gods_glory"
    if "personal use" in normalized:
        return "personal_use"
    if "uncertain" in normalized:
        return "uncertain"
    return "missing"


def parse_index(data: bytes, *, index_url: str = INDEX_URL) -> list[WorkReference]:
    html = data.decode("utf-8", errors="replace")
    relative_slugs = re.findall(
        r'href="(?:\.\./)+music/([^"/]+)/score/"',
        html,
    )
    slugs = list(dict.fromkeys(unquote(value) for value in relative_slugs))
    if not slugs:
        raise TimelessTruthsInventoryError("Music index contains no score links.")
    return [
        WorkReference(
            ordinal=ordinal,
            slug=slug,
            page_url=urljoin(index_url, f"../{slug}/"),
        )
        for ordinal, slug in enumerate(slugs, start=1)
    ]


class _WorkPageParser(HTMLParser):
    def __init__(self, page_url: str) -> None:
        super().__init__(convert_charrefs=True)
        self.page_url = page_url
        self.title = ""
        self.work_fields: dict[str, str] = {}
        self.scores: list[dict[str, str]] = []
        self._capture: tuple[str, str] | None = None
        self._buffer: list[str] = []

    def _begin(self, owner: str, field: str) -> None:
        self._capture = (owner, field)
        self._buffer = []

    def handle_starttag(
        self,
        tag: str,
        attrs_list: list[tuple[str, str | None]],
    ) -> None:
        attrs = dict(attrs_list)
        if tag == "br" and self._capture:
            self._buffer.append(" ")
        if tag == "h1" and "first" in (attrs.get("class") or "").split():
            self._begin("work", "title")
            return
        if tag == "p":
            classes = (attrs.get("class") or "").split()
            editable = attrs.get("data-editable") or ""
            if "scoretitle" in classes:
                self.scores.append(
                    {
                        "title": "",
                        "author_label": "",
                        "rights_label": "",
                        "key_label": "",
                        "meter": "",
                        "xml_url": "",
                    }
                )
                self._begin("score", "title")
                return
            match = re.fullmatch(r"tt3_(music|scores)\|.*\|([^|]+)", editable)
            if match:
                owner = "work" if match.group(1) == "music" else "score"
                field = match.group(2)
                mapped = {
                    "author": "author_label",
                    "copyright": "rights_label",
                    "keytone": "key_label",
                    "meter": "meter",
                    "scripture": "scripture",
                    "subject": "subjects",
                }.get(field)
                if mapped and (owner == "work" or self.scores):
                    self._begin(owner, mapped)
                    return
        if tag == "a" and self.scores:
            href = attrs.get("href") or ""
            if href.casefold().endswith(".xml"):
                self.scores[-1]["xml_url"] = urljoin(self.page_url, href)

    def handle_data(self, data: str) -> None:
        if self._capture:
            self._buffer.append(data)

    def handle_endtag(self, tag: str) -> None:
        if not self._capture:
            return
        owner, field = self._capture
        expected_tag = "h1" if field == "title" and owner == "work" else "p"
        if tag != expected_tag:
            return
        value = _clean_text("".join(self._buffer))
        if field == "title" and owner == "score":
            value = re.sub(r"\s*\[\.xml\]\s*$", "", value)
        if field == "key_label":
            value = re.sub(r"^Key:\s*", "", value)
        elif field == "meter":
            value = re.sub(r"^Meter:\s*", "", value)
        elif field == "subjects":
            value = re.sub(r"^Subjects?:\s*", "", value)
        elif field == "scripture":
            value = re.sub(r"^Scripture:\s*", "", value)
        if owner == "work":
            self.work_fields[field] = value
            if field == "title":
                self.title = value
        elif self.scores:
            self.scores[-1][field] = value
        self._capture = None
        self._buffer = []


def parse_work_page(data: bytes, *, page_url: str) -> dict[str, object]:
    parser = _WorkPageParser(page_url)
    parser.feed(data.decode("utf-8", errors="replace"))
    if not parser.title:
        raise TimelessTruthsInventoryError(f"Work page has no title: {page_url}")
    if not parser.scores:
        raise TimelessTruthsInventoryError(
            f"Work page has no score settings: {page_url}"
        )
    for score in parser.scores:
        if not score["title"] or not score["xml_url"]:
            raise TimelessTruthsInventoryError(
                f"Work page has an incomplete score setting: {page_url}"
            )
    return {
        "title": parser.title,
        "author_label": parser.work_fields.get("author_label", ""),
        "rights_label": parser.work_fields.get("rights_label", ""),
        "rights_kind": _rights_kind(
            parser.work_fields.get("rights_label", "")
        ),
        "subjects": parser.work_fields.get("subjects", ""),
        "scripture": parser.work_fields.get("scripture", ""),
        "scores": [
            {
                **score,
                "rights_kind": _rights_kind(score["rights_label"]),
            }
            for score in parser.scores
        ],
    }


def _score_reference(xml_url: str) -> str:
    path = unquote(urlparse(xml_url).path)
    if not path.casefold().endswith(".xml"):
        raise TimelessTruthsInventoryError(
            f"Score reference is not MusicXML: {xml_url}"
        )
    return path.rsplit("/", 1)[-1][:-4]


def _arrangement_id(work_id: str, xml_url: str) -> str:
    reference = _slug(_score_reference(xml_url))
    if reference == work_id:
        return work_id
    suffix = re.sub(rf"^{re.escape(work_id)}-?", "", reference)
    return f"{work_id}-{suffix}" if suffix else work_id


def analyze_musicxml(data: bytes) -> dict[str, object]:
    try:
        root = ET.fromstring(data)
    except ET.ParseError as exc:
        raise TimelessTruthsInventoryError(f"invalid MusicXML: {exc}") from exc
    if _local_name(root.tag) != "score-partwise":
        raise TimelessTruthsInventoryError(
            f"expected score-partwise, found {_local_name(root.tag)}"
        )

    parts = _direct_children(root, "part")
    part_list = _direct_child(root, "part-list")
    part_names: dict[str, str] = {}
    if part_list is not None:
        for score_part in _direct_children(part_list, "score-part"):
            part_name = _direct_child(score_part, "part-name")
            part_names[score_part.get("id", "")] = (
                (part_name.text or "").strip() if part_name is not None else ""
            )

    voice_locations: set[tuple[int, str]] = set()
    lyric_locations: set[tuple[int, str]] = set()
    lyric_numbers: set[str] = set()
    part_voice_ids: list[list[str]] = []
    measure_counts: list[int] = []
    note_count = 0
    pitched_note_count = 0
    chord_note_count = 0
    lyric_count = 0
    for part_index, part in enumerate(parts):
        voices: set[str] = set()
        measure_counts.append(len(_direct_children(part, "measure")))
        for note in (
            element
            for element in part.iter()
            if _local_name(element.tag) == "note"
        ):
            note_count += 1
            voice_element = _direct_child(note, "voice")
            voice = (
                (voice_element.text or "").strip()
                if voice_element is not None
                else ""
            )
            if voice:
                voices.add(voice)
                voice_locations.add((part_index, voice))
            if _direct_child(note, "pitch") is not None:
                pitched_note_count += 1
            if _direct_child(note, "chord") is not None:
                chord_note_count += 1
            lyrics = _direct_children(note, "lyric")
            if lyrics:
                lyric_locations.add((part_index, voice))
            lyric_count += len(lyrics)
            lyric_numbers.update(
                lyric.get("number", "") for lyric in lyrics if lyric.get("number")
            )
        part_voice_ids.append(sorted(voices))

    semantic_locations = {
        (0, "1"),
        (0, "2"),
        (1, "1"),
        (1, "2"),
    }
    aligned_measures = len(set(measure_counts)) <= 1
    soprano_lyrics = (0, "1") in lyric_locations
    if (
        len(parts) == 2
        and voice_locations == semantic_locations
        and aligned_measures
        and soprano_lyrics
    ):
        profile = "semantic_satb_two_staff"
    elif (
        len(parts) == 2
        and chord_note_count > 0
        and aligned_measures
        and soprano_lyrics
    ):
        profile = "sibelius_two_staff_chords"
    else:
        profile = "other"

    encoders = [
        (element.text or "").strip()
        for element in root.iter()
        if _local_name(element.tag) in {"encoder", "software"}
        and (element.text or "").strip()
    ]
    return {
        "aligned_measure_counts": aligned_measures,
        "chord_note_count": chord_note_count,
        "encoders": encoders,
        "fifths": _first_text(root, "fifths"),
        "lyric_count": lyric_count,
        "lyric_locations": [list(value) for value in sorted(lyric_locations)],
        "lyric_numbers": sorted(lyric_numbers),
        "measure_counts": measure_counts,
        "music_fingerprint_sha256": _music_fingerprint(root),
        "mode": _first_text(root, "mode"),
        "note_count": note_count,
        "part_count": len(parts),
        "part_names": [part_names.get(part.get("id", ""), "") for part in parts],
        "part_voice_ids": part_voice_ids,
        "pitched_note_count": pitched_note_count,
        "profile": profile,
        "work_title": _first_text(root, "work-title"),
    }


def _read_or_fetch(
    *,
    url: str,
    path: Path,
    limiter: _RateLimiter,
    retries: int = 4,
) -> tuple[bytes, bool]:
    if path.is_file():
        return path.read_bytes(), True
    last_error: Exception | None = None
    for attempt in range(retries):
        limiter.wait()
        try:
            request = Request(url, headers={"User-Agent": USER_AGENT})
            with urlopen(request, timeout=45) as response:
                data = response.read()
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
            return data, False
        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            last_error = exc
            time.sleep(0.75 * (attempt + 1))
    raise TimelessTruthsInventoryError(
        f"failed to retrieve {url}: {last_error}"
    )


def _page_cache_path(output_root: Path, work: WorkReference) -> Path:
    return output_root / "raw/pages" / f"{work.slug}.html"


def _xml_cache_path(output_root: Path, record: dict[str, object]) -> Path:
    return output_root / "raw/xml" / f"{record['arrangement_id']}.xml"


def inventory_collection(
    *,
    output_root: Path,
    index_url: str = INDEX_URL,
    index_file: Path | None = None,
    audit_date: str | None = None,
    max_workers: int = 4,
    request_delay: float = 0.15,
    limit: int | None = None,
    include_xml: bool = True,
    enforce_expected_counts: bool = True,
) -> dict[str, object]:
    limiter = _RateLimiter(request_delay)
    if index_file is not None:
        index_data = index_file.read_bytes()
    else:
        index_data, _ = _read_or_fetch(
            url=index_url,
            path=output_root / "raw/index.html",
            limiter=limiter,
        )
    works = parse_index(index_data, index_url=index_url)
    if enforce_expected_counts and len(works) != EXPECTED_WORK_COUNT:
        raise TimelessTruthsInventoryError(
            f"expected {EXPECTED_WORK_COUNT} work pages, found {len(works)}"
        )
    if limit is not None:
        works = works[:limit]

    work_results: dict[str, tuple[bytes, dict[str, object]]] = {}

    def load_work(work: WorkReference) -> tuple[WorkReference, bytes, dict[str, object]]:
        data, _ = _read_or_fetch(
            url=work.page_url,
            path=_page_cache_path(output_root, work),
            limiter=limiter,
        )
        return work, data, parse_work_page(data, page_url=work.page_url)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(load_work, work): work for work in works}
        for future in as_completed(futures):
            work, data, parsed = future.result()
            work_results[work.slug] = (data, parsed)

    records: list[dict[str, object]] = []
    for work in works:
        page_data, parsed = work_results[work.slug]
        work_id = _slug(work.slug)
        work_rights_kind = str(parsed["rights_kind"])
        scores = list(parsed["scores"])
        for score_ordinal, score in enumerate(scores, start=1):
            xml_url = str(score["xml_url"])
            arrangement_id = _arrangement_id(work_id, xml_url)
            record: dict[str, object] = {
                "arrangement_id": arrangement_id,
                "arrangement_label": score["title"],
                "composer_label": score["author_label"],
                "disposition": "pending_structure_audit",
                "key_label": score["key_label"],
                "meter": score["meter"],
                "page_file": f"raw/pages/{work.slug}.html",
                "page_ordinal": work.ordinal,
                "page_sha256": _sha256(page_data),
                "page_url": work.page_url,
                "score_ordinal": score_ordinal,
                "score_reference": _score_reference(xml_url),
                "score_rights_kind": score["rights_kind"],
                "score_rights_label": score["rights_label"],
                "source_url": xml_url,
                "text_author_label": parsed["author_label"],
                "title": parsed["title"],
                "work_id": work_id,
                "work_rights_kind": work_rights_kind,
                "work_rights_label": parsed["rights_label"],
            }
            if (
                work_rights_kind != "public_domain"
                or score["rights_kind"] != "public_domain"
            ):
                record.update(
                    disposition="rights_hold",
                    hold_reason=(
                        f"work={work_rights_kind}; "
                        f"score={score['rights_kind']}"
                    ),
                )
            records.append(record)

    arrangement_ids = [str(record["arrangement_id"]) for record in records]
    duplicates = sorted(
        value for value, count in Counter(arrangement_ids).items() if count > 1
    )
    if duplicates:
        raise TimelessTruthsInventoryError(
            f"duplicate arrangement IDs: {duplicates[:10]}"
        )
    if (
        enforce_expected_counts
        and limit is None
        and len(records) != EXPECTED_SCORE_COUNT
    ):
        raise TimelessTruthsInventoryError(
            f"expected {EXPECTED_SCORE_COUNT} score settings, found {len(records)}"
        )

    if include_xml:
        eligible = [
            record
            for record in records
            if record["disposition"] == "pending_structure_audit"
        ]

        def load_score(
            record: dict[str, object],
        ) -> tuple[
            str,
            bytes,
            dict[str, object],
            dict[str, object],
        ]:
            data, _ = _read_or_fetch(
                url=str(record["source_url"]),
                path=_xml_cache_path(output_root, record),
                limiter=limiter,
            )
            structure = analyze_musicxml(data)
            try:
                normalized = normalize_timeless_truths_musicxml(
                    data,
                    work_title=str(record["title"]),
                )
                normalized_structure = analyze_musicxml(normalized.data)
                if (
                    normalized_structure["profile"]
                    != "semantic_satb_two_staff"
                    or normalized_structure["chord_note_count"] != 0
                    or normalized_structure["lyric_locations"] != [[0, "1"]]
                ):
                    raise SatbNormalizationError(
                        "normalized score is not lyric-bearing semantic SATB"
                    )
                normalization: dict[str, object] = {
                    "name": TIMELESS_TRUTHS_NORMALIZER_NAME,
                    "normalized_sha256": _sha256(normalized.data),
                    "operations": list(normalized.operations),
                    "profile": "split_aligned_satb_dyads",
                    "status": "eligible",
                    "structure": normalized_structure,
                    "version": "1",
                }
            except SatbNormalizationError as exc:
                normalization = {
                    "error": str(exc),
                    "name": TIMELESS_TRUTHS_NORMALIZER_NAME,
                    "status": "unsupported",
                    "version": "1",
                }
            return (
                str(record["arrangement_id"]),
                data,
                structure,
                normalization,
            )

        score_results: dict[
            str,
            tuple[bytes, dict[str, object], dict[str, object]],
        ] = {}
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(load_score, record): record
                for record in eligible
            }
            for future in as_completed(futures):
                arrangement_id, data, structure, normalization = future.result()
                score_results[arrangement_id] = (
                    data,
                    structure,
                    normalization,
                )

        for record in eligible:
            data, structure, normalization = score_results[
                str(record["arrangement_id"])
            ]
            record["source_file"] = (
                f"raw/xml/{record['arrangement_id']}.xml"
            )
            record["source_sha256"] = _sha256(data)
            record["structure"] = structure
            record["normalization"] = normalization
            profile = structure["profile"]
            if normalization["status"] == "eligible":
                record["disposition"] = "straightforward_candidate"
            elif profile in {
                "semantic_satb_two_staff",
                "sibelius_two_staff_chords",
            }:
                record["disposition"] = "normalization_candidate"
            else:
                record.update(
                    disposition="structure_hold",
                    hold_reason=f"unsupported structure profile {profile}",
                )

    disposition_counts = Counter(str(record["disposition"]) for record in records)
    strict_pd_count = sum(
        record["work_rights_kind"] == "public_domain"
        and record["score_rights_kind"] == "public_domain"
        for record in records
    )
    if (
        enforce_expected_counts
        and limit is None
        and strict_pd_count != EXPECTED_STRICT_PUBLIC_DOMAIN_COUNT
    ):
        raise TimelessTruthsInventoryError(
            "strict public-domain count drifted: "
            f"{strict_pd_count} != {EXPECTED_STRICT_PUBLIC_DOMAIN_COUNT}"
        )

    inventory: dict[str, object] = {
        "audit_date": audit_date or date.today().isoformat(),
        "dataset_id": DATASET_ID,
        "index": {
            "file": "raw/index.html",
            "sha256": _sha256(index_data),
            "url": index_url,
            "work_count": len(works),
        },
        "public_domain_mark_url": PUBLIC_DOMAIN_MARK_URL,
        "records": records,
        "schema_version": 1,
        "summary": {
            "score_settings": len(records),
            "strict_public_domain_musicxml": strict_pd_count,
            **dict(sorted(disposition_counts.items())),
        },
    }
    output_root.mkdir(parents=True, exist_ok=True)
    (output_root / "inventory.json").write_text(
        json.dumps(inventory, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return inventory


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--index-url", default=INDEX_URL)
    parser.add_argument("--index-file", type=Path)
    parser.add_argument("--audit-date")
    parser.add_argument("--max-workers", type=int, default=4)
    parser.add_argument("--request-delay", type=float, default=0.15)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--metadata-only", action="store_true")
    parser.add_argument("--allow-source-count-drift", action="store_true")
    args = parser.parse_args()
    try:
        inventory = inventory_collection(
            output_root=args.output_root.resolve(),
            index_url=args.index_url,
            index_file=args.index_file.resolve() if args.index_file else None,
            audit_date=args.audit_date,
            max_workers=args.max_workers,
            request_delay=args.request_delay,
            limit=args.limit,
            include_xml=not args.metadata_only,
            enforce_expected_counts=not args.allow_source_count_drift,
        )
    except (TimelessTruthsInventoryError, OSError, ValueError) as exc:
        print(f"Timeless Truths inventory failed: {exc}")
        return 2
    print(json.dumps(inventory["summary"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
