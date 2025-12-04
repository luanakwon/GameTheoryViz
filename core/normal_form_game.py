
from typing import List

import numpy as np
import json

class NFG_Core:
    def __init__(
        self,
        n_players:int,
        n_strategies: List[int],
        utility_mat: np.ndarray | None = None,
        # viz elements
        game_name:str = '',
        strategy_labels: List[List[str]] = None,
    ):
        assert (len(n_strategies) == n_players)

        self.n_players = n_players
        self.n_strategies = n_strategies
        
        if utility_mat is None:
            self.u_mat = np.zeros([n_players,]+n_strategies)
        else:
            assert (list(utility_mat.shape) == [n_players,]+n_strategies)
            self.u_mat = utility_mat

        assert ([len(per_player_label) for per_player_label in strategy_labels] == n_strategies)
        self.labels = strategy_labels
        self.title = game_name

    def get_util(self,player,sprofile):
        # Reorder MixedStrategy by player index
        mixed_by_player = [None] * self.n_players
        for ms in sprofile:
            mixed_by_player[ms.pid] = ms

        # Build dense probability vectors
        prob_vecs = []
        for p in range(self.n_players):
            ms = mixed_by_player[p]
            vec = np.zeros(self.n_strategies[p], dtype=float)
            for pure, prob in zip(ms.supports, ms.ratios):
                vec[pure.sid] = prob
            total = vec.sum()
            if total > 0:
                vec /= total
            else:
                return 0.0
            prob_vecs.append(vec)

        # Start with this player's payoff tensor: shape (s0, s1, ..., s_{n-1})
        res = self.u_mat[player]

        # Repeatedly contract over the first axis with each prob vector.
        # After each tensordot, the tensor loses one dimension.
        for p_vec in prob_vecs:
            res = np.tensordot(res, p_vec, axes=([0], [0]))
            # res shape shrinks: (s1,...,sn-1) -> (s2,...,sn-1) -> ... -> scalar

        return float(res)


    def to_dict(self) -> dict:
        return {
            "n_players": self.n_players,
            "n_strategies": self.n_strategies,
            "utility_mat": self.u_mat.tolist(),   # numpy -> list
            "game_name": self.title,
            "strategy_labels": self.labels,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "NFG_Core":
        return cls(
            n_players=data["n_players"],
            n_strategies=data["n_strategies"],
            utility_mat=np.array(data["utility_mat"]),
            game_name=data.get("game_name", ""),
            strategy_labels=data["strategy_labels"],
        )

    @staticmethod
    def load_from_json(fp) -> "NFG_Core":
        data = json.load(fp)
        return NFG_Core.from_dict(data)
    
if __name__ == "__main__":
    
    # game = NFG_Core(
    #     n_players=2,
    #     n_strategies=[2,2],
    #     utility_mat=np.array([
    #         [
    #             [2,0],
    #             [3,1]
    #         ],[
    #             [2,3],
    #             [0,1]
    #         ]
    #     ]),
    #     game_name="Prisoner's Dilemma",
    #     strategy_labels=[
    #         ['silent','betray'],
    #         ['silent','betray']
    #     ]
    # )
    
    # print(game.to_dict())

    # with open('example_game.json','w') as f:
    #     json.dump(game.to_dict(),f)


    game = NFG_Core(
        n_players=2,
        n_strategies=[3,2],
        utility_mat=np.array([
            [
                [0,6],
                [2,5],
                [3,3]
            ],[
                [1,0],
                [0,2],
                [4,3]
            ]
        ]),
        game_name="Lemke-Howson-Example",
        strategy_labels=[
            ['p0','p1','p2'],
            ['q0','q1']
        ]
    )
    
    print(game.to_dict())

    with open('example_game.json','w') as f:
        json.dump(game.to_dict(),f)