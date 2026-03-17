# -*- coding: utf-8 -*-
import json
import logging
import threading

_logger = logging.getLogger(__name__)

try:
    from odoo.addons.hw_drivers.driver import Driver
    from odoo.addons.hw_drivers.iot_handlers.interfaces.Interface import Interface
    HAS_IOT = True
except ImportError:
    HAS_IOT = False
    _logger.info('ia_mada_iot: hw_drivers not available — IoT handler skipped.')

if HAS_IOT:
    try:
        import websocket
        HAS_WEBSOCKET = True
    except ImportError:
        HAS_WEBSOCKET = False
        _logger.warning('ia_mada_iot: websocket-client not installed. Run: pip3 install websocket-client')

    STATUS_APPROVED  = '00'
    STATUS_DECLINED  = '01'
    STATUS_CANCELLED = '11'
    DEFAULT_PORT     = 7000

    class MadaDriver(Driver):
        """
        IoT driver running on Raspberry Pi.
        Connects to NeoLeap via WebSocket using IP from Odoo payment method config.
        """
        connection_type = 'mada'

        def __init__(self, identifier, device):
            super().__init__(identifier, device)
            self.device_type       = 'payment'
            self.device_name       = 'Mada Terminal (NeoLeap)'
            self.device_identifier = identifier
            self._lock             = threading.Lock()

        @classmethod
        def supported(cls, device):
            return device.get('type') == 'mada'

        def action(self, data):
            act = data.get('action')
            _logger.info('MadaDriver.action: %s | data: %s', act, data)

            if act == 'pay':
                return self._send_payment(
                    amount    = data.get('amount', '0.00'),
                    order_id  = data.get('order_id', ''),
                    neoleap_ip= data.get('neoleap_ip', ''),
                )
            elif act == 'cancel':
                return self._send_cancel(data.get('neoleap_ip', ''))
            else:
                return self._error('Unknown action: %s' % act)

        def _get_ws_url(self, neoleap_ip):
            """Build WebSocket URL from IP. Falls back to localhost if not provided."""
            ip = (neoleap_ip or '').strip()
            if not ip:
                _logger.warning('MadaDriver: no NeoLeap IP provided, falling back to localhost')
                ip = 'localhost'
            return 'ws://%s:%d' % (ip, DEFAULT_PORT)

        def _send_payment(self, amount, order_id, neoleap_ip):
            if not HAS_WEBSOCKET:
                return self._error(
                    'websocket-client is not installed. Run: pip3 install websocket-client'
                )

            url    = self._get_ws_url(neoleap_ip)
            result = self._error('No response received from Mada terminal.')
            event  = threading.Event()
            state  = {'ready': False}

            def on_open(ws):
                _logger.info('MadaDriver: connected to %s — sending CHECK_STATUS', url)
                ws.send(json.dumps({'Command': 'CHECK_STATUS'}))

            def on_message(ws, message):
                nonlocal result
                _logger.debug('MadaDriver: received — %s', message)
                try:
                    data = json.loads(message)
                except json.JSONDecodeError as exc:
                    result = self._error('JSON parse error: %s' % exc)
                    ws.close(); event.set(); return

                event_name = data.get('EventName', '')

                if event_name == 'TERMINAL_STATUS':
                    if data.get('TerminalStatus') == 'READY':
                        state['ready'] = True
                        _logger.info('MadaDriver: terminal READY — sending SALE amount=%s', amount)
                        ws.send(json.dumps({
                            'Command'       : 'SALE',
                            'Amount'        : str(amount),
                            'AdditionalData': str(order_id),
                        }))
                    else:
                        result = self._error(
                            'Terminal is busy (status: %s). Please try again.' % data.get('TerminalStatus')
                        )
                        ws.close(); event.set()

                elif event_name == 'TERMINAL_RESPONSE':
                    result = self._parse_response(data)
                    ws.close(); event.set()

            def on_error(ws, error):
                nonlocal result
                _logger.error('MadaDriver: WebSocket error — %s', error)
                result = self._error(str(error))
                event.set()

            def on_close(ws, code, msg):
                _logger.info('MadaDriver: WebSocket closed (code=%s)', code)
                event.set()

            with self._lock:
                try:
                    ws = websocket.WebSocketApp(
                        url,
                        on_open    = on_open,
                        on_message = on_message,
                        on_error   = on_error,
                        on_close   = on_close,
                    )
                    t = threading.Thread(target=ws.run_forever)
                    t.daemon = True
                    t.start()

                    if not event.wait(timeout=90):
                        ws.close()
                        result = self._error('Connection to Mada terminal timed out (90 seconds).')
                except Exception as exc:
                    _logger.exception('MadaDriver: unexpected error')
                    result = self._error(str(exc))

            return result

        def _send_cancel(self, neoleap_ip):
            if not HAS_WEBSOCKET:
                return self._error('websocket-client is not installed.')
            url = self._get_ws_url(neoleap_ip)
            try:
                ws = websocket.create_connection(url, timeout=10)
                ws.send(json.dumps({'Command': 'CANCEL'}))
                ws.close()
                return {'success': True}
            except Exception as exc:
                return self._error(str(exc))

        def _parse_response(self, data):
            json_result = data.get('JsonResult', {})
            status_code = json_result.get('StatusCode', '')

            if status_code == STATUS_APPROVED:
                return {
                    'success'      : True,
                    'transactionId': json_result.get('ECRReferenceNumber', ''),
                    'authCode'     : json_result.get('TransactionAuthCode', ''),
                    'cardType'     : json_result.get('CardType', ''),
                    'statusCode'   : status_code,
                }
            elif status_code == STATUS_DECLINED:
                return self._error('Transaction declined by the bank.', status_code)
            elif status_code == STATUS_CANCELLED:
                return {'success': False, 'cancelled': True,
                        'errorMsg': 'Transaction cancelled.', 'statusCode': status_code}
            else:
                return self._error('Unexpected response (StatusCode: %s).' % status_code, status_code)

        @staticmethod
        def _error(msg, status_code=''):
            return {'success': False, 'errorMsg': msg, 'statusCode': status_code}


    class MadaInterface(Interface):
        """Registers Mada devices on IoT Box startup — one per configured payment method."""
        _loop_delay     = 0
        connection_type = 'mada'

        def get_devices(self):
            """
            Returns one mada device per payment method that has mada_iot configured.
            Each device carries the neoleap_ip so MadaDriver can connect to the right terminal.
            """
            devices = {}
            try:
                from odoo.addons.hw_drivers.tools import helpers
                db_url = helpers.get_odoo_server_url()
                if not db_url:
                    return devices

                import requests
                resp = requests.get(
                    '%s/web/dataset/call_kw' % db_url,
                    json={
                        'jsonrpc': '2.0', 'method': 'call', 'id': 1,
                        'params': {
                            'model' : 'pos.payment.method',
                            'method': 'search_read',
                            'args'  : [[['use_payment_terminal', '=', 'mada_iot']]],
                            'kwargs': {'fields': ['id', 'name', 'neoleap_ip']},
                        }
                    },
                    timeout=10
                )
                methods = resp.json().get('result', [])
                for pm in methods:
                    identifier = 'mada_%s' % pm['id']
                    devices[identifier] = {
                        'type'      : 'mada',
                        'name'      : 'Mada — %s' % pm.get('name', ''),
                        'neoleap_ip': pm.get('neoleap_ip', ''),
                    }
            except Exception as exc:
                _logger.warning('MadaInterface.get_devices failed: %s', exc)
                # Fallback — single device using localhost
                devices['mada_neoleap'] = {
                    'type'      : 'mada',
                    'name'      : 'Mada Terminal (NeoLeap)',
                    'neoleap_ip': '',
                }
            return devices
