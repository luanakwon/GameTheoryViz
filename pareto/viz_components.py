from __future__ import annotations
from typing import Dict, List
import random
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
    def __init__(self, game:NFG_Core=None):
        self.mixed_strats: List[MixedStrategy] = []
        self.visible:bool = True
        self.icon:str = ''
        self.label:str = 'New Mixed Strategy Profile -i'

        if game is not None:
            self._fill_mixed_strats(game)

    def _normalize(self):
        for ms in self.mixed_strats:
            ms._normalize()

    def _fill_mixed_strats(self, game:NFG_Core):
        for player in range(game.n_players):
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
        out = cls(None)
        out.mixed_strats = [MixedStrategy.from_dict(d) for d in data['mixed_strats']]
        out.visible = bool(data['visible'])
        out.icon = data['icon']
        out.label = data['label']
        return out
    

class ParetoViz:
    def __init__(self, game:NFG_Core):
        self.game:NFG_Core = game
        # mixed strategy profiles. each profile includes every player
        self.msps: List[MixedStrategyProfile] = []
        # utility matrice: u[msprofile][player]
        self.u_mat:List[List[float]] = []

    
    def _add_sprofile(self,sprofile:MixedStrategyProfile):
        pids = set([ms.pid for ms in sprofile.mixed_strats])
        if len(pids) == self.game.n_players:
            sprofile._normalize()
            self.msps.append(sprofile)
            self.u_mat.append(
                [
                    self.game.get_util(player, sprofile.mixed_strats)
                    for player in pids
                ]
            )

    def _modify_sprofile(self,index:int,sprofile:MixedStrategyProfile):
        # validity check - index in range, sprofile includes all players except player i
        # replace opponents strategy profile at self.oppo_sps[index]
        # update self.u_mat[index][:]
        pids = set([ms.pid for ms in sprofile.mixed_strats])
        if len(pids) == self.game.n_players:
            if len(self.msps) > index and index >= 0:
                sprofile._normalize()
                self.msps[index] = sprofile
                self.u_mat[index] = [
                    self.game.get_util(player,sprofile.mixed_strats)
                    for player in pids
                ]

    def _delete_sprofile(self,index:int):
        # validity check - index in range
        # delete opponent strategy profile at self.oppo_sps[index]
        # delete opponent sp visiblity at self.oppo_viz[index]
        # delete column self.u_mat[:],[index]
        if len(self.msps) > index and index >= 0:
            self.msps.pop(index)
            self.u_mat.pop(index)
        
    def reset_viz(self):
        # initialize to default visualization
        # the game is given
        
        # random sample 3 pure strategy profiles
        self.msps = []
        self.u_mat = []
        for _ in range(3):
            msp = MixedStrategyProfile(game=self.game)
            for ms in msp.mixed_strats:
                sid = random.randint(0,len(ms.supports)-1)
                ms.update(PureStrategy(ms.pid,sid,True,'',''),1,True)
            self._add_sprofile(msp)
            # utility mat will be updated when adding.
    
    def get_msps(self):
        return self.msps
    
    def get_plot_data(self):
        """Return everything needed for plotting for the current player."""
        return self.u_mat, self.msps
        
    def to_json(self):
        return json.dumps(self.to_dict())

    def to_dict(self) -> dict:
        print(self)
        print(self.msps)
        return {
            'game':self.game.to_dict(),
            'msps':[
                msp.to_dict() for msp in self.msps
            ],
            'u_mat':self.u_mat
        }
    
    @classmethod
    def from_dict(cls, data:dict) -> "ParetoViz":
        out = cls(
            game=NFG_Core.from_dict(data['game']))
        out.msps = [MixedStrategyProfile.from_dict(msp) for msp in data['msps']]
        out.u_mat = data['u_mat']
        return out

    @staticmethod
    def load_from_json(fp) -> ParetoViz:
        data = json.load(fp)
        return ParetoViz.from_dict(data)
        
    def set_visible(self,index,is_visible:bool):
        if len(self.msps) > index and index >= 0:
            self.msps[index].visible = is_visible    




if __name__ == "__main__":
    with open('example_game.json','r') as f:
        game = NFG_Core.load_from_json(f)

    viz = ParetoViz(
        game=game
    )

    viz.reset_viz()

    with open('example_viz.json','w') as f:
        json.dump(viz.to_dict(),f)