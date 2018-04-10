# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
import odoo.addons.decimal_precision as dp
from odoo.tools import float_compare
from odoo.exceptions import UserError


class PosOrder(models.Model):
    _inherit = 'pos.order'

    simplified_invoice = fields.Char('Simplified invoice', copy=False)

    @api.model
    def simplified_limit_check(self, pos_order):
        limit = self.env['pos.session'].browse(
            pos_order['pos_session_id']).config_id.simplified_invoice_limit
        precision_digits = dp.get_precision('Account')(self.env.cr)[1]
        # -1 or 0: amount_total <= limit, simplified
        #       1: amount_total > limit, can not be simplified
        return float_compare(pos_order['amount_total'], limit,
                             precision_digits=precision_digits) < 0

    @api.model
    def _process_order(self, pos_order):
        order = super(PosOrder, self)._process_order(pos_order)
        simplified = self.simplified_limit_check(pos_order)
        if simplified:
            config = order.session_id.config_id
            if config.simple_invoice_prefix:
                config.set_next_simple_invoice_number(
                    pos_order.get('simplified_invoice',
                                  config.simple_invoice_prefix + '1'))
                order.write({
                    'simplified_invoice': pos_order.get(
                        'simplified_invoice', ''),
                })
            else:
                raise UserError(_('You need to define a simplified invoice '
                                  'prefix.'))
        return order
