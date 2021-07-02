#!/usr/bin/env python3

# Copyright 2021 PAL Robotics S.L.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import rclpy
import time

from play_motion_msgs.action import PlayMotion
from rclpy.action import ActionClient
from rclpy.node import Node
from std_srvs.srv import Trigger


class PlayMotionActionClient(Node):

    def __init__(self):
        super().__init__('play_motion_play_motion_client')
        self._play_motion_client = ActionClient(
            self, PlayMotion, 'play_motion')
        self._is_ready_client = self.create_client(
            Trigger, '/play_motion/is_ready')

    def wait_for_server(self):
        self._play_motion_client.wait_for_server()

        while not self._is_ready_client.wait_for_service(timeout_sec=1.0):
            self.get_logger().error('is_ready service not ready, waiting...')

        request = Trigger.Request()

        is_ready = False
        while not is_ready:
            time.sleep(1.0)
            future = self._is_ready_client.call_async(request)
            while rclpy.ok() and not is_ready:
                rclpy.spin_once(self)
                if future.done():
                    try:
                        response = future.result()
                    except Exception as e:
                        self.get_logger().info('Service call failed %r' % (e,))
                    else:
                        is_ready = response.success
                        if is_ready:
                            self.get_logger().info('play_motion is ready')
                        else:
                            self.get_logger().error('play_motion is not ready')
                    break

    def send_goal(self, motion_name, skip_planning):
        goal_msg = PlayMotion.Goal()
        goal_msg.motion_name = motion_name
        goal_msg.skip_planning = skip_planning

        self._send_goal_future = \
            self._play_motion_client.send_goal_async(goal_msg)

        self._send_goal_future.add_done_callback(self.goal_response_callback)

    def goal_response_callback(self, future):
        goal_handle = future.result()

        if not goal_handle.accepted:
            self.get_logger().error('Goal rejected')
            return

        self.get_logger().info('Goal accepted')

        self._get_result_future = goal_handle.get_result_async()

        self._get_result_future.add_done_callback(self.get_result_callback)

    def get_result_callback(self, future):
        result = future.result().result

        error_code = result.error_code
        error_string = result.error_string

        if error_code == result.SUCCEEDED:
            self.get_logger().info('Motion succeeded')
        else:
            self.get_logger().error(
                'Motion failed with error ({}): {}'
                .format(error_code, error_string))

        rclpy.shutdown()


def main(args=None):
    rclpy.init(args=args)

    action_client = PlayMotionActionClient()

    action_client.wait_for_server()

    action_client.send_goal('home', True)

    rclpy.spin(action_client)


if __name__ == '__main__':
    main()
