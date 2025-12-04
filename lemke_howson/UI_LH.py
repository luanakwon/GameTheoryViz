from __future__ import annotations
import streamlit as st
import plotly.graph_objects as go
from fractions import Fraction
import numpy as np

from core.normal_form_game import NFG_Core
from lemke_howson.solver import LH_solver

# temporary uid
class uid:
    id=0
    @staticmethod       
    def get():
        uid.id += 1
        return uid.id
    
def reset_session_state(load_if_exist=False):
    """Reset session states."""
    if not load_if_exist:
        st.session_state.lh = {}
    else:
        if not hasattr(st.session_state, 'lh'):
            st.session_state.lh = {}

def main():
    # set session states
    reset_session_state(load_if_exist=True)
    
    # render title, description
    render_page_header()

    # render game loader
    render_game_loader()

    # render main viz content
    render_content()
    

def render_page_header():
    """Render title and description"""
    st.write("### Step-by-step Visualization of Lemke-Howson Algorithm")
    st.write(
        """This visualization demonstrates the Lemke-Howson algorithm for two-player normal-form games.
            It displays each pivot in the corresponding LCP system and shows the 
            evolving mixed-strategy profile on the players' simplices until a Nash equilibrium is reached."""
        )

def render_game_loader():
    game_file = st.file_uploader(
        label="Load Game", type='json',
        accept_multiple_files=False,
        on_change=reset_session_state
    )

    # if game exist in session -> no change
    if 'game' in st.session_state.lh:
        return

    # if game loaded -> load game to session
    if game_file is not None:
        st.session_state.lh['game'] = NFG_Core.load_from_json(game_file)
        # For LH viz, game must be 2 player, max 3 actions each.
        game:NFG_Core = st.session_state.lh['game']
        if game.n_players != 2:
            st.error(
                f"Lemke Howson algorithm only takes 2-player games. ({game.n_players}-player game given)"
            )
            # revert to default game
            game_file = None
        else:
            for pid, n_strat in enumerate(game.n_strategies):
                if n_strat > 3:
                    st.warning(
                        f"Graphic visuallization is only supported for number of pure strategies <= 3. ({n_strat} given for player {pid})"
                    )
                break

    # if no game loaded -> load default game to session
    if game_file is None:
        default_game = "data/lh/example_game_LH.json"
        with open(default_game) as f:
            st.session_state.lh['game'] = NFG_Core.load_from_json(f)

def render_content():
    # Here is the payoff mat of the game {title}. 
    # PAYOFF MAT
    game:NFG_Core = st.session_state.lh['game']
    st.write(
        f"Below is the payoff matrix for the game [{game.title}]."
    )
    render_payoff_matrix()

    # init LH solver model
    game = st.session_state.lh['game']
    model = LH_solver(game=game)

    # LH algorithm starts from the origin, where no player plays any strategy.
    st.write(
        "The Lemke-Howson algorithm begins at the origin, a point where both players assign probability 0 to all pure strategies.   "+
        "Geometrically, this corresponds to the corner in each player's strategy diagram."
    )
    _render_diagram(model)

    # initial LCP
    st.write(
        "The initial Linear Complementarity Problem (LCP) formulation is shown below."
    )
    _render_LCP(model)

    # pick initial move
    st.write(
        "To start the algorithm, we must drop one label.   "+
        "Select which label you want to introduce into the basis.  "+
        "This determines the first pivot of the Lemke-Howson path."
    )

    options = model.get_init_options()
    selected_option = st.selectbox(
        "How would you like to start algorithm",
        options,
        index=None,
        placeholder="Select an action"
    )

    # if an option is selected, roll out full algorithm
    if selected_option is not None:
        info = model.update(initial=selected_option, log_info=True)

        # ?? is selected, so x? must enter. 
        st.write(
            f"You selected ${selected_option}$, so the corresponding variable ${info['enter_var']}$ must enter the basis."
        )
        # clashes and min ratio test
        if len(info['clashes']) == 1:
            st.write(
                f"${info['enter_var']}$ clashes with ${info['leave_var']}$, so ${info['leave_var']}$ leaves the basis."
            )
        else:
            st.write(
                f"${info['enter_var']}$ clashes with ${info['clashes']}$.   "+
                f"Using the minimum-ratio test, teh algorithm determines that ${info['leave_var']}$ must leave "+
                f"(ratio = ${info['ratio']}$)."
            )

        _render_LCP(model)

        # how to min ratio test
        st.write(
            "> Minimum-Ratio Test:   \n"+
            "When several constraints clash with the entering variable, the minimum-ratio test selects the leaving variable by examining  \n"+
            "$$ratio=|c/q|$$  \n" +
            "where $c$ is the constant and $q$ is the coefficient of the entering variable.   \n"+
            "Variable to leave is the one with the smalles ratio."
        )

        # finding intermediate mix strategy
        st.write(
            "**Interpreting the Current Basis**  \n"+
            """Variables currently on the LHS represents the strategies with positive probability. 
            Variables on the RHS are non-basis, and therefore fixed at zero.   
            By substituting all RHS variables with 0 and applying the sum of probability constraint $\\sum(x_{i}) = 1$,  
            we obtain the intermediate mixed strategy at this pivot.
            """
        )
        st.write(
            f"The resulting intermediate mixed strategy is:"
        )
        st.latex(
            f"{info['mix']}"
        )
        st.write(
            f"(normalization constant $a={info['a']}$)"
        )

        # show in diagram
        st.write(
            "This point corresponds to the following location in the strategy diagram:"
        )
        _render_diagram(model)

        for _ in range(30):
            # IF NOT DONE
            if not info['done']:
                info = model.update(log_info=True)
                              
                st.write(
                    f"The basis is missing label ${info['enter_var']}$, so it must enter in the next pivot."
                )
                # clashes and min ratio test
                if len(info['clashes']) == 1:
                    st.write(
                        f"${info['enter_var']}$ clashes with ${info['leave_var']}$, so ${info['leave_var']}$ leaves the basis."
                    )    
                else:
                    st.write(
                        f"${info['enter_var']}$ clashes with ${info['clashes']}$. "+
                        f"Using the minimum-ratio test, the algorithm determines that ${info['leave_var']}$ must leave "+
                        f"(ratio = ${info['ratio']}$)."
                    )

                
                # render LCP
                _render_LCP(model)

                # substitute to 0, sum prob property
                st.write(
                    "Again, we set all RHS variables to 0 and use sum probability constraint to compute the intermediate mixed strategy."
                )
                st.write(
                    f"The resulting intermediate mixed strategy is:"
                )
                st.latex(
                    f"{info['mix']}"
                )
                st.write(
                    f"(normalization constant $a={info['a']}$)"
                )

                # show diagram
                st.write(
                    "This pivot moves us to the next point in the diagram:"
                )
                _render_diagram(model)

            # IF DONE
            else:
                st.write(
                    "All labels now appear in the LHS, so the algorithm terminates.   \n"+
                    "The final mixed strategy is a Nash equilibrium:"
                )
                st.latex(
                    f"{info['mix']}"
                )
                break

        # render if needed after LH is done


def _render_LCP(model: LH_solver):
    # issue: convert float coef to fraction 
    """
    linear program representation in model:
    0 = C*VAR
    LHS = indices of terms in C that should be in LHS.

    output equations
    -C[LHS]*VAR[LHS] = C[~LHS]*VAR[~LHS]
    """
    # helper ----
    def float_to_tex(val):
        if val == 0: return ""
        
        f = Fraction(val).limit_denominator(1000) 
        
        # if integer
        if f.denominator == 1:
            return str(f.numerator)
        
        # float
        sign = '-' if val < 0 else ''
        return f"{sign}\\frac{{{abs(f.numerator)}}}{{{f.denominator}}}"

    # -------------------

    out = ""
    for LHS_id, coef in zip(model.LHS, model.c):
        # LHS
        out += f"{-coef[LHS_id]}" if -coef[LHS_id] != 1 else ''
        out += model._var_id2name(LHS_id)
        out += ' &=& '
        # RHS
        for i, c in enumerate(coef):
            # skip c=0
            if c == 0:
                out += " & &"
                continue
            # skip LHS var
            if i == LHS_id:
                out += " & &"
                continue
            # constant
            if i == 0:
                out += " &"+float_to_tex(c)+"&"
            # vars
            else:
                out += " &"
                if c > 0:
                    out += '+'
                    out += '' if c == 1 else float_to_tex(c)
                else:
                    out += '-' if c == 1 else float_to_tex(c)
                out += model._var_id2name(i) + "&"
        # newline
        out += ' \\\\ '

    out = "\\begin{align*}" + out + "\\end{align*}"
    
    st.latex(out)

def _render_diagram(model:LH_solver):
    """
    plot diagram for player 0 and 1, side by side.
    
    For each plot:
    if n_strategies <= 2: 2D plot
    if n_strategies == 3: 3D plot
    if n_strategies > 3: dont plot, put blank

    each strategy = axis. if player 0 has strategies (p0, p1, p2),
    x axis = p0, y axis = p1, z axis = p2
    axis range = [0,1] (probabilities)
    dot plot current mix strategy for player.
    annotate dot with 
        1. coordinate (ex: 0,0.25,0.75)
        2. player's non support labels
        3. opponent's best response supports
            can be caculated given player's mix and opponent's u_mat.

    """
    # helper
    def _get_annotation(pid, mix, labels, u_mat):
        """
        returns 
            mix in fraction,
            player's actions that are not supports
            supports of opponent's best response
        in string 
        """
        # fractional mix
        fmix = [
            str(Fraction(m).limit_denominator(1000))
            for m in mix
        ]

        # player's actions that are not supports
        p_lbl = [
            labels[pid][i]
            for i, m in enumerate(mix) if m == 0
        ]

        # supports of opponent's best response
        u_mat = u_mat[1] if pid == 0 else u_mat[0].T
        u = np.sum(
            u_mat * mix.reshape((-1,1)), axis=0)
        u = (u==np.max(u))
        o_lbl = [
            labels[1-pid][i]
            for i, is_bs in enumerate(u) if is_bs
        ]

        return f"Mix: ({','.join(fmix)}) \n"+\
               f"P{pid}: {','.join(p_lbl)} \n"+\
               f"P{1-pid}: {','.join(o_lbl)}"

    # -----------------------------

    figs = [
        go.Figure(),
        go.Figure()
    ]
    for pid in range(2):
        na = model.game.n_strategies[pid]
        mix = model.mix[pid]
        labels = model.game.labels[pid]
        fig = figs[pid]

        # 2D or 3D
        if na <= 2: # 2D
            # plot dot
            fig.add_trace(
                go.Scatter(
                    x=mix[0:1], y=mix[1:2],
                    mode='markers',
                    marker=dict(size=10),
                    name="Mixed Strategy",
                    showlegend=False
                )
            )
            # plot triangle
            fig.add_trace(
                go.Scatter(
                    x=[0,0,1,0], y=[0,1,0,0],
                    mode="lines", line=dict(color="black", width=2),
                    showlegend=False
                )
            )
            # label axes
            fig.update_xaxes(
                title=labels[0],
                range=[-.05,1.05],
                zeroline=True, zerolinecolor='black', zerolinewidth=1, 
            )
            fig.update_yaxes(
                title=labels[1],
                range=[-.05,1.05],
                zeroline=True, zerolinecolor='black', zerolinewidth=1, 
            )
            # add annotation
            fig.add_annotation(
                x=mix[0], y=mix[1],
                text=_get_annotation(
                    pid, mix, model.game.labels,model.game.u_mat)
            )
        elif na == 3: # 3D
            # plot dot + annotation
            fig.add_trace(
                go.Scatter3d(
                    x=mix[0:1], y=mix[1:2], z=mix[2:3],
                    mode='markers+text',
                    marker=dict(size=4),
                    text=_get_annotation(
                        pid, mix, model.game.labels,model.game.u_mat),
                    textposition="top center",
                    name="Mixed Strategy",
                    showlegend=False
                )
            )
            # plot xyz
            line_range = [0,1] 
            fig.add_trace(go.Scatter3d(x=[0, 0], y=line_range, z=[0, 0],
                                    mode="lines", line=dict(color="black", width=2),
                                    showlegend=False))
            fig.add_trace(go.Scatter3d(x=line_range, y=[0, 0], z=[0, 0],
                                    mode="lines", line=dict(color="black", width=2),
                                    showlegend=False)) 
            fig.add_trace(go.Scatter3d(x=[0, 0], y=[0, 0], z=line_range,
                                    mode="lines", line=dict(color="black", width=2),
                                    showlegend=False)) 

            # label axes
            graphic_config = dict(showgrid=False, ticks="outside", showticklabels=True, zeroline=False)
            fig.update_scenes(    
                xaxis=dict(**graphic_config, title=labels[0]),
                yaxis=dict(**graphic_config, title=labels[1]),
                zaxis=dict(**graphic_config, title=labels[2]),
            )

        else:
            # above 3D - skip
            continue

    # render
    with st.container(horizontal=True):
        st.plotly_chart(figs[0], width='stretch',key=uid.get())
        st.plotly_chart(figs[1], width='stretch',key=uid.get())

def render_payoff_matrix():
    game:NFG_Core = st.session_state.lh['game']
    
    # mat[col][row], as in plotly
    mat = []
    for a1 in range(game.n_strategies[1]):
        col = []
        for a0 in range(game.n_strategies[0]):
            col.append(
                (game.u_mat[0,a0,a1],game.u_mat[1,a0,a1])
            )
        mat.append(col)

    row_labels = game.labels[0]
    col_labels = game.labels[1]

    # render table
    fig = go.Figure(
        data=[  
            go.Table(
                header=dict(
                    values=[""] + col_labels,
                    fill_color="#f0f0f0",
                    align="center"
                ),
                cells=dict(
                    values=[row_labels, *mat],
                    align="center"
                ),
            )
        ]
    )

    # set height
    n_rows = game.n_strategies[0] + 1
    fig.update_layout(
        height = 20*(n_rows+1),
        margin=dict(t=4, b=4, l=4, r=4),
        autosize=False
    )

    st.plotly_chart(fig, width='stretch', key=uid.get())


if __name__ == "__main__":
    main()