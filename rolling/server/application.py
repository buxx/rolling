# coding: utf-8
from aiohttp import web
from aiohttp.web_app import Application

from rolling.kernel import Kernel
from rolling.server.controller.admin import AdminController
from rolling.server.controller.affinity import AffinityController
from rolling.server.controller.build import BuildController
from rolling.server.controller.business import BusinessController
from rolling.server.controller.character import CharacterController
from rolling.server.controller.common import CommonController
from rolling.server.controller.conversation import ConversationController
from rolling.server.controller.system import SystemController
from rolling.server.controller.world import WorldController
from rolling.server.controller.zone import ZoneController


def get_application(kernel: Kernel) -> Application:
    app = web.Application()

    # Bind routes
    CommonController(kernel).bind(app)
    CharacterController(kernel).bind(app)
    ZoneController(kernel).bind(app)
    WorldController(kernel).bind(app)
    BuildController(kernel).bind(app)
    ConversationController(kernel).bind(app)
    AffinityController(kernel).bind(app)
    BusinessController(kernel).bind(app)
    BusinessController(kernel).bind(app)
    AdminController(kernel).bind(app)
    SystemController(kernel).bind(app)

    return app
