############################ Copyrights and license ############################
#                                                                              #
# Copyright 2020 Steve Kowalik <steven@wedontsleep.org>                        #
#                                                                              #
# This file is part of PyGithub.                                               #
# http://pygithub.readthedocs.io/                                              #
#                                                                              #
# PyGithub is free software: you can redistribute it and/or modify it under    #
# the terms of the GNU Lesser General Public License as published by the Free  #
# Software Foundation, either version 3 of the License, or (at your option)    #
# any later version.                                                           #
#                                                                              #
# PyGithub is distributed in the hope that it will be useful, but WITHOUT ANY  #
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS    #
# FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more #
# details.                                                                     #
#                                                                              #
# You should have received a copy of the GNU Lesser General Public License     #
# along with PyGithub. If not, see <http://www.gnu.org/licenses/>.             #
#                                                                              #
################################################################################

from . import Framework

collect_ignore = ["condor/tests"]


def pytest_addoption(parser):
    parser.addoption("--record", action="store_true", help="record mode")
    parser.addoption("--record_action", action="store_true", help="record actions mode")
    parser.addoption("--auth_with_token", action="store_true", help="legacy option, does nothing")


def pytest_configure(config):
    if config.getoption("record"):
        Framework.activateRecordMode()
    if config.getoption("record_action"):
        Framework.activateRecordActionMode()
    Framework.activateTokenAuthMode()
