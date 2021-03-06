#  -*- coding: utf-8 -*-
__author__ = "Varun Nayyar <nayyarv@gmail.com>"

import logging

import attr
from matplotlib import pyplot as plt, animation
import seaborn as sns
import numpy as np
import tqdm
import deprecation

from typing import List, Optional, Callable, Union, Iterable, Dict, Any, Tuple

logger = logging.getLogger(__name__)
# set a good default
sns.set()


@deprecation.deprecated("Use SwarmPlots and swarm_animate instead")
def make_animation(xd, yd, data, title: str, destfile: str):
    """
    Convenience method to produce an animation - requires a refactor too

    Args:
        xd: np.ndarray (N,)
        yd: np.ndarray (N,)
        data: np.ndarray (Bees, epochs, N)
        title :str
        destfile: str
    """
    plt.rcParams["figure.figsize"] = (14.0, 7.0)
    sns.set()
    # Determine a proper format
    nepoch = data[0].shape[0]
    fig = plt.figure()
    ax = plt.axes()
    ax.set_title(title)
    ax.plot(xd, yd, ".")

    line_ref = []
    for i in range(len(data)):
        (liner,) = ax.plot([], [], lw=2)
        line_ref.append(liner)

    def init():
        for line in line_ref:
            line.set_data([], [])
        return line_ref

    def animate(i):
        for dnum, line in enumerate(line_ref):
            line.set_data(xd, data[dnum][i])
        return line_ref

    anim = animation.FuncAnimation(
        fig, animate, init_func=init, frames=nepoch, interval=20, blit=True, repeat=False
    )
    # i think interval is basically overwritten by fps
    # increase fps if you feel like the animation is moving too slowly
    if destfile:
        # secret skip
        anim.save(destfile, fps=30, extra_args=["-vcodec", "libx264"])
    plt.close()


@attr.s
class SwarmPlot:
    """
    Just for automcomplete, but this is the expected API for each plot

    Attributes:
        artists: List[plt.Artist] - this is necessary for the underlying
            FuncAnimation used here. These are created in the `init` and
            used in the animate.
    """

    artists = attr.ib(init=False, factory=list, type=List[plt.Artist])

    @property
    def num_frames(self) -> int:
        """Nice to have, allows animation to know how long to go for"""
        return 0

    def plot_init(self, ax: plt.Axes):
        """Populate the artists and call the hooks"""
        pass

    def animate(self, frame: int):
        """Move the artists"""
        pass


def _validate_ax_kwargs(**kwargs):
    """
    This is an attempt to validate the kwargs on definition rather than at runtime for quicker
    feedback to the developer.
    This isn't needed by end-user, but could be used ahead of time if they like.

    Raises:
        ValueError: in the case of invalid arguments
    """
    cls = plt.Axes
    missing = []
    for k in kwargs:
        if not hasattr(cls, k):
            missing.append(k)
    if missing:
        raise ValueError("plt.Axes does not have {}".format(",".join(missing)))


def _kwargs_hook(**kwargs):
    """
    Our animation library uses hooks to allow once-off configuration of an axes. These
    include things like plotting the true y value or setting sensible x/y limits for the plot

    This can be time consuming to do, so this provides an easy way to do so, allowing
    one to call the various functions of ``plt.Axes`` as below. This is expected to be fit
    into the existing machinery of the SwarmPlot sub/duck classes so you won't need to make
    this call directly

    Examples:
        >>> _kwargs_hook(set_title="Goofy Experiment", set_ylabel="loss")
        # will be used mostly with constructors like
        >>> LineSwarm.standard(x, y, data, set_title="Goofy Experiment", set_ylabel="loss")

    Raises:
        ValueError: will attempt to validate the kwargs ahead of time, but also on execution
        in case the function arg is incorrect

    """
    # get an early error if this is a problem
    # rather than at animate time
    _validate_ax_kwargs(**kwargs)

    def inner_hook(ax):
        for k, v in kwargs.items():
            try:
                func = getattr(ax, k)
            except AttributeError:
                raise ValueError(f"Used a method {k}")
            else:
                try:
                    func(v)
                except Exception as e:
                    # we might have an issue that we're hitting a property
                    # or have type mismatches
                    raise ValueError("Unexpected failure") from e

    return inner_hook


def _apply_hook(ax: plt.Axes, hook: Union[Iterable[Callable], Callable, None]):
    """Applies a list of hooks to the axes object"""
    if not hook:
        return
    try:
        for h in hook:
            h(ax)
    except TypeError:
        # can't iterate, must be single callabe
        hook(ax)


@attr.s
class LineSwarm(SwarmPlot):
    """
    This is the standard class
    """

    x = attr.ib(type=np.ndarray)  # shape of (N,)
    data = attr.ib(type=np.ndarray)  # shape of (num_lines, timestep, N)
    hook = attr.ib(type=List[Callable], factory=list)

    @classmethod
    def standard(cls, xd, yd, data, **kwargs):
        """Plot against true yd"""
        hook = [lambda ax: ax.plot(xd, yd, "."), _kwargs_hook(**kwargs)]
        return cls(xd, data, hook)

    @classmethod
    def auto_range(cls, xd, data, **kwargs):
        """In the abscence of a true value, make sensible choices"""
        mx, mn = [data.max(), data.min()]

        def set_lim(ax: plt.Axes):
            ax.set_ylim(mn, mx)
            ax.set_xlim(xd.min(), xd.max())

        hook = [set_lim, _kwargs_hook(**kwargs)]
        return cls(xd, data, hook)

    @property
    def num_frames(self) -> int:
        return self.data.shape[1]

    def plot_init(self, ax: plt.Axes):
        self.artists = []
        ax.clear()
        _apply_hook(ax, self.hook)
        for i in range(self.data.shape[0]):
            (liner,) = ax.plot([], [], lw=2, label=str(i))
            self.artists.append(liner)

    def animate(self, frame: int):
        for bee, line in enumerate(self.artists):
            line.set_data(self.x, self.data[bee][frame])


@attr.s
class HistogramSwarm(SwarmPlot):
    """
    A histogram animation.
    This is a little limited in that that the histogram bins can't change during the animation
    so there is onus on you to clean up the data somewhat.
    """

    data = attr.ib(type=np.array)  # shape of (time, value)
    num_bins = attr.ib(type=int, default=100)
    hook = attr.ib(type=List[Callable], factory=list)

    # secret internals
    _verts = attr.ib(init=False, default=None)
    _bottom = attr.ib(init=False, default=None)

    @property
    def num_frames(self) -> int:
        return self.data.shape[0]

    @classmethod
    def from_swarm(cls, data: np.ndarray, num_bins=100, **kwargs):
        """
        Data from swarm is split across bees and epoch. In the case of a histogram, we only step
        across time and so we we merge all non-timed data for our histogram

        Args:
            data: np.ndaarray (bee, epoch, value)
            num_bins: int
                number of bins to use

        Returns:
            HistogramSwarm
        """
        beel, epochl, vall = data.shape
        hist_data = data.transpose(1, 0, 2).reshape(epochl, beel * vall)
        return cls(hist_data, num_bins, [_kwargs_hook(**kwargs)])

    def plot_init(self, ax: plt.Axes):
        """Copied from https://matplotlib.org/3.1.1/gallery/animation/animated_histogram.html"""
        import matplotlib.patches as patches
        import matplotlib.path as path

        self.artists = []
        ax.clear()
        _apply_hook(ax, self.hook)
        init_data = self.data.flatten()
        n, bins = np.histogram(init_data, self.num_bins)

        # get the corners of the rectangles for the histogram
        left = np.array(bins[:-1])
        right = np.array(bins[1:])
        self._bottom = np.zeros(len(left))
        top = self._bottom + n / (self.num_frames * 0.9)
        nrects = len(left)

        # here comes the tricky part -- we have to set up the vertex and path
        # codes arrays using moveto, lineto and closepoly

        # for each rect: 1 for the MOVETO, 3 for the LINETO, 1 for the
        # CLOSEPOLY; the vert for the closepoly is ignored but we still need
        # it to keep the codes aligned with the vertices
        nverts = nrects * (1 + 3 + 1)
        self._verts = np.zeros((nverts, 2))
        codes = np.ones(nverts, int) * path.Path.LINETO
        codes[0::5] = path.Path.MOVETO
        codes[4::5] = path.Path.CLOSEPOLY

        self._verts[0::5, 0] = left
        self._verts[1::5, 0] = left

        self._verts[2::5, 0] = right
        self._verts[3::5, 0] = right

        self._verts[1::5, 1] = top
        self._verts[2::5, 1] = top

        self._verts[0::5, 1] = self._bottom
        self._verts[3::5, 1] = self._bottom

        barpath = path.Path(self._verts, codes)
        patch = patches.PathPatch(barpath, facecolor="green", edgecolor="yellow", alpha=0.5)
        ax.add_patch(patch)

        ax.set_xlim(left[0], right[-1])
        ax.set_ylim(self._bottom.min(), top.max())
        self.artists.append(patch)

    def animate(self, frame: int):
        # simulate new data coming in
        data = self.data[frame]

        n, bins = np.histogram(data, self.num_bins)
        top = self._bottom + n
        self._verts[1::5, 1] = top
        self._verts[2::5, 1] = top


def _make_init_func(plots: List[SwarmPlot], axes: List[plt.Axes]):
    """create a chained init for each frame"""

    def inner():
        all_artists = []
        for p, ax in zip(plots, axes):
            # print(p.artists)
            p.plot_init(ax)
        return all_artists

    return inner


def _make_animate_func(plots: List[SwarmPlot]):
    def inner(frame: int):
        all_artists = []
        for p in plots:
            p.animate(frame)
            all_artists.extend(p.artists)
        return all_artists

    return inner


def figuresize(l, r):
    return plt.rc_context({"figure.figsize": (float(l), float(r))})


def swarm_animate(
    plots: List[SwarmPlot],
    destfile: str,
    num_frames: Optional[int] = None,
    layout: Tuple[int, int] = None,
):
    if not layout:
        # be somewhat intelligent
        sqrt = int(len(plots) ** 0.5)
        if sqrt ** 2 == len(plots):
            layout = (sqrt, sqrt)
        else:
            layout = (len(plots), 1)
        logger.info("Using a %s as layout", layout)

    if not num_frames:
        all_frames = {p.num_frames for p in plots}
        assert len(all_frames) == 1
        num_frames = all_frames.pop()

    # for animation only, we want a smaller default. May refactor out
    fig = plt.figure()
    fig.subplots(*layout)

    anim = animation.FuncAnimation(
        fig,
        _make_animate_func(plots),
        init_func=_make_init_func(plots, fig.axes),
        frames=tqdm.tqdm(range(num_frames), initial=1, position=0, desc="Animating", disable=None),
        interval=20,
        blit=True,
        repeat=False,
    )

    if not destfile.endswith(".mp4"):
        destfile = f"{destfile}.mp4"
    anim.save(destfile, fps=30, extra_args=["-vcodec", "libx264"])
    plt.close()


def xlabel_hook(label):
    def inner(ax: plt.Axes):
        ax.set_xlabel(label)

    return inner


def ylabel_hook(label):
    def inner(ax: plt.Axes):
        ax.set_ylabel(label)

    return inner


def hive_animate(hive_data: List[Dict[str, Any]], facx: str, facy: str, destfile: str):
    loc_dat = [(d[facx], d[facy]) for d in hive_data]

    # dicts are ordered while sets are not, we use a dict here as a set
    xvals = {d[facx]: None for d in hive_data}
    yvals = {d[facy]: None for d in hive_data}

    splots = []

    for iy, y in enumerate(yvals):
        for ix, x in enumerate(xvals):
            hive_index = loc_dat.index((x, y))
            data = hive_data[hive_index]
            swarm_plot = LineSwarm.standard(data["x"], data["y"], data["ypred"])
            # this is the prettifying
            if iy == 0:
                # top row
                hooks = [
                    xlabel_hook(f"{facx}={x}"),
                    lambda ax: ax.xaxis.set_label_position("top"),
                ]
                swarm_plot.hook.extend(hooks)
            if ix == 0:
                # left column
                swarm_plot.hook.append(ylabel_hook(f"{facy}={y}"))

            splots.append(swarm_plot)

    all_frames = {p.num_frames for p in splots}
    assert len(all_frames) == 1
    num_frames = all_frames.pop()

    swarm_animate(splots, destfile, num_frames, (len(yvals), len(xvals)))


def hive_plot(hive_data: List[Dict[str, Any]], facx: str, facy: str, epoch: int):
    sns.set()
    loc_dat = [(d[facx], d[facy]) for d in hive_data]

    # dicts are ordered while sets are not, we use a dict here as a set
    xvals = {d[facx]: None for d in hive_data}
    yvals = {d[facy]: None for d in hive_data}

    plot_index = 1
    for iy, y in enumerate(yvals):
        for ix, x in enumerate(xvals):
            plt.subplot(len(yvals), len(xvals), plot_index)
            hive_index = loc_dat.index((x, y))
            data = hive_data[hive_index]

            ypred = data["ypred"]  # bee, epoch, yindex
            plt.plot(data["x"], data["y"], ".", color="silver")

            # this is to make it look a bit nicer,
            # so only the top row has the xlabel
            if iy == 0:
                plt.xlabel(f"{facx}={x}")
                plt.gca().xaxis.set_label_position("top")
            # and only left column has the ylabel
            if ix == 0:
                plt.ylabel(f"{facy}={y}")

            for bee in range(ypred.shape[0]):
                plt.plot(data["x"], ypred[bee][epoch])

            plot_index += 1

    return plt.gcf()
