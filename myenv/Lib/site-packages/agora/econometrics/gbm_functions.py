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

__all__ = ["GbmPricePaths"]


# -----------------------------------------------------------------------------
def GbmPricePaths(vol, n_days, rd=0.0, rf=0.0, n_sims=1000, acc=False):
    """
    Description:
        Returns normalized simulated price paths. The actual prices can be
        obtained by multiplying the paths by the current spot price.
    Inputs:
        vol    - the daily volatility
        n_days - number of days in the simulation. each path will be of length
                 ndays+1, with initial value set to 1.
        rd     - daily domestic risk-free interest rate
        rf     - daily foreign risk-free interest rate (or dividend yield)
        n_sims - number of simulation paths
        acc    - if True, it will only return the final normalized prices after
                 n_days days
    Returns:
        numpy.array, according to acc
    """
    # --- Ito's drift term: it's only present when using continuous compounding
    #     of daily returns, i.e. using e^(r*n) instead of (1+r)^n
    ito = 0.5*vol*vol

    if acc:
        half = int(n_sims / 2)
        n_sims = 2*half
        prices = np.ones(n_sims)
        for n in range(n_days):
            z = np.random.standard_normal(half)
            z = np.hstack((z, -z))
            prices *= np.exp(rd - rf - ito + vol*z)

        return prices

    else:
        half = int(n_sims / 2)
        z = np.random.standard_normal((n_days, half))
        drift = rd - rf - ito

        paths = np.ones((n_days + 1, n_sims))
        paths[1:,:] = np.hstack((
                np.cumprod(np.exp(drift - vol*z), axis=0),
                np.cumprod(np.exp(drift + vol*z), axis=0)))

        return paths
