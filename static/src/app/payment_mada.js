/** @odoo-module */

import { PaymentInterface } from "@point_of_sale/app/payment/payment_interface";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { TextInputPopup } from "@point_of_sale/app/utils/input_popups/text_input_popup";

/**
 * PaymentMada
 * -----------
 * Handles Mada payment via IoT Box (Raspberry Pi) → NeoLeap WebSocket.
 *
 * Flow:
 *   POS JS  →  IoT device.action('pay')
 *           →  Pi opens ws://localhost:7000
 *           →  CHECK_STATUS → SALE
 *           →  result callback → resolve promise
 *
 * Bilingual: Arabic for ar_* users, English for all others.
 */
export class PaymentMada extends PaymentInterface {

    setup(pos, payment_method) {
        super.setup(...arguments);
        this.dialog = this.env.services.dialog;
    }

    // ── Overrides ────────────────────────────────────────────────────────────

    send_payment_request(uuid) {
        super.send_payment_request(uuid);
        return this._madaPay(uuid);
    }

    send_payment_cancel(order, uuid) {
        super.send_payment_cancel(order, uuid);
        return this._madaCancel(uuid);
    }

    close() {}

    // ── Language helper ──────────────────────────────────────────────────────

    /**
     * Returns Arabic text for Arabic users, English for others.
     * @param {string} ar - Arabic text
     * @param {string} en - English text
     */
    _t(ar, en) {
        const lang = this.env.services.user?.lang || 'en_US';
        return lang.startsWith('ar') ? ar : en;
    }

    _title() {
        return this._t('جهاز مدى', 'Mada Terminal');
    }

    // ── Helpers ──────────────────────────────────────────────────────────────

    _getIotDevice() {
        const proxies = this.pos.iot_device_proxies || [];
        return proxies.find(
            (d) => d.identifier === 'mada_neoleap' || d.device_type === 'payment'
        ) || null;
    }

    _getPendingLine() {
        return this.pos.getPendingPaymentLine('mada_iot');
    }

    // ── Payment flow ─────────────────────────────────────────────────────────

    async _madaPay(uuid) {
        const order = this.pos.get_order();
        const line  = order.payment_ids.find((l) => l.uuid === uuid);
        if (!line) return false;

        const device = this._getIotDevice();
        if (!device) {
            this._showError(
                this._t(
                    'جهاز مدى غير متصل. تأكد من تشغيل IoT Box وأن تطبيق NeoLeap مفتوح على الجهاز.',
                    'Mada terminal is not connected. Make sure the IoT Box is running and NeoLeap is open on the terminal.'
                )
            );
            line.set_payment_status('retry');
            return false;
        }

        const amount     = line.amount.toFixed(2);
        const orderId    = order.uid || '';
        const neoleapIp  = this.payment_method.neoleap_ip || '';
        line.set_payment_status('waitingCard');

        return new Promise((resolve) => {
            const timer = setTimeout(() => {
                this._showError(
                    this._t(
                        'انتهت مهلة الاتصال بجهاز مدى. يرجى المحاولة مرة أخرى.',
                        'Connection to Mada terminal timed out. Please try again.'
                    )
                );
                line.set_payment_status('retry');
                resolve(false);
            }, 95_000);

            device.action(
                { action: 'pay', amount, order_id: orderId, neoleap_ip: neoleapIp },
                (result) => {
                    clearTimeout(timer);
                    this._handleResult(line, result, resolve);
                }
            );
        });
    }

    _handleResult(line, result, resolve) {
        if (!result) {
            this._showError(
                this._t(
                    'لم يصل أي رد من جهاز مدى.',
                    'No response received from Mada terminal.'
                )
            );
            line.set_payment_status('retry');
            return resolve(false);
        }

        if (result.success) {
            if (result.transactionId) line.transaction_id = result.transactionId;
            if (result.authCode)      line.card_type      = result.authCode;
            return resolve(true);
        }

        // Cancelled by customer — silent retry
        if (result.cancelled) {
            line.set_payment_status('retry');
            return resolve(false);
        }

        // Bank decline
        if (result.statusCode === '01') {
            this._showError(
                this._t('رفضت البنك البطاقة.', 'Transaction declined by the bank.')
            );
            line.set_payment_status('retry');
            return resolve(false);
        }

        // All other failures
        const msg = result.errorMsg || this._t(
            'فشلت عملية الدفع. يرجى المحاولة مرة أخرى.',
            'Payment failed. Please try again.'
        );
        this._showError(msg);
        line.set_payment_status('retry');
        return resolve(false);
    }

    async _madaCancel(uuid) {
        const device = this._getIotDevice();
        if (device) {
            try {
                await new Promise((resolve) => {
                    device.action({ action: 'cancel', neoleap_ip: this.payment_method.neoleap_ip || '' }, resolve);
                });
            } catch {
                // Cancel failure should not block UI
            }
        }
        return true;
    }

    // ── Manual payment fallback ──────────────────────────────────────────────

    async manualPayment(uuid) {
        const order = this.pos.get_order();
        const line  = order.payment_ids.find((l) => l.uuid === uuid);
        if (!line) return;

        const { confirmed, inputValue } = await new Promise((resolve) => {
            this.dialog.add(TextInputPopup, {
                title      : this._t('أدخل رقم الموافقة', 'Enter Approval Code'),
                placeholder: this._t('6 أحرف على الأقل', 'Minimum 6 characters'),
                getPayload : (val) => resolve({ confirmed: true,  inputValue: val }),
                close      : ()   => resolve({ confirmed: false, inputValue: ''  }),
            });
        });

        if (!confirmed) return;

        if (!inputValue || inputValue.trim().length < 6) {
            this._showError(
                this._t(
                    'يجب أن يكون رقم الموافقة 6 أحرف على الأقل.',
                    'Approval code must be at least 6 characters.'
                )
            );
            return;
        }

        line.transaction_id = inputValue.trim();
        line.set_payment_status('force_done');
    }

    // ── UI ───────────────────────────────────────────────────────────────────

    _showError(msg) {
        this.dialog.add(AlertDialog, {
            title: this._title(),
            body : msg,
        });
    }
}
