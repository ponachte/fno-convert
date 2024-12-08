#!/usr/bin/env python
# coding: utf-8

import numpy as np
import pandas as pd
from scipy import signal, interpolate
from scipy.signal import butter, lfilter
import scipy as sp
import requests
from typing import Dict, List, Union
from datetime import timedelta

from scipy.ndimage import gaussian_filter1d
from tsflex.chunking import chunk_data



SENSOR_FREQUENCIES = {'acc' : 32, 'gsr' : 4, 'tmp' : 4, 'ppg' : 64}

#### ACCELEROMETER ####

def rolling_acc(df_raw, sec, sampling_rate, overlap):
    x_feats = []
    y_feats = []
    z_feats = []
    acc_feats = []
    timestamps = []
    window = sec*sampling_rate
    step = int(window*overlap)
    for ix in range(0, len(df_raw), step):
        curr_df = df_raw.iloc[ix:ix+window]
        if len(curr_df) == window:
            
            x_feats.append(curr_df.ACC_x.values)
            y_feats.append(curr_df.ACC_y.values)
            z_feats.append(curr_df.ACC_z.values)
            timestamps.append(curr_df.index[0])
                
    return np.array(x_feats),np.array(y_feats),np.array(z_feats),np.array(timestamps)

######## General ##################

def butter_bandpass_filter(data, lowcut, highcut, fs, order=5):
    nyq = 0.5 * fs
    low = lowcut / nyq
    high = highcut / nyq
    b, a = signal.butter(order, [low, high], btype='band')
    return signal.lfilter(b, a, data).astype(np.float32)

def butter_lowpass_filter(data, cutoff, fs, order=5):
    nyq = 0.5 * fs
    normal_cutoff = cutoff / nyq
    b, a = butter(order, normal_cutoff, btype='low', analog=False)
    y = lfilter(b, a, data)
    return y

def gaussian_filter(data, time_sigma, fs, order=0):
    
    sigma = time_sigma * fs
    
    return gaussian_filter1d(data, sigma=sigma, order=order)

    
    
    