from collections import defaultdict
import re
from typing import DefaultDict, Iterable, Literal, Sequence, Union
import pygame
from pygame import sprite
from family_tree import Tree, Person, Relation, Gender, Family
from random import randrange
from numbers import Number
from PIL import Image
import time
from math import ceil
import sys

pygame.init()
font = pygame.font.Font(pygame.font.get_default_font(), 24)

generations = int(sys.argv[1]) if len(sys.argv) > 1 else 5
# generations = 3
screen_size = (1500, 900)

BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 0, 0)
GRAY = (240, 240, 240)
PERSON_COMPLETE = (200, 200, 200)
PERSON_CHECK = (250, 250, 150)
# \([0-9]+, [0-9]+, [0-9]+\)


class Vector:
    def __init__(self, point) -> None:
        self.values = list(point)

    def __iter__(self):
        return iter(self.values)

    def __getitem__(self, key):
        return self.values[key]

    def __setitem__(self, key, value):
        self.values[key] = value

    def __len__(self):
        return len(self.values)

    def __add__(self, other) -> 'Vector':

        if isinstance(other, Number):
            return Vector(
                [v + other for v in self]
            )

        if isinstance(other, Iterable):
            if len(self) != len(other):
                raise ValueError('Vectors must be same size')

            return Vector(
                [x + y for x, y in zip(self, other)]
            )

    def __sub__(self, other) -> 'Vector':

        if isinstance(other, Iterable):
            if len(self) != len(other):
                raise ValueError('Vectors must be same size')

            return Vector(
                [x - y for x, y in zip(self, other)]
            )

        elif isinstance(other, Number):
            return Vector(
                [v - other for v in self]
            )

    def __truediv__(self, other: Number):
        return Vector(
            [v / other for v in self]
        )

    def __str__(self) -> str:
        return f'Vector({self.values})'


class Node(pygame.sprite.Sprite):
    def __init__(self, person: Person, pos, offset):
        pygame.sprite.Sprite.__init__(self)
        self.person = person

        self.clicked = False
        self.click_offset = 0, 0
        self.pos = Vector(pos)
        self.redraw()

        self.update(offset, None)

    def redraw(self):
        # Create an image of the block, and fill it with a color.
        # This could also be an image loaded from the disk.
        self.text: pygame.Surface = font.render(
            self.person.name, True, BLACK)
        self.image = pygame.Surface(self.text.get_size())
        self.image.fill(GRAY)

        if self.person.name.endswith(' children'):
            color = PERSON_COMPLETE
        elif not self.person.child_complete:
            color = PERSON_CHECK
        elif self.person.double_check:
            color = PERSON_CHECK
        else:
            color = PERSON_COMPLETE

        pygame.draw.rect(
            self.image,
            color,
            (5, 5, *self.image.get_size()),
        )
        self.image.blit(self.text, (0, 0))

        # Fetch the rectangle object that has the dimensions of the image
        # Update the position of this object by setting the values of rect.x and rect.y
        self.rect = self.image.get_rect()

    def update(self, offset, mouse_pos):
        if self.clicked:
            self.pos = Vector((
                mouse_pos[0] - offset[0] + self.click_offset[0],
                mouse_pos[1] - offset[1] + self.click_offset[1]
            ))
            # self.rect.center = mouse_pos
        # else:
        self.rect.center = self.pos[0] + offset[0], self.pos[1] + offset[1]

    def click(self, mouse_pos):
        self.click_offset = (
            self.rect.centerx - mouse_pos[0],
            self.rect.centery - mouse_pos[1]
        )
        if self.rect.collidepoint(mouse_pos):
            self.clicked = True

    def unclick(self):
        self.clicked = False


def _draw(screen, offset: tuple[int, int], people: set[Person], nodeGroup):
    screen.fill(WHITE)
    # screen.blit(people[0].image, (0, 0))

    for i in range(generations+1):
        pygame.draw.rect(
            screen,
            GRAY,
            (0, i*300+offset[1]+40, screen.get_width(), 40)
        )

    # draw a black line from people to their parent(s)
    for person in people:
        allowed_parents = [p for p in person.parents if p in people]
        if len(allowed_parents) == 1:
            parent = allowed_parents[0]
            pygame.draw.line(
                screen, BLACK, person.sprite.rect.center, parent.sprite.rect.center)
        elif len(allowed_parents) == 2:
            parent0 = allowed_parents[0]
            parent1 = allowed_parents[1]
            new_pos = (Vector(parent0.sprite.rect.center) +
                        Vector(parent1.sprite.rect.center))/2
            pygame.draw.line(screen, BLACK,
                                person.sprite.rect.center, new_pos)

        for spouse in person.spouses:
            if spouse in people:
                pygame.draw.line(screen, RED, person.sprite.rect.center, spouse.sprite.rect.center, 3)

    nodeGroup.draw(screen)

    pygame.display.flip()


def drawTree(tree: Tree):

    offset: Vector = Vector(screen_size) / 2
    drag_screen = None

    people = tree.explore_blood(generations)
    print(f'{len(people)=}')

    generation_rows: DefaultDict[list[Person]] = defaultdict(list)
    # generation_rows: list[list[Person]] = [list() for i in range(generations+1)]
    tree.head.g = 0
    tree.head.pos = 0
    smallest_g = 0
    largest_g = 0
    tree.head.seen_path = []
    next_add = {tree.head}
    seen = {tree.head.id}

    generation_rows[0].append(tree.head)

    def add_left(person: Person, new: Person, update_path: bool=True):
        assert person.g == new.g
        new.pos = person.pos
        if update_path:
            new.seen_path = person.seen_path + [person]
        generation_rows[new.g].insert(person.pos, new)
        for p in generation_rows[person.g][person.pos+1:]:
            p.pos += 1

    def add_right(person: Person, new: Person, update_path: bool=True):
        assert person.g == new.g
        new.pos = person.pos+1
        if update_path:
            new.seen_path = person.seen_path + [person]
        generation_rows[new.g].insert(person.pos+1, new)
        for p in generation_rows[person.g][person.pos+2:]:
            p.pos += 1

    def add_parent(person: Person, new: Person):
        assert person.g + 1 == new.g
        # if there's no people yet
        if not len(generation_rows[new.g]):
            new.pos = 0 
            generation_rows[new.g].append(new)
            return

        # if they have a spouse
        for parent in person.parents:
            if not hasattr(parent, 'pos'):
                continue

            if new.gender == Gender.male:
                add_left(parent, new, False)
                return
            else:
                add_right(parent, new, False)
                return

        # if there's a person on their left
        for p in generation_rows[person.g][person.pos::-1]:
            value = None
            for p2 in p.parents:
                if hasattr(p2, 'pos'):
                    if value is None or p2.pos > value.pos:
                        value = p2
            if value is not None:
                add_right(value, new, False)
                return

        # if there's a person on their right
        for p in generation_rows[person.g][person.pos+1:]:
            value = None
            for p2 in p.parents:
                if hasattr(p2, 'pos'):
                    if value is None or p2.pos < value.pos:
                        value = p2
            if value is not None:
                add_left(value, new, False)
                return

    def get_child_row(person: Person, row: int, dir:Literal['left', 'right'], ignore=None) -> Union[None, Person]:
        if not hasattr(person, 'g'):
            return
        # if person.blood and any(p.blood for p in person.spouses):
        #     return
        if person == ignore:
            return
        if not hasattr(person, 'pos'):
            return
        if person.g == row:
            print('    gcr', row, '-> ', person.name)
            return person
        print('    gcr', row, person.name, f'(ignore {ignore if ignore is None else ignore.name})')
        children: list[Person] = []
        for child in person.children:
            rv = get_child_row(child, row, dir)
            if rv is not None:
                children.append(rv)
        if children:
            # print('looking at children', [c.name for c in children])
            if dir == 'left':
                return min(children, key=lambda x: x.pos)
            else:
                return max(children, key=lambda x: x.pos)

    def add_child(person: Person, new: Person):
        assert person.g - 1 == new.g
        print('\nadding child', new.name, 'from', person.name)
        print('path', [p.name for p in new.seen_path])
        # if there's no people yet
        if not len(generation_rows[new.g]):
            new.pos = 0
            generation_rows[new.g].append(new)
            return

        # if person.pos > 0 and generation_rows[person.g][person.pos-1] in person.seen_path:
        #     idx = person.seen_path.index(generation_rows[person.g][person.pos-1])
        #     print('checking left', [p.name for p in person.seen_path])
        #     if person.seen_path[idx-1].blood and any(p.blood for p in person.seen_path[idx-1].spouses):
        #         if person.seen_path[idx].sex == Sex.female:
        #             if person.seen_path[idx-1].sex == Sex.male:
        #                 add_left(person.seen_path[idx-1], new, False)
        #                 print('finished 0')
        #                 return
        # if person.pos < len(generation_rows[person.g]) - 1 and generation_rows[person.g][person.pos+1] in person.seen_path:
        #     print('checking right', [p.name for p in person.seen_path])
        #     idx = person.seen_path.index(generation_rows[person.g][person.pos+1])
        #     if person.seen_path[idx-1].blood and any(p.blood for p in person.seen_path[idx-1].spouses):
        #         if person.seen_path[idx].sex == Sex.male:
        #             if person.seen_path[idx-1].sex == Sex.female:
        #                 add_right(person.seen_path[idx-1], new, False)
        #                 print('finished 1')
        #                 return

        # if child is on the left
        for p in reversed(generation_rows[person.g][:person.pos]):
            print('checking left person', p.name)
            child = get_child_row(p, new.g, 'right')
            if child is not None:
                print('child of', p.name)

                if child.blood and any(p.blood for p in child.spouses):
                    # add_left(child, new, False)
                    continue
                else:
                    add_right(child, new, False)
                print('finished 2')
                return
        # if child is on the right
        for p in generation_rows[person.g][person.pos+1:]:
            print('checking left person', p.name)
            child = get_child_row(p, new.g, 'left')
            if child is not None:
                print('child of', p.name)

                if child.blood and any(p.blood for p in child.spouses):
                    # add_right(child, new, False)
                    continue
                else:
                    add_left(child, new, False)

                print('finished 3')
                return

        # last = None
        # for p1 in reversed(new.seen_path):
        #     p1: Person
        #     for p in p1.siblings:
        #         p: Person = p
        #         p: Person
        #         if p.pos < p1.pos:
        #             print('checking next person right', p.name)
        #             child = get_child_row(p, new.g, 'right', last)
        #             if child is not None:
        #                 child_parent = [cp for cp in child.parents if hasattr(cp, 'pos')]
        #                 new_parent = [cp for cp in new.parents if hasattr(cp, 'pos')]
        #                 # check if the rightmost child of this person in the 
        #                 #   chain is more left than the current persons parents
        #                 print('check', child.name)
        #                 if child_parent[0].pos < new_parent[0].pos:
        #                     closest = None
        #                     print('comparing right row', p.name)
        #                     # if we're adding to the left of the blood related person we
        #                     #   want to make sure there's no one on our right already left of it
        #                     for p2 in generation_rows[person.g][person.pos+1:]:
        #                         c2 = get_child_row(p2, new.g, 'left')
        #                         print('blood checking left of', p2.name)
        #                         if c2 is not None:
        #                             print('furthest left is', c2.name)
        #                             if c2.pos < child.pos:
        #                                 add_left(c2, new, False)
        #                                 print('finished 0 - 0')
        #                                 return
        #                             # break
        #                     if child.blood and any(p.blood for p in child.spouses):
        #                         add_left(child, new, False)
        #                         print('left of', child.name)
        #                     else:
        #                         add_right(child, new, False)
        #                         print('right of', child.name)
        #                     print('finished 0')
        #                     return
        #         elif p.pos > p1.pos:
        #             print('checking person left', p.name)
        #             child = get_child_row(p, new.g, 'left', last)
        #             if child is not None:
        #                 child_parent = [cp for cp in child.parents if hasattr(cp, 'pos')]
        #                 new_parent = [cp for cp in new.parents if hasattr(cp, 'pos')]
        #                 # check if the leftmost child of this person in the 
        #                 #   chain is more right than the current persons parents
        #                 print('check', child.name)
        #                 if child_parent[0].pos > new_parent[0].pos:
        #                     print('comparing left row', p.name)
        #                     # if we're adding to the right of the blood related person we
        #                     # want to make sure there's no one on our left already right of it
        #                     for p2 in reversed(generation_rows[person.g][:person.pos]):
        #                         c2 = get_child_row(p2, new.g, 'right')
        #                         print('blood checking right of', p2.name)
        #                         if c2 is not None:
        #                             print('furthest right is', c2.name)
        #                             if c2.pos > child.pos:
        #                                 add_right(c2, new, False)
        #                                 print('finished 1 - 0')
        #                                 return
        #                             # break
        #                     if child.blood and any(p.blood for p in child.spouses):
        #                         add_right(child, new, False)
        #                         print('right of', child.name)
        #                     else:
        #                         add_left(child, new, False)
        #                         print('left of', child.name)
        #                     print('finished 1')
        #                     return
        #     # child = get_child_row(p, new.g, 'left', last)
        #     # if child is not None:
        #     #     print('child of', p.name)
        #     #     if child.blood and any(p.blood for p in child.spouses):
        #     #         add_right(child, new, False)
        #     #     else:
        #     #         add_left(child, new, False)

        #     #     print('finished 1')
        #     #     return
        #     last = p1
        # assert False


        for p in reversed(new.seen_path):
            p: Person
            print(p.name, p.g, '==', new.g, end=' ')
            if p.g == new.g:
                if p.gender == Gender.male:
                    add_left(p, new, False)
                    print('finished 4')
                    return
                else:
                    add_right(p, new, False)
                    print('finished 5')
                    return


    while next_add:
        person = next_add.pop()
        smallest_g = min(person.g, smallest_g)
        largest_g = max(person.g, largest_g)
        for sibling in person.siblings:
            if sibling.id in seen:
                continue
            if sibling not in people:
                continue
            sibling.g = person.g
            sibling.seen_path = person.seen_path + [person]
            if person.gender == Gender.male:
                add_left(person, sibling)
            else:
                add_right(person, sibling)
                
            assert hasattr(sibling, 'pos')
            next_add.add(sibling)
            seen.add(sibling.id)

        for spouse in person.spouses:
            if spouse.id in seen:
                continue
            if spouse not in people:
                continue
            spouse.g = person.g
            spouse.seen_path = person.seen_path + [person]
            if person.gender == Gender.male:
                add_right(person, spouse)
            else:
                add_left(person, spouse)
                
            assert hasattr(spouse, 'pos')
            seen.add(spouse.id)

        for parent in person.parents:
            if parent.id in seen:
                continue
            if parent not in people:
                continue
            parent.ignore_tree = True
            parent.g = person.g + 1
            parent.seen_path = person.seen_path + [person]
            add_parent(person, parent)

            assert hasattr(parent, 'pos')
            next_add.add(parent)
            seen.add(parent.id)

        for child in person.children:
            if child.id in seen:
                continue
            if child not in people:
                continue
            child.g = person.g - 1
            child.seen_path = person.seen_path + [person]
            add_child(person, child)

            assert hasattr(child, 'pos')
            next_add.add(child)
            seen.add(child.id)

    people: list[Person] = []
        
    person_width = 300
    nodes = []
    generations_size = largest_g - smallest_g
    for generation in range(generations_size+1):
        print('gen', generation)
        print([p.name for p in generation_rows[generation+smallest_g]], sep=', ')
        for i, person in enumerate(generation_rows[generation+smallest_g]):
            people.append(person)
            person.sprite = Node(
                person,
                (
                    (i - len(generation_rows[generation+smallest_g])/2)*person_width,
                    # randrange(-3000, 3000),
                    (generations_size - generation+smallest_g) * 300 + 60
                ),
                offset,
            )
            nodes.append(person.sprite)

    print('total =', len(people))

    # for person in people:
    #     print(person.name)
    #     generation = tree.head.generation(person)
    #     path = tree.head.path(person)

    #     person.sprite = Node(
    #         person,
    #         (
    #             sort_people(path) * 500,
    #             # randrange(-3000, 3000),
    #             (generations - generation) * 300
    #         ),
    #         offset,
    #     )
    #     nodes.append(person.sprite)
    print('---done---')
    screen: pygame.Surface = pygame.display.set_mode(screen_size, pygame.RESIZABLE)
    nodeGroup = pygame.sprite.Group(nodes)

    repos = False

    while True:
        mouse = Vector(pygame.mouse.get_pos())
        if drag_screen is not None:
            diff = mouse - drag_screen
            view_offset = offset + diff
        else:
            view_offset = offset

        nodeGroup.update(view_offset, mouse)

        _draw(screen, view_offset, people, nodeGroup)

        for e in pygame.event.get():
            if e.type == pygame.MOUSEBUTTONDOWN:
                if e.button == pygame.BUTTON_RIGHT:
                    drag_screen = mouse
                elif e.button == pygame.BUTTON_LEFT:
                    for n in nodeGroup:
                        n.click(mouse)

            elif e.type == pygame.MOUSEBUTTONUP:
                if e.button == pygame.BUTTON_RIGHT and drag_screen is not None:
                    drag_screen = None
                    offset = view_offset
                elif e.button == pygame.BUTTON_LEFT:
                    for n in nodeGroup:
                        n.unclick()

            elif e.type == pygame.QUIT:
                pygame.quit()
                return
            elif e.type == pygame.KEYDOWN and e.key == pygame.K_h:
                for person in tuple(people):
                    if person.sprite.rect.collidepoint(mouse):
                        nodeGroup.remove(person.sprite)
                        people.remove(person)
                        for generation in range(generations_size+1):
                            generation_rows[generation+smallest_g].sort(key=lambda x:x.sprite.pos[0])
                            if person in generation_rows[generation+smallest_g]:
                                generation_rows[generation+smallest_g].remove(person)
            elif e.type == pygame.KEYDOWN and e.key == pygame.K_g:
                for person in tuple(people):
                    if person.sprite.rect.collidepoint(mouse):
                        any_children = False
                        for sib in person.siblings:
                            if sib.name.endswith(' children'):
                                sib.name = str(int(sib.name.split()[0]) + 1) + ' children'
                                any_children = True
                                sib.sprite.redraw()
                        if not any_children:
                            person.name = '1 children'
                            person.sprite.redraw()
                            break
                        nodeGroup.remove(person.sprite)
                        people.remove(person)
                        for generation in range(generations_size+1):
                            generation_rows[generation+smallest_g].sort(key=lambda x:x.sprite.pos[0])
                            if person in generation_rows[generation+smallest_g]:
                                generation_rows[generation+smallest_g].remove(person)
            elif e.type == pygame.KEYDOWN and e.key == pygame.K_r:
                for generation in range(generations_size+1):
                    # sort all rows based on their new positions
                    generation_rows[generation+smallest_g].sort(key=lambda x:x.sprite.pos[0])
                    if pygame.key.get_mods() & pygame.KMOD_CTRL:
                        for i, person in enumerate(generation_rows[generation+smallest_g]):
                            old = person.sprite.pos[0]
                            new = (i - len(generation_rows[generation+smallest_g]) / 2) * 300
                            person.sprite.pos[0] = new
                            person.sprite.rect.centerx += new - old
                    for i, person in enumerate(generation_rows[generation+smallest_g]):
                        person.sprite.pos[1] = (generations_size - generation+smallest_g) * 300 + 60
                        if person.sprite.pos[0] > 0:
                            if i > 0:
                                diff = person.sprite.rect.left - generation_rows[generation+smallest_g][i-1].sprite.rect.right - 40
                                if diff < 0 or pygame.key.get_mods() & pygame.KMOD_CTRL:
                                    person.sprite.pos[0] -= diff
                                    person.sprite.rect.x -= diff
                    for i, person in reversed(tuple(enumerate(generation_rows[generation+smallest_g]))):
                        person.sprite.pos[1] = (generations_size - generation+smallest_g) * 300 + 60
                        if person.sprite.pos[0] < 0:
                            if i < len(generation_rows[generation+smallest_g])-1:
                                diff = generation_rows[generation+smallest_g][i+1].sprite.rect.left - person.sprite.rect.right - 40
                                if diff < 0 or pygame.key.get_mods() & pygame.KMOD_CTRL:
                                    person.sprite.pos[0] += diff
                                    person.sprite.rect.x += diff
            elif e.type == pygame.KEYDOWN and e.key == pygame.K_s:
                rect = pygame.Rect(tree.head.sprite.rect)
                for node in nodeGroup:
                    rect.union_ip(node.rect)
                print(*rect.topleft, *rect.size)
                sub = screen.subsurface(screen.get_rect())
                print(offset)
                offset -= rect.topleft

                from PIL import Image
                im = Image.new(mode='RGB', size=rect.size)

                for y in range(ceil(rect.height / screen.get_height())):
                    for x in range(ceil(rect.width / screen.get_width())):
                        view_offset = offset - (x * screen.get_width(), y * screen.get_height())
                        # view_offset = offset - (x * 3, y * 3)
                        nodeGroup.update(view_offset, mouse)
                        # print(offset)
                        _draw(screen, view_offset, people, nodeGroup)
                        screenshot = pygame.image.tostring(sub, 'RGB')
                        im.paste(Image.frombytes('RGB', screen.get_size(), screenshot), (x * screen.get_width(), y * screen.get_height()))
                        # q = True
                        time.sleep(0.1)
                        pygame.event.get()

                im.save('screenshot.png')
                im.close()

