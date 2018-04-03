# -*- coding: utf-8 -*-
# flake8: noqa: D102
# pylint: disable=missing-docstring,no-self-use
"""
:mod:`metaopt.core.worker.transformer` -- Perform operations on Dimensions
==========================================================================

.. module:: transformer
   :platform: Unix
   :synopsis: Provide functions and classes to build a Space which an
      algorithm can operate on.

"""
from abc import (ABCMeta, abstractmethod)

from metaopt.algo.space import Space


def build_required_space(requirements, original_space):
    """Build a `Space` object which agrees to the `requirements` imposed
    by the desired optimization algorithm.

    It uses appropriate cascade of `Transformer` objects per `Dimension`
    contained in `original_space`.
    """
    requirements = requirements if isinstance(requirements, list) else [requirements]
    space = TransformedSpace()
    for dim in original_space.values():
        transformers = []
        type_ = dim.type
        for requirement in requirements:
            # TODO Write classes and instantiate transformers accordingly
            if type_ == 'real':
                pass
            elif type_ == 'integer':
                pass
            elif type_ == 'categorical':
                pass
            else:
                raise TypeError("Unsupported dimension type '{}'".format(type_))
            last_type = transformers[-1].target_type
            type_ = last_type if last_type != 'invariant' else type_
        space.register(TransformedDimension(Compose(transformers), dim))
    return space


class Transformer(object, metaclass=ABCMeta):
    """Define a injective function and its inverse. Base transformation class.

    :attr:`target_type` defines the type of the target space of the forward function.
    It can take the values: ``['real', 'integer', 'categorical', 'invariant']``.
    In the case of ``'invariant'``, target == domain dimension type.
    """

    target_type = None

    @abstractmethod
    def transform(self, point):
        """Transform a point from domain dimension to the target dimension."""
        pass

    @abstractmethod
    def reverse(self, transformed_point):
        """Reverse transform a point from target dimension to the domain dimension."""
        pass

    def infer_target_shape(self, shape):
        """Return the shape of the dimension after transformation."""
        return shape

    def repr_format(self, what):
        """Format a string for calling ``__repr__`` in `TransformedDimension`."""
        return "{}({})".format(self.__class__.__name__, what)


class Identity(Transformer):
    """Implement an identity transformation. Everything as it is."""

    target_type = 'invariant'

    def transform(self, point):
        return point

    def reverse(self, transformed_point):
        return transformed_point

    def repr_format(self, what):
        return what


class Compose(Transformer):

    def __init__(self, transformers):
        self.composition = Identity()
        try:
            self.apply = transformers.pop()
        except IndexError:
            self.apply = Identity()
        if transformers:
            self.composition = Compose(transformers)

    def transform(self, point):
        point = self.composition.transform(point)
        return self.apply.transform(point)

    def reverse(self, transformed_point):
        transformed_point = self.apply.reverse(transformed_point)
        return self.composition.reverse(transformed_point)

    def infer_target_shape(self, shape):
        shape = self.composition.infer_target_shape(shape)
        return self.apply.infer_target_shape(shape)

    def repr_format(self, what):
        return self.apply.repr_format(self.composition.repr_format(what))

    @property
    def target_type(self):
        type_before = self.composition.target_type
        type_after = self.apply.target_type
        return type_after if type_after != 'invariant' else type_before


class TransformedDimension(object):

    def __init__(self, transformer, original_dimension):
        self.original_dimension = original_dimension
        self.transformer = transformer

    def transform(self, point):
        return self.transformer.transform(point)

    def reverse(self, transformed_point):
        return self.transformer.reverse(transformed_point)

    def sample(self, n_samples=1, seed=None):
        """Sample from the original dimension and forward transform them."""
        samples = self.original_dimension.sample(n_samples, seed)
        return [self.transform(sample) for sample in samples]

    def interval(self, alpha=1.0):
        """Map the interval bounds to the transformed ones."""
        low, high = self.original_dimension.interval(alpha)
        return self.transform(low), self.transform(high)

    def __contains__(self, point):
        """Reverse transform and ask the original dimension if it is a possible
        sample.
        """
        orig_point = self.reverse(point)
        return orig_point in self.original_dimension

    def __repr__(self):
        """Represent the object as a string."""
        return self.transformer.repr_format(repr(self.original_dimension))

    @property
    def name(self):
        """Do not change the name of the original dimension."""
        return self.original_dimension.name

    @property
    def type(self):
        """Ask transformer which is its target class."""
        type_ = self.transformer.target_type
        return type_ if type_ != 'invariant' else self.original_dimension.type

    @property
    def shape(self):
        """Wrap original shape with transformer, because it may have changed."""
        return self.transformer.infer_target_shape(self.original_dimension.shape)


class TransformedSpace(Space):
    """Wrap the `Space` to support transformation methods."""

    contains = TransformedDimension

    def transform(self, point):
        """Transform a point that was in the original space to be in this one."""
        return tuple([dim.transform(point[i]) for i, dim in enumerate(self.values())])

    def reverse(self, transformed_point):
        """Reverses transformation so that a point from this `TransformedSpace`
        to be in the original one.
        """
        return tuple([dim.reverse(transformed_point[i]) for i, dim in enumerate(self.values())])
