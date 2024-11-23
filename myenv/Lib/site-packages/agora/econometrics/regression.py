###############################################################################
#
#   Copyright: (c) 2015-2018 Carlo Sbraccia
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
###############################################################################

import numpy as np
import math

__all__ = ["RegressionError", "DemingRegression", "RobustRegression"]


###############################################################################
class RegressionError(Exception):
    pass


# -----------------------------------------------------------------------------
def DemingRegression(x, y):
    """
    Description:
        Deming regression tries to find the line of best fit for a two
        dimensional dataset. It differs from the simple linear regression in
        that it accounts for errors in observations on both the x- and the
        y- axis.
        See: http://en.wikipedia.org/wiki/Deming_regression
    Inputs:
        x - dependent input vector
        y - independent input vector
    Returns:
        A tuple containing:
            - slope
            - intercept
            - signal/noise ratio defined as the ratio between the variances
              along the two pricipal components
            - vector of residuals
    """
    if len(x) < 3 or len(y) < 3:
        raise RegressionError("Insuffcient data for regression")

    xmean = x.mean()
    ymean = y.mean()

    xm = x - xmean
    ym = y - ymean

    den = 1.0 / (len(x) - 1.0)
    sxx = np.dot(xm, xm)*den
    syy = np.dot(ym, ym)*den
    sxy = np.dot(xm, ym)*den

    m = 0.5*(syy - sxx + math.sqrt((syy - sxx)**2 + 4.0*sxy*sxy)) / sxy
    c = ymean - m*xmean

    # --- rotate all point so that the regression line corresponds to the
    #     abscissas and the residuals to the ordinates (i.e. use pricipal
    #     components)
    theta = -math.atan(m)
    cos_t = math.cos(theta)
    sin_t = math.sin(theta)

    rx = (x - c)*cos_t - y*sin_t
    ry = (x - c)*sin_t + y*cos_t

    return m, c, rx.var() / ry.var(), ry - ry.mean()


# -----------------------------------------------------------------------------
def RobustRegression(x, y, thr=2.0):
    """
    Description:
        Two steps linear fit (symmetric in x and y), based on DemingRegression:
            - first identify best fit using the whole sample
            - remove outliers (see thr below) and refit model
    Inputs:
        x   - independent input vector
        y   - dependent input vector
        thr - only include points with residual distance (in units of std) from
              the mean of less than this value.
    Returns:
        A tuple, see DemingRegression
    """
    m, c, _, res = DemingRegression(x, y)

    # --- NB: residuals have zero mean by construction
    idx = np.nonzero(np.ravel(np.abs(res) < thr*res.std()))

    m, c, snr, res = DemingRegression(x[idx], y[idx])

    # --- residuals are calculated including all datapoints
    res = (y - m*x - c) * math.cos(-math.atan(m))

    return m, c, snr, res
