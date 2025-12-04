from __future__ import annotations
import streamlit as st
import plotly.graph_objects as go
import json

from core.normal_form_game import NFG_Core
from pareto.viz_components import ParetoViz, MixedStrategyProfile

# temporary uid
class uid:
    id=0
    @staticmethod       
    def get():
        uid.id += 1
        return uid.id

def main():
    if not hasattr(st.session_state,'pr'):
        st.session_state.pr = {}
    if 'tmp' not in st.session_state.pr:
        st.session_state.pr['tmp'] = {}
    # render headers, load game and viz
    render_page_header() 
    game: NFG_Core = st.session_state.pr['game']
    viz: ParetoViz = st.session_state.pr['viz']

    render_game_header()

    plot_tab, table_tab = st.tabs(("Plot","Table"))
    with plot_tab:
        render_plot()
    with table_tab:
        render_table()

    render_editor_tabs(viz,game)


def render_page_header():
    # render title description, savefileloader gametitle
    st.write("### Utility vs Strategy Profiles Chart")
    st.write("short description of this page here")
    render_file_uploaders()

def render_game_header():
    # render game title, save viz button
    with st.container(horizontal=True):
        st.write(f"### Game: [{st.session_state.pr['game'].title}]")
        # save_viz = st.button('Save Viz',key='save_viz_btn')
        # if save_viz:
        #     viz:ParetoViz = st.session_state.pr['viz']
        #     viz.sav

        st.download_button(
            label='Download Viz',
            data=st.session_state.pr['viz'].to_json(),
            file_name=f'viz2_{st.session_state.pr['viz'].game.title}.json',
            mime="text/json",
            icon=":material/download:"
        )
                  
def render_file_uploaders():
    # render viz file uploader
    def del_session_viz():
        st.session_state.pr.pop('viz')
        st.session_state.pr.pop('game')
    # if in session -> session load
    # if no session, has file -> load file
    # if no session, no file --> default file
    viz_file = st.file_uploader(
        label='Load Viz',type='json',accept_multiple_files=False,on_change=del_session_viz)
    
    if 'viz' in st.session_state.pr:
        return
    if viz_file is not None:
        st.session_state.pr['viz'] = ParetoViz.load_from_json(viz_file)
        st.session_state.pr['game'] = st.session_state.pr['viz'].game
    else:
        with open("data/pr/viz2_prisoner's_dilemma.json") as f:
            st.session_state.pr['viz'] = ParetoViz.load_from_json(f)
        st.session_state.pr['game'] = st.session_state.pr['viz'].game


def render_plot():
    viz: ParetoViz = st.session_state.pr['viz']
    msps = [] # mixed strategy profiles
    u_mat = [] # utiliti matrice [msp][players]

    u_mat, msps = viz.get_plot_data()

    # show message at default
    if len(msps) == 0:
        with st.container():
            st.write("No strategies to plot yet.")
        return

    # build x axis
    x_values = list(range(viz.game.n_players))
    x_labels = [f'P{i}' for i in x_values]

    fig = go.Figure()

    for i, msp in enumerate(msps):
        # skip invisible mixed strategy profiles
        if not msp.visible:
            continue

        y_values = u_mat[i]

        fig.add_trace(
            go.Scatter(
                x=x_values,
                y=y_values,
                mode="lines+markers",
                name=msp.label,
            )
        )

    fig.update_layout(
        margin=dict(l=40, r=20, t=40, b=40),
        xaxis=dict(
            tickmode="array",
            tickvals=list(range(len(x_labels))),
            ticktext=x_labels,
            title="Players"
        ),
        yaxis=dict(
            title=f"Utilities"
        ),
        legend=dict(
            title=f"Mixed Strategy Profiles"
        )
    )

    with st.container():
        st.plotly_chart(fig, width='stretch')

    
def render_table():
    game:NFG_Core = st.session_state.pr['game']

    if game.n_players == 2:
        for pid in range(game.n_players):
            st.write(f"**Player {pid}'s utility**")
            st.table(game.u_mat[pid])

    else:
        st.write("Utility Matrix is only supported for 2 player games")

def render_editor_tabs(viz:ParetoViz, game:NFG_Core):
    # tabs: Legend, Edit Pi, Edit P-i
    tab_legend, tab_edit = st.tabs(
        ('Legend', 'Edit Strategy Profiles')
    )
    with tab_legend:
        render_legend_tab(viz)
    with tab_edit:
        render_edit_oppo_tab(viz,game)


def render_legend_tab(viz:ParetoViz):

    def toggle_s_po_cb(spid:int):
        viz:ParetoViz = st.session_state.pr['viz']
        current_vis = viz.get_msps()[spid].visible
        viz.set_visible(spid,not current_vis)
        # reload UI?

    with st.container(height=250):
        st.write('Mixed Strategy Profiles')
        # sample player strategies
        sprofiles = viz.get_msps()

        # === Logic ===
        # load actual opponents strategy profiles from viz
        # =============

        # list player's strategies
        for spid, sp in enumerate(sprofiles):
            st.toggle(
                label=f"{sp.label}", # removed icon
                value=sp.visible, on_change=toggle_s_po_cb,args=(spid,),
                key=uid.get())

def render_edit_oppo_tab(viz:ParetoViz, game:NFG_Core):
    # callbacks
    def btn_add_cb(msp:MixedStrategyProfile):
        viz:ParetoViz = st.session_state.pr['viz']
        viz._add_sprofile(msp)
        # clear this edit tab to default
        st.session_state.pr['tmp'].pop('msp')
        st.session_state['pr_mixed_strategy_selectbox'] = 'Add_new'

    def btn_mod_cb(spid:int, msp:MixedStrategyProfile):
        viz:ParetoViz = st.session_state.pr['viz']
        viz._modify_sprofile(spid,msp)
        # clear this edit tab to default
        st.session_state.pr['tmp'].pop('msp')
        st.session_state['pr_mixed_strategy_selectbox'] = 'Add_new'

    def btn_del_cb(spid:int):
        viz:ParetoViz = st.session_state.pr['viz']
        viz._delete_sprofile(spid)
        # clear this edit tab to default
        st.session_state.pr['tmp'].pop('msp')
        st.session_state['pr_mixed_strategy_selectbox'] = 'Add_new'

    def del_ses_msp():
        st.session_state.pr['tmp'].pop('msp')

    # fixed height scrollable window
    with st.container(height=250):
        # drop down menu for choosing which strategy to edit
        # first option is to add a new mixed strategy
        option_labels = ["Add_new",]+[s.label for s in viz.get_msps()]
        option = st.selectbox('oppo mixed strategy profile selectbox',
            option_labels,
            label_visibility='collapsed', 
            key='pr_mixed_strategy_selectbox',
            on_change=del_ses_msp)
        
        # msp = temporary dataholder for mixed strategy profile, before updated to viz
        # when options change, resets msp, and re-instantiate below
        # when option choose existing mixed strategy profile, deepcopy from viz
        if 'msp' in st.session_state.pr['tmp']:
            NEW_MSP = False
            msp = st.session_state.pr['tmp']['msp']
            if option != 'Add_new':
                spid = option_labels.index(option)-1
        else:
            NEW_MSP = True
            if option == 'Add_new':
                msp = MixedStrategyProfile(
                    game=game
                )
                st.session_state.pr['tmp']['msp'] = msp
            else:
                spid = option_labels.index(option)-1
                msp = MixedStrategyProfile.from_dict(
                    viz.get_msps()[spid].to_dict()
                )
                st.session_state.pr['tmp']['msp'] = msp
            
        # Mixed Strategy Profile Header: Name, Buttons
        # put name, add, modify, delete horizontally
        with st.container(horizontal=True):
            # Name of current strategy.
            msp.label = st.text_input('oppo msp name text_input',msp.label,label_visibility='collapsed')
            
            # buttons
            if option == 'Add_new':
                st.button('Add',on_click=btn_add_cb,args=(msp,),key=uid.get())
            else:
                st.button('Modify',on_click=btn_mod_cb,args=(spid,msp),key=uid.get())
                st.button('Delete',on_click=btn_del_cb,args=(spid,),key=uid.get())   
        
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
                            st.session_state[f"pr_supports_slider_{ms.pid}_{support.sid}"] = float(ratio)
                        new_ratio = st.slider(
                            'oppo mix slider',
                            0.0,1.0,
                            key=f"pr_supports_slider_{ms.pid}_{support.sid}",
                            label_visibility='collapsed')
                        ms.update(support,new_ratio, normalize=False)
                    # no delete nor add support. only use ratio


if __name__ == "__main__":
    main()