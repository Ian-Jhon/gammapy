
import numpy as np
from astropy.table import Table
from .parameter import Parameters



__all__ = ["Covariance"]


class Covariance:
    """"""

    def __init__(self, parameters=None, data=None):
        if parameters is None:
            parameters = Parameters()

        self.parameters = parameters

        if data is None:
            data = np.diag([p.error ** 2 for p in parameters])

        self._data = np.asanyarray(data, dtype=float)

    @property
    def shape(self):
        npars = len(self.parameters)
        return (npars, npars)

    @property
    def data(self):
        return self._data

    @data.setter
    def data(self, value):
        value = np.asanyarray(value)

        npars = len(self.parameters)
        shape = (npars, npars)
        if value.shape != shape:
            raise ValueError(f"Invalid covariance shape: {value.shape}, expected {shape}")

        self._data = value

    @property
    def _scale_matrix(self):
        scales = [par.scale for par in self.parameters]
        return np.outer(scales, scales)

    def _expand_factor_matrix(self, matrix):
        """Expand covariance matrix with zeros for frozen parameters"""
        matrix_expanded = np.zeros(self.shape)
        mask = np.array([par.frozen for par in self.parameters])
        free_parameters = ~(mask | mask[:, np.newaxis])
        matrix_expanded[free_parameters] = matrix.ravel()
        return matrix_expanded

    def set_covariance_factors(self, matrix):
        """Set covariance from factor covariance matrix.

        Used in the optimizer interface.
        """
        # FIXME: this is weird to do sqrt(size). Simplify
        if matrix.shape == self.shape:
            matrix = self._expand_factor_matrix(matrix)

        self._data = self._scale_matrix * matrix

    @classmethod
    def from_stack(cls, covar_list):
        """"""
        parameters = Parameters.from_stack(
            [_.parameters for _ in covar_list]
        )

        covar = cls(parameters)

        for subcovar in covar_list:
            covar.set_subcovariance(subcovar)

        return covar

    def to_table(self):
        """"""
        table = Table()
        table["name"] = self.parameters.names

        for idx, par in enumerate(self.parameters):
            vals = self.data[idx]
            table[par.name] = vals
            table[par.name].format = ".3e"

        return table

    def read(self, filename):
        pass

    def write(self, filename, **kwargs):
        """Write covariance to file

        Parameters
        ----------
        filename : str
            Filename
        **kwargs : dict
            Keyword arguments passed to `~astropy.table.Table.write`

        """
        table = self.to_table()
        table.write(filename, **kwargs)

    def get_subcovariance(self, covar):
        """"""
        idx = [self.parameters._get_idx(par) for par in covar.parameters]
        data = self._data[np.ix_(idx, idx)]

        return self.__class__(
            parameters=covar.parameters, data=data
        )

    def set_subcovariance(self, covar):
        """"""
        idx = [self.parameters._get_idx(par) for par in covar.parameters]

        if not np.allclose(self.data[np.ix_(idx, idx)], covar.data):
            self.data[idx, :] = 0
            self.data[:, idx] = 0

        self._data[np.ix_(idx, idx)] = covar.data

    def plot_correlation(self, ax=None, **kwargs):
        """Plot correlation matrix.

        Parameters
        ----------
        ax :


        """
        kwargs.setdefault("cmap", "coolwarm")
        ax.imshow(self.correlation, vmin=-1, vmax=1, **kwargs)

    @property
    def correlation(self):
        r"""Correlation matrix (`numpy.ndarray`).

        Correlation :math:`C` is related to covariance :math:`\Sigma` via:

        .. math::
            C_{ij} = \frac{ \Sigma_{ij} }{ \sqrt{\Sigma_{ii} \Sigma_{jj}} }
        """
        err = np.sqrt(np.diag(self.data))
        return self.data / np.outer(err, err)

    def __str__(self):
        return str(self.data)

    def __array__(self):
        return self.data

    def needs_update(self, parameters):
        """"""
        return not self.parameters == parameters