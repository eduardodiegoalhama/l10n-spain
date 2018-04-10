/* Copyright 2016 David Gómez Quilón <david.gomez@aselcis.com>
   License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
*/

odoo.define('l10n_es_pos.models', function (require) {
    "use strict";

    var models = require('point_of_sale.models');


    var pos_super = models.PosModel.prototype;
    models.PosModel = models.PosModel.extend({
        initialize: function (attributes, options) {
            pos_super.initialize.apply(this, arguments);
            this.pushed_simple_invoices = [];
            return this;
        },
        after_load_server_data: function () {
            ++this.config.simple_invoice_number;
            return pos_super.after_load_server_data.apply(this, arguments);
        },
        get_simple_inv_next_number: function () {
            if (this.pushed_simple_invoices.indexOf(this.config.simple_invoice_number) > -1) {
                ++this.config.simple_invoice_number;
            }
            return this.config.simple_invoice_prefix+this.get_padding_simple_inv(this.config.simple_invoice_number);
        },
        get_padding_simple_inv: function (number) {
            var diff = this.config.simple_invoice_padding - number.toString().length;
            var result = '';
            if (diff <= 0) {
                result = number;
            } else {
                for (var i = 0; i < diff; i++) {
                    result += '0';
                }
                result += number;
            }
            return result;
        },
        push_simple_invoice: function (order) {
            if (this.pushed_simple_invoices.indexOf(order.data.simplified_invoice) === -1) {
                this.pushed_simple_invoices.push(order.data.simplified_invoice);
                ++this.config.simple_invoice_number;
            }
        },
        _flush_orders: function (orders, options) {
            var self = this;
            // Save pushed orders numbers
            _.each(orders, function (order) {
                if (!order.data.to_invoice) {
                    self.push_simple_invoice(order);
                }
            });
            return pos_super._flush_orders.apply(this, arguments);
        }
    });

    var order_super = models.Order.prototype;
    models.Order = models.Order.extend({
        set_simple_inv_number: function () {
            this.simplified_invoice = this.pos.get_simple_inv_next_number();
        },
        init_from_JSON: function (json) {
            order_super.init_from_JSON.apply(this, arguments);
            this.to_invoice = json.to_invoice;
            this.simplified_invoice = json.simplified_invoice;
        },
        export_as_JSON: function () {
            var res = order_super.export_as_JSON.apply(this, arguments);
            res.to_invoice = this.is_to_invoice();
            if (!res.to_invoice) {
                res.simplified_invoice = this.simplified_invoice;
            }
            return res;
        }
    });

    models.load_fields('res.company', ['street', 'city', 'state_id', 'zip']);

});
