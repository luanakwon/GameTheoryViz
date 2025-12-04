from __future__ import annotations
import streamlit as st
import plotly.graph_objects as go

from core.normal_form_game import NFG_Core
from strategy_utility.viz_components import StrategyUtilityViz, MixedStrategy, MixedStrategyProfile

# temporary uid
class uid:
    id=0
    @staticmethod       
    def get():
        uid.id += 1
        return uid.id

def main():
    if not hasattr(st.session_state,'su'):
        st.session_state.su = {}
    if 'tmp' not in st.session_state.su:
        st.session_state.su['tmp'] = {}
    # render headers, load game and viz
    render_page_header() 
    game: NFG_Core = st.session_state.su['game']
    viz: StrategyUtilityViz = st.session_state.su['viz']
    render_game_header()

    render_player_selector(viz,game)
    plot_tab, table_tab = st.tabs(("Plot","Table"))
    with plot_tab:
        render_plot()
    with table_tab:
        render_table()
    render_editor_tabs(viz,game)


def render_page_header():
    # render title description, savefileloader gametitle
    st.write("### Opponents' Strategy vs Utility Chart")
    st.write(
        "This visualization demonstrates how the player's utility for each strategy changes with the opponents' strategy profile. "+
        "The y-axis displays expected utility, and each curve corresponds one of the player i's strategy. "+ 
        "This helps reveal how utilities change as the strategy profiles shifts. "    
    )
    render_file_uploaders()

def render_game_header():
    # render game title, save viz button
    with st.container(horizontal=True):
        st.write(f"### Game: [{st.session_state.su['game'].title}]")
        # save_viz = st.button('Save Viz',key='save_viz_btn')
        # if save_viz:
        #     viz:StrategyUtilityViz = st.session_state.su['viz']
        #     viz.sav

        st.download_button(
            label='Download Viz',
            data=st.session_state.su['viz'].to_json(),
            file_name=f'viz1_{st.session_state.su['viz'].game.title}.json',
            mime="text/json",
            icon=":material/download:"
        )
                  
def render_file_uploaders():
    # render viz file uploader
    def del_session_viz():
        st.session_state.su.pop('viz')
        st.session_state.su.pop('game')
    # if in session -> session load
    # if no session, has file -> load file
    # if no session, no file --> default file
    viz_file = st.file_uploader(
        label='Load Viz',type='json',accept_multiple_files=False,on_change=del_session_viz)
    
    if 'viz' in st.session_state.su:
        return
    if viz_file is not None:
        st.session_state.su['viz'] = StrategyUtilityViz.load_from_json(viz_file)
        st.session_state.su['game'] = st.session_state.su['viz'].game
    else:
        with open("data/su/viz1_Prisoner's Dilemma.json") as f:
            st.session_state.su['viz'] = StrategyUtilityViz.load_from_json(f)
        st.session_state.su['game'] = st.session_state.su['viz'].game

        
def render_player_selector(viz:StrategyUtilityViz,game:NFG_Core):
    n = game.n_players
    option_labels = [f"Player {i}" for i in range(n)]
    player = st.selectbox(
        'render player selector',
        option_labels,
        label_visibility='collapsed',
        index=viz.player,
        key=uid.get())
    player = option_labels.index(player)
    viz.change_player(player)
    # on change - viz.change_player to change the core data
    #       reset the rest of UIs
    #       only when actually changed


def render_plot():
    viz: StrategyUtilityViz = st.session_state.su['viz']
    u_mat, pi_s, oppo_sps = viz.get_plot_data()

    # show message at default
    if len(pi_s) == 0 or len(oppo_sps) == 0:
        with st.container(height=300):
            st.write("No strategies to plot yet.")
        return

    # collect visible opponent profiles (x-axis)
    x_indices = [j for j, sp in enumerate(oppo_sps) if sp.visible]
    x_labels = [oppo_sps[j].label for j in x_indices]

    fig = go.Figure()

    for i, ms in enumerate(pi_s):
        if not ms.visible:
            continue

        # y-values filtered by visible opponent profiles
        y_values = [u_mat[i][j] for j in x_indices]

        # x positions: just indices 0..len-1
        x_values = list(range(len(x_indices)))

        fig.add_trace(
            go.Scatter(
                x=x_values,
                y=y_values,
                mode="lines+markers",
                name=ms.label,
            )
        )

    fig.update_layout(
        margin=dict(l=40, r=20, t=40, b=40),
        xaxis=dict(
            tickmode="array",
            tickvals=list(range(len(x_labels))),
            ticktext=x_labels,
            title="Opponent mixed strategy profile"
        ),
        yaxis=dict(
            title=f"Utility of Player {viz.player}"
        ),
        legend=dict(
            title=f"P{viz.player} strategies"
        )
    )

    with st.container():
        st.plotly_chart(fig, width='stretch')

    
def render_table():
    game:NFG_Core = st.session_state.su['game']

    if game.n_players == 2:
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
                        align="center",
                        font=dict(size=15),
                        height=30
                    ),
                    cells=dict(
                        values=[row_labels, *mat],
                        align="center",
                        font=dict(size=15),
                        height=30
                    ),
                )
            ]
        )

        # set height
        n_rows = game.n_strategies[0] + 1
        fig.update_layout(
            height = 30*(n_rows+1),
            margin=dict(t=15, b=10, l=10, r=10),
            autosize=True
        )

        st.plotly_chart(fig, width='stretch', key=uid.get())

    else:
        st.write("Utility Matrix is only supported for 2 player games")

def render_editor_tabs(viz:StrategyUtilityViz, game:NFG_Core):
    # tabs: Legend, Edit Pi, Edit P-i
    tab_legend, tab_edit_self, tab_edit_oppo = st.tabs(
        ('Legend', f'Edit P{viz.player}', 'Edit Opponents')
    )
    with tab_legend:
        render_legend_tab(viz)
    with tab_edit_self:
        render_edit_pself_tab(viz,game)
    with tab_edit_oppo:
        render_edit_oppo_tab(viz,game)


def render_legend_tab(viz:StrategyUtilityViz):

    def toggle_s_pi_cb(sid:int):
        viz:StrategyUtilityViz = st.session_state.su['viz']
        current_vis = viz.get_pi_s()[sid].visible
        viz.set_visible('self',sid, not current_vis)
        # reload UI..?

    def toggle_s_po_cb(sid:int):
        viz:StrategyUtilityViz = st.session_state.su['viz']
        current_vis = viz.get_oppo_sps()[sid].visible
        viz.set_visible('oppo',sid,not current_vis)
        # reload UI?
    
    # split into two columns: player i, player oppo
    col1, col2 = st.columns(2)

    # player i column
    with col1:
        # fixed height scrollable window
        with st.container(height=250):
            st.write(f'Player {viz.player}')
            player_i_strategies = viz.get_pi_s()
            
            # list player's strategies
            for sid, strategy in enumerate(player_i_strategies):
                st.toggle(
                    label=f"{strategy.label}", # removed icon
                    value=strategy.visible, on_change=toggle_s_pi_cb, args=(sid,),
                    key=uid.get())
  
    with col2:
        with st.container(height=250):
            st.write('Opponents')
            # sample player strategies
            p_o_sprofiles = viz.get_oppo_sps()

            # === Logic ===
            # load actual opponents strategy profiles from viz
            # =============

            # list player's strategies
            for sid, sp in enumerate(p_o_sprofiles):
                st.toggle(
                    label=f"{sp.label}", # removed icon
                    value=sp.visible, on_change=toggle_s_po_cb,args=(sid,),
                    key=uid.get())


def render_edit_pself_tab(viz:StrategyUtilityViz, game:NFG_Core):
    # callbacks
    def btn_add_cb(ms:MixedStrategy):
        viz:StrategyUtilityViz = st.session_state.su['viz']
        viz._add_strategy_player_i(ms)
        # clear this edit tab to default
        st.session_state.su['tmp'].pop('ms')
        st.session_state['su_pself_tab_mixed_strategy_selectbox'] = 'Add_new'

    def btn_mod_cb(sid:int, ms:MixedStrategy):
        viz:StrategyUtilityViz = st.session_state.su['viz']
        viz._modify_strategy_player_i(sid,ms)
        # clear this edit tab to default
        st.session_state.su['tmp'].pop('ms')
        st.session_state['su_pself_tab_mixed_strategy_selectbox'] = 'Add_new'

    def btn_del_cb(sid:int):
        viz:StrategyUtilityViz = st.session_state.su['viz']
        viz._delete_strategy_player_i(sid)
        # clear this edit tab to default
        st.session_state.su['tmp'].pop('ms')
        st.session_state['su_pself_tab_mixed_strategy_selectbox'] = 'Add_new'

    def del_ses_ms():
        st.session_state.su['tmp'].pop('ms')

    # fixed height scrollable window
    with st.container(height=250):
        # drop down menu for choosing which strategy to edit
        # first option is to add a new mixed strategy
        option_labels = ["Add_new",]+[s.label for s in viz.get_pi_s()]
        option = st.selectbox('pself mixed strategy selectbox',
            option_labels,
            label_visibility='collapsed', 
            key='su_pself_tab_mixed_strategy_selectbox', 
            on_change=del_ses_ms)
        
        # ms = temporary dataholder for mixed strategy, before updated to viz via buttons.
        # when options change, resets ms, and re-instantiate below
        # when option choose existing mixed strategy, deepcopy from viz
        if 'ms' in st.session_state.su['tmp']:
            NEW_MS = False
            ms = st.session_state.su['tmp']['ms']
            if option != 'Add_new':
                sid = option_labels.index(option)-1
        else:
            NEW_MS = True
            if option == 'Add_new':
                ms = MixedStrategy(viz.player, game.labels[viz.player])
                st.session_state.su['tmp']['ms'] = ms
            else:
                sid = option_labels.index(option)-1
                ms = MixedStrategy.from_dict(viz.get_pi_s()[sid].to_dict())
                st.session_state.su['tmp']['ms'] = ms

        # Mixed Strategy header: Name, Add/Modify/Delete
        # put name, add, modify, delete horizontally
        with st.container(horizontal=True):
            # Name of current strategy.
            ms.label = st.text_input('pself mixed strategy name text_input',ms.label,label_visibility='collapsed')
            
            # buttons
            if option == 'Add_new':
                st.button('Add',on_click=btn_add_cb,args=(ms,),key=uid.get())
            else:
                st.button('Modify',on_click=btn_mod_cb,args=(sid,ms),key=uid.get())
                st.button('Delete',on_click=btn_del_cb,args=(sid,),key=uid.get())   
        
        # Mixed strategy supports and mixes
        # list all the supports (even with 0 ratio)
        # border container
        with st.container(border=True):
        
            # list supports
            for i, (support, ratio) in enumerate(ms.get_items()):
                label_col, slider_col = st.columns(2, vertical_alignment='center')
                with label_col:
                    st.write(support.label)
                with slider_col:
                    # match slider value with ms fo the first time ms is instantiated
                    if NEW_MS:
                        st.session_state[f"su_pself_supports_slider_{support.sid}"] = float(ratio)
                    new_ratio = st.slider(
                        'pself ms support mix ratio slider',
                        0.0,1.0,
                        key=f"su_pself_supports_slider_{support.sid}",
                        label_visibility='collapsed')
                    ms.update(support,new_ratio,normalize=False)

                # no delete nor add, only use ratio


def render_edit_oppo_tab(viz:StrategyUtilityViz, game:NFG_Core):
    # callbacks
    def btn_add_cb(msp:MixedStrategyProfile):
        viz:StrategyUtilityViz = st.session_state.su['viz']
        viz._add_sprofile_player_o(msp)
        # clear this edit tab to default
        st.session_state.su['tmp'].pop('msp')
        st.session_state['su_oppo_tab_mixed_strategy_selectbox'] = 'Add_new'

    def btn_mod_cb(sid:int, msp:MixedStrategyProfile):
        viz:StrategyUtilityViz = st.session_state.su['viz']
        viz._modify_sprofile_player_o(sid,msp)
        # clear this edit tab to default
        st.session_state.su['tmp'].pop('msp')
        st.session_state['su_oppo_tab_mixed_strategy_selectbox'] = 'Add_new'

    def btn_del_cb(sid:int):
        viz:StrategyUtilityViz = st.session_state.su['viz']
        viz._delete_sprofile_player_o(sid)
        # clear this edit tab to default
        st.session_state.su['tmp'].pop('msp')
        st.session_state['su_oppo_tab_mixed_strategy_selectbox'] = 'Add_new'

    def del_ses_msp():
        st.session_state.su['tmp'].pop('msp')

    # fixed height scrollable window
    with st.container(height=250):
        # drop down menu for choosing which strategy to edit
        # first option is to add a new mixed strategy
        option_labels = ["Add_new",]+[s.label for s in viz.get_oppo_sps()]
        option = st.selectbox('oppo mixed strategy profile selectbox',
            option_labels,
            label_visibility='collapsed', 
            key='su_oppo_tab_mixed_strategy_selectbox',
            on_change=del_ses_msp)
        
        # msp = temporary dataholder for mixed strategy profile, before updated to viz
        # when options change, resets msp, and re-instantiate below
        # when option choose existing mixed strategy profile, deepcopy from viz
        if 'msp' in st.session_state.su['tmp']:
            NEW_MSP = False
            msp = st.session_state.su['tmp']['msp']
            if option != 'Add_new':
                sid = option_labels.index(option)-1
        else:
            NEW_MSP = True
            if option == 'Add_new':
                msp = MixedStrategyProfile(
                    excluding_player=viz.player,
                    game=game
                )
                st.session_state.su['tmp']['msp'] = msp
            else:
                sid = option_labels.index(option)-1
                msp = MixedStrategyProfile.from_dict(
                    viz.get_oppo_sps()[sid].to_dict()
                )
                st.session_state.su['tmp']['msp'] = msp
            
        # Mixed Strategy Profile Header: Name, Buttons
        # put name, add, modify, delete horizontally
        with st.container(horizontal=True):
            # Name of current strategy.
            msp.label = st.text_input('oppo msp name text_input',msp.label,label_visibility='collapsed')
            
            # buttons
            if option == 'Add_new':
                st.button('Add',on_click=btn_add_cb,args=(msp,),key=uid.get())
            else:
                st.button('Modify',on_click=btn_mod_cb,args=(sid,msp),key=uid.get())
                st.button('Delete',on_click=btn_del_cb,args=(sid,),key=uid.get())   
        
        # Mixed Strategies in the profile
        # list all supports for each mixed strategy
        # border container
        with st.container(border=True):
            # for each mixed strategies
            for ms in msp.mixed_strats:
                st.write(f"**Player {ms.pid}**")
                # list supports
                for i, (support, ratio) in enumerate(ms.get_items()):
                    label_col, slider_col = st.columns(2, vertical_alignment='center')
                    with label_col:
                        st.write(support.label)
                    with slider_col:
                        if NEW_MSP:
                            st.session_state[f"su_oppo_supports_slider_{ms.pid}_{support.sid}"] = float(ratio)
                        new_ratio = st.slider(
                            'oppo mix slider',
                            0.0,1.0,
                            key=f"su_oppo_supports_slider_{ms.pid}_{support.sid}",
                            label_visibility='collapsed')
                        ms.update(support,new_ratio, normalize=False)
                    # no delete nor add support. only use ratio


if __name__ == "__main__":
    main()