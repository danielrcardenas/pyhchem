# = A clone of chemistry simulator. =
## A chemistry self assembly environment for searching parameter
import datetime
import math
import os
import re
import sys
import time

import numpy as np
import powerlaw
import pygame

from actchem import *
from particleChem import *
from rl import *


class HChemRule:
    def __init__(self, filename):
        self.cnt = 0
        self.num = None
        self.fill = []
        self.types = []
        self.map = {}
        self.color_count = 0
        self.colors = []
        self.colormap = {}
        self.wildcards = ['X', 'Y']
        self.wildstates = ['x', 'y']
        self.state_max = 10
        self.name = []
        self.ruleb = {}  # Rules for bounded pair
        self.ruleu = {}  # Rules for unbounded pair
        self.rule_texts = []
        self.colortable = [
            (0, 0, 0), (255, 0, 0), (0, 255, 0), (0, 0, 255),
            (255, 255, 0), (255, 0, 255), (0, 255, 255),
            (255, 127, 0), (255, 0, 127), (127, 255, 0), (127, 0, 255),
            (0, 255, 127), (0, 127, 255)
        ]

        self.parse(filename)
        for t in self.types:
            for s in range(0, self.state_max + 1):
                self.to_index(t, str(s))

    def gen_color(self, a):
        self.color_count += 1
        return self.colortable[(self.color_count - 1) % len(self.colortable)]

    def to_index(self, t, n):
        term = t + n
        if not term in self.map:
            self.map[term] = self.cnt
            self.colors.append(self.colormap[t])
            self.name.append(term)
            self.cnt += 1
        return self.map[term]

    def is_valid_type(self, term):
        if term in self.map:
            return True
        else:
            return False

    def get_index(self, term):
        return self.map[term]

    def get_name(self, idx):
        return self.name[idx]

    def parse_expr(self, str):
        if "-" in str:
            bnd = True
            M0, M1 = str.split("-")
        else:
            bnd = False
            output_reactants = str.split()
            if len(output_reactants) < 2:
                raise Exception("Too few reactants")
            M0 = output_reactants[0]
            M1 = output_reactants[1]
        p = re.search(r'([a-wzA-Z]+)(\d+|[xy])', M0)
        q = re.search(r'([a-wzA-Z]+)(\d+|[xy])', M1)
        return (p.group(1), p.group(2), q.group(1), q.group(2), bnd)

    def add_rule(self, L0, l0, L1, l1, lbnd, R0, r0, R1, r1, rbnd, prob):
        if l0 in self.wildstates and l1 in self.wildstates:
            if l0 == l1:
                for s in range(self.state_max + 1):
                    s = str(s)
                    _l0 = s
                    _l1 = s
                    if r0 == l0:
                        _r0 = s
                    else:
                        _r0 = r0
                    if r1 == l0:
                        _r1 = s
                    else:
                        _r1 = r1
                    self.add_rule(L0, _l0, L1, _l1, lbnd, R0, _r0, R1, _r1, rbnd, prob)
                return
            else:
                for s0 in range(self.state_max + 1):
                    for s1 in range(self.state_max + 1):
                        if l0 == l1 and s0 > s1: continue
                        s0 = str(s0)
                        s1 = str(s1)
                        _l0 = s0
                        _l1 = s1
                        if r0 == l0:
                            _r0 = s0
                        elif r0 == l1:
                            _r0 = s1
                        else:
                            _r0 = r0
                        if r1 == l0:
                            _r1 = s0
                        elif r1 == l1:
                            _r1 = s1
                        else:
                            _r1 = r1
                        self.add_rule(L0, _l0, L1, _l1, lbnd, R0, _r0, R1, _r1, rbnd, prob)
                return
        elif l0 in self.wildstates or l1 in self.wildstates:
            if l0 in self.wildstates:
                for s in range(self.state_max + 1):
                    s = str(s)
                    _l0 = s
                    if r0 == l0:
                        _r0 = s
                    else:
                        _r0 = r0
                    if r1 == l0:
                        _r1 = s
                    else:
                        _r1 = r1
                    self.add_rule(L0, _l0, L1, l1, lbnd, R0, _r0, R1, _r1, rbnd, prob)
                return
            else:
                for s in range(self.state_max + 1):
                    s = str(s)
                    _l1 = s
                    if r0 == l1:
                        _r0 = s
                    else:
                        _r0 = r0
                    if r1 == l1:
                        _r1 = s
                    else:
                        _r1 = r1
                    self.add_rule(L0, l0, L1, _l1, lbnd, R0, _r0, R1, _r1, rbnd, prob)
                return
        LL0 = self.to_index(L0, l0)
        LL1 = self.to_index(L1, l1)
        RR0 = self.to_index(R0, r0)
        RR1 = self.to_index(R1, r1)
        if lbnd:
            if not (LL0, LL1) in self.ruleb:
                self.ruleb[(LL0, LL1)] = []
                if LL0 != LL1:
                    self.ruleb[(LL1, LL0)] = []
            self.ruleb[(LL0, LL1)].append((RR0, RR1, rbnd, prob))
            if LL0 != LL1:
                self.ruleb[(LL1, LL0)].append((RR1, RR0, rbnd, prob))
        else:
            if not (LL0, LL1) in self.ruleu:
                self.ruleu[(LL0, LL1)] = []
                if LL0 != LL1:
                    self.ruleu[(LL1, LL0)] = []
            self.ruleu[(LL0, LL1)].append((RR0, RR1, rbnd, prob))
            if LL0 != LL1:
                self.ruleu[(LL1, LL0)].append((RR1, RR0, rbnd, prob))

    def parse_rule(self, line):
        try:
            lhs, rhs = line.split("->")
        except:
            return
        self.rule_texts.append(line)
        prob = 1.0
        if ":" in rhs:
            rhs, p = rhs.split(":")
            prob = eval(p.strip())
        try:
            L0, l0, L1, l1, lbnd = self.parse_expr(lhs.strip())
            R0, r0, R1, r1, rbnd = self.parse_expr(rhs.strip())
        except Exception as e:
            print("Error parsing line:", line)
            exit()
        if L0 in self.wildcards and L1 in self.wildcards:
            if L0 == L1:
                for t in self.types:
                    _L0 = t
                    _L1 = t
                    if R0 == L0:
                        _R0 = t
                    else:
                        _R0 = R0
                    if R1 == L0:
                        _R1 = t
                    else:
                        _R1 = R1
                    self.add_rule(_L0, l0, _L1, l1, lbnd, _R0, r0, _R1, r1, rbnd, prob)
            else:
                for t0 in self.types:
                    for t1 in self.types:
                        if l0 == l1 and t0 > t1: continue
                        _L0 = t0
                        _L1 = t1
                        if R0 == L0:
                            _R0 = t0
                        elif R0 == L1:
                            _R0 = t1
                        else:
                            _R0 = R0
                        if R1 == L0:
                            _R1 = t0
                        elif R1 == L1:
                            _R1 = t1
                        else:
                            _R1 = R1
                        self.add_rule(_L0, l0, _L1, l1, lbnd, _R0, r0, _R1, r1, rbnd, prob)
        elif L0 in self.wildcards or L1 in self.wildcards:
            if L0 in self.wildcards:
                for t in self.types:
                    _L0 = t
                    if R0 == L0:
                        _R0 = t
                    else:
                        _R0 = R0
                    if R1 == L0:
                        _R1 = t
                    else:
                        _R1 = R1
                    self.add_rule(_L0, l0, L1, l1, lbnd, _R0, r0, _R1, r1, rbnd, prob)
            else:
                for t in self.types:
                    _L1 = t
                    if R0 == L1:
                        _R0 = t
                    else:
                        _R0 = R0
                    if R1 == L1:
                        _R1 = t
                    else:
                        _R1 = R1
                    self.add_rule(L0, l0, _L1, l1, lbnd, _R0, r0, _R1, r1, rbnd, prob)
        else:
            self.add_rule(L0, l0, L1, l1, lbnd, R0, r0, R1, r1, rbnd, prob)

    def add_type(self, t):
        self.types.append(t)
        self.colormap[t] = self.gen_color(t)

    def setup_types(self, str):
        lhs, rhs = str.split(":")
        for t in rhs.split(","):
            self.add_type(t.strip())

    def setup_fill(self, str):
        lhs, rhs = str.split(":")
        for decl in rhs.split(","):
            t, p = decl.strip().split(" ")
            self.fill.append((t, eval(p)))

    def parse(self, filename):
        f = open(filename, "r")
        while True:
            line = f.readline()
            if not line: break
            if line[0] == '#': continue
            line = line.strip()
            if line.find("type") == 0:
                self.setup_types(line)
            elif line.find("number of particles") == 0:
                self.num = int(line.split(":")[1].strip())
            elif line.find("state max") == 0:
                self.state_max = int(line.split(":")[1].strip())
            elif line.find("fill") == 0:
                self.setup_fill(line)
            elif "->" in line:
                self.parse_rule(line)
        f.close()

    def check(self, L0, L1, bound):
        possible_reactions = []
        if bound:
            if (L0, L1) in self.ruleb:
                possible_reactions += self.ruleb[(L0, L1)]
        else:
            if (L0, L1) in self.ruleu:
                possible_reactions += self.ruleu[(L0, L1)]
        if len(possible_reactions) == 0:
            return None
        return possible_reactions


class HChem:
    # n   : number of particles
    # r   : radious of particles
    # v0  : initial velocity of particles
    # dt  : duration of one frame
    # k   : strength of bonds
    # w,h : width and height of the universe
    # seed: random seed
    def __init__(self, rules, particles_filename=None, n=1000, r=10, v0=None, dt=0.1,
                 width=1200, height=700, bucket_size=None, seed=None):
        self.rule = HChemRule(rules)
        if seed: np.random.seed(seed)
        if v0 == None: v0 = r
        if bucket_size == None: bucket_size = 2 * r

        self.n = n
        if self.rule.num is not None:
            self.n = self.rule.num
        self.r = r
        self.dt = dt
        self.w = width
        self.h = height
        self.speed = 1
        self.show_applied_rules = False
        self.randomize_rule_order = False
        self.state_max = self.rule.state_max
        self.R = 0  # The R hipotesis probe
        self.p = 0  # the p-value of the statistical distribution

        # Initialize positions of particles
        self.pos = np.zeros((n, 2))
        self.pos[:, 0] = np.random.uniform(r, width - r, n)
        self.pos[:, 1] = np.random.uniform(r, height - r, n)

        ##Create a set of q agents per state


        self.q_agents = [QLearningAgent(ParticleTypeMDP(self, i), Ne=5, Rplus=2,
                                        alpha=lambda n: 60. / (59 + n)) for i in range(self.n)]
        self.visited_agents = []
        self.chain_lengths = None

        # Initialize velocities of particles
        # N.B. this discards the velocities for particles files loaded on the command line
        direction = np.random.uniform(0, 2 * np.pi, n)
        self.vel = np.zeros((n, 2))
        self.vel[:, 0] = v0 * np.cos(direction)
        self.vel[:, 1] = v0 * np.sin(direction)

        # Initialize types
        self.types = np.zeros(n, dtype=int)
        for k in range(self.n):
            p = np.random.uniform(0, 1)
            q = 0
            for (t, r) in self.rule.fill:
                q += r
                if p < q:
                    self.types[k] = self.rule.get_index(t)
                    break
        self.stypes = np.zeros(n, dtype=object)  # n number of particles
        for k in range(self.n):
            self.stypes[k] = self.rule.get_name(self.types[k])

        # self.bonds[i] == list of indexes of particles which is bound to i.
        self.bonds = np.zeros(n, dtype=object)
        for i in range(n): self.bonds[i] = []

        # Initialize buckets for compute_collision detection
        self.bucket_size = bucket_size
        self.nbx = int(math.ceil(float(width) / bucket_size))
        self.nby = int(math.ceil(float(height) / bucket_size))
        self.buckets = np.zeros((self.nbx, self.nby), dtype=object)

        if particles_filename:
            self.load_particles(particles_filename)
            # Randomize velocities of particles
            # N.B. this discards the velocities for particles files loaded on the command line
            direction = np.random.uniform(0, 2 * np.pi, self.n)
            self.vel = np.zeros((self.n, 2))
            self.vel[:, 0] = v0 * np.cos(direction)
            self.vel[:, 1] = v0 * np.sin(direction)
            print("Randomizing velocites. If want stored velocities, reload the particles file.")

    def bucket_index(self, x):
        return (min(max(int(x[0] / self.bucket_size), 0), self.nbx - 1),
                min(max(int(x[1] / self.bucket_size), 0), self.nby - 1))

    def init_bucket(self):
        for i in range(self.nbx):
            for j in range(self.nby):
                self.buckets[i, j] = []
        for k in range(self.n):
            i, j = self.bucket_index(self.pos[k, :])
            self.buckets[i, j].append(k)

    def add_impulse_from_walls(self):
        r = self.r
        for k in range(self.n):
            x = self.pos[k, 0]
            y = self.pos[k, 1]
            vx = self.vel[k, 0]
            vy = self.vel[k, 1]
            if (x < r and vx < 0) or (x > self.w - r and vx > 0):
                self.vel[k, 0] += -2 * self.vel[k, 0]
                self.vel[k, 1] += 0
            if (y < r and vy < 0) or (y > self.h - r and vy > 0):
                self.vel[k, 0] += 0
                self.vel[k, 1] += -2 * self.vel[k, 1]

    def update_state_of_particle_pair(self, k, l):
        mdp = self.q_agents[k].mdp
        mdp.other_index = l
        run_single_trial(self.q_agents[k], mdp)
        #run_single_trial(self.q_agents[l], ParticleMDP(self, l,k))
        if l in self.bonds[k]:
            return True
        return False
        # is_bond =False
        #
        # if l in self.bonds[k]:
        #     is_bond = True
        # type_k = self.types[k]
        # if not self.visited_agents[type_k]:
        #     mdp = self.q_agents[type_k].mdp
        #     mdp.other_index = l
        #     self.visited_agents[type_k] = True
        #     run_single_trial(self.q_agents[type_k], mdp)
        #
        # type_l = self.types[l]
        # if not self.visited_agents[type_l]:
        #     mdp = self.q_agents[type_l].mdp
        #     mdp.other_index = k
        #     self.visited_agents[type_l] = True
        #     run_single_trial(self.q_agents[type_l], mdp)
        # LL0 = type_k
        # LL1 = type_l
        # RR0 = type_k
        # RR1 = type_l
        # if l in self.bonds[k] and not is_bond:
        #     if not (LL0, LL1) in self.ruleb:
        #         self.ruleb[(LL0, LL1)] = []
        #         if LL0 != LL1:
        #             self.ruleb[(LL1, LL0)] = []
        #     self.ruleb[(LL0, LL1)].append((RR0, RR1, rbnd, 1))
        #     if LL0 != LL1:
        #         self.ruleb[(LL1, LL0)].append((RR1, RR0, rbnd, 1))
        # else:
        #     if not (LL0, LL1) in self.ruleu:
        #         self.ruleu[(LL0, LL1)] = []
        #         if LL0 != LL1:
        #             self.ruleu[(LL1, LL0)] = []
        #     self.ruleu[(LL0, LL1)].append((RR0, RR1, rbnd, prob))
        #     if LL0 != LL1:
        #         self.ruleu[(LL1, LL0)].append((RR1, RR0, rbnd, prob))
        # if l in self.bonds[k]:
        #     # bound pair
        #     rules = self.rule.check(self.types[k], self.types[l], True)
        #
        #     if rules:
        #         if self.randomize_rule_order:
        #             np.random.shuffle(rules)
        #         for r in rules:
        #             p = r[3]
        #             if np.random.uniform(0, 1) < p:
        #                 if self.show_applied_rules:
        #                     print("apply:", )
        #                     print(self.rule.get_name(
        #                         self.types[k]), )  #### TODO: Ingresar aqui el q learning por cada accion
        #                     print("-", )
        #                     print(self.rule.get_name(self.types[l]), )
        #                     print(" -> ", )
        #                     print(self.rule.get_name(r[0]), )
        #                     if r[2]:
        #                         print("-", )
        #                     else:
        #                         print(" ", )
        #                     print(self.rule.get_name(r[1]))
        #                 self.types[k] = r[0]
        #                 self.types[l] = r[1]
        #                 if not r[2]:
        #                     self.bonds[k].remove(l)
        #                     self.bonds[l].remove(k)
        #                     return False
        #                 return True
        #     return True
        # else:
        #     # unbound pair
        #     rules = self.rule.check(self.types[k], self.types[l], False)
        #     if rules:
        #         if self.randomize_rule_order:
        #             np.random.shuffle(rules)
        #         for r in rules:
        #             p = r[3]
        #             if np.random.uniform(0, 1) < p:
        #                 if self.show_applied_rules:
        #                     print("apply:", )
        #                     print(self.rule.get_name(self.types[k]), )
        #                     print(" ", )
        #                     print(self.rule.get_name(self.types[l]), )
        #                     print(" -> ", )
        #                     print(self.rule.get_name(r[0]), )
        #                     if r[2]:
        #                         print("-", )
        #                     else:
        #                         print(" ", )
        #                     print(self.rule.get_name(r[1]))
        #                 self.types[k] = r[0]
        #                 self.types[l] = r[1]
        #                 if r[2]:
        #                     self.bonds[k].append(l)
        #                     self.bonds[l].append(k)
        #                     return True
        #                 return False
        #     return False

    def add_impulse_between_unbound_pair(self, k, l, rx, rv, d2):
        if self.update_state_of_particle_pair(k, l):
            return
        d = math.sqrt(d2)
        n = rx / d
        ldt = -n.dot(rv)
        self.vel[k, :] += ldt * n
        self.vel[l, :] -= ldt * n

    def add_impulse_between_bound_pair(self, k, l, rx, rv, d2):
        d = math.sqrt(d2)
        n = rx / d
        c = rx.dot(rv)
        # ldt = -(2*c + 3*(d2-4*self.r*self.r))/(8*d2)
        # self.vel[k,:] += 2*ldt*rx
        # self.vel[l,:] -= 2*ldt*rx
        if (d < 2 * self.r and c < 0) or (d > 2 * self.r and c > 0):
            ldt = -n.dot(rv)
            self.vel[k, :] += ldt * n
            self.vel[l, :] -= ldt * n

    def add_impulse_between_particles_sub(self, k, i, j):
        if i < 0 or j < 0 or i >= self.nbx or j >= self.nby: return
        for l in self.buckets[i, j]:
            if k >= l: continue
            rx = self.pos[k, :] - self.pos[l, :]
            rv = self.vel[k, :] - self.vel[l, :]
            if rx.dot(rv) >= 0: continue
            d2 = np.sum(rx * rx)
            if d2 > 4 * self.r * self.r: continue
            self.add_impulse_between_unbound_pair(k, l, rx, rv, d2)

    def add_impulse_between_particles(self):
        r = self.r

        # add impulse between unbound pairs
        for k in range(self.n):
            i, j = self.bucket_index(self.pos[k, :])
            self.add_impulse_between_particles_sub(k, i - 1, j)
            self.add_impulse_between_particles_sub(k, i - 1, j - 1)
            self.add_impulse_between_particles_sub(k, i - 1, j + 1)
            self.add_impulse_between_particles_sub(k, i, j - 1)
            self.add_impulse_between_particles_sub(k, i, j)
            self.add_impulse_between_particles_sub(k, i, j + 1)
            self.add_impulse_between_particles_sub(k, i + 1, j - 1)
            self.add_impulse_between_particles_sub(k, i + 1, j)
            self.add_impulse_between_particles_sub(k, i + 1, j + 1)

    def add_impulse_between_bound_particles(self):
        # add impulse between bound pairs
        for k in range(self.n):
            for l in self.bonds[k]:
                if k >= l: continue
                rx = self.pos[k, :] - self.pos[l, :]
                rv = self.vel[k, :] - self.vel[l, :]
                d2 = np.sum(rx * rx)
                self.add_impulse_between_bound_pair(k, l, rx, rv, d2)

    def compute_impulse(self):
        self.init_bucket()
        self.add_impulse_from_walls()
        self.add_impulse_between_particles()
        self.add_impulse_between_bound_particles()
        self.pos += self.vel * self.dt

    def change_speed(self, delta):
        self.speed += delta;
        if self.speed < 0:
            self.speed = 1

    def update(self):
        # Update position
        for k in range(self.speed):
            #self.visited_agents = [False] * self.state_max
            self.compute_impulse()
            self.chain_lengths = self.calculate_chain_lengths()
            unique, counts = np.unique(self.chain_lengths, return_counts=True)
            freq = dict(zip(unique, counts))
            if self.chain_lengths is not None and len(freq) > 2:
                results = powerlaw.Fit(self.chain_lengths)
                self.R, self.p = results.distribution_compare('power_law', 'lognormal')

    def total_energy(self):
        return np.sum(self.vel * self.vel) / 2

    def save(self, fname, type):
        if type == "particles":
            self.save_particles(fname)
        else:
            self.save_rules(fname)

    def save_particles(self, fname):
        try:
            with open(fname, "w") as f:
                f.write(repr(self.n));
                f.write("\n")
                f.write(repr(self.dt));
                f.write("\n")
                for k in range(self.n):
                    f.write(self.stypes[k]);
                    f.write(",")
                    f.write(repr(self.pos[k, 0]));
                    f.write(",")
                    f.write(repr(self.pos[k, 1]));
                    f.write(",")
                    f.write(repr(self.vel[k, 0]));
                    f.write(",")
                    f.write(repr(self.vel[k, 1]));
                    f.write("\n")
                for k in range(self.n):
                    bonds = " ".join(map(str, self.bonds[k]))
                    f.write(bonds);
                    f.write("\n")
        except Exception as e:
            print("Error:", str(e))

    def load_particles(self, fname):
        try:
            with open(fname, "r") as f:
                n = int(f.readline())
                dt = float(f.readline())
                pos = []
                vel = []
                types = []
                bonds = []
                for k in range(n):
                    line = f.readline()
                    t, p0, p1, v0, v1 = line.strip().split(",")
                    pos.append((float(p0), float(p1)))
                    vel.append((float(v0), float(v1)))
                    if not self.rule.is_valid_type(t):
                        print("Unknown type on line:", line)
                        return
                    types.append(t)
                for k in range(n):
                    bonds.append(map(int, f.readline().strip().split()))
                self.n = n
                self.dt = dt
                self.pos = np.array(pos)
                self.vel = np.array(vel)
                self.stypes = np.array(types, dtype=object)
                self.types = np.array(map(lambda t: self.rule.get_index(t), types), dtype=int)
                self.bonds = bonds

        except Exception as e:
            print("Error:", str(e))

    def load(self, fname, type):
        if type == "particles":
            self.load_particles(fname)
        else:
            self.load_rules(fname)

    def start_record(self):
        date = datetime.date.today()
        now = time.time()
        dirname = str(date) + str(now)
        os.mkdir(dirname)
        self.record_dir = dirname

    def record(self, iteration):
        self.save_particles("%s/iteration-%d.dat" % (self.record_dir, iteration))

    def calculate_chain_lengths(self):
        chain_lengths = []
        visited_bonds = []

        for x in range(len(self.bonds)):
            bond = self.bonds[x]
            if x not in visited_bonds and len(bond) > 0:
                current_chain = self.look_deep_chain(x, [])
                visited_bonds.extend(current_chain)
                if len(current_chain) > 1:
                    chain_lengths.append(len(current_chain))

        return chain_lengths

    def look_deep_chain(self, particle, current_chain=[]):
        current_chain.append(particle)
        for pair in self.bonds[particle]:
            if pair not in current_chain:
                current_chain = self.look_deep_chain(pair, current_chain)
        return current_chain


class HChemViewer:
    RED = (255, 0, 0)
    BLUE = (0, 0, 255)
    WHITE = (255, 255, 255)
    BLACK = (0, 0, 0)
    INFO = [
        # "(P) play/pause, (F) stepwise, (R) record, (Q) quit, (T) show/hide particle types, (up) Speed up, (down) Speed down",
        # "(drag) move particle, (shift + drag) bind/unbind particles, (double click) chanppppppppsdpsdfospdfpsfopppppppppppppppolerwqertyuilokpppppppge type and state of a particle"
    ]

    def __init__(self, sim, w=None, h=None):
        if w == None: w = sim.w
        if h == None: h = sim.h

        self.sim = sim
        pygame.init()
        self.screen = pygame.display.set_mode((w, h),
                                              pygame.DOUBLEBUF)  # | pygame.FULLSCREEN | pygame.HWSURFACE
        # )
        pygame.display.set_caption("Artificial Chemistry - Chain Simulator")
        self.fontsize = 18
        self.font = pygame.font.SysFont(None, self.fontsize)
        # info_texts = self.INFO + sim.rule.rule_texts
        info_texts = self.INFO  # prefer not to see rules at the moment
        self.info = map(lambda text: self.font.render(text, False, self.BLUE),
                        info_texts)

        self.speed = 10

        # For events
        self.record = False
        self.shift = False
        self.play = True
        self.stepwise = False
        self.dragged = False
        self.which_dragged = None
        self.moving = False
        self.binding = False
        self.display_types = True
        self.prev_lclick = time.time()

    def get_clicked(self):
        for k in range(self.sim.n):
            d2 = np.sum((self.sim.pos[k, :] - pygame.mouse.get_pos()) ** 2)
            if d2 < self.sim.r ** 2:
                return k
                break
        return None

    def ask_particle(self):
        return raw_input("Enter particle type and state: ")

    def ask_file(self, title):
        filename = raw_input("Enter filename: ")
        if ".dat" in filename:
            savetype = "particles"
        else:
            savetype = "rules"
        return filename, savetype

    def check_event(self):
        for event in pygame.event.get():
            if event.type == pygame.KEYDOWN:
                key = pygame.key.get_pressed()
                if key[pygame.K_RSHIFT] or key[pygame.K_LSHIFT]:
                    self.shift = True
                if key[pygame.K_r]:
                    self.record = not self.record
                    if self.record:
                        self.sim.start_record()
                if key[pygame.K_q]:
                    sys.exit()
                if key[pygame.K_p]:
                    self.play = not self.play
                if key[pygame.K_UP]:
                    self.sim.change_speed(1)
                if key[pygame.K_DOWN]:
                    self.sim.change_speed(-1)
                if key[pygame.K_s]:
                    fname, type = self.ask_file("Save configuration")
                    if fname: self.sim.save(fname, type)
                if key[pygame.K_l]:
                    fname, type = self.ask_file("Load configuration")
                    if fname: self.sim.load(fname, type)
                if key[pygame.K_t]:
                    self.display_types = not self.display_types
                if key[pygame.K_f]:
                    self.stepwise = True
                    self.play = True
            if event.type == pygame.KEYUP:
                key = pygame.key.get_pressed()
                if not key[pygame.K_RSHIFT] and not key[pygame.K_LSHIFT]:
                    self.shift = False
            if not self.dragged and event.type == pygame.MOUSEBUTTONDOWN:
                self.play = False
                which_clicked = self.get_clicked()
                clicked = not (which_clicked == None)

                # Detect double click
                t = time.time()
                double_click = False
                if t - self.prev_lclick < 1.0 / 3:
                    double_click = True
                self.prev_lclick = t

                if clicked and double_click:
                    t = self.ask_particle()
                    try:
                        self.sim.stypes[which_clicked] = t
                        self.sim.types[which_clicked] = self.sim.rule.get_index(t)
                    except:
                        pass
                elif clicked:
                    self.dragged = True
                    self.which_dragged = which_clicked
                    if not self.shift:
                        self.moving = True
                    elif self.shift:
                        self.binding = True
            elif self.dragged and event.type == pygame.MOUSEMOTION:
                if self.moving:
                    self.sim.pos[self.which_dragged, :] = pygame.mouse.get_pos()
            elif self.dragged and event.type == pygame.MOUSEBUTTONUP:
                if self.binding:
                    which_clicked = self.get_clicked()
                    clicked = not (which_clicked == None)
                    if clicked and self.which_dragged != which_clicked and \
                            not (which_clicked in self.sim.bonds[self.which_dragged]):
                        self.sim.bonds[self.which_dragged].append(which_clicked)
                        self.sim.bonds[which_clicked].append(self.which_dragged)
                    elif clicked and self.which_dragged != which_clicked and \
                            (which_clicked in self.sim.bonds[self.which_dragged]):
                        self.sim.bonds[self.which_dragged].remove(which_clicked)
                        self.sim.bonds[which_clicked].remove(self.which_dragged)
                self.moving = False
                self.binding = False
                self.dragged = False
                self.which_dragged = None
            elif event.type == pygame.QUIT:
                sys.exit()

    def loop(self, iterations=float('inf')):
        iteration = 0
        screen = self.screen
        sim = self.sim
        while iteration * sim.dt < iterations:

            n = sim.n
            r = sim.r
            if self.play:
                iteration += 1
                sim.update()
                if self.record:
                    sim.record(iteration)

            if self.stepwise:
                self.play = False
                self.stepwise = False

            pos = sim.pos

            screen.fill(self.WHITE)
            # Draw particles
            for k in range(n):
                pygame.draw.circle(screen, sim.rule.colors[sim.types[k]],
                                   (int(pos[k, 0]), int(pos[k, 1])), r, 1)

            if self.display_types:
                for k in range(sim.n):
                    t = sim.rule.get_name(sim.types[k])
                    t = t[1:]  # DEBUG: just draw the state
                    text = self.font.render(t, False, self.BLACK)
                    rect = text.get_rect()
                    rect.centerx = pos[k, 0]
                    rect.centery = pos[k, 1]
                    self.screen.blit(text, rect)

            # Draw bonds
            for k in range(n):
                for l in sim.bonds[k]:
                    if k >= l: continue
                    pygame.draw.line(screen, self.BLACK, pos[k, :], pos[l, :])
            y = 10

            # update chain longs
            # if iteration * sim.dt % 10 == 0 :
            #chains = sim.calculate_chain_lengths()


            # results = powerlaw.Fit(chains)
            # print(results.power_law.alpha)
            # print(results.power_law.xmin)
            #R, p = results.distribution_compare('power_law', 'lognormal')
            text = self.font.render("chains: " + str(sim.chain_lengths), False, self.BLUE)
            self.screen.blit(text, (10, y + 2 * self.fontsize))
            # text = self.font.render("Ratio: " + str(R) + " P-value: " + str(p), False, self.BLUE)
            # self.screen.blit(text, (10, y + 3 * self.fontsize))
            # Other info
            if self.binding:
                pygame.draw.line(screen, self.BLACK,
                                 pos[self.which_dragged, :], pygame.mouse.get_pos())

            for i in self.info:
                self.screen.blit(i, (10, y))
                y += self.fontsize
            text = self.font.render(
                "time = " + str(iteration * sim.dt),
                False, self.BLUE)
            self.screen.blit(text, (10, y))
            energy = sim.total_energy()
            text = self.font.render(
                "energy = " + str(energy),
                False, self.BLUE)
            self.screen.blit(text, (10, y + self.fontsize))

            self.check_event()
            pygame.display.update()


class ChemMDP(MDP):
    def __init__(self, terminals, state, rules_file, gamma=.9):
        MDP.__init__(self, state, actlist=chem_actions,
                     terminals=terminals, gamma=gamma)
        self.rules = HChemRule(rules_file)
        self.reward = -0.04
        self.sim_steps = 10

    def R(self, state):
        "Return a numeric reward for this state."
        sim = HChem(self.rules, state)
        chain_lenghts = sim.calculate_chain_lengths()
        results = powerlaw.Fit(chain_lenghts)
        R, p = results.distribution_compare('power_law', 'lognormal')
        reward = self.reward
        if R > 0:
            reward = p
        return reward

    def T(self, state, action):
        if action is None:
            return [(0.0, state)]
        else:
            return [(0.7, self.go(state, action)),
                    (0.1, self.go(state, add_bond_rule())),
                    (0.1, self.go(state, add_unbond_rule())),
                    (0.1, self.go(state, add_particles()))]

    def go(self, state, action):
        """Return the state that results from going in this action."""
        rules = self.rules
        # TODO: apply the action and apply it
        sim = HChem(rules, state)  # Ejecutar aqui el modelo y medir sim loop aqui
        viewer = HChemViewer(sim)
        viewer.loop(self.sim_steps)
        state1 = r"particles/exp1" + str(time.time()) + ".dat"
        sim.save(state1, "particles")
        return state1


class ParticleMDP(MDP):
    '''gets an state from the particle and calculates the T transaction, the terminal node is when the statistics
    distribution of power law gets the p value < 0.05'''


    def __init__(self, simulator, my_index=None, its_index = None, gamma=.9):

        self.sim = simulator
        self.index = my_index
        self.other_index = its_index
        self.default_reward = -0.04
        self.terminal = 10.0
        MDP.__init__(self, -0.04, actlist=particle_actions,
                     terminals=[self.terminal], gamma=gamma)
        self.main_states = ['single', 'double']






    def R(self, state):
        """"Return a numeric reward for this state."""
        sim = self.sim
        if sim.R > 0 and 0.05 > sim.p > 0.0:
            return self.terminal
        else:
            self.reward[state] = self.reward[state]-self.default_reward + sim.p
            return self.reward[state]

    def T(self, state, action):
        # else:
        #     costs = []
        #     for act in particle_actions:
        #         if act != action:
        #             costs.append((0.1, self.default_reward))
        #     costs.append((0.7, self.go(state, action)))
        return [(0.7, self.go(state, action))]

    def go(self, state, action):
        """Return the state that results from going in this action."""
        action(self.sim, self.index, self.other_index) # no se sabe en reward hasta la siguiente iteracion
        return self.default_reward + self.R(state)

class ParticleTypeMDP(MDP):
    '''gets an state from the particle and calculates the T transaction, the terminal node is when the statistics
    distribution of power law gets the p value < 0.05'''


    def __init__(self, simulator, my_index, gamma=.9):

        self.sim = simulator
        self.index = my_index
        self.default_reward = -0.04
        self.terminal = 10.0
        self.last_state = None
        self.action_reward = {}
        self.other_index = None

        MDP.__init__(self, -0.04, actlist=particle_actions,
                     terminals=[self.terminal], gamma=gamma)

        self.reward[self.last_state] = self.default_reward
        for action in particle_actions:
            self.action_reward[action] = self.default_reward


    def R(self, state):
        """"Return a numeric reward for this state."""
        sim = self.sim
        if sim.R > 0 and 0.05 > sim.p > 0.0:
            self.last_state = state
            return self.terminal
        else:
            if state not in self.reward.keys():
                self.reward[state] = 0.0
            self.reward[self.last_state] = self.reward[self.last_state] + sim.p
            self.reward[state] += 0.4 * self.reward[self.last_state]
            return self.reward[state]

    def T(self, state, action):
        # else:
        #     costs = []
        #     for act in particle_actions:
        #         if act != action:
        #             costs.append((0.1, self.default_reward))
        #     costs.append((0.7, self.go(state, action)))
        cost = []
        for act in particle_actions:
            if act != action:
                cost.append((0.1,self.action_reward[act]))
        self.action_reward[action] = self.go(state,action)
        cost.append((0.8, self.action_reward[action]))
        return cost

    def go(self, state, action):
        """Return the state that results from going in this action."""
        action(self.sim, self.index, self.other_index) # no se sabe en reward hasta la siguiente iteracion
        return self.terminal

if __name__ == '__main__':
    if len(sys.argv) == 2:
        sim = HChem(sys.argv[1])
    elif len(sys.argv) == 3:
        sim = HChem(sys.argv[1], sys.argv[2])

    else:
        print("Usage: python", sys.argv[0], "<rules_filename> [optional: particles_filename]")
        exit()

    HChemViewer(sim).loop(1000)
    # q_agent = QLearningAgent(chemMDP_env, Ne=5, Rplus=2,
    #                          alpha=lambda n: 60. / (59 + n))  # TODO: Definir los parametros de esta funcion
    # for i in range(200):
    #     run_single_trial(q_agent, chemMDP_env)
