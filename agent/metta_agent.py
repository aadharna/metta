from __future__ import annotations

from typing import List

import hydra
from omegaconf import OmegaConf
from sample_factory.model.action_parameterization import ActionParameterizationDefault
from sample_factory.model.core import ModelCoreRNN
from sample_factory.utils.typing import ActionSpace, ObsSpace
from torch import Tensor
from sample_factory.algo.utils.action_distributions import sample_actions_log_probs
import pufferlib.spaces

from tensordict import TensorDict
from torch import Tensor, nn
import torch
from agent.agent_interface import MettaAgentInterface
from agent.lib.util import make_nn_stack
from agent.lib.weight_transformer import WeightTransformer

class MettaAgent(nn.Module, MettaAgentInterface):
    def __init__(
        self,
        obs_space: ObsSpace,
        action_space: ActionSpace,
        grid_features: List[str],
        global_features: List[str],
        weight_transformer: WeightTransformer,
        **cfg
    ):
        super().__init__()
        cfg = OmegaConf.create(cfg)
        self.cfg = cfg
        self.observation_space = obs_space
        self.action_space = action_space
        self.weight_transformer = weight_transformer
        self._encoder = hydra.utils.instantiate(
            cfg.observation_encoder,
            obs_space, grid_features, global_features)

        self._decoder = hydra.utils.instantiate(
            cfg.decoder,
            cfg.core.rnn_size)
        
        self._critic_linear = make_nn_stack(
            self.decoder_out_size(),
            1,
            list(cfg.critic.hidden_sizes),
            nonlinearity=getattr(nn, cfg.get('critic.nonlinearity', 'ReLU'), nn.ReLU)(),
            transform_weights=self.weight_transformer.key('critic'),
        )

        if isinstance(action_space, pufferlib.spaces.Discrete):
            self.atn_type = make_nn_stack(
                input_size=self.decoder_out_size(),
                hidden_sizes=list(cfg.actor.hidden_sizes),
                output_size=action_space.n,
                nonlinearity=getattr(nn, cfg.get('actor.nonlinearity', 'ReLU'), nn.ReLU)(),
                transform_weights=self.weight_transformer.key('actor')
            )
            self.atn_param = None
        elif hasattr(action_space, 'nvec') and len(action_space.nvec) == 2:
            self.atn_type = make_nn_stack(
                input_size=self.decoder_out_size(),
                output_size=action_space.nvec[0],
                hidden_sizes=list(cfg.actor.hidden_sizes),
                nonlinearity=getattr(nn, cfg.get('actor.nonlinearity', 'ReLU'), nn.ReLU)(),
                transform_weights=self.weight_transformer.key('actor')
            )
            self.atn_param = make_nn_stack(
                input_size=self.decoder_out_size(),
                output_size=action_space.nvec[1],
                hidden_sizes=list(cfg.actor.hidden_sizes),
                nonlinearity=getattr(nn, cfg.get('actor.nonlinearity', 'ReLU'), nn.ReLU)(),
                transform_weights=self.weight_transformer.key('actor')
            )
        else:
            raise ValueError(f"Unsupported action space: {action_space}")

        self.apply(self.initialize_weights)

    def decoder_out_size(self):
        return self._decoder.get_out_size()

    def encode_observations(self, td: TensorDict):
        td["encoded_obs"] = self._encoder(td["obs"])

    def decode_state(self, td: TensorDict):
        td["state"] = self._decoder(td["core_output"])
        td["values"] = self._critic_linear(td["state"]).squeeze()

    def aux_loss(self, normalized_obs_dict, rnn_states):
        raise NotImplementedError()

    #move this to make_nn_stack?
    def initialize_weights(self, layer):
        gain = 1.0

        if type(layer) is nn.Conv2d:
            nn.init.orthogonal_(layer.weight.data, gain=gain)

            if hasattr(layer, "bias") and isinstance(layer.bias, torch.nn.parameter.Parameter):
                layer.bias.data.fill_(0)
        else:
            # LSTMs and GRUs initialize themselves
            # should we use orthogonal/xavier for LSTM cells as well?
            # I never noticed much difference between different initialization schemes, and here it seems safer to
            # go with default initialization,
            pass

    def get_action_networks(self):
        return self.atn_type, self.atn_param
