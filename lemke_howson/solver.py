from __future__ import annotations

import numpy as np

from core.normal_form_game import NFG_Core

class LH_solver:
    def __init__(self, game:NFG_Core):
        self.game: NFG_Core = game
        
        # lcp
        m = sum(game.n_strategies)
        # coefficients
        self.c = np.zeros((m,2*m+1))
        self.LHS = np.zeros(m,dtype=int) # indices for LHS var
        
        # current mix
        self.mix = [
            np.zeros(self.game.n_strategies[0]),
            np.zeros(self.game.n_strategies[1])
        ]
        self.a = np.zeros(2)

        self.done = False

        self.__init_vnames()
        self.__init_lcp()

    def __init_vnames(self):
        self.var_names = [
            f"r_{{{i}}}" for i in range(len(self.LHS))
        ]
        self.var_names += [
            f"a_{{0}}x_{{{i}}}" for i in range(self.game.n_strategies[0])
        ]
        self.var_names += [
            f"a_{{1}}x_{{{i}}}" 
            for i in range(self.game.n_strategies[0], len(self.LHS))
        ]
        self.var_names.insert(0,'')

    def __init_lcp(self):
        na0, na1 = self.game.n_strategies

        # 1s for the constant
        self.c[:,0] = 1
        # slack 
        for i in range(na0+na1):
            self.c[i,i+1] = -1
        # mix probs
        for a0 in range(na0):
            for a1 in range(na1):
                u = self.game.u_mat[0]
                self.c[a0,1+2*na0+na1+a1] = -u[a0,a1]
        for a1 in range(na1):
            for a0 in range(na0):
                u = self.game.u_mat[1]
                self.c[na0+a1,1+na0+na1+a0] = -u[a0,a1]
        # LHS
        for i in range(na0+na1):
            self.LHS[i] = i+1


    def get_init_options(self):
        options = self.game.labels[0] + self.game.labels[1]
        return options

    def get_state(self):
        return {
            'coef': self.c,
            'LHS': self.LHS,
            'mix':self.mix,
            'a': self.a,
            'done':self.done
        }

    def update(self, initial=None, log_info=False):
        
        # 1. pick/find entering var (what to enter)
        #   if no enter : done
        # 2. introduce the variable
        #   find what to leave
        # 3. find 'a' (sum(ax) == 1)
        # 4. find 'mix'

        if log_info:
            info = {}

        if not self.done:
            na0, na1 = self.game.n_strategies

            # pick / find enter var
            enter_var = None
            options = self.get_init_options()
            try:
                enter_var = options.index(initial)
            except ValueError:
                # find entering var
                LHS_id = (self.LHS - 1) % (na0+na1)
                for i in range(na0+na1):
                    if i not in LHS_id:
                        enter_var = i
                        break
            
            # print(f"enter var = {enter_var}")

            # find leaving slack variable
            clashes = []
            for i in range(na0+na1):
                # if enter var has nonzero coef -> means it exists in RHS
                if self.c[i,1+na0+na1+enter_var] != 0:
                    clashes.append(i)

            # print(f"clash={clashes}")
            
            # pick one with minimum ratio test
            if log_info: ratios = []
            ratio = np.inf
            leave_var = None
            for i in clashes:
                q = self.c[i,1+na0+na1+enter_var]
                cst = self.c[i,0]
                r = np.abs(cst/q) # ratio is the opposite of what is written in slide p.12
                if r < ratio:
                    ratio = r
                    leave_var = i

                if log_info: ratios.append(r)

            # print(f"leave var = {leave_var}")
            
            # leave leave_var, enter enter_var
            q = -self.c[leave_var,1+na0+na1+enter_var]
            self.c[leave_var] /= q
            self.LHS[leave_var] = 1+na0+na1+enter_var
            
            # print(f"q = {q}")
            # print(self.c[leave_var])

            # substitude enter_vars on RHS to leave_var
            for row in clashes:
                if row == leave_var:
                    continue

                q = self.c[row,1+na0+na1+enter_var]
                self.c[row] += self.c[leave_var]*q

                # print(f"row={row}")
                # print(self.c[row])

            # find 'a'
            c_p0 = np.zeros(na0)
            c_p1 = np.zeros(na1)
            for row in range(na0+na1):
                # if mix prob in LHS
                if self.LHS[row] >= 1+na0+na1:
                    # if mix prob is for player 0
                    if self.LHS[row] < 1+na0+na1+na0:
                        # ax = c
                        # x = c/a
                        # sum(x) = c1/a + c2/a + ... = 1
                        # c1+c2+... = a
                        i = self.LHS[row] - (1+na0+na1)
                        c_p0[i] = self.c[row,0]

                    # else: mix prob is for player 1
                    else:
                        i = self.LHS[row] - (1+na0+na1+na0)
                        c_p1[i] = self.c[row,0]

            # c1+c2+... = a
            self.a[0] = np.sum(c_p0)
            self.a[1] = np.sum(c_p1)
            # find mix: x = c/a
            self.mix[0] = c_p0/self.a[0] if self.a[0] != 0 else np.zeros(na0)
            self.mix[1] = c_p1/self.a[1] if self.a[1] != 0 else np.zeros(na1)

            # all var found in lhs and mix is not 0: done
            LHS_id = (self.LHS - 1) % (na0+na1)
            if np.sum(np.arange(na0+na1) - LHS_id) == 0:
                if np.any(self.mix[0] > 0) and np.any(self.mix[1] > 0):
                    self.done = True

        if log_info:
            info = dict(
                enter_var=self._var_id2name(1+na0+na1+enter_var),
                leave_var=self._var_id2name(1+leave_var),
                clashes=', '.join([
                    self._var_id2name(1+c) for c in clashes]),
                ratio=', '.join(
                    [f"{r:.3f}" for r in ratios]
                ),
                mix=[[round(float(p),3) for p in self.mix[pid]] for pid in range(2)],
                a = [round(float(_a),3) for _a in self.a],
                done=self.done
            )
        
        return info if log_info else None

    def _var_id2name(self,var_id):
        return self.var_names[var_id]
# from fractions import Fraction

# def _render_LCP_foo(model: LH_solver):
#     # issue: convert float coef to fraction 
#     """
#     linear program representation in model:
#     0 = C*VAR
#     LHS = indices of terms in C that should be in LHS.

#     output equations
#     -C[LHS]*VAR[LHS] = C[~LHS]*VAR[~LHS]
#     """
#     # helper
#     def float_to_tex(val):
#         if val == 0: return ""
        
#         f = Fraction(val).limit_denominator(1000) 
        
#         # if integer
#         if f.denominator == 1:
#             return str(f.numerator)
        
#         # float
#         sign = '-' if val < 0 else ''
#         return f"{sign}\\frac{{{abs(f.numerator)}}}{{{f.denominator}}}"
    

#     var_names = [
#         f"r_{{{i}}}" for i in range(len(model.LHS))
#     ]
#     var_names += [
#         f"a_{{0}}x_{{{i}}}" for i in range(model.game.n_strategies[0])
#     ]
#     var_names += [
#         f"a_{{1}}x_{{{i}}}" 
#         for i in range(model.game.n_strategies[0], len(model.LHS))
#     ]
#     var_names.insert(0,'')

#     out = ""
#     for LHS_id, coef in zip(model.LHS, model.c):
#         # LHS
#         out += f"{-coef[LHS_id]}" if -coef[LHS_id] != 1 else ''
#         out += var_names[LHS_id]
#         out += ' &=& '
#         # RHS
#         for i, c in enumerate(coef):
#             # skip c=0
#             if c == 0:
#                 out += " & &"
#                 continue
#             # skip LHS var
#             if i == LHS_id:
#                 out += " & &"
#                 continue
#             # constant
#             if i == 0:
#                 out += " &"+float_to_tex(c)+"&"
#             # vars
#             else:
#                 out += " &"
#                 if c > 0:
#                     out += '+'
#                     out += '' if c == 1 else float_to_tex(c)
#                 else:
#                     out += '-' if c == 1 else float_to_tex(c)
#                 out += var_names[i] + "&"
#         # newline
#         out += ' \\\\ '

#     out = "\\begin{align*}" + out + "\\end{align*}"
#     print(out)
#     # print test
#     print(out.replace('\\\\','\n'))


if __name__ == "__main__":
    with open("data/lh/example_game_LH.json",'r') as f:
        game = NFG_Core.load_from_json(f)
    
    model = LH_solver(game=game)

    state = model.get_state()
    print(state)

    options = model.get_init_options()
    print(f"options: {options}")
    i = int(input("select: "))
    selected = options[i]
    print(f"selected {selected}")

    model.update(initial=selected)
    state = model.get_state()
    print(state)

    while not state['done']:
        model.update()
        state = model.get_state()
        # _render_LCP_foo(model)
        print("="*40)
        print()








            
            

         
