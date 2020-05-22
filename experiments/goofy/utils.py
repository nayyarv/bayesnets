import functools
import numpy as np

def make_bee(regime, x, y, *args, **kwargs):
    """
    Convenience function for turning a simple arg
    based training function into a the bee format of argless
    This can be used to pass state between swarm iterations
    and share resources
    Also optional to use
    """
    thestrkwargs = {key: str(value) for key, value in kwargs.items()}
    return functools.partial(regime, x, y, *args, **kwargs), thestrkwargs

def add_anindex(an_array, anindex):
    return np.c_[an_array, np.array([anindex for a in range(len(an_array))])]

def flatten_sim(data_list, loss_list, xd, yd):
    xy = np.c_[xd, yd]
    data_list = [add_anindex(data_list[a], a) for a in range(len(data_list))]
    flat_data = data_list[0]
    for i in range(1, len(data_list)):
        flat_data = np.vstack((flat_data, data_list[i]))
    loss_list = [add_anindex(loss_list[a], a) for a in range(len(loss_list))]
    flat_loss = loss_list[0]
    for i in range(1, len(loss_list)):
        flat_loss = np.vstack((flat_loss, loss_list[i]))
    
    return flat_data, flat_loss, xy

def unpacker(reslist, static_params):
    data_list = [x['results']['ypred'] for x in reslist]
    loss_list = [x['results']['loss'] for x in reslist]
    params_list = [x['params'] for x in reslist]
    params_list = [params_list[i].update({'index':i}) for i in range(len(params_list))]
    xd = static_params['x']
    yd = static_params['y']
    all_data = []
    all_loss = []
    all_xy = []
    for i in range(len(reslist)):
        flat_data, flat_loss, xy = flatten_sim(data_list[0], loss_list[0], xd, yd)
        flat_data = add_anindex(flat_data, i)
        flat_loss = add_anindex(flat_loss, i)
        xy = add_anindex(xy, i)
    return flat_data, flat_loss, xy