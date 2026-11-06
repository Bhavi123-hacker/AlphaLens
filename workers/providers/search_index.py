"""In-memory current identity index. Never a historical membership/sector index."""

from dataclasses import dataclass, field

from alphalens_data.providers.multi_contracts import Instrument


def grams(text: str) -> set[str]:
    return {text[i : i + 3] for i in range(max(0, len(text) - 2))}


@dataclass
class InstrumentIndex:
    instruments: tuple[Instrument, ...]
    texts: list[str] = field(init=False)
    postings: dict[str, set[int]] = field(init=False, default_factory=dict)

    def __post_init__(self) -> None:
        self.texts = [
            "\n".join((i.symbol, i.isin or "", i.name or "", i.provider_key)).upper()
            for i in self.instruments
        ]
        for index, text in enumerate(self.texts):
            for gram in grams(text):
                self.postings.setdefault(gram, set()).add(index)

    def search(self, query: str, limit: int, offset: int) -> tuple[list[Instrument], int]:
        q = query.strip().upper()
        candidates = set(range(len(self.instruments)))
        for gram in grams(q):
            candidates.intersection_update(self.postings.get(gram, set()))
        matches = [self.instruments[i] for i in candidates if q in self.texts[i]]
        matches.sort(
            key=lambda i: (
                q not in {i.symbol.upper(), i.isin, i.provider_key.upper()},
                not i.symbol.upper().startswith(q),
                i.symbol,
                i.provider_key,
            )
        )
        return matches[offset : offset + limit], len(matches)
