from aiogram import Router

from handlers.main_panel.start import router as start_router
from handlers.main_panel.menu import router as menu_router
from handlers.main_panel.subscription import router as sub_router
from handlers.main_panel.broadcast import router as broadcast_router
from handlers.main_panel.callbacks import router as callbacks_router

main_panel_router = Router()

main_panel_router.include_router(start_router)
main_panel_router.include_router(menu_router)
main_panel_router.include_router(sub_router)
# main_panel_router.include_router(broadcast_router)
main_panel_router.include_router(callbacks_router)
