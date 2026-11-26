"""The only live graph reads exposed to APM. IDs belong to the official fixtures."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Review:
    name: str
    target: str
    kind: str
    label: str
    source: str

    @property
    def query(self):
        return f"MATCH p=(a)-[:{self.kind}]->(b:{self.label} {{objectid: '{self.target}'}}) RETURN p"


REVIEWS = {
    "ad": Review("Domain Admins · Phantom", "S-1-5-21-2697957641-2271029196-387917394-512",
                 "MemberOf", "Group", "ad_sampledata.zip"),
    "entra": Review("Resource Group Admins", "D9EEF709-975D-4EE0-8D84-FFA9A1BAB9DD",
                    "AZMemberOf", "AZGroup", "entra_sampledata.zip"),
}


def authorize(name):
    if not isinstance(name, str) or name not in REVIEWS:
        raise PermissionError("Unknown review")
    return REVIEWS[name]
