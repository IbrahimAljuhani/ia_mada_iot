# -*- coding: utf-8 -*-
# Fix: IoT Box saas~19.1 sends 'mac' as a parameter to /iot/get_handlers
# but Odoo 18.0 defines download_iot_handlers(self, mac, auto) without defaults,
# causing a 500 error when 'mac' is missing or unexpected.
# This override adds default values to prevent the crash.

import io
import pathlib
import zipfile

from odoo import http
from odoo.http import request
from odoo.modules.module import get_module_path


class IoTControllerFix(http.Controller):

    @http.route('/iot/get_handlers', type='http', auth='public', csrf=False)
    def download_iot_handlers(self, mac=None, auto=True):
        """
        Override of iot.controllers.main.IoTController.download_iot_handlers
        Adds default values for 'mac' and 'auto' to fix compatibility with
        IoT Box saas~19.1 which may send different parameters than Odoo 18.0 expects.
        """
        # Find the IoT Box by MAC address if provided
        box = None
        if mac:
            box = request.env['iot.box'].sudo().search(
                [('identifier', '=', mac)], limit=1
            )

        # If auto=True and box has disabled auto-update, return empty
        if box and str(auto) == 'True' and not box.drivers_auto_update:
            return ''

        # Build zip of all iot_handlers from installed modules
        module_ids = request.env['ir.module.module'].sudo().search(
            [('state', '=', 'installed')]
        )
        fobj = io.BytesIO()
        with zipfile.ZipFile(fobj, 'w', zipfile.ZIP_DEFLATED) as zf:
            for module in module_ids.mapped('name') + ['hw_drivers']:
                module_path = get_module_path(module)
                if module_path:
                    iot_handlers = pathlib.Path(module_path) / 'iot_handlers'
                    for handler in iot_handlers.glob('*/*'):
                        if handler.is_file() and not handler.name.startswith(('.', '_')):
                            zf.write(handler, handler.relative_to(iot_handlers))

        return fobj.getvalue()
