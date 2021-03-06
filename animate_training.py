#!/usr/bin/env python3
#  -*- coding: utf-8 -*-
__author__ = "Varun Nayyar <nayyarv@gmail.com>"

import os
from typing import Dict, Any
import numpy as np

import attr
import click

import torch
from torch import nn
from torch.optim import sgd

import swarm
import swarm.core
from swarm import animator, core, regimes
from swarm.regimes import log


def get_function(name):

    if hasattr(torch, name) == True:
        # let it error if it fails
        return getattr(torch, name)
    else:
        target = np.nan_to_num(eval("lambda x: " + name))
        return target


@attr.s(auto_attribs=True)
class SwarmTrainerBase:
    """
    WIP - do not use
    """

    xt: torch.Tensor
    yt: torch.Tensor

    network: swarm.get_network = nn.Linear
    netkwargs: Dict[str, Any] = {}

    optim: swarm.get_torch_optim = sgd.SGD
    optimkwargs: Dict[str, Any] = {}

    loss_func: swarm.get_torch_nn = nn.MSELoss()
    num_epochs: int = 200

    def __attrs_post_init__(self):
        assert self.xt.size() == self.yt.size()
        assert self.new_network()

    def to_metadata(self):
        md = attr.asdict(self)
        # remove
        del md["xt"]
        del md["yt"]

        return {
            "x": self.xt.tolist(),
            "y": self.yt.tolist(),
            "regime": self.__class__.__name__,
            "regimedict": md,
        }

    def new_network(self):
        return self.network(**self.netkwargs)

    def train_bee(self):
        net = self.new_network()
        optimiser = self.optim(net.parameters(), **self.optimkwargs)

        start_loss = self.loss_func(net(self.xt), self.yt)
        loss = 0
        for epoch in range(self.num_epochs):
            optimiser.zero_grad()
            ypred = net(self.xt)

            loss = self.loss_func(ypred, self.yt)
            log.debug("e: %s, loss: %s", epoch, loss)
            if torch.isnan(loss):
                raise RuntimeError("NaN loss, poorly configured experiment")

            yield ypred, loss

            loss.backward()
            optimiser.step()

        log.debug("First loss %s v final %s", start_loss, loss)


@click.command()
@click.option("--hidden", "-h", type=int, default=2)
@click.option("--width", "-w", type=int, default=2)
@click.option("--activation", "-a", type=str, default="ReLU")
@click.option("-n", "--nepoch", type=int, default=200)
@click.option("--lr", "--learning-rate", type=float, default=0.002)
@click.option("--xdomain", type=str, default="-1:3")
@click.option("--func", "funcname", type=str, default="exp")
@click.option("--swarmsize", type=int, default=50)
@click.option("--destdir", type=str, default="sample_animations")
@click.option("--show/--no-show", default=True)
def main(hidden, width, activation, nepoch, lr, funcname, xdomain, swarmsize, destdir, show):
    print(hidden, width, activation, nepoch, lr, funcname, xdomain, swarmsize, destdir, show)

    xdomain = [float(x) for x in xdomain.split(":")]
    xt = torch.linspace(xdomain[0], xdomain[1], 101)
    yt = get_function(funcname)(xt)
    afunc = swarm.get_activation(activation)

    bee_trainer = regimes.make_bee(
        regimes.default_train,
        xt,
        yt,
        activation=afunc,
        hidden=hidden,
        width=width,
        lr=lr,
        num_epochs=nepoch,
    )

    results = core.swarm_train(bee_trainer, num_bees=swarmsize, fields="ypred,loss")

    xdstr = f"[{xdomain[0]}:{xdomain[1]}]"
    fname = f"{funcname}_{xdstr}_{hidden}h{width}w_{activation}_{nepoch}e.mp4"

    destfile = os.path.join(destdir, fname)
    print(f"Creating animation and saving to {destfile}")
    ls1 = animator.LineSwarm.standard(
        xt.detach().numpy(),
        yt.detach().numpy(),
        results["ypred"],
        set_title=f"NN with {hidden} layers {width} wide and {activation} activation approximates {funcname}",
    )
    animator.swarm_animate([ls1], destfile)
    if show:
        import webbrowser

        print(f"Opening {os.path.abspath(destfile)} in browser")
        webbrowser.open_new_tab(os.path.abspath(destfile))


if __name__ == "__main__":
    main()
