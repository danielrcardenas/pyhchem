def bond(sim, index, other_index):
    """" Add a rule for reaction form a cuple of types an state particles to create a couple of
    attached particles"""
    my = sim.bonds[index]
    other = sim.bonds[other_index]
    if other_index not in my:
        my.append(other_index)
        other.append(index)


def unbond(sim,  index, other_index):
    my = sim.bonds[index]
    other = sim.bonds[other_index]
    if other_index in my: # if they are linked
        my.remove(other_index)
        other.remove(index)


def do_nothing(sim,  index, other_index):
    pass


def strengthen(sim,  index, other_index):
    return  NotImplementedError


def weaken (sim,  index, other_index):
    return NotImplementedError

particle_actions = [bond, unbond, do_nothing]
