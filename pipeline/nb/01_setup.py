import json
import pickle
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import sparse, stats
from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor
from sklearn.linear_model import PoissonRegressor, RidgeCV
from sklearn.model_selection import KFold, cross_val_predict
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.metrics import log_loss, mean_poisson_deviance, r2_score

pd.set_option('display.max_columns', None)
pd.set_option('display.width', 200)

PROJECT_DIR = Path.cwd()
JSON_DIR = PROJECT_DIR / 'all_male_json'
CACHE_DIR = PROJECT_DIR / 'cache'
CACHE_DIR.mkdir(exist_ok=True)

WICKET_WINDOW = 50                 # each bowler is measured over their first N Test wickets
SENSITIVITY_WINDOW = 100           # the core results are repeated at this N
RESULTS_FILE = 'factor_results.json'   # read by the HTML report
FULL_COVERAGE_FROM = pd.Timestamp('2007-01-01')   # Cricsheet's Test coverage is patchy before this

# Dismissals credited to the bowler (run outs, retirements, obstruction etc. are not)
BOWLER_WICKET_KINDS = ('caught', 'bowled', 'lbw', 'caught and bowled', 'stumped', 'hit wicket')
NON_DISMISSAL_KINDS = ('retired hurt', 'retired not out')
# Full-member national sides; anything else (e.g. ICC World XI) is not a national team
NATIONAL_TEAMS = {'Australia', 'England', 'India', 'Pakistan', 'South Africa', 'New Zealand', 'Sri Lanka',
                  'West Indies', 'Bangladesh', 'Zimbabwe', 'Afghanistan', 'Ireland'}

N_BOOT = 1000
RNG = np.random.default_rng(42)
