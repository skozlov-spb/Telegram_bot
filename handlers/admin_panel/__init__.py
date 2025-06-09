from aiogram import Router

from handlers.admin_panel.menu import admin_router as menu_router
from handlers.admin_panel.stats import admin_router as stats_router
from handlers.admin_panel.data_upload import admin_router as data_upload_router
from handlers.admin_panel.delete_book import admin_router as delete_book_router
from handlers.admin_panel.delete_subtheme import admin_router as delete_subtheme_router
from handlers.admin_panel.delete_expert import admin_router as delete_expert_router
from handlers.admin_panel.broadcast import admin_router as broadcast_router
from handlers.admin_panel.add_admin import admin_router as add_admin_router


admin_panel_router = Router()

admin_panel_router.include_router(menu_router)
admin_panel_router.include_router(stats_router)
admin_panel_router.include_router(data_upload_router)
admin_panel_router.include_router(delete_book_router)
admin_panel_router.include_router(delete_subtheme_router)
admin_panel_router.include_router(delete_expert_router)
# admin_panel_router.include_router(broadcast_router)
admin_panel_router.include_router(add_admin_router)
