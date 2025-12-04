from __future__ import annotations
from typing import Dict, List
import json
from core.normal_form_game import NFG_Core

class PureStrategy:
    def __init__(self,pid,sid,visible,icon,label):
        self.pid:int = pid # player id
        self.sid:int = sid # strategy id
        # pid * sid form unique key
        self.visible:bool = visible # visibility
        self.icon:str = icon # icon path
        self.label:str = label # strat name

    def __eq__(self,x):
        if isinstance(x,PureStrategy):
            if self.pid==x.pid and self.sid == x.sid:
                return True
        return False
    
    def to_dict(self) -> Dict:
        return {
            'pid':self.pid,
            'sid':self.sid,
            'visible':self.visible,
            'icon':self.icon,
            'label':self.label
        }
    
    @classmethod
    def from_dict(cls, data:dict) -> "PureStrategy":
        return cls(
            pid = int(data['pid']),
            sid = int(data['sid']),
            visible=bool(data['visible']),
            icon=data.get('icon',''),
            label=data.get('label',f"s{data['sid']}")
        )
    

  

class MixedStrategy:
    def __init__(self,pid, labels):
        self.pid:int = pid
        # self.mix:Dict[PureStrategy, float] = {
        #     PureStrategy(pid,sid,True,'',label):0
        #     for sid, label in enumerate(labels)
        # }
        self.supports = [
            PureStrategy(pid,sid,True,'',label)
            for sid, label in enumerate(labels)
        ]
        self.ratios = [
            0.0 for _ in labels
        ]

        self.visible: bool = True # visibility
        self.icon:str = '' # icon path
        self.label:str = 'New Strategy'# strategy name
    
    def update(self,support:PureStrategy, ratio=1, normalize=True):
        if support.pid != self.pid:
            print(f'support {support.label} does not belong to p{self.pid}')
        else:
            self.ratios[support.sid] = max(ratio,0.0)
        if normalize:
            self._normalize()

    def pop(self,sid:int=None,support:PureStrategy=None):
        if sid is not None:
            self.ratios[sid] = 0
        elif support is not None:
            self.ratios[support.sid] = 0
        else:
            print("provide either sid or a support")

    def get_items(self):
        return zip(self.supports, self.ratios)

    def _normalize(self):
        total = sum(self.ratios)
        if total > 0:
            for i in range(len(self.ratios)):
                self.ratios[i] /= total


    # save/loading supports for each mixedStrategy might be a waste.
    # later: Optimize
    def to_dict(self) -> Dict:
        return {
            'pid':self.pid,
            'supports':[sup.to_dict() for sup in self.supports],
            'ratios':self.ratios,
            'visible':self.visible,
            'icon':self.icon,
            'label':self.label
        }
    
    @classmethod
    def from_dict(cls, data:dict) -> "MixedStrategy":
        out = cls(
            pid=int(data['pid']),
            labels=['']
        )
        out.supports = [
            PureStrategy.from_dict(d) for d in data['supports']
        ]
        out.ratios = data['ratios']
        out.visible = data['visible']
        out.icon = data.get('icon','')
        out.label = data.get('label','New Strategy')
        out._normalize()
        return out
    


class MixedStrategyProfile:
    def __init__(self, excluding_player:int, game:NFG_Core=None):
        self.mixed_strats: List[MixedStrategy] = []
        self.visible:bool = True
        self.icon:str = ''
        self.label:str = 'New Mixed Strategy Profile -i'

        if game is not None:
            self._fill_mixed_strats(excluding_player,game)

    def _fill_mixed_strats(self,excluding_player:int,game:NFG_Core):
        for player in range(game.n_players):
            if player == excluding_player:
                continue

            self.mixed_strats.append(
                MixedStrategy(player,game.labels[player])
            )
    
    def to_dict(self) -> Dict:
        return {
            'mixed_strats':[ms.to_dict() for ms in self.mixed_strats],
            'visible':self.visible,
            'icon':self.icon,
            'label':self.label
        }
    
    @classmethod
    def from_dict(cls, data:dict) -> "MixedStrategyProfile":
        out = cls(0,None)
        out.mixed_strats = [MixedStrategy.from_dict(d) for d in data['mixed_strats']]
        out.visible = bool(data['visible'])
        out.icon = data['icon']
        out.label = data['label']
        return out
    

class compressed_suv:
    def __init__(self,player,pi_s,oppo_sps,u_mat):
        self.player:int = player
        self.pi_s: List[MixedStrategy] = pi_s
        self.oppo_sps: List[MixedStrategyProfile] = oppo_sps
        self.u_mat: List[List[float]] = u_mat

    # Do I also need to_dict/from_dict for the data class?
    def to_dict(self) -> dict:
        return {
            'player':self.player,
            'pi_s':[ms.to_dict() for ms in self.pi_s],
            'oppo_sps':[msp.to_dict() for msp in self.oppo_sps],
            'u_mat':self.u_mat
        }
    
    @classmethod
    def from_dict(cls, data:dict) -> "compressed_suv":
        return cls(
            player=int(data['player']),
            pi_s=[MixedStrategy.from_dict(d) for d in data['pi_s']],
            oppo_sps=[MixedStrategyProfile.from_dict(d) for d in data['oppo_sps']],
            u_mat=data['u_mat']
        )

class StrategyUtilityViz:
    def __init__(self, game:NFG_Core, main_player):
        self.game:NFG_Core = game
        self.player:int = main_player
        # all perspectives
        self.all_player_data: Dict[int,compressed_suv] = {}
        # in each perspective:
        # pi_s:List[MixedStrategy] = [] # player i strategies
        # oppo_sps:List[MixedStrategyProfile] = []  # opponent mixed strategy profile = x data points
        # u_mat:List[List[float]] = [] # utility[self_player_strat][oppo_stat_profile]

    def _add_strategy_player_i(self,strategy:MixedStrategy):
        strategy._normalize()
        if strategy.pid == self.player:
            data = self.all_player_data[self.player]
            data.pi_s.append(strategy)
            data.u_mat.append(
                [0 for _ in range(len(data.oppo_sps))])
            for i, oppo_sprofile in enumerate(data.oppo_sps):
                data.u_mat[-1][i] = self.game.get_util(
                    self.player,
                    [strategy,]+oppo_sprofile.mixed_strats
                )

    def _modify_strategy_player_i(self,index:int,new_strategy:MixedStrategy):
        # validity check - index in range, new_strategy belong to player i
        # replace player i's strategy at index
        # update self.u_mat[index]
        new_strategy._normalize()
        if new_strategy.pid == self.player:
            data = self.all_player_data[self.player]
            if len(data.pi_s) > index and index >= 0:
                data.pi_s[index] = new_strategy
                for i, oppo_sprofile in enumerate(data.oppo_sps):
                    data.u_mat[index][i] = self.game.get_util(
                        self.player,
                        [new_strategy,]+oppo_sprofile.mixed_strats
                    )

    def _delete_strategy_player_i(self,index:int):
        # validity check - index in range
        # delete strategy from self.pi_s
        # delete utility row (self.u_mat[index])
        data = self.all_player_data[self.player]
        if len(data.pi_s) > index and index >= 0:
            data.pi_s.pop(index)
            data.u_mat.pop(index)
        

    def _add_sprofile_player_o(self,sprofile:MixedStrategyProfile):
        pids = set([ms.pid for ms in sprofile.mixed_strats])
        if self.player not in pids and len(pids) == self.game.n_players - 1:
            data = self.all_player_data[self.player]
            data.oppo_sps.append(sprofile)
            for i, u_list in enumerate(data.u_mat):
                pi_strat = data.pi_s[i]
                pi_strat._normalize()
                utility = self.game.get_util(
                    self.player,
                    [pi_strat,]+sprofile.mixed_strats
                )
                u_list.append(utility)

    def _modify_sprofile_player_o(self,index:int,sprofile:MixedStrategyProfile):
        # validity check - index in range, sprofile includes all players except player i
        # replace opponents strategy profile at self.oppo_sps[index]
        # update self.u_mat[:][index]
        pids = set([ms.pid for ms in sprofile.mixed_strats])
        if self.player not in pids and len(pids) == self.game.n_players - 1:
            data = self.all_player_data[self.player]
            if len(data.oppo_sps) > index and index >= 0:
                data.oppo_sps[index] = sprofile
                for i, ulist in enumerate(data.u_mat):
                    pi_strat = data.pi_s[i]
                    pi_strat._normalize()
                    ulist[index] = self.game.get_util(
                        self.player,
                        [pi_strat,]+sprofile.mixed_strats
                    )

    def _delete_sprofile_player_o(self,index:int):
        # validity check - index in range
        # delete opponent strategy profile at self.oppo_sps[index]
        # delete opponent sp visiblity at self.oppo_viz[index]
        # delete column self.u_mat[:],[index]
        data = self.all_player_data[self.player]
        if len(data.oppo_sps) > index and index >= 0:
            data.oppo_sps.pop(index)
            for i in range(len(data.u_mat)):
                data.u_mat[i].pop(index)
        

    def change_player(self,p_id):
        if p_id == self.player:
            return
        # change pid
        self.player = p_id
        # set default if no previous data
        if p_id not in self.all_player_data:
            self.all_player_data[p_id] = compressed_suv(
                player=p_id,
                pi_s=[],
                oppo_sps=[],
                u_mat=[]
            )
        if len(self.all_player_data[p_id].pi_s) == 0:
            # reset player p_id's viz
            self.reset_viz()
        
    def reset_viz(self):
        # initialize to default visualization
        # the game is given
        # dont change the player
        data = self.all_player_data.get(self.player,None)
        if data is None:
            data = compressed_suv(self.player,[],[],[])
            self.all_player_data[self.player] = data

        # add player 0's pure strategies into self.pi_s (as a mixed strategy of single support)
        for sid in range(self.game.n_strategies[self.player]):
            pure = MixedStrategy(self.player,self.game.labels[self.player])
            pure.update(PureStrategy(self.player,sid,True,'',''),ratio = 1)
            pure.label = pure.supports[sid].label
            self._add_strategy_player_i(pure)

        # sample pure strategy profile where player i's strategy is their first pure strategy
        #   in other words: sprofile=(p1support0, p2support0, p3support0,...)
        # add the sampled sprofile into self.oppo_sps
        msp = MixedStrategyProfile(self.player,self.game)
        msp.label = ','.join([f'p{ms.pid}s0' for ms in msp.mixed_strats])
        for ms in msp.mixed_strats:
            ms.update(
                PureStrategy(ms.pid,0,True,'',''),
                ratio=1
            )
        self._add_sprofile_player_o(msp)
        # utility mat will be updated when adding.

    def get_pi_s(self):
        return self.all_player_data[self.player].pi_s
    
    def get_oppo_sps(self):
        return self.all_player_data[self.player].oppo_sps
    
    def get_plot_data(self):
        """Return everything needed for plotting for the current player."""
        data = self.all_player_data[self.player]
        return data.u_mat, data.pi_s, data.oppo_sps
        
    def to_json(self):
        return json.dumps(self.to_dict())

    def to_dict(self) -> dict:
        return {
            'game':self.game.to_dict(),
            'player':self.player,
            'all_player_data':{
                k:csuv.to_dict() for k,csuv in self.all_player_data.items()
            }
        }
    
    @classmethod
    def from_dict(cls, data:dict) -> "StrategyUtilityViz":
        out = cls(
            game=NFG_Core.from_dict(data['game']),
            main_player=int(data['player']))
        if len(data['all_player_data']) > 0:
            out.all_player_data = {
                int(k):compressed_suv.from_dict(d) for k,d in data['all_player_data'].items()
            }
        else:
            out.all_player_data = {
                0:compressed_suv(
                    0,[],[],[]
                )
            }
        return out

    @staticmethod
    def load_from_json(fp) -> StrategyUtilityViz:
        data = json.load(fp)
        return StrategyUtilityViz.from_dict(data)
        
    def set_visible(self,axis,index,is_visible:bool):

        data = self.all_player_data[self.player]
        # if axis == 'y' or 'self'
        #   toggle visibility of player i's strategy at index to is_visible
        if axis == 'y' or axis == 'self':
            data.pi_s[index].visible = is_visible
        # elif axis == 'x' or 'oppo'
        #   toggle visibility of opponent strategy profile at index to is_visible
        elif axis == 'x' or axis == 'oppo':
            data.oppo_sps[index].visible = is_visible
        




if __name__ == "__main__":
    with open('example_game.json','r') as f:
        game = NFG_Core.load_from_json(f)

    viz = StrategyUtilityViz(
        game=game,
        main_player=0,
    )

    d = viz.to_dict()