import draw_tree
from data.TCBL import family

for node in sorted(family.get_incomplete_nodes(4), key=lambda x: x.id):
    # print(node.id)
    if node.ignore:
        continue
    needs = []
    # print(node)
    # print(node.parent_complete)
    if not node.parent_complete:
        needs.append('parent')
    if not node.child_complete:
        needs.append('child')
    # if not node.spouse_complete:
    #     needs.append('spouse')
    print(f'{node.id: >3} {node.name} (needs {", ".join(needs)})')
    # break

# print(family.get(0))
# print(f'next id: {Person.curr_id}')

for i in range(8):
    print(i, len(family.explore(i)))

draw_tree.drawTree(family)

# print(family)
