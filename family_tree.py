from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import ClassVar, Union
import re

re_fix_enum = re.compile(r'<([\w\.]+): [^>]+>')


class Sex(Enum):
    male = 1
    female = 2
    other = 3
    unknown = 4


class Relation(Enum):
    parent = 1
    child = 2
    spouse = 3
    partner = 4
    sibling = 5
    step_sibling = 6
    adopted_child = 7
    adopted_parent = 8
    father = 9
    mother = 10
    son = 11
    daughter = 12

    def is_parent(self):
        return self in (
            Relation.parent,
            Relation.adopted_parent,
            Relation.father,
            Relation.mother,
        )

    def is_child(self):
        return self in (
            Relation.child,
            Relation.adopted_child,
            Relation.son,
            Relation.daughter,
        )

    def is_spouse(self):
        return self in (
            Relation.spouse,
            Relation.partner,
        )

@dataclass
class Family:
    """What relation one person has to another"""
    relation: Relation
    person_id: int
    person: 'Person' = None
    start: date = None
    end: date = None

    def __str__(self) -> str:
        if self.person is None:
            return repr(self)
        return f'Family({self.relation}, {self.person_id}, {repr(self.person.name)})'

    def __repr__(self) -> str:
        return f'Family({self.relation}, {self.person_id})'


@dataclass
class Person:
    """A person as seen inside a family tree"""
    name: str
    blood: bool = False
    sources: list[str] = field(default_factory=list)

    family: list[Family] = field(default_factory=list)

    dob: str = None
    dod: str = None

    sex: Sex = Sex.unknown

    child_complete: Union[date, bool] = False
    spouse_complete: Union[date, bool] = False
    double_check: bool = False
    ignore: bool = False

    notes: str = ''

    id: int = None
    curr_id: ClassVar[int] = 0
    seen_ids: ClassVar[set[int]] = set()

    def __post_init__(self) -> None:
        assert self.id not in Person.seen_ids

        if self.id is not None:
            Person.curr_id = max(self.id + 1, Person.curr_id)
        else:
            self.id = Person.curr_id
            Person.curr_id += 1
        
        Person.seen_ids.add(self.id)
        assert 0 <= len(self.parents) <= 2

    def generation(self, other: 'Person'):
        level: set[tuple['Person', int]] = {(self, 0)}
        next_level: set[tuple['Person', int]] = set()

        while True:
            for item in level:
                if other == item[0]:
                    return item[1]
            for person in level:
                for fam in person[0].parents:
                    next_level.add((fam.person, person[1]+1))
                for fam in person[0].children:
                    next_level.add((fam.person, person[1]-1))
            level = next_level
            next_level = set()

    def path(self, other: 'Person') -> tuple[Relation]:
        level: set[tuple['Person', tuple]] = {(self, tuple())}
        next_level: set[tuple['Person', tuple]] = set()

        while True:
            for item in level:
                if other == item[0]:
                    return item[1]
            for person in level:
                for fam in person[0].parents:
                    if fam.person.sex == Sex.male:
                        rel = Relation.father
                    elif fam.person.sex == Sex.female:
                        rel = Relation.mother
                    else:
                        rel = Relation.parent
                    next_level.add((fam.person, person[1]+(rel,)))
                for fam in person[0].children:
                    next_level.add((fam.person, person[1]+(Relation.child,)))
            level = next_level
            next_level = set()


    def __hash__(self) -> int:
        return self.id

    def save_str(self):
        out = repr(self)
        out = re_fix_enum.sub(r'\1', out)
        out = out.replace('datetime.', '')
        return out

    def __str__(self) -> str:
        fam = [
            str(f) for f in self.family
        ]
        sep = ',\n        '
        parts = [
            f"name={repr(self.name)}",
            f"id={self.id}",
            f"sources={self.sources}",
            f"family=[\n        {sep.join(str(f) for f in self.family)}\n    ]",
            f"dob={repr(self.dob)}",
            f"dod={repr(self.dod)}",
            f"sex={self.sex}",
            f"child_complete={repr(self.child_complete)}",
            f"spouse_complete={repr(self.spouse_complete)}",
            f"blood={self.blood}",
            f"notes={repr(self.notes)}",
        ]
        sep = ',\n    '
        return f"""Person(\n    {sep.join(parts)}\n)"""

    def __repr__(self) -> str:
        fam = [
            repr(f) for f in self.family
        ]
        sep = ',\n        '
        parts = [
            f"name={repr(self.name)}",
            f"id={self.id}",
            f"sources={self.sources}",
            f"family=[\n        {sep.join(str(f) for f in self.family)}\n    ]",
            f"dob={repr(self.dob)}",
            f"dod={repr(self.dod)}",
            f"sex={self.sex}",
            f"child_complete={repr(self.child_complete)}",
            f"spouse_complete={repr(self.spouse_complete)}",
            f"blood={self.blood}",
            f"notes={repr(self.notes)}",
        ]
        sep = ',\n    '
        return f"""Person(\n    {sep.join(parts)}\n)"""

    def __eq__(self, other: 'Person') -> bool:
        if type(self) != type(other):
            return False
        return self.id == other.id

    @property
    def parent_complete(self):
        return len(self.parents) == 2

    @property
    def complete(self):
        return self.parent_complete and self.child_complete

    @property
    def parents(self):
        return [
            f
            for f in self.family
            if f.relation.is_parent()
        ]

    @property
    def children(self):
        return [
            f
            for f in self.family
            if f.relation.is_child()
        ]

    @property
    def spouses(self):
        return [
            f
            for f in self.family
            if f.relation.is_spouse()
        ]

    @property
    def siblings(self):
        return [
            f
            for f in self.family
            if f.relation == Relation.sibling
        ]


class Tree:
    """A family tree"""
    def __init__(self, tree=None):
        self.tree: set[Person] = set() if tree is None else set(tree)
        self._head = None
        self.connect()
        self.fix()

    @property
    def head(self) -> Person:
        if self._head is None and self.tree:
            self._head = next(iter(self.tree))
        return self._head

    def set_head(self, head: Person):
        self._head = head

    def fix(self):
        for node in self.tree:
            for fam in node.family:
                if fam.person is None:
                    fam.person = self.get(fam.person_id)
                if fam.relation == Relation.parent:
                    if fam.person.sex == Sex.male:
                        fam.relation = Relation.father
                    elif fam.person.sex == Sex.female:
                        fam.relation = Relation.mother
        for node in self.explore():
            node.blood = True

    def connect(self):
        for node in self.tree:
            for family in node.family:
                rel = self.get(family.person_id)
                # make sure parents and children are bidirectional
                if family.relation.is_parent():
                    if not any(f.person_id == node.id for f in rel.family):
                        rel.family.append(
                            Family(Relation.child, node.id)
                        )
                if family.relation == Relation.child:
                    if not any(f.person_id == node.id for f in rel.family):
                        rel.family.append(
                            Family(Relation.parent, node.id)
                        )
                if family.relation == Relation.adopted_parent:
                    if not any(f.person_id == node.id for f in rel.family):
                        rel.family.append(
                            Family(Relation.adopted_child, node.id)
                        )
                if family.relation == Relation.adopted_child:
                    if not any(f.person_id == node.id for f in rel.family):
                        rel.family.append(
                            Family(Relation.adopted_parent, node.id)
                        )
                # make sure spouses are bidirectional
                if family.relation.is_spouse():
                    if not any(f.person_id == node.id for f in rel.family):
                        rel.family.append(
                            Family(Relation.spouse, node.id)
                        )
            # add sibling connector
            for node2 in self.tree:
                if node.id == node2.id:
                    continue
                node_parents = [f.person_id for f in node.family if f.relation.is_parent()]
                node2_parents = [f.person_id for f in node2.family if f.relation.is_parent()]

                same = len([x for x in node_parents if x in node2_parents])
                if same == 2:
                    node.family.append(
                        Family(Relation.sibling, node2.id)
                    )
                elif same == 1:
                    node.family.append(
                        Family(Relation.step_sibling, node2.id)
                    )

    def search_names(self, name: str) -> set[Person]:
        """Get a list of people who have a partial match to a name"""
        nodes: set[Person] = set()

        for node in self.tree:
            if name in node.name:
                nodes.add(node)

        return nodes

    def explore_all(self, levels=None) -> set[Person]:
        explore: set[Person] = {self.head}
        seen: set[Person] = set()
        next_nodes: set[Person] = set()
        nodes: set[Person] = set()

        if levels is None:
            levels = len(self.tree)

        for _ in range(levels+1):
            for node in explore:
                nodes.add(node)
                for fam in node.family:
                    if fam.relation.is_parent():
                        adding = fam.person
                        if adding not in seen:
                            next_nodes.add(adding)
                            seen.add(adding)

            explore = set()
            while next_nodes:
                node = next_nodes.pop()
                explore.add(node)
                for fam in node.family:
                    if fam.relation.is_child():
                        adding = fam.person
                        if adding not in seen:
                            next_nodes.add(adding)
                            seen.add(adding)

        return nodes

    def explore(self, levels=None) -> set[Person]:
        top: set[Person] = {self.head}
        seen: set[Person] = {self.head}
        next_nodes: set[Person] = set()
        nodes: set[Person] = set()

        nodes.add(self.head)

        if levels is None:
            levels = len(self.tree)

        for _ in range(levels):
            for node in set(top):
                nodes.add(node)
                next_nodes.add(node)
                for fam in node.family:
                    if fam.relation.is_parent():
                        adding = fam.person
                        if adding not in seen:
                            top.add(adding)
                            next_nodes.add(adding)
                            seen.add(adding)
                            nodes.add(adding)

            while next_nodes:
                node = next_nodes.pop()
                for fam in node.family:
                    if fam.relation.is_child():
                        adding = fam.person
                        if adding not in seen:
                            next_nodes.add(adding)
                            seen.add(adding)
                            nodes.add(adding)
                    # if fam.relation.is_spouse():
                    #     adding = fam.person
                    #     if adding not in seen:
                    #         seen.add(adding)
                    #         nodes.add(adding)

        return nodes


    def get_incomplete_nodes(self, levels=None) -> set[Person]:
        nodes: set[Person] = set()

        for node in self.explore(levels):
            # if not (node.parent_complete and node.child_complete and node.spouse_complete):
            if not (node.parent_complete and node.child_complete):
                # print(node.id, node.parent_complete, node.child_complete)
                nodes.add(node)

        return nodes

    def add(self, node: Person) -> None:
        self.tree.add(node)
        self.connect()
        self.fix()

    def get(self, id: int) -> Person:
        for node in self.tree:
            if node.id == id:
                return node

    def rename(self, old: int, new: int):
        for node in self.tree:
            if node.id == old:
                node.id = new
            for fam in node.family:
                if fam.person_id == old:
                    fam.person_id = new

    def __str__(self) -> str:
        return str(self.tree)

    def __contains__(self, other: Person) -> bool:
        return other in self.tree

    # def match(self, other: 'Tree', start: int, end: int) -> list[tuple[int, int]]:
    #     pass

    # def combine(self, other: 'Tree', start: int, end: int):
    #     new1 = Tree(self.tree)
    #     new2 = Tree(other.tree)

    #     return new1


    
