from pydantic import BaseModel, Field
from typing import Literal

class EvidenceItem(BaseModel):
    claim: str = Field(
        description="Claim directly supported by the research"
    )

    supporting_text: str = Field(
        description="Supporting information directly present in the research"
    )

    source_url: str = Field(
        description="Source URL associated with the evidence"
    )

    evidence_type: Literal[
        "statistic",
        "factual_claim",
        "projection"
    ] = Field(
        description="Type of evidence"
    )
