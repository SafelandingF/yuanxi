"""Load the versioned, Git-shareable synthetic dataset (no runtime generation)."""

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ..domain.schemas import Profile

DATASET_PATH = Path(__file__).resolve().parents[2] / "datasets" / "candidates.json"


class SeedCandidate(Profile):
    id: int = Field(strict=True, ge=1)
    occupation: str = Field(min_length=1, max_length=50)
    color: Literal["sage", "sand", "clay"]
    quote: str = Field(min_length=1, max_length=200)
    detail: str = Field(min_length=1, max_length=500)
    budget: int = Field(strict=True, ge=30, le=500)
    food: Literal["清淡、不太辣", "素食友好", "都可以，爱尝鲜"]


class CandidateDataset(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal[1]
    dataset_version: str = Field(min_length=1)
    synthetic: Literal[True]
    description: str
    candidates: list[SeedCandidate] = Field(min_length=1)

    @model_validator(mode="after")
    def unique_ids(self):
        ids = [candidate.id for candidate in self.candidates]
        if len(ids) != len(set(ids)):
            raise ValueError("虚构候选数据集包含重复 ID")
        return self


def seed_candidates(path: Path = DATASET_PATH):
    data = CandidateDataset.model_validate(json.loads(path.read_text(encoding="utf-8")))
    return [candidate.model_dump(exclude={"note"}) for candidate in data.candidates]
