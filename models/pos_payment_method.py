# -*- coding: utf-8 -*-
import socket
from odoo import fields, models, api, _
from odoo.exceptions import UserError


class PosPaymentMethod(models.Model):
    _inherit = 'pos.payment.method'

    neoleap_ip = fields.Char(
        string='NeoLeap IP Address',
        help='IP address of the NeoLeap Mada device on the local network (e.g. 192.168.1.10)',
    )

    def _get_payment_terminal_selection(self):
        return super()._get_payment_terminal_selection() + [
            ('mada_iot', 'Mada Terminal (IoT)')
        ]

    @api.model
    def _load_pos_data_fields(self, config_id):
        params = super()._load_pos_data_fields(config_id)
        params += ['neoleap_ip']
        return params

    def action_test_neoleap_connection(self):
        """Test TCP connection to NeoLeap device on port 7000."""
        self.ensure_one()
        if self.use_payment_terminal != 'mada_iot':
            raise UserError(_('This action is only available for Mada Terminal (IoT).'))

        if not self.neoleap_ip:
            raise UserError(_('Please enter the NeoLeap IP address first.'))

        ip   = self.neoleap_ip.strip()
        port = 7000

        try:
            sock = socket.create_connection((ip, port), timeout=5)
            sock.close()
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Connection Successful ✅'),
                    'message': _('Successfully connected to NeoLeap at %s:%s') % (ip, port),
                    'type': 'success',
                    'sticky': False,
                },
            }
        except (socket.timeout, ConnectionRefusedError, OSError) as e:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Connection Failed ❌'),
                    'message': _('Could not connect to NeoLeap at %s:%s — %s') % (ip, port, str(e)),
                    'type': 'danger',
                    'sticky': True,
                },
            }
