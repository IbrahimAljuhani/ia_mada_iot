/** @odoo-module */

import { PaymentMada } from "./payment_mada";
import { register_payment_method } from "@point_of_sale/app/store/pos_store";

register_payment_method("mada_iot", PaymentMada);
