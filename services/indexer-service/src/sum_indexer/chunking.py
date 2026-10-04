from __future__ import annotations

import hashlib
from uuid import UUID, uuid5

from sum_contracts.models import Chunk, EmbeddingProfile, Metadata, Page, ServiceError

from .ports import Tokenizer

PIPELINE_VERSION = "institutional-v1"


class HuggingFaceTokenizer:
    def __init__(self, model: str, revision: str):
        from huggingface_hub import hf_hub_download
        from tokenizers import Tokenizer as HFTokenizer

        path = hf_hub_download(model, "tokenizer.json", revision=revision)
        self.tokenizer = HFTokenizer.from_file(path)
        self.tokenizer.no_truncation()
        self.tokenizer.no_padding()

    def count(self, text: str) -> int:
        return len(self.tokenizer.encode(text).ids)

    def split(self, text: str, limit: int, overlap: int) -> list[str]:
        encoding = self.tokenizer.encode(text, add_special_tokens=False)
        offsets = encoding.offsets
        pieces = []
        for start in range(0, len(offsets), limit - overlap):
            end = min(start + limit, len(offsets))
            pieces.append(text[offsets[start][0] : offsets[end - 1][1]])
            if end == len(offsets):
                break
        return pieces


class DocumentChunker:
    def __init__(self, tokenizer: Tokenizer, profile: EmbeddingProfile, tokens: int, overlap: int):
        self.tokenizer, self.profile, self.tokens, self.overlap = (
            tokenizer,
            profile,
            tokens,
            overlap,
        )

    def chunks(
        self, job_id: str, metadata: Metadata, pages: list[Page], ordinal: int = 0
    ) -> list[Chunk]:
        header = metadata.titulo + "\n"
        budget = min(
            self.tokens,
            self.profile.max_tokens
            - self.tokenizer.count(self.profile.passage_prefix + header)
            - 4,
        )
        if budget <= self.overlap:
            raise ServiceError(
                "MODELO_INCOMPATIBLE", "El título supera el presupuesto de tokens del modelo."
            )
        result = []
        for page in pages:
            for block in page.blocks:
                for piece in self.tokenizer.split(block.text, budget, self.overlap):
                    text = header + piece.strip()
                    count = self.tokenizer.count(self.profile.passage_prefix + text)
                    if count > self.profile.max_tokens:
                        raise ServiceError(
                            "MODELO_INCOMPATIBLE", "Un fragmento supera el límite del modelo."
                        )
                    identity = (
                        f"{PIPELINE_VERSION}:{ordinal}:{hashlib.sha256(text.encode()).hexdigest()}"
                    )
                    locator = f"página {page.number}, {block.locator}"
                    result.append(
                        Chunk(
                            str(uuid5(UUID(job_id), identity)),
                            text,
                            page.number,
                            locator,
                            ordinal,
                            {
                                **metadata.to_dict(),
                                "metodo_extraccion": "ocr" if page.ocr else "texto",
                                "tipo_bloque": block.kind,
                            },
                            count,
                        )
                    )
                    ordinal += 1
        return result
