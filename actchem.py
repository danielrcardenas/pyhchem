
def add_bond_rule():
    """" Add a rule for reaction form a cuple of types an state particles to create a couple of
    attached particles"""
    return NotImplementedError


def add_unbond_rule():
    return NotImplementedError



def add_particles(n=1):
    return  NotImplementedError


def add_types():
    return NotImplementedError


def get_check_point_time():
    return NotImplementedError

chem_actions = [add_bond_rule, add_unbond_rule, add_particles, add_types, get_check_point_time]
