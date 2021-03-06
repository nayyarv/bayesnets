import numpy as np
from swarm import metrics
import pytest

# Example y with 11 points from -1.5 to 1.5.
y = np.array(
    [
        -0.997495,
        -0.9320391,
        -0.78332686,
        -0.5646425,
        -0.29552022,
        0.0,
        0.29552022,
        0.5646425,
        0.78332686,
        0.9320391,
        0.997495,
    ]
)

losses = np.array([[0.82777214, 0.82301313], [0.35649812, 0.35499558], [0.82012618, 0.81833321]])

# Example predictions for first two epochs of a swarm of three bees.
ypreds = np.array(
    [
        [
            [
                -0.75819135,
                -0.6721624,
                -0.5914593,
                -0.5263963,
                -0.4742774,
                -0.42794737,
                -0.4386463,
                -0.45942548,
                -0.5183165,
                -0.6156955,
                -0.7488868,
            ],
            [
                -0.75616974,
                -0.6701199,
                -0.5893732,
                -0.5242175,
                -0.4719131,
                -0.42543185,
                -0.43560237,
                -0.45590907,
                -0.51438874,
                -0.61130494,
                -0.74402857,
            ],
        ],
        [
            [
                -0.18297303,
                -0.21213517,
                -0.18341143,
                -0.15066521,
                -0.11950047,
                -0.09036797,
                -0.0256229,
                0.0269562,
                0.06986493,
                0.1414077,
                0.19563401,
            ],
            [
                -0.18315202,
                -0.21226275,
                -0.18336335,
                -0.15038337,
                -0.11897573,
                -0.08946133,
                -0.0242492,
                0.02882081,
                0.07219976,
                0.14433557,
                0.19909364,
            ],
        ],
        [
            [
                0.36912787,
                0.34506714,
                0.32219756,
                0.3202601,
                0.30032292,
                0.259299,
                0.21430482,
                0.14271711,
                0.05134173,
                -0.063667,
                -0.17867568,
            ],
            [
                0.36715215,
                0.34335977,
                0.32078195,
                0.3192455,
                0.2996201,
                0.2587561,
                0.21395013,
                0.14270164,
                0.05165949,
                -0.06302758,
                -0.1777146,
            ],
        ],
    ]
)

# An example of scores obtained for a swarm that bounce around on the way down.
epoch_scores = [
    0.51727545,
    0.4584964,
    0.3589881,
    0.2524824,
    0.20734829,
    0.2482427,
    0.30246153,
    0.3388226,
    0.34041768,
    0.3064342,
    0.26800793,
    0.2686419,
    0.24010916,
    0.18522426,
    0.22644123,
    0.26727045,
    0.28942722,
    0.28332102,
    0.25410518,
    0.22259913,
    0.25512502,
    0.28029743,
    0.29604492,
    0.30136263,
    0.29408443,
    0.27543014,
    0.24885914,
    0.21919054,
    0.22593765,
    0.2305434,
    0.22474495,
    0.21082267,
    0.19170743,
    0.17090012,
    0.1521816,
    0.13839552,
    0.1299243,
    0.12569669,
    0.12456866,
    0.12922356,
    0.14023647,
    0.15060309,
    0.15662336,
    0.15730526,
    0.15512368,
    0.15510257,
    0.16903949,
    0.1815229,
    0.20310307,
    0.21428823,
    0.21110815,
    0.19391632,
    0.16897929,
    0.15510854,
    0.1513776,
    0.15778454,
    0.15062831,
    0.1423014,
    0.1533089,
    0.16309854,
]


def test_summarise_across_bees_ypreds():
    """This shows how to get a summary feature for each point x in a swarm. Eg, the average of the swarms ypreds"""
    for summ_metric in [np.min, np.max, np.mean, np.median, np.std, np.ptp]:
        out = summ_metric(ypreds, axis=0)
        assert type(out) == np.ndarray
        assert out.shape == (2, 11)


def test_summarise_across_bees_losses():
    """This shows how to get the average loss across a swarm"""
    for summ_metric in [np.min, np.max, np.mean, np.median, np.std, np.ptp]:
        out = summ_metric(losses, axis=0)
        assert type(out) == np.ndarray
        assert out.shape == (2,)


def test_rmse_2d():
    b0_preds = ypreds[0]
    out = metrics.mse_loss(b0_preds, y)
    assert len(out.shape) == len(b0_preds.shape) - 1
    assert (
        np.max(np.abs(out - losses[0])) < 0.000001
    )  # I dont' know why this isn't exactly 0, have tried pytest.approx

    b2_preds = ypreds[2]
    out = metrics.mse_loss(b2_preds, y)
    assert len(out.shape) == len(b2_preds.shape) - 1
    assert np.max(np.abs(out - losses[2])) < 0.000001  # I dont' know why this isn't exactly 0


def test_rmse_3d():
    out = metrics.mse_loss(ypreds, y)
    assert len(out.shape) == len(ypreds.shape) - 1
    assert np.max(np.abs(out - losses)) < 0.000001  # I don't know why this isn't exactly 0


def test_loss_mean_point_pred():
    """
    This is an example of interest, since it is plausible (and of interest) if the averaged prediction of many bees
    in a swarm, at a given point x, might tend to be better than any given one.
    """
    mean_point_preds = np.mean(ypreds, axis=0)
    loss_mean_preds = metrics.mse_loss(mean_point_preds, y)
    assert loss_mean_preds.shape == (2,)


def test_if_nom_first_below():
    epoch = metrics.iteration_threshold(epoch_scores, 0.25, "first", "below")
    assert epoch_scores[epoch] <= 0.25
    assert np.all(np.array(epoch_scores[:epoch]) > 0.25)
    assert metrics.iteration_threshold(epoch_scores, 0.001, "first", "below") is None


def test_if_nom_always_below():
    epoch = metrics.iteration_threshold(epoch_scores, 0.25, "always", "below")
    assert np.max(epoch_scores[epoch:]) <= 0.25
    assert epoch_scores[epoch - 1] > 0.25
    assert metrics.iteration_threshold(epoch_scores, 0.001, "always", "below") is None


def test_if_nom_first_above():
    reverse_scores = 1 - np.array(epoch_scores)
    epoch = metrics.iteration_threshold(reverse_scores, 0.75, "first", "above")
    assert reverse_scores[epoch] >= 0.75
    assert np.all(reverse_scores[:epoch] < 0.75)
    assert metrics.iteration_threshold(reverse_scores, 0.999, "first", "above") is None


def test_if_nom_always_above():
    reverse_scores = 1 - np.array(epoch_scores)
    epoch = metrics.iteration_threshold(reverse_scores, 0.75, "always", "above")
    assert np.min(reverse_scores[epoch:]) >= 0.75
    assert reverse_scores[epoch - 1] < 0.75
    assert metrics.iteration_threshold(reverse_scores, 0.999, "always", "above") is None


def test_if_ratio_first_below():
    epoch = metrics.iteration_threshold_ratio(epoch_scores, 0.5, "first", "below")
    epoch_ratios = np.array(epoch_scores) / epoch_scores[0]
    assert epoch_ratios[epoch] <= 0.5
    assert np.all(epoch_ratios[:epoch] > 0.5)
    assert metrics.iteration_threshold_ratio(epoch_scores, 0.001, "first", "below") is None


def test_if_ratio_always_below():
    epoch = metrics.iteration_threshold_ratio(epoch_scores, 0.5, "always", "below")
    epoch_ratios = np.array(epoch_scores) / epoch_scores[0]
    assert np.max(epoch_ratios[epoch:]) <= 0.5
    assert epoch_ratios[epoch - 1] > 0.5
    assert metrics.iteration_threshold_ratio(epoch_scores, 0.001, "always", "below") is None


def test_if_ratio_first_above():
    reverse_scores = 1 / np.array(epoch_scores)
    epoch = metrics.iteration_threshold_ratio(reverse_scores, 1.5, "first", "above", 3)
    reverse_ratios = reverse_scores / reverse_scores[3]
    assert reverse_ratios[epoch] >= 1.5
    assert np.all(reverse_ratios[:epoch] < 1.5)
    assert metrics.iteration_threshold_ratio(reverse_scores, 200, "first", "above") is None


def test_if_ratio_always_above():
    reverse_scores = 1 / np.array(epoch_scores)
    epoch = metrics.iteration_threshold_ratio(reverse_scores, 1.1, "always", "above", 3)
    reverse_ratios = reverse_scores / reverse_scores[3]
    assert np.min(reverse_ratios[epoch:]) >= 1.1
    assert reverse_ratios[epoch - 1] < 1.1
    assert metrics.iteration_threshold_ratio(reverse_scores, 200, "always", "above") is None


def test_if_ratio_error():
    """Should fail due to the score crossing zero"""
    with pytest.raises(ValueError):
        metrics.iteration_threshold_ratio(np.array([-0.1, 0, 0.1, 1]), 0.1)
