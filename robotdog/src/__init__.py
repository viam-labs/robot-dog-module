"""
This file registers the model with the Python SDK.
"""

from viam.components.base import Base
from viam.resource.registry import Registry, ResourceCreatorRegistration

from .robotdog import robotdog

Registry.register_resource_creator(Base.SUBTYPE, robotdog.MODEL, ResourceCreatorRegistration(robotdog.new, robotdog.validate))
