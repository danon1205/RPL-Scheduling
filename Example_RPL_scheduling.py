import pyomo.environ as pyo
from pyomo.opt import SolverFactory
import pandas as pd

# Создание конкретной модели pyomo
model = pyo.ConcreteModel()

#Вспомогательные множества
SLOTS1 = [s for s in SLOTS if s > 1]
iCA3_max_SET = [(c,t1,s) for (c,t1) in CONSTRAINTS_TEAMS1 for s in SLOTS \
    if ConstrName[c] == "CA3" and Type[c] == "HARD" and (s + int(Intp[c]) - 1) in SLOTS]
iCA5_max_SET = [(c,t1,s) for (c,t1) in CONSTRAINTS_TEAMS1 for (key,s) in CONSTRAINTS_SLOTS \
    if ConstrName[c] == "CA5" and Type[c] == "HARD" and (s + int(Intp[c]) - 1) in SLOTS and key == c]    

phase = 16
#Первый круг
FIRST = range(1, phase)

#Второй круг
SECOND = range(phase, 2 * phase - 1)

# Переменные решения

#Индикатор, что две команды играют в конкретный тур
model.x = pyo.Var(SLOTS, [(t1,t2) for t1 in TEAMS for t2 in TEAMS if t1 != t2], within = pyo.Binary)

#Индикатор двух выездных игр подряд для команды
model.iBreak = pyo.Var(SLOTS1, TEAMS, within = pyo.Binary)

#Линеаризация нарушения мягкого ограничения CA1
model.iCA1_max = pyo.Var([(c,t1) for (c,t1) in CONSTRAINTS_TEAMS1 \
    if ConstrName[c] == "CA1" and Type[c] == "SOFT"], within = pyo.NonNegativeReals)

#Линеаризация нарушения мягкого ограничения CA4
model.iCA4_max = pyo.Var([c for c in CONSTRAINTS  if ConstrName[c] == "CA4" and Type[c] == "SOFT"], within = pyo.NonNegativeReals)


def CountCA1 (key, t1):
    if Mode1[key] == "H":
        return sum(model.x[s,t1,t2] for (c,s) in CONSTRAINTS_SLOTS for t2 in TEAMS if c == key and t1 != t2)
    elif Mode1[key] == "A":
        return sum(model.x[s,t2,t1] for (c,s) in CONSTRAINTS_SLOTS for t2 in TEAMS if c == key and t1 != t2)
    else:
        return sum((model.x[s,t2,t1] + model.x[s,t1,t2]) for (c,s) in CONSTRAINTS_SLOTS for t2 in TEAMS if c == key and t1 != t2) 


def CountCA3 (key, t1, s1):
    if Mode1[key] == "H":
        return sum(model.x[s,t1,t2] for s in range(s1,s1 + int(Intp[key])) for (c,t2) in CONSTRAINTS_TEAMS2 if c == key and t1 != t2)
    elif Mode1[key] == "A":
        return sum(model.x[s,t2,t1] for s in range(s1,s1 + int(Intp[key])) for (c,t2) in CONSTRAINTS_TEAMS2 if c == key and t1 != t2)
    else:
        return sum((model.x[s,t1,t2] + model.x[s,t2,t1]) for s in range(s1,s1 + int(Intp[key])) for (c,t2) in CONSTRAINTS_TEAMS2 if c == key and t1 != t2)

def CountCA4 (key):
    SLOTS_CA4 = [s for (c,s) in CONSTRAINTS_SLOTS if c == key]
    TEAMS1_CA4 = [t for (c,t) in CONSTRAINTS_TEAMS1 if c == key]
    TEAMS2_CA4 = [t for (c,t) in CONSTRAINTS_TEAMS2 if c == key]
    if Mode1[key] == "H":
        return sum(model.x[s,t1,t2] for s in SLOTS_CA4 for t1 in TEAMS1_CA4 for t2 in TEAMS2_CA4 if t1 != t2)
    elif Mode1[key] == "A":
        return sum(model.x[s,t2,t1] for s in SLOTS_CA4 for t1 in TEAMS1_CA4 for t2 in TEAMS2_CA4 if t1 != t2)
    else:
        return sum((model.x[s,t1,t2] + model.x[s,t2,t1]) for s in SLOTS_CA4 for t1 in TEAMS1_CA4 for t2 in TEAMS2_CA4 if t1 != t2)


def CountAwayRow (t1,s):
    return sum((model.x[s,t2,t1] + model.x[s-1,t2,t1]) for t2 in TEAMS if t1 != t2)

# Ограничения

# Есть ровно 1 соперник в каждый тур
def cUnique_rule (model, t, s):
    return sum(model.x[s,t,t2] + model.x[s,t2,t] for t2 in TEAMS if t != t2) == 1

model.cUnique = pyo.Constraint(TEAMS, SLOTS, rule = cUnique_rule)

# Между любыми двумя командами есть матч в первом круге
def cRR_phased_1_rule (model, t1, t2):
    return sum((model.x[s,t1,t2] + model.x[s,t2,t1]) for s in FIRST) == 1

model.cRR_phased_1 = pyo.Constraint([(t1,t2) for t1 in TEAMS for t2 in TEAMS if t1 < t2], rule = cRR_phased_1_rule)

# Между любыми двумя командами есть матч во втором круге
def cRR_phased_2_rule (model, t1, t2):
    return sum((model.x[s,t1,t2] + model.x[s,t2,t1]) for s in SECOND) == 1

model.cRR_phased_2 = pyo.Constraint([(t1,t2) for t1 in TEAMS for t2 in TEAMS if t1 < t2], rule = cRR_phased_2_rule)

# Ровно 1 домашний и выездной матч между любыми двумя командами за сезон
def cHomeAway_rule (model, t1, t2):
    return sum(model.x[s,t1,t2] for s in SLOTS) == 1

model.cHomeAway = pyo.Constraint([(t1,t2) for t1 in TEAMS for t2 in TEAMS if t1 != t2], rule = cHomeAway_rule)

def cHardCA1_max_rule (model, key, t1):
    return CountCA1(key,t1) <= ConstrMax[key]

model.cHardCA1_max = pyo.Constraint([(key, t1) for (key,t1) in CONSTRAINTS_TEAMS1 \
    if ConstrName[key] == "CA1" and Type[key] == "HARD"], rule = cHardCA1_max_rule)

def cHardCA1_min_rule (model, key, t1):
    return CountCA1(key,t1) >= ConstrMin[key]

model.cHardCA1_min = pyo.Constraint([(key, t1) for (key,t1) in CONSTRAINTS_TEAMS1 \
    if ConstrName[key] == "CA1" and Type[key] == "HARD"], rule = cHardCA1_min_rule)


def cHardCA3_max_rule (model, key, t1, s):
    return CountCA3(key,t1,s) <= ConstrMax[key]

model.cHardCA3_max = pyo.Constraint(iCA3_max_SET, rule = cHardCA3_max_rule)

def cHardCA5_max_rule (model, key, t1, s):
    return CountCA3(key,t1,s) <= ConstrMax[key]

model.cHardCA5_max = pyo.Constraint(iCA5_max_SET, rule = cHardCA5_max_rule)


def cHardCA4_max_rule (model, key):
    return CountCA4(key) <= ConstrMax[key]

model.cHardCA4_max = pyo.Constraint([key for key in CONSTRAINTS \
    if ConstrName[key] == "CA4" and Type[key] == "HARD"], rule = cHardCA4_max_rule)


def cLinCA1_max_rule (model, key, t1):
    return CountCA1(key,t1) - ConstrMax[key] <= model.iCA1_max[key,t1]

model.cLinCA1_max = pyo.Constraint([(c,t1) for c in CONSTRAINTS for (c1,t1) in CONSTRAINTS_TEAMS1 \
    if ConstrName[c] == "CA1" and c == c1 and Type[c] == "SOFT"], rule = cLinCA1_max_rule)

def cLinCA4_max_rule (model, key):
    return CountCA4(key) - ConstrMax[key] <= model.iCA4_max[key]

model.cLinCA4_max = pyo.Constraint([c for c in CONSTRAINTS  if ConstrName[c] == "CA4" and Type[c] == "SOFT"], rule = cLinCA4_max_rule)

def cLinBreak_rule (model, t1, s):
    return CountAwayRow(t1,s) - 1 <= model.iBreak[s,t1]

model.cLinBreak = pyo.Constraint(TEAMS, SLOTS1, rule = cLinBreak_rule)

# Минимизация суммарного штрафа
model.OBJ = pyo.Objective(expr = \
      sum(model.iCA4_max[c] * Penalty[c] for c in CONSTRAINTS  if ConstrName[c] == "CA4" and Type[c] == "SOFT")
    + sum(model.iBreak[s,t] * 2 for s in SLOTS1 for t in TEAMS)
    + sum(model.iCA1_max[c,t] * Penalty[c] for (c,t) in CONSTRAINTS_TEAMS1 if ConstrName[c] == "CA1" and Type[c] == "SOFT"))



# Вызов Gurobi солвера
opt = SolverFactory("gurobi", solver_io="python", options={'TimeLimit': 72000, "threads" : 4})
instance = model



results = opt.solve(instance, tee=True).write()

model.OBJ.display()

