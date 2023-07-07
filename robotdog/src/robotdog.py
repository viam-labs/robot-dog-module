from typing import ClassVar, Mapping, Sequence, Any, Dict, Optional, cast
from typing_extensions import Self

from viam.module.types import Reconfigurable
from viam.proto.app.robot import ComponentConfig
from viam.proto.common import ResourceName, Vector3
from viam.resource.base import ResourceBase
from viam.resource.types import Model, ModelFamily

from viam.components.base import Base
from viam.logging import getLogger

import time
import asyncio
import socket

LOGGER = getLogger(__name__)

class robotdog(Base, Reconfigurable):
    MODEL: ClassVar[Model] = Model(ModelFamily("viamlabs", "base"), "robotdog")
    
    # Class parameters
    ip_address: str
    port: int

    # Constructor
    @classmethod
    def new(cls, config: ComponentConfig, dependencies: Mapping[ResourceName, ResourceBase]) -> Self:
        my_class = cls(config.name)
        my_class.reconfigure(config, dependencies)
        return my_class

    # Validates JSON Configuration
    @classmethod
    def validate(cls, config: ComponentConfig):
        # Here we validate config, ensuring that an IP address was provided
        ip_address = config.attributes.fields["ip_address"].string_value
        if ip_address == "":
            raise ValueError("No IP address provided")

        port = int(config.attributes.fields["port"].number_value)
        # Per the Freenove code, 5001 is for sending/receiving instructions. Port 8001 is used for video.
        if port == "":
            port = 5001
        return

    # Define a way to send commands to the robot dog server
    def send_data(self, data):
        try:
            self.client_socket.send(data.encode("utf-8"))
        except Exception as e:
            LOGGER.error(e)

    # Handles attribute reconfiguration
    def reconfigure(self, config: ComponentConfig, dependencies: Mapping[ResourceName, ResourceBase]):
        # Here we initialize the resource instance
        ip_address = config.attributes.fields["ip_address"].string_value
        port = int(config.attributes.fields["port"].number_value)
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client_socket.connect((ip_address, port))
        return

    """ Implement the methods the Viam RDK defines for the Base API (rdk:components:base) """

    
    async def move_straight(
        self,
        distance: int,
        velocity: float,
        *,
        extra: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None,
        **kwargs,
    ):
        if distance == 0 or velocity == 0:
            return await self.stop()

        # Convert velocity in mm/s to correct number to send in the CMD_MOVE_FORWARD/BACKWARD command.
        conversion_factor = 0.25
        velocity = velocity * conversion_factor

        if velocity > 0:
            command = "CMD_MOVE_FORWARD#" + str(velocity) + "\n"
            self.send_data(command)
        else:
            command = "CMD_MOVE_BACKWARD#" + str(velocity) + "\n"
            self.send_data(command)

        self.is_stopped = False

    
    async def spin(
        self,
        angle: float,
        velocity: float,
        *,
        extra: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None,
        **kwargs,
    ):
        if angle == 0 or velocity == 0:
            return await self.stop()

        spin_time = angle / velocity

        # Convert from velocity in deg/s to what to send to robot dog.
        conversion_factor = 0.85
        vel = velocity * conversion_factor

        if velocity > 0:
            self.angle += angle
            self.stand()
            command = "CMD_TURN_LEFT#" + str(vel) + "\n"

        else:
            self.angle -= angle
            self.stand()
            command = "CMD_TURN_RIGHT#" + str(vel) + "\n"

        self.send_data(command)
        time.sleep(spin_time)

        self.is_stopped = False

    
    async def set_power(
        self,
        linear: Vector3,
        angular: Vector3,
        *,
        extra: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None,
        **kwargs,
    ):
        self.linear_pwr = linear
        self.angular_pwr = angular

        # Convert from power percentage (0-1) to what to send to robot dog.
        conversion_factor_a = 30
        conversion_factor_l = 25
        ang_vel = int(angular.z * conversion_factor_a)
        lin_vel = int(linear.y * conversion_factor_l)

        if ang_vel > 0:
            command = "CMD_TURN_LEFT#" + str(ang_vel) + "\n"

        if ang_vel < 0:
            ang_vel = abs(ang_vel)
            command = "CMD_TURN_RIGHT#" + str(ang_vel) + "\n"

        if ang_vel != 0:
            self.send_data(command)

        if lin_vel > 0:
            command = "CMD_MOVE_FORWARD#" + str(lin_vel) + "\n"

        if lin_vel < 0:
            lin_vel = abs(lin_vel)
            command = "CMD_MOVE_BACKWARD#" + str(lin_vel) + "\n"

        if lin_vel != 0:
            self.send_data(command)

    
    async def set_velocity(
        self,
        linear: Vector3,
        angular: Vector3,
        *,
        extra: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None,
        **kwargs,
    ):

        self.linear_vel = linear
        self.angular_vel = angular

        # Convert from velocity in deg/s (angular) and in mm/s (linear) to what to send to robot dog.
        conversion_factor_a = 0.85
        conversion_factor_l = 0.25
        ang_vel = angular.z * conversion_factor_a
        # Linear components, where y is forward and x is side to side
        y_lin_vel = linear.y * conversion_factor_l
        x_lin_vel = linear.x * conversion_factor_l

        if ang_vel > 0:
            command = "CMD_TURN_LEFT#" + str(ang_vel) + "\n"

        if ang_vel < 0:
            ang_vel = abs(ang_vel)
            command = "CMD_TURN_RIGHT#" + str(ang_vel) + "\n"

        self.send_data(command)

        if y_lin_vel > 0:
            command = "CMD_MOVE_FORWARD#" + str(y_lin_vel) + "\n"

        if y_lin_vel < 0:
            y_lin_vel = abs(y_lin_vel)
            command = "CMD_MOVE_BACKWARD#" + str(y_lin_vel) + "\n"

        self.send_data(command)

        if x_lin_vel > 0:
            command = "CMD_STEP_RIGHT#" + str(x_lin_vel) + "\n"

        if x_lin_vel < 0:
            x_lin_vel = abs(x_lin_vel)
            command = "CMD_STEP_LEFT#" + str(x_lin_vel) + "\n"

        self.send_data(command)

    
    async def stop(
        self,
        *,
        extra: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None,
        **kwargs,
    ):
        self.is_stopped = True

        command = "CMD_MOVE_STOP#8\n"
        self.send_data(command)

    
    async def is_moving(self) -> bool:
        return False

    
    async def get_properties(
        self,
        *,
        timeout: Optional[float] = None,
        **kwargs
    ):
        """
        Get the base width and turning radius

        Returns:
            Properties: The properties of the base
        """
        return properties(
            width_meters = 0.1,
            turning_radius_meters = 0.0
        )
