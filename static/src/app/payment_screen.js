/** @odoo-module */

import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";

patch(PaymentScreen.prototype, {

    // ── Send payment ─────────────────────────────────────────────────────────

    async sendPaymentRequest(line) {
        if (line.payment_method_id?.use_payment_terminal !== 'mada_iot') {
            return super.sendPaymentRequest(line);
        }

        this.pos.paymentTerminalInProgress = true;
        this.numberBuffer.capture();
        this.paymentLines.forEach((pl) => { pl.can_be_reversed = false; });

        let success = false;
        try {
            success = await line.pay();
        } catch {
            line.set_payment_status('retry');
        }

        this.pos.paymentTerminalInProgress = false;

        if (
            success &&
            this.currentOrder.is_paid() &&
            this.pos.config.auto_validate_terminal_payment
        ) {
            this.validateOrder(false);
        }

        return success;
    },

    // ── Delete payment line ───────────────────────────────────────────────────

    deletePaymentLine(uuid) {
        const line = this.paymentLines.find((l) => l.uuid === uuid);

        if (line?.payment_method_id?.use_payment_terminal !== 'mada_iot') {
            return super.deletePaymentLine(uuid);
        }

        const status = line.get_payment_status();

        if (
            ['waiting', 'waitingCard', 'timeout'].includes(status) &&
            line.payment_method_id.payment_terminal
        ) {
            line.set_payment_status('waitingCancel');
            line.payment_method_id.payment_terminal
                .send_payment_cancel(this.currentOrder, uuid)
                .then(() => {
                    this.currentOrder.remove_paymentline(line);
                    this.numberBuffer.reset();
                });
        } else if (status !== 'waitingCancel') {
            this.currentOrder.remove_paymentline(line);
            this.numberBuffer.reset();
        }
    },

    // ── Manual payment (approval code fallback) ───────────────────────────────

    async handleManualMadaPayment(uuid) {
        const line = this.paymentLines.find((l) => l.uuid === uuid);
        if (!line) return;

        const terminal = line.payment_method_id?.payment_terminal;
        if (terminal?.manualPayment) {
            await terminal.manualPayment(uuid);
        }
    },
});
