"""Mock org chart for demo purposes."""

from __future__ import annotations
from dataclasses import dataclass


@dataclass
class Person:
    name: str
    title: str
    slack_handle: str
    manager_name: str


# Keyed by author name as it appears in git log
ORG_CHART: dict[str, Person] = {
    "Kenji Watanabe": Person(
        name="Kenji Watanabe",
        title="Senior Software Engineer",
        slack_handle="kenji-w",
        manager_name="Hiroshi Nakamura",
    ),
    "Sara Chen": Person(
        name="Sara Chen",
        title="Software Engineer",
        slack_handle="sara-c",
        manager_name="Lisa Thompson",
    ),
    "Tomás Rivera": Person(
        name="Tomás Rivera",
        title="Staff Engineer",
        slack_handle="tomas-r",
        manager_name="Carlos Mendoza",
    ),
    "Yuki Tanaka": Person(
        name="Yuki Tanaka",
        title="Software Engineer",
        slack_handle="yuki-t",
        manager_name="Hiroshi Nakamura",
    ),
    # Managers
    "Hiroshi Nakamura": Person(
        name="Hiroshi Nakamura",
        title="Engineering Manager, Platform",
        slack_handle="hiroshi",
        manager_name="Akiko Sato",
    ),
    "Lisa Thompson": Person(
        name="Lisa Thompson",
        title="Engineering Manager, Integrations",
        slack_handle="lisa-t",
        manager_name="Akiko Sato",
    ),
    "Carlos Mendoza": Person(
        name="Carlos Mendoza",
        title="Engineering Manager, Core",
        slack_handle="carlos-m",
        manager_name="Akiko Sato",
    ),
    "Akiko Sato": Person(
        name="Akiko Sato",
        title="VP Engineering",
        slack_handle="akiko-s",
        manager_name="",
    ),
}


def lookup(author_name: str) -> Person | None:
    return ORG_CHART.get(author_name)


def manager_of(author_name: str) -> Person | None:
    person = ORG_CHART.get(author_name)
    if not person or not person.manager_name:
        return None
    return ORG_CHART.get(person.manager_name)
